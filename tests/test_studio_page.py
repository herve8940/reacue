"""Page ReaCue Studio (écran Travail) dans Chromium headless, sur le faux REAPER de tools/make_screenshots.py :
FR / EN sans erreur console, polices servies localement, commandes envoyées à l'API web native de REAPER
(mute, solo, volume, position, transport), « mon instrument » coupé, commandes ReaCue avec PIN (boucle,
rampe, transposition, export) et liens de téléchargement des exports."""
import json
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip("playwright")
sys.path.insert(0, str(ROOT / "tools"))


def _run(fn):
    import make_screenshots as M
    from playwright.sync_api import sync_playwright
    srv, base = M.serve()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                return fn(M, browser, base)
            finally:
                browser.close()
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium non installé")
        raise
    finally:
        srv.shutdown()


def _setup(M, lang="fr"):
    song = M.demo_song(lang)
    M.FakeReaper.song, M.FakeReaper.peaks, M.FakeReaper.tracks = song, M.demo_peaks(song), M.demo_tracks()
    M.FakeReaper.pos, M.FakeReaper.play, M.FakeReaper.log = M.bar_time(30, 1.1), 0, []
    M.FakeReaper.rehearsal, M.FakeReaper.studio, M.FakeReaper.export = "", "1.000|0|0|0|0.00|0.00", None
    return song


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_studio_renders_without_errors(lang):
    def go(M, browser, base):
        song = _setup(M, lang)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors, requests = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("request", lambda r: requests.append(r.url))
        page.goto(f"{base}/studio.html?lang={lang}")
        page.wait_for_function("document.querySelectorAll('.tv-row').length === 5", timeout=8000)
        page.wait_for_timeout(500)
        out = {
            "errors": errors, "requests": requests,
            "title": page.text_content("#title"), "nav": page.text_content("#nav"),
            "rows": page.locator(".tv-row .nm").all_text_contents(),
            "strips": page.locator(".tv-strip .sh").all_text_contents(),
            "secs": page.locator(".tv-sec").count(), "pos": page.text_content("#lcdPos"),
            "tempo": page.text_content("#lcdTempo"), "key": page.text_content("#lcdKey"),
            "tc": page.text_content("#lcdTc"),
            "fonts": page.evaluate("document.fonts.check('16px \"IBM Plex Mono\"') && document.fonts.check('700 22px \"Barlow Condensed\"')"),
            "canvas": page.evaluate("[...document.querySelectorAll('.tv-row canvas')].every(c => c.width > 100)"),
        }
        return out, song
    out, song = _run(go)
    assert not out["errors"], out["errors"]
    assert all(u.startswith("http://127.0.0.1") for u in out["requests"]), [u for u in out["requests"] if "127.0.0.1" not in u]
    assert out["title"] == "Demo Song"
    assert ("TRAVAIL" if lang == "fr" else "PRACTICE") in out["nav"]
    assert out["rows"] == ["Chant", "Batterie", "Basse", "Guitares", "Claviers"]
    assert out["strips"] == (["VOX", "DRM", "BAS", "GTR", "KEY", "ANN", "CLK"] if lang == "fr" else
                             ["VOX", "DRM", "BAS", "GTR", "KEY", "CUE", "CLK"])
    assert out["secs"] == len(song["sections"]) + 1                     # + count-in
    assert out["pos"] == "030.2.1" and out["tempo"] == "112.0" and out["key"] == "Am"
    assert out["tc"].startswith("01:01:0")                              # départ 01:00:00:00 + 67 s
    assert out["fonts"] and out["canvas"]


def test_studio_native_commands_and_me():
    def go(M, browser, base):
        _setup(M)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script("localStorage.setItem('reacue_studio_me', 'Basse'); localStorage.setItem('reacue_pin', '1234')")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{base}/studio.html?lang=fr")
        page.wait_for_function("document.querySelectorAll('.tv-row').length === 5", timeout=8000)
        page.wait_for_timeout(400)
        me_label = page.locator(".tv-row .nm").nth(2).text_content()
        page.locator(".tv-row .rc-ms.m").nth(0).click()                    # mute Chant
        page.locator(".tv-row .rc-ms.s").nth(1).click()                    # solo Batterie
        page.locator(".tv-strip .tv-rail").nth(4).dblclick()               # Claviers à 0 dB
        page.click(".tv-sec[data-i='3']")                                # aller au Refrain 1
        page.click("#bPlay")
        page.click("#cClick")                                            # CLICK OFF
        page.wait_for_timeout(500)
        page.click("#trUp")                                              # transposition (commande ReaCue)
        page.wait_for_timeout(400)
        page.dblclick(".tv-sec[data-i='3']")                             # boucler la section
        page.wait_for_timeout(600)
        log = list(M.FakeReaper.log)
        chip = page.text_content("#cClick")
        ctx.close()
        return log, me_label, errors, M.FakeReaper.tracks
    log, me_label, errors, tracks = _run(go)
    assert not errors, errors
    assert me_label == "Basse · MOI"
    assert "SET/TRACK/3/MUTE/1" in log                                  # « mon instrument » coupé automatiquement
    assert "SET/TRACK/1/MUTE/1" in log and "SET/TRACK/2/SOLO/1" in log
    assert "SET/TRACK/5/VOL/1.000000" in log
    import make_screenshots as M
    t = M.bar_time(29)
    assert any(c.startswith("SET/POS/") and abs(float(c.split("/")[2]) - t) < 0.01 for c in log)
    assert "1007" in log                                                # lecture (action REAPER)
    assert "SET/TRACK/8/MUTE/1" in log                                  # CLICK coupé
    remote = [unquote(c).split("/", 4)[4] for c in log if c.startswith("SET/EXTSTATE/ReaCue/remote/")]
    assert [r.split("|")[:3] for r in remote] == [["pitch", "+1", "1234"], ["loopsec", f"{t:.3f}", "1234"]]


def test_studio_export_flow():
    def go(M, browser, base):
        _setup(M)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script("localStorage.setItem('reacue_pin', '1234')")
        page = ctx.new_page()
        page.goto(f"{base}/studio.html?lang=en")
        page.wait_for_function("document.querySelectorAll('.tv-row').length === 5", timeout=8000)
        page.click("#expBtn")
        page.click("#expNone")
        page.check("#expStems input[value='Basse']")
        page.check("#expStems input[value='Batterie']")
        page.check("input[name=mode][value=mix]")
        page.select_option("#expKbps", "256")
        page.check("input[name=rng][value=section]")
        page.select_option("#expSection", "3")
        page.click("#expGo")
        page.wait_for_timeout(700)
        log = list(M.FakeReaper.log)
        req = next(json.loads(unquote(c)[len("SET/EXTSTATE/ReaCue/export_req/"):]) for c in log
                   if c.startswith("SET/EXTSTATE/ReaCue/export_req/"))
        M.FakeReaper.export = {"id": req["id"], "state": "done", "progress": 1, "dir": "/x/exports",
                               "files": [{"name": "Demo Song - Batterie + Basse - Chorus 1.mp3",
                                          "url": "reacue_exports/a_Demo.mp3", "bytes": 2097152}]}
        page.wait_for_selector("#expFiles a", timeout=4000)
        link = page.get_attribute("#expFiles a", "download"), page.get_attribute("#expFiles a", "href")
        msg = page.text_content("#expMsg")
        ctx.close()
        return log, req, link, msg
    log, req, link, msg = _run(go)
    assert req["stems"] == ["Batterie", "Basse"] or set(req["stems"]) == {"Batterie", "Basse"}
    assert req["mode"] == "mix" and req["format"] == "mp3" and req["kbps"] == 256
    assert req["range"] == {"kind": "section", "section": 3} and req["click"] is False
    i_req = next(i for i, c in enumerate(log) if c.startswith("SET/EXTSTATE/ReaCue/export_req/"))
    i_cmd = next(i for i, c in enumerate(log) if unquote(c).startswith(f"SET/EXTSTATE/ReaCue/remote/export|{req['id']}|1234|"))
    assert i_req < i_cmd                                                 # la demande avant la commande
    assert link == ("Demo Song - Batterie + Basse - Chorus 1.mp3", "reacue_exports/a_Demo.mp3")
    assert "1 file(s)" in msg


def test_studio_asks_pin_once_then_sends():
    def go(M, browser, base):
        _setup(M)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{base}/studio.html?lang=fr")
        page.wait_for_function("document.querySelectorAll('.tv-row').length === 5", timeout=8000)
        page.click("#trDown")
        page.wait_for_selector("#pinVeil.show", timeout=3000)
        page.fill("#pinIn", "12")
        page.wait_for_timeout(1200)                       # le dialogue n'est pas réouvert ni vidé
        typed = page.input_value("#pinIn")
        page.fill("#pinIn", "1234")
        page.click("#pinOk")
        page.wait_for_timeout(600)
        sent = [unquote(c) for c in M.FakeReaper.log if c.startswith("SET/EXTSTATE/ReaCue/remote/")]
        stored = page.evaluate("localStorage.getItem('reacue_pin')")
        return typed, sent, stored
    typed, sent, stored = _run(go)
    assert typed == "12" and stored == "1234"
    assert len(sent) == 1 and sent[0].split("/", 4)[4].startswith("pitch|-1|1234|")


# --------------------------------------------------------------------------- écrans CONCERT et LUMIÈRE
def _concert(M, lang="fr", bar=31, play=0):
    data = M.demo_concert(lang)
    s2 = data["songs"][1]
    M.FakeReaper.song, M.FakeReaper.tracks, M.FakeReaper.peaks = data, M.demo_tracks(), M.demo_peaks(s2)
    M.FakeReaper.pos, M.FakeReaper.play = M.bar_time(bar, 0.5, s2["bpm"], s2["start_t"]), play
    M.FakeReaper.log, M.FakeReaper.rehearsal, M.FakeReaper.studio, M.FakeReaper.tctest = [], "", "", ""
    return data


def _remote(M):
    return [unquote(c).split("/", 4)[4].split("|")[:3] for c in M.FakeReaper.log if c.startswith("SET/EXTSTATE/ReaCue/remote/")]


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_studio_concert_and_lighting_screens(lang):
    def go(M, browser, base):
        data = _concert(M, lang)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors, requests = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("request", lambda r: requests.append(r.url))
        page.goto(f"{base}/studio.html?lang={lang}#concert")
        page.wait_for_selector("#csSecs .cs-sec.now", timeout=8000)
        page.wait_for_timeout(300)
        c = {
            "visible": [page.is_visible(s) for s in ("#concert", "#travail", "#lumiere", ".rc-foot")],
            "nav": page.text_content("#nav button.on"), "title": page.text_content("#csTitle"),
            "rank": page.text_content("#csRank"), "state": page.text_content("#csStateTxt"),
            "songs": page.locator(".cs-song .t").all_text_contents(),
            "now": page.locator(".cs-song.now .t").all_text_contents(), "done": page.locator(".cs-song.done").count(),
            "secnow": page.text_content("#csSecs .cs-sec.now .s"), "secs": page.locator("#csSecs .cs-sec").count(),
            "cues": page.locator("#csCues .cs-cue").count(), "cuenow": page.text_content("#csCues .cs-cue.now .nm"),
            "fx": page.text_content("#csCues .cs-cue.now .fx"), "light": page.text_content("#csLightH"),
            "pills": [page.text_content(s) for s in ("#csLtc", "#csMtc", "#csExp")], "tc": page.text_content("#csTc"),
            "msg": page.is_visible("#csMsg"),
        }
        page.click("#nav button[data-mode=lumiere]")
        page.wait_for_selector("#lmList .cs-cue.now", timeout=4000)
        lm = {
            "hash": page.evaluate("location.hash"), "visible": page.is_visible("#lumiere") and not page.is_visible("#concert"),
            "rows": page.locator("#lmList .cs-cue").count(), "heads": page.locator("#lmList .cs-song-h").count(),
            "now": page.text_content("#lmNowName"), "files": [(a.get_attribute("href"), a.get_attribute("download"))
                                                              for a in page.locator("#lmFiles a").all()],
            "kv": page.text_content("#lmKv"), "ro": page.text_content(".cs-ro"),
        }
        page.click("#nav button[data-mode=travail]")
        page.wait_for_timeout(200)
        back = page.is_visible("#travail") and page.is_visible(".rc-foot") and page.evaluate("location.hash") == ""
        return errors, requests, c, lm, back, data
    errors, requests, c, lm, back, data = _run(go)
    fr = lang == "fr"
    assert not errors, errors
    assert all(u.startswith("http://127.0.0.1") for u in requests)
    assert c["visible"] == [True, False, False, False]
    assert c["nav"] == ("CONCERT" if fr else "SHOW")
    assert c["title"] == "Second Demo" and c["rank"] == ("MORCEAU 2 / 3" if fr else "SONG 2 / 3")
    assert c["state"] == ("ARRÊT" if fr else "STOPPED") and not c["msg"]
    assert c["songs"] == ["Demo Song", "Second Demo", "Third Demo"] and c["now"] == ["Second Demo"] and c["done"] == 1
    assert c["secs"] == 11 and c["secnow"] == ("EN COURS · 3/16" if fr else "NOW · 3/16")
    assert c["cues"] == 11 and c["cuenow"] == ("Refrain 1" if fr else "Chorus 1")    # 11 cues du morceau 2
    assert c["fx"] == ("Effet plein, toutes les têtes en mouvement" if fr else "Full effect, all heads moving")
    assert c["light"].endswith("TC SLOT 1") and c["tc"].startswith("01:0")
    assert c["pills"] == (["REAPER → LTC 7", "MTC → IAC BUS 1", "EXPORT À JOUR"] if fr else
                          ["REAPER → LTC 7", "MTC → IAC BUS 1", "EXPORT UP TO DATE"])
    assert lm["hash"] == "#lumiere" and lm["visible"]
    assert lm["rows"] == 33 and lm["heads"] == 3
    assert lm["now"] == ("Second Demo · Refrain 1" if fr else "Second Demo · Chorus 1")
    lg = data["lighting"]
    assert lm["files"] == [(f["url"], f["name"]) for f in lg["files"]] and len(lm["files"]) == 5
    assert all(h.startswith("reacue_gma3_") for h, _ in lm["files"])
    assert "IAC Bus 1" in lm["kv"] and "01:00:00:00" in lm["kv"]
    assert ("LECTURE SEULE" if fr else "READ ONLY") in lm["ro"]
    assert back


def test_studio_concert_commands_with_pin():
    def go(M, browser, base):
        data = _concert(M, "fr")
        s2 = data["songs"][1]
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script("localStorage.setItem('reacue_pin', '1234')")
        page = ctx.new_page()
        page.goto(f"{base}/studio.html?lang=fr#concert")
        page.wait_for_selector("#csSecs .cs-sec.now", timeout=8000)
        page.wait_for_timeout(300)
        page.click(".cs-song[data-k='2']")                    # morceau 3
        page.click("#csSecs .cs-sec[data-i='4']")             # Couplet 2
        page.click("#csPrev")
        page.click("#csNext")
        page.click("#csPlay")
        page.click("#csTest")
        page.click("#csCues .cs-cue[data-i='15']")           # cue 5 du morceau 2
        page.wait_for_timeout(1500)
        stopped = _remote(M)
        # lecture en cours : PRÉC. demande deux appuis, le test aussi
        M.FakeReaper.log, M.FakeReaper.play = [], 1
        page.wait_for_timeout(300)
        page.click("#csPrev")
        armed = page.text_content("#csPrevL")
        page.wait_for_timeout(500)
        one = _remote(M)
        page.click("#csPrev")
        page.wait_for_timeout(700)
        two = _remote(M)
        # test en cours (publié par la fenêtre : secondes restantes)
        M.FakeReaper.tctest = "7"
        page.wait_for_timeout(500)
        label = page.text_content("#csTest")
        M.FakeReaper.tctest, M.FakeReaper.play = "", 0
        ctx.close()
        return stopped, armed, one, two, label, s2, data
    stopped, armed, one, two, label, s2, data = _run(go)
    import make_screenshots as M
    t_verse2 = M.bar_time(45, 0.0, s2["bpm"], s2["start_t"])
    q = data["lighting"]["cues"][15]
    assert stopped == [["song", "3", "1234"], ["seek", f"{t_verse2:.3f}", "1234"], ["prev", "", "1234"],
                       ["next", "", "1234"], ["toggle", "", "1234"], ["tctest", "", "1234"],
                       ["seek", f"{q['t']:.3f}", "1234"]]
    assert q["track"] == 1 and q["n"] == 5
    assert armed == "ENCORE ?" and one == [] and two == [["prev", "", "1234"]]
    assert label == "ARRÊTER · 7 S"


def test_studio_concert_single_song():
    def go(M, browser, base):
        song = _setup(M, "en")
        M.FakeReaper.pos = M.bar_time(30, 1.0)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script("localStorage.setItem('reacue_pin', '1234')")
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{base}/studio.html?lang=en#concert")
        page.wait_for_selector("#csSecs .cs-sec.now", timeout=8000)
        out = {"msg": page.text_content("#csMsg") if page.is_visible("#csMsg") else "", "rank": page.text_content("#csRank"),
               "songs": page.locator(".cs-song").count(), "el": page.text_content("#csElK")}
        page.click("#csNext")
        page.wait_for_timeout(700)
        out["remote"] = _remote(M)
        ctx.close()
        return errors, out, song
    errors, out, song = _run(go)
    import make_screenshots as M
    assert not errors, errors
    assert out["msg"].startswith("No show open: single song") and out["rank"] == "SINGLE SONG"
    assert out["songs"] == 1 and out["el"] == "SONG"
    assert out["remote"] == [["seek", f"{M.bar_time(45):.3f}", "1234"]]        # section suivante (Couplet 2)


def test_studio_concert_without_window_falls_back_to_native_api():
    def go(M, browser, base):
        _concert(M, "fr")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        # fenêtre ReaCue fermée : remote_alive vide
        page.route("**/_/*", lambda r: r.continue_())
        page.goto(f"{base}/studio.html?lang=fr#concert")
        page.wait_for_selector("#csSecs .cs-sec.now", timeout=8000)
        page.evaluate("RC.windowOk = () => false")
        page.click("#csPlay")
        page.click("#csSecs .cs-sec[data-i='0']")
        page.click("#csTest")
        page.wait_for_timeout(600)
        toast = page.text_content("#toast")
        ctx.close()
        return list(M.FakeReaper.log), toast
    log, toast = _run(go)
    assert "1007" in log and any(c.startswith("SET/POS/") for c in log)
    assert not any(c.startswith("SET/EXTSTATE/ReaCue/remote/") for c in log)
    assert toast.startswith("Ouvre la fenêtre")
