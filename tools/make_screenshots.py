#!/usr/bin/env python3
"""Captures d'écran du prompteur pour la documentation (outil de développement).

Fabrique un morceau de démonstration entièrement fictif (« Demo Song » : structure, accords,
paroles et batterie inventés) et un concert fictif de trois morceaux, les sert avec la page du prompteur
sur un faux serveur REAPER (/_/TRANSPORT renvoie une position fixe ; instruments, Régie et répétition
simulés), puis photographie chaque vue avec Playwright (Chromium) : rôles, tablette, concert, Régie (PIN 1234).

    pip install playwright && playwright install chromium
    python3 tools/make_screenshots.py [--out docs/images] [--check]

--check : vérifie seulement que la page s'affiche sans erreur console (FR et EN, tous les rôles).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reacue_mcp.i18n import localize_section, section_color, section_kind  # noqa: E402

PAGE = ROOT / "reacue_mcp" / "web" / "prompteur.html"

BPM = 112.0
BPB = 4
COUNT_IN = 2
# structure (noms internes FR, traduits pour la version anglaise)
STRUCT = [("Intro", 1, 8), ("Couplet 1", 9, 24), ("Pré-refrain 1", 25, 28), ("Refrain 1", 29, 44),
          ("Couplet 2", 45, 60), ("Pré-refrain 2", 61, 64), ("Refrain 2", 65, 80), ("Pont", 81, 88),
          ("Solo", 89, 96), ("Refrain 3", 97, 112), ("Outro", 113, 120)]
N_BARS = 120
CHORDS = {"intro": ["Am", "F", "C", "G"], "verse": ["Am", "F", "C", "G"], "prechorus": ["Dm", "Em", "F", "G"],
          "chorus": ["C", "G", "Am", "F"], "bridge": ["F", "G", "Em", "Am"], "solo": ["Am", "F", "C", "G"],
          "outro": ["Am", "F", "C", "G"]}

# paroles 100 % inventées pour cette démonstration
LYRICS = {
    "fr": {
        "verse": ["La ville s'allume au bout du quai", "On compte les pas jusqu'au dernier train",
                  "Les néons fredonnent un air oublié", "Et la nuit nous tend la main",
                  "Les vitrines dorment, le pavé luit", "Un vieux refrain tourne dans nos têtes",
                  "On garde le tempo jusqu'à minuit", "La rue entière bat la mesure"],
        "prechorus": ["Encore un tour, encore un soir"],
        "chorus": ["Allume le son, laisse-nous chanter", "Quatre temps pour tout recommencer",
                   "Allume le son, jusqu'au matin", "On tient la mesure, on tient le refrain"],
    },
    "en": {
        "verse": ["The city hums along the empty pier", "We count the steps until the final train",
                  "Neon signs are singing something we can't hear", "And the night calls out our name",
                  "Shop windows sleep, the pavement gleams", "An old refrain keeps spinning round",
                  "We hold the tempo past midnight", "The whole street keeps the time"],
        "prechorus": ["One more round, one more night"],
        "chorus": ["Turn the sound up, let the whole room sing", "Four on the floor and we start again",
                   "Turn the sound up till the morning light", "Hold the tempo, hold the line tonight"],
    },
}


def bar_len(bpm: float = BPM) -> float:
    return 60.0 * BPB / bpm


def bar_time(bar: int, pos: float = 0.0, bpm: float = BPM, t0: float = 0.0) -> float:
    """Mesure 1-based (≤ 0 : count-in) -> secondes sur la timeline (t0 : début du morceau dans un concert)."""
    return round(t0 + (bar - 1 + COUNT_IN + pos / BPB) * bar_len(bpm), 4)


def _drums(lang: str) -> dict:
    hh8 = list(range(0, 16, 2))
    pats = {
        "A": {"hits": {"HH": hh8, "SD": [4, 12], "BD": [0, 7, 8]}, "accents": {"HH": [0, 4, 8, 12]}},
        "B": {"hits": {"RD": hh8, "SD": [4, 12], "BD": [0, 6, 8, 10]}, "accents": {}},
        "C": {"hits": {"HH": list(range(16)), "SD": [12], "BD": [0, 8]}, "accents": {}},
    }
    use = {"A": ["verse", "intro", "outro"], "B": ["chorus", "solo"], "C": ["prechorus"]}
    for k, p in pats.items():
        names = []
        for kind in use[k]:
            fr = {"verse": "couplet", "intro": "intro", "outro": "outro", "chorus": "refrain", "solo": "solo",
                  "prechorus": "pré-refrain"}[kind]
            names.append(fr if lang == "fr" else {"verse": "verse", "chorus": "chorus", "prechorus": "pre-chorus"}.get(kind, kind))
        p["name"] = f"Groove {k} — " + " / ".join(names)
    groove = {"verse": "A", "intro": "A", "outro": "A", "chorus": "B", "solo": "B", "prechorus": "C", "bridge": "A"}
    bars = []
    for name, a, b in STRUCT:
        kind = section_kind(name)
        for bar in range(a, b + 1):
            if kind == "bridge" and bar <= a + 3:
                bars.append({"bar": bar, "pattern": None, "rest": True})
                continue
            e = {"bar": bar, "pattern": groove[kind], "fill": False, "crash": bar == a and kind in ("chorus", "solo"),
                 "hits": dict(pats[groove[kind]]["hits"])}
            if bar == b and bar != N_BARS:
                e.update(pattern=None, fill=True, hits={"SD": [8, 10, 12, 13], "T1": [9, 14], "FT": [11, 15],
                                                        "BD": [0, 4], "HH": [0, 2, 4, 6]})
            bars.append(e)
    return {"steps": 16, "lanes": ["CR", "HH", "RD", "SD", "T1", "T2", "FT", "BD"], "patterns": pats, "bars": bars,
            "version": "demo"}


def demo_song(lang: str, title: str = "Demo Song", bpm: float = BPM, t0: float = 0.0) -> dict:
    secs = []
    for name, a, b in STRUCT:
        nm = localize_section(name, lang)
        secs.append({"name": nm, "type": section_kind(nm), "group": "", "start_bar": a, "end_bar": b,
                     "color": "#%02x%02x%02x" % section_color(nm)})
    chords = []
    for name, a, b in STRUCT:
        prog = CHORDS[section_kind(name)]
        for bar in range(a, b + 1):
            c = prog[(bar - a) % len(prog)]
            entry = [{"beat": 1, "chord": c, "bass": c.rstrip("m"), "confidence": 0.9}]
            if section_kind(name) == "prechorus" and (bar - a) % 4 == 3:
                entry.append({"beat": 3, "chord": "E", "bass": "E", "confidence": 0.7})
            chords.append({"bar": bar, "chords": entry})
    act = {"drums": [], "bass": [], "guitars": [], "lead_guitar": [], "vocals": []}
    for bar in range(1, N_BARS + 1):
        kind = section_kind(next(n for n, a, b in STRUCT if a <= bar <= b))
        act["drums"].append(0 if 81 <= bar <= 84 else 1)
        act["bass"].append(0 if bar <= 4 else 1)
        act["guitars"].append(0 if 81 <= bar <= 84 else 1)
        act["lead_guitar"].append(1 if kind in ("solo", "intro") else 0)
        act["vocals"].append(1 if kind in ("verse", "prechorus", "chorus") else 0)
    lyrics, i = [], 0
    L = LYRICS[lang]
    for name, a, b in STRUCT:
        kind = section_kind(name)
        lines = L.get(kind)
        if not lines:
            continue
        step = 2 if kind != "prechorus" else 4
        for k, bar in enumerate(range(a, b + 1, step)):
            text = lines[k % len(lines)]
            ta, tb = bar_time(bar, 0.5, bpm, t0), bar_time(bar + 1, 3.0, bpm, t0)
            lyrics.append({"i": i, "line": i + 1, "bar": bar, "beat": 0, "pos": 0.5, "t": ta, "end": tb,
                           "text": text, "confidence": 0.9, "copy": False})
            i += 1
    song = {
        "version": 1, "language": lang, "title": title, "bpm": bpm, "beats_per_bar": BPB,
        "tempo_mode": "constant", "count_in_bars": COUNT_IN, "n_bars": N_BARS,
        "bar_times": [bar_time(k, 0.0, bpm, t0) for k in range(-COUNT_IN + 1, N_BARS + 2)],
        "key": {"chord": "Am", "fr": "La mineur", "en": "A minor"},
        "sections": secs, "activity": act, "roles": sorted(act), "chords": chords, "lyrics": lyrics,
        "drums": _drums(lang),
    }
    song["id"] = hashlib.md5(json.dumps(song, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return song


# concert fictif : trois morceaux inventés à la suite sur la même timeline, 4 s de blanc entre eux
CONCERT = [("Demo Song", 112.0), ("Second Demo", 150.0), ("Third Demo", 100.0)]
GAP = 4.0


def demo_concert(lang: str) -> dict:
    songs, t = [], 0.0
    for k, (title, bpm) in enumerate(CONCERT):
        s = demo_song(lang, title, bpm, t)
        stop = s["bar_times"][-1]
        s.update({"n": k + 1, "start_t": t, "stop_t": stop, "next_t": stop + GAP,
                  "next_title": CONCERT[k + 1][0] if k + 1 < len(CONCERT) else None})
        songs.append(s)
        t = stop + GAP
    name = "Concert de démo" if lang == "fr" else "Demo concert"
    data = {"version": 1, "language": lang, "concert": {"name": name, "n": len(songs), "titles": [x[0] for x in CONCERT]},
            "songs": songs}
    data["id"] = hashlib.md5(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return data


# --------------------------------------------------------------------------- faux REAPER
class FakeReaper(SimpleHTTPRequestHandler):
    song: dict = {}
    pos: float = 0.0
    play: int = 0
    mix: str = ""
    rehearsal: str = ""

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/_/TRANSPORT"):           # + EXTSTATE ReaCue : instruments, Régie
            body = f"TRANSPORT\t{self.play}\t{self.pos:.4f}\t0\t1.1.00\t1.1.00\n"
            for key, val in (("mix", self.mix), ("remote_alive", str(int(time.time() * 2))),
                             ("remote_ack", ""), ("rehearsal", self.rehearsal)):
                if f"GET/EXTSTATE/ReaCue/{key}" in path:
                    body += f"EXTSTATE\tReaCue\t{key}\t{val}\n"
            body, ctype = body.encode("utf-8"), "text/plain"
        elif path == "/reacue_song.json":
            body, ctype = json.dumps(self.song, ensure_ascii=False).encode("utf-8"), "application/json"
        elif path in ("/", "/prompteur.html"):
            body, ctype = PAGE.read_bytes(), "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def serve():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(FakeReaper))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


# position affichée pour chaque vue : (mesure, temps 0-based)
VIEWS = {
    "drums": (21, 1.2),        # couplet 1 : groove, pré-refrain bientôt
    "bass": (31, 2.3),         # refrain 1
    "guitars": (27, 2.6),      # pré-refrain : changement d'accord imminent
    "vocals": (11, 1.6),       # couplet 1, ligne en cours
    "lead_guitar": (93, 1.0),  # solo
    "all": (30, 0.5),
}
TABLET_VIEWS = {"drums": (24, 1.2), "vocals": (30, 1.5)}   # fill avant le pré-refrain ; refrain 1
PHONE = {"width": 390, "height": 844}
TABLET = {"width": 1180, "height": 820}


def run(out: Path | None, check_only: bool) -> list[str]:
    from playwright.sync_api import sync_playwright
    srv, base = serve()
    errors, shots = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for lang in ("fr", "en"):
                FakeReaper.song = demo_song(lang)
                plan = [(r, PHONE, "phone") for r in VIEWS] + [("drums", TABLET, "tablet"), ("vocals", TABLET, "tablet")]
                for role, vp, kind in plan:
                    bar, beat = (TABLET_VIEWS if kind == "tablet" else VIEWS)[role]
                    FakeReaper.pos = bar_time(bar, beat)
                    ctx = browser.new_context(viewport=vp, device_scale_factor=2 if kind == "phone" else 1.5,
                                              locale="fr-FR" if lang == "fr" else "en-US")
                    page = ctx.new_page()
                    page.on("console", lambda m, r=role, lg=lang: m.type == "error" and errors.append(f"{lg}/{r}: {m.text}"))
                    page.on("pageerror", lambda e, r=role, lg=lang: errors.append(f"{lg}/{r}: {e}"))
                    page.goto(f"{base}/prompteur.html?role={role}&lang={lang}")
                    page.wait_for_function("document.getElementById('nowName').textContent !== '—'", timeout=8000)
                    page.wait_for_timeout(600)
                    if out and not check_only and role in ("drums", "bass", "vocals", "guitars"):
                        f = out / f"prompter_{role}_{lang}{'_tablet' if kind == 'tablet' else ''}.png"
                        page.screenshot(path=str(f))
                        shots.append(f.name)
                    ctx.close()
            # mode concert (2e morceau, stem de la batterie coupé) et Régie (télécommande, PIN 1234)
            for lang in ("fr", "en"):
                data = demo_concert(lang)
                s2 = data["songs"][1]
                bt = lambda bar, beat=0.0: bar_time(bar, beat, s2["bpm"], s2["start_t"])
                FakeReaper.song = data
                FakeReaper.mix = "vocals=1,drums=0L,bass=1,guitars=1;;0;2"
                chorus = next(x for x in s2["sections"] if x["start_bar"] == 29)
                shots_c = [("drums", "concert", PHONE, bt(21, 1.2), 0, ""),
                           ("vocals", "concert_vocals", PHONE, bt(11, 1.6), 0, ""),
                           ("regie", "regie", PHONE, bt(31, 0.5), 1,
                            f"1|0.9|{bt(29):.3f}|{bt(45):.3f}|{chorus['name']}")]
                for role, name, vp, pos, play, reh in shots_c:
                    FakeReaper.pos, FakeReaper.play, FakeReaper.rehearsal = pos, play, reh
                    ctx = browser.new_context(viewport=vp, device_scale_factor=2, locale="fr-FR" if lang == "fr" else "en-US")
                    ctx.add_init_script("localStorage.setItem('reacue_pin', '1234')")
                    page = ctx.new_page()
                    page.on("console", lambda m, r=name, lg=lang: m.type == "error" and errors.append(f"{lg}/{r}: {m.text}"))
                    page.on("pageerror", lambda e, r=name, lg=lang: errors.append(f"{lg}/{r}: {e}"))
                    page.goto(f"{base}/prompteur.html?role={role}&lang={lang}")
                    sel = "rTitle" if role == "regie" else "nowName"
                    page.wait_for_function(f"document.getElementById('{sel}').textContent !== '—'", timeout=8000)
                    page.wait_for_timeout(900)
                    rank = page.text_content("#rRank" if role == "regie" else "#title") or ""
                    if "2" not in rank:
                        errors.append(f"{lang}/{name}: concert rank missing ({rank!r})")
                    if out and not check_only:
                        f = out / f"prompter_{name}_{lang}.png"
                        page.screenshot(path=str(f))
                        shots.append(f.name)
                        if role == "regie":           # bas de la Régie : sections, setlist
                            page.eval_on_selector("#regie", "e => e.scrollTop = e.scrollHeight")
                            page.wait_for_timeout(300)
                            f = out / f"prompter_regie2_{lang}.png"
                            page.screenshot(path=str(f))
                            shots.append(f.name)
                    ctx.close()
            FakeReaper.mix, FakeReaper.play, FakeReaper.rehearsal = "", 0, ""
            # bouton de langue : FR -> EN sans erreur, mémorisé
            ctx = browser.new_context(viewport=PHONE)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(f"toggle: {e}"))
            FakeReaper.song = demo_song("fr")
            page.goto(f"{base}/prompteur.html?role=bass")
            page.wait_for_function("document.getElementById('nowName').textContent !== '—'", timeout=8000)
            page.click("#langBtn")
            page.wait_for_timeout(300)
            if page.text_content("#nextK") != "Next":
                errors.append("toggle: language button did not switch to English")
            ctx.close()
            browser.close()
    finally:
        srv.shutdown()
    if errors:
        raise SystemExit("Erreurs dans la page :\n" + "\n".join(errors))
    return shots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "images"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    shots = run(out, args.check)
    print("OK, aucune erreur console." + (f" Captures : {', '.join(shots)}" if shots else ""))


if __name__ == "__main__":
    main()
