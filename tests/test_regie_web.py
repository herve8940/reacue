"""Régie (télécommande du concert) de bout en bout : la vraie page du prompteur dans Chromium headless,
un faux serveur web REAPER dont les commandes /_/ sont exécutées par la vraie bibliothèque Lua de la
fenêtre Concert (lupa). Français et anglais. Concert de démonstration fictif."""
import json
import threading
import time
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytest.importorskip("lupa")

import test_concert_lua as TL  # noqa: E402  (API REAPER simulée + concert de démonstration)

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "reacue_mcp" / "web"
PAGE = (WEB / "prompteur.html").read_text(encoding="utf-8")
CTYPES = {".css": "text/css", ".js": "application/javascript", ".woff2": "font/woff2"}

TXT = {
    "fr": {"pick": "Régie", "state_play": "Lecture", "state_stop": "Arrêt", "pin4": "4 chiffres.",
           "bad": "incorrect", "again": "Encore ?", "closed": "Ouvre la fenêtre ReaCue sur",
           "noanswer": "Pas de réponse", "pin_foot": "Code PIN : 2468", "reh": "Répétition", "reh_on": "Répétition ✓",
           "banner": "Répétition · boucle : ", "loopoff": "Boucle off", "drums": "Batterie", "vocals": "Chant",
           "cut": "coupé", "on": "joué", "solo": "solo", "hear": "Tout entendre",
           "stem_cut": "ton stem est coupé", "stem_on": "ton stem est joué"},
    "en": {"pick": "Stage control", "state_play": "Playing", "state_stop": "Stopped", "pin4": "4 digits.",
           "bad": "Wrong", "again": "Again?", "closed": "Open the ReaCue window",
           "noanswer": "No answer", "pin_foot": "PIN code: 2468", "reh": "Rehearsal", "reh_on": "Rehearsal ✓",
           "banner": "Rehearsal · loop: ", "loopoff": "Loop off", "drums": "Drums", "vocals": "Vocals",
           "cut": "muted", "on": "playing", "solo": "solo", "hear": "Hear everything",
           "stem_cut": "your stem is muted", "stem_on": "your stem is playing"},
}


class Fake:
    def __init__(self, concert, lang):
        self.L, self.g = TL.runtime(concert, lang=lang)
        self.M = TL.lib(self.L)
        self.C = self.M.load_concert()
        self.st = self.g.state
        self.M.set_remote_pin("2468")
        self.L.execute("""TRACKS = { {name="Chant"}, {name="Batterie"}, {name="Basse"}, {name="Guitares"},
                                     {name="CUES"}, {name="VOIX"}, {name="CLICK"} }""")
        self.alive = True
        self.log = []
        self.lock = threading.Lock()
        self.song = concert[0].prompter.read_text(encoding="utf-8")

    def handler(self):
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, body, ctype="text/plain"):
                b = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                path = self.path.split("?")[0]
                if path in ("/", "/prompteur.html"):
                    return self.send(PAGE, "text/html; charset=utf-8")
                if path == "/reacue_song.json":
                    return self.send(fake.song, "application/json")
                if path.startswith("/reacue_studio/") and ".." not in path:     # base commune (style, core.js, polices)
                    f = WEB / urllib.parse.unquote(path.lstrip("/"))
                    if f.is_file():
                        b = f.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", CTYPES.get(f.suffix, "application/octet-stream"))
                        self.send_header("Content-Length", str(len(b)))
                        self.end_headers()
                        self.wfile.write(b)
                        return
                if path.startswith("/_/"):
                    out, st = [], fake.st
                    with fake.lock:
                        for cmd in path[3:].split(";"):
                            fake.log.append(cmd)
                            if cmd == "TRANSPORT":
                                pos = st.pos if st.play == 1 else st.cursor
                                out.append(f"TRANSPORT\t{st.play}\t{pos:.6f}\t0\t0\t0")
                            elif cmd.startswith("SET/EXTSTATE/"):
                                _, _, sec, key, val = cmd.split("/", 4)
                                st.ext[urllib.parse.unquote(key)] = urllib.parse.unquote(val)
                            elif cmd.startswith("GET/EXTSTATE/"):
                                _, _, sec, key = cmd.split("/", 3)
                                out.append(f"EXTSTATE\t{sec}\t{key}\t{st.ext[key] or ''}")
                        if fake.alive:                    # « boucle defer » de la fenêtre Concert
                            st.t = time.time()
                            fake.M.remote_alive(st.t)
                            fake.M.poll_seen(st.t)
                            fake.M.remote_poll(fake.C)
                            fake.M.mix_tick(fake.C, st.t)
                        if st.play == 1:
                            st.pos = st.pos + 0.02
                    return self.send("\n".join(out) + "\n")
                self.send_response(404)
                self.end_headers()
        return H


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_regie_end_to_end(TL_concert, lang):
    from playwright.sync_api import sync_playwright
    res = TL_concert[0]
    tx = TXT[lang]
    fake = Fake(TL_concert, lang)
    st = fake.st
    srv = ThreadingHTTPServer(("127.0.0.1", 0), fake.handler())
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            try:
                br = p.chromium.launch()
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    pytest.skip("Chromium non installé")
                raise
            pg = br.new_context(viewport={"width": 390, "height": 844}, locale="fr-FR" if lang == "fr" else "en-US").new_page()
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errors.append(str(e)))
            st.cursor = res.songs[1]["bar1"] + 1.0
            pg.goto(f"http://127.0.0.1:{port}/prompteur.html?lang={lang}")
            pg.wait_for_timeout(600)
            assert pg.is_visible("#picker") and pg.is_visible(f"text={tx['pick']}")
            pg.click("#picker button[data-role=regie]")
            pg.wait_for_timeout(700)
            assert pg.is_visible("#regie") and not pg.is_visible("#now")
            assert pg.inner_text("#rTitle") == "Second Demo"
            assert pg.inner_text("#rRank") == "2 / 3"
            # 1re commande : PIN demandé ; trop court, faux, puis bon
            pg.click("#rPlay"); pg.wait_for_timeout(200)
            assert pg.is_visible("#pinBox")
            pg.fill("#pinIn", "12"); pg.click("#pinOk")
            assert pg.inner_text("#pinErr") == tx["pin4"]
            pg.fill("#pinIn", "1111"); pg.click("#pinOk"); pg.wait_for_timeout(700)
            assert st.play == 0 and pg.is_visible("#pinBox") and tx["bad"] in pg.inner_text("#pinErr")
            pg.fill("#pinIn", "2468"); pg.click("#pinOk"); pg.wait_for_timeout(700)
            assert st.play == 1 and pg.inner_text("#rState") == tx["state_play"]
            # Stop pendant la lecture : double appui
            pg.click("#rStop"); pg.wait_for_timeout(250)
            assert st.play == 1 and tx["again"] in pg.inner_text("#rStop")
            pg.click("#rStop"); pg.wait_for_timeout(600)
            assert st.play == 0 and pg.inner_text("#rState") == tx["state_stop"]
            # Suivant (à l'arrêt : un appui)
            pg.click("#rNext"); pg.wait_for_timeout(600)
            assert st.cursor == pytest.approx(res.songs[2]["start"], abs=1e-3)
            pg.wait_for_timeout(300)
            assert pg.inner_text("#rTitle") == "Third Demo"
            # setlist : morceau 1
            pg.click("#rList button[data-k='0']"); pg.wait_for_timeout(600)
            assert st.cursor == pytest.approx(0.0, abs=1e-3)
            # section pendant la lecture : saut immédiat
            pg.click("#rPlay"); pg.wait_for_timeout(500); assert st.play == 1
            names = [b.inner_text() for b in pg.query_selector_all("#rSecs button")]
            k = next(i for i, n in enumerate(names) if n.startswith("Chorus"))
            pg.click(f"#rSecs button[data-i='{k}']"); pg.wait_for_timeout(600)
            song1 = json.loads(fake.song)["songs"][0]
            exp = song1["bar_times"][song1["sections"][k]["start_bar"] - 1 + song1["count_in_bars"]]
            assert st.pos == pytest.approx(exp, abs=0.3) and st.play == 1
            pg.click("#rHome"); pg.wait_for_timeout(300)        # pendant la lecture : sans confirmation
            pg.wait_for_timeout(400)
            # instruments : mute (appui), solo (appui long), tout entendre
            pg.click("#rStop"); pg.click("#rStop"); pg.wait_for_timeout(600)
            assert st.play == 0
            mut = lambda n: next(t.mute or 0 for t in fake.g.TRACKS.values() if t.name == n)
            assert pg.is_visible("#rMix") and pg.inner_text("#rMixT").lower().startswith("instruments")
            drums = "#rMix button[data-r=drums]"
            assert tx["drums"] in pg.inner_text(drums) and tx["on"] in pg.inner_text(drums)
            pg.click(drums); pg.wait_for_timeout(700)
            assert mut("Batterie") == 1 and tx["cut"] in pg.inner_text(drums) and "cut" in pg.get_attribute(drums, "class")
            voc = "#rMix button[data-r=vocals]"
            pg.hover(voc); pg.mouse.down(); pg.wait_for_timeout(800); pg.mouse.up(); pg.wait_for_timeout(600)
            assert mut("Chant") == 0 and mut("Basse") == 1 and mut("Guitares") == 1
            assert tx["solo"] in pg.inner_text(voc)
            pg.click("#rHearAll"); pg.wait_for_timeout(700)
            assert {mut(n) for n in ("Chant", "Batterie", "Basse", "Guitares")} == {0}
            assert "on" in pg.get_attribute("#rHearAll", "class") and pg.inner_text("#rHearAll") == tx["hear"]
            pg.click("#rHearAll"); pg.wait_for_timeout(700)
            assert any("mute%7Cdrums%7C2468" in x or "mute|drums|2468" in x for x in fake.log)
            pg.click("#rHome"); pg.wait_for_timeout(300)
            # mode répétition : boucle sur une section (1 mesure avant), vitesse, boucle off, sortie
            assert pg.inner_text("#rRehBtn") == tx["reh"] and not pg.is_visible("#rLoopOff")
            pg.click("#rRehBtn"); pg.wait_for_timeout(700)
            assert fake.M.reh.on and pg.inner_text("#rRehBtn") == tx["reh_on"] and pg.is_visible("#rLoopOff")
            pg.click(f"#rSecs button[data-i='{k}']"); pg.wait_for_timeout(700)
            assert fake.M.reh.loop and fake.M.reh.loop.start == pytest.approx(exp, abs=0.05)
            assert st.play == 1 and st.pos < exp
            assert pg.inner_text("#rRehB").startswith(tx["banner"])
            assert "inloop" in pg.get_attribute(f"#rSecs button[data-i='{k}']", "class")
            pg.click("#rReh button[data-rate='0.8']"); pg.wait_for_timeout(600)
            assert st.rate == pytest.approx(0.8) and "80 %" in pg.inner_text("#rRehB")
            pg.click("#rLoopOff"); pg.wait_for_timeout(600)
            assert fake.M.reh.loop is None and fake.M.reh.on
            pg.click("#rRehBtn"); pg.wait_for_timeout(700)
            assert not fake.M.reh.on and st.rate == pytest.approx(1.0) and not pg.is_visible("#rLoopOff")
            assert any(x.startswith("SET/EXTSTATE/ReaCue/remote_seen/") for x in fake.log)
            # fenêtre Concert fermée -> message
            fake.alive = False
            st.ext["remote_alive"] = ""
            pg.wait_for_timeout(3600)
            assert tx["closed"] in pg.inner_text("#rWarn")
            pg.click("#rPlay"); pg.wait_for_timeout(3000)
            assert tx["noanswer"] in pg.inner_text("#rWarn")
            fake.alive = True
            # PIN mémorisé après rechargement ; autres rôles : aucune requête Régie
            pg.reload(); pg.wait_for_timeout(800)
            assert pg.is_visible("#regie") and tx["pin_foot"] in pg.inner_text("#rFootL")
            # musiciens : seulement l'état des stems (« ton stem est coupé / joué ») et la vitesse / transposition
            # (ReaCue/studio, lecture seule) ; vue générale : vitesse / transposition seulement ; jamais la Régie
            fake.M.mix_toggle(fake.C, "drums")
            for r in ["drums", "vocals", "all"]:
                pg.evaluate(f"localStorage.setItem('reacue_role','{r}')"); pg.reload(); pg.wait_for_timeout(900)
                assert not pg.is_visible("#regie")
                n0 = len(fake.log)
                pg.wait_for_timeout(400)
                got = {x for x in fake.log[n0:] if x.startswith(("GET/EXTSTATE", "SET/EXTSTATE"))}
                if r == "all":
                    assert got == {"GET/EXTSTATE/ReaCue/studio"}, got
                    assert not pg.is_visible("#stemNote")
                else:
                    assert got == {"GET/EXTSTATE/ReaCue/mix", "GET/EXTSTATE/ReaCue/studio"}, got
                    assert pg.inner_text("#stemNote") == (tx["stem_cut"] if r == "drums" else tx["stem_on"])
            br.close()
    finally:
        srv.shutdown()
    assert not errors, errors


@pytest.fixture(scope="module")
def TL_concert(tmp_path_factory):
    return TL.make_concert(tmp_path_factory.mktemp("regie"))
