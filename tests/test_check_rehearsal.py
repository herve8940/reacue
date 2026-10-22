"""Contrôle avant concert (« Vérifier ») et mode répétition (boucle avec 1 mesure de décompte, ralenti) de la
fenêtre « ReaCue - Concert » : Lua 5.4 via lupa, API REAPER simulée (tests/test_concert_lua.py), concert de
démonstration fictif construit par le vrai code Python. Français et anglais."""
import time
from pathlib import Path

import pytest

pytest.importorskip("lupa")

import test_concert_lua as TL  # noqa: E402


@pytest.fixture(scope="module")
def concert(tmp_path_factory):
    return TL.make_concert(tmp_path_factory.mktemp("check"))


def setup(concert, lang="fr", heartbeat=True):
    L, g = TL.runtime(concert, lang=lang)
    rdir = Path(g.RES)
    (rdir / "reaper_www_root").mkdir(exist_ok=True)
    for f in (rdir / "reaper_www_root").iterdir():
        f.unlink()
    if heartbeat:
        (rdir / "ReaCueMCP" / "heartbeat.txt").write_text(str(int(time.time())), encoding="utf-8")
    else:
        (rdir / "ReaCueMCP" / "heartbeat.txt").unlink(missing_ok=True)
    res = concert[0]
    # pistes : stems (musique) + générées ; items : un fichier par stem, des annonces
    stems = sorted({p for p in res.rpp.parent.parent.rglob("*.wav")})[:3] or [res.rpp]
    L.execute("""
      TRACKS = { {name="Chant"}, {name="Batterie"}, {name="Basse"}, {name="CUES"}, {name="VOIX"},
                 {name="CLICK", main=0, sends={2}} }
      NOUT = 4
    """)
    items = [f'{{track={k + 1}, file=[[{f}]]}}' for k, f in enumerate(stems)]
    voice = sorted(Path(res.rpp.parent.parent).rglob("*.wav"))[:1]
    items += [f'{{track=5, file=[[{voice[0] if voice else stems[0]}]]}}', '{track=6}']
    L.execute("ITEMS = {" + ",".join(items) + "}")
    return L, g, TL.lib(L)


def by_id(lst):
    return {x.id: x for x in lst.values()}


def test_checks_all_green_then_problems_and_fixes(concert, tmp_path):
    res = concert[0]
    L, g, M = setup(concert)
    c = M.load_concert()
    assert c.built and c.songs[1].project_sum and c.songs[1].project_size
    lst = by_id(M.run_checks(c, L.table_from({"ips": L.table_from(["192.168.1.20"])})))
    for k in ["media", "voice", "songs", "fresh", "bridge", "web", "ip", "audio", "outs"]:
        assert lst[k].status == "ok", (k, lst[k].detail)
    assert "8090" in lst["web"].detail and "192.168.1.20:8090" in lst["ip"].detail
    assert "CLICK → sorties 3/4" in lst["outs"].detail
    assert lst["prompter"].status == "warn" and lst["prompter"].fix == "publish"     # pas encore publié
    assert lst["regie"].status == "info"
    assert M.apply_fix(c, "publish")
    lst = by_id(M.run_checks(c, L.table_from({"ips": L.table_from(["192.168.1.20"])})))
    assert lst["prompter"].status == "ok"
    bad, warn = M.check_summary(M.run_checks(c, L.table_from({"ips": L.table_from(["1.2.3.4"])})))
    assert (bad, warn) == (0, 0)

    # problèmes : fichier hors ligne et fichier absent, sortie 3/4 absente, carte arrêtée, pas d'IP, pas de pont
    L.execute("ITEMS[1].sr = 0; ITEMS[2].file = '/nope/Gone-drums.wav'; NOUT = 2; AUDIO_ON = 0")
    (Path(g.RES) / "ReaCueMCP" / "heartbeat.txt").write_text("1", encoding="utf-8")
    lst = by_id(M.run_checks(c, L.table_from({"ips": L.table_from([])})))
    assert lst["media"].status == "bad" and "Gone-drums.wav" in lst["media"].detail and lst["media"].fix == "media"
    assert lst["outs"].status == "bad" and "sortie 4 absente" in lst["outs"].detail
    assert lst["audio"].status == "bad" and lst["ip"].status == "bad" and lst["bridge"].status == "bad"
    M.apply_fix(c, "media")
    assert 40101 in list(g.state.cmds.values())
    # piste CLICK coupée, ou envoyée nulle part
    L.execute("NOUT = 4; TRACKS[6].mute = 1")
    assert "coupée" in by_id(M.run_checks(c))["outs"].detail
    L.execute("TRACKS[6].mute = 0; TRACKS[6].sends = {}")
    assert "nulle part" in by_id(M.run_checks(c))["outs"].detail

    # concert pas à jour : le projet d'un morceau a changé depuis la construction
    proj = Path(c.songs[2].project)
    orig = proj.read_bytes()
    try:
        proj.write_bytes(orig + b"\n")
        f = by_id(M.run_checks(c))["fresh"]
        assert f.status == "warn" and "Second Demo" in f.detail and f.fix == "rebuild"
    finally:
        proj.write_bytes(orig)
    assert by_id(M.run_checks(c))["fresh"].status == "ok"
    # ancien concert (sans empreinte) ; morceau sans structure
    g.CC = c
    L.execute("CC.songs[1].project_sum = nil; CC.songs[3].sections = 0")
    lst = by_id(M.run_checks(c))
    assert lst["fresh"].status == "warn" and "ancienne version" in lst["fresh"].detail
    assert lst["songs"].status == "bad" and "Third Demo" in lst["songs"].detail

    # téléphones Régie vus (la page écrit remote_seen qui change)
    g.state.ext["remote_seen"] = "abc-1"; M.poll_seen(100.0)
    g.state.ext["remote_seen"] = "abc-2"; M.poll_seen(101.0)
    r = by_id(M.run_checks(c, L.table_from({"now": 105.0})))["regie"]
    assert r.status == "info" and "4 s" in r.detail

    # sans concert : seulement la partie système
    ids = set(by_id(M.run_checks(None)).keys())
    assert ids == {"bridge", "web", "ip", "audio", "regie"}
    assert M.adler32("Wikipedia") == 0x11E60398


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_window_check_view(concert, lang):
    L, g, M = setup(concert, lang=lang)
    TL.window(L, g)
    g.state.cursor = concert[0].songs[1]["bar1"] + 1
    TL.frame(L, g); TL.frame(L, g)
    lab = "Vérifier" if lang == "fr" else "Check"
    xy = TL.find_text(g, lab); assert xy, TL.texts(g)
    L.execute("ITEMS[1].sr = 0")                     # un fichier hors ligne
    TL.frame(L, g, (xy[0] + 3, xy[1] + 3)); TL.frame(L, g)
    T = TL.texts(g)
    assert ("Contrôle avant concert" if lang == "fr" else "Pre-show check") in T
    assert any(t.startswith("1 problème") or t.startswith("1 problem") for t in T), T
    xy = TL.find_text(g, "Corriger" if lang == "fr" else "Fix"); assert xy
    TL.frame(L, g, (xy[0] + 3, xy[1] + 3))
    assert 40101 in list(g.state.cmds.values())       # Set all media online
    L.execute("ITEMS[1].sr = 44100")
    g.state.t += 1.0; TL.frame(L, g)
    T = TL.texts(g)
    assert any(t.startswith("Tout est prêt" if lang == "fr" else "All set") for t in T), T
    xy = TL.find_text(g, "Fermer" if lang == "fr" else "Close")
    TL.frame(L, g, (xy[0] + 3, xy[1] + 3)); TL.frame(L, g)
    assert "Second Demo" in TL.texts(g)


def regions_of(concert, title):
    return [r for r in concert[1] if r[3].startswith(title + " · ")]


def test_rehearsal_loop_countin_rate_and_exit(concert):
    res = concert[0]
    L, g, M = setup(concert)
    c = M.load_concert()
    st = g.state
    secs = regions_of(concert, "Second Demo")
    ch = [r for r in secs if r[3].endswith("Refrain 1")][0]
    v1 = [r for r in secs if r[3].endswith("Couplet 1")][0]
    bars = sorted(g.BARS.values())
    prev_bar = max(b for b in bars if b < ch[1] - 0.01)
    # entrée en répétition : répétition native coupée, sélection et vitesse mémorisées
    M.set_rehearsal(True)
    assert M.reh.on and st.rep == 0
    # boucle sur une section : 1 mesure avant, au tempo du début de section, musique coupée, click/voix non
    assert M.loop_tap(c, ch[1])
    assert st.play == 1 and st.cursor == pytest.approx(prev_bar)
    assert M.reh.loop.pre == pytest.approx(ch[1] - prev_bar)
    muted = {t.name: (t.mute or 0) for t in g.TRACKS.values()}
    assert muted["Chant"] == 1 and muted["Batterie"] == 1 and muted.get("CLICK", 0) == 0 and muted.get("VOIX", 0) == 0
    assert tuple(st.sel.values()) == pytest.approx((ch[1], ch[2]))
    assert st.ext["rehearsal"].startswith("1|1.00|") and "Refrain 1" in st.ext["rehearsal"]
    # la mesure de décompte passe : la musique revient au début de la section
    assert M.loop_tick(prev_bar + 0.1, ch[1] - 0.01) == "start"
    assert {t.name: (t.mute or 0) for t in g.TRACKS.values()}["Chant"] == 0
    # fin de la boucle : reprise 1 mesure avant, musique coupée de nouveau
    assert M.loop_tick(ch[2] - 0.05, ch[2] + 0.02) == "restart"
    assert st.cursor == pytest.approx(prev_bar) and {t.name: (t.mute or 0) for t in g.TRACKS.values()}["Chant"] == 1
    # 2e section = plage (Couplet 1 → Refrain 1)
    assert M.loop_tap(c, v1[1])
    assert M.reh.loop.start == pytest.approx(v1[1]) and M.reh.loop.stop == pytest.approx(ch[2])
    assert "Couplet 1 → Refrain 1" in st.ext["rehearsal"]
    # arrêt pendant la mesure de décompte : la musique n'est pas laissée coupée
    st.play = 0
    M.loop_tick(None, st.cursor)
    assert all((t.mute or 0) == 0 for t in g.TRACKS.values())
    st.play = 1
    # 3e appui : nouvelle boucle simple
    assert M.loop_tap(c, ch[1]) and M.reh.loop.start == pytest.approx(ch[1])
    # ralenti : hauteur préservée, puis sortie : tout est remis comme avant
    assert M.set_rate(0.8) and st.rate == pytest.approx(0.8) and st.toggles[40671] == 1
    assert not M.set_rate(0.2)
    M.set_rehearsal(False)
    assert not M.reh.on and M.reh.loop is None and st.rate == pytest.approx(1.0)
    assert st.toggles[40671] == 0 and st.rep == 1 and tuple(st.sel.values()) == (12, 20)
    assert all((t.mute or 0) == 0 for t in g.TRACKS.values())
    assert st.ext["rehearsal"].startswith("0|")


def test_rehearsal_remote_commands(concert):
    L, g, M = setup(concert)
    c = M.load_concert()
    st = g.state
    M.set_remote_pin("2468")
    ch = [r for r in regions_of(concert, "Third Demo")][1]
    for n, (cmd, arg) in enumerate([("reh", "1"), ("loop", f"{ch[1]:.3f}"), ("rate", "0.9"), ("loopoff", ""), ("reh", "0")]):
        st.ext["remote"] = f"{cmd}|{arg}|2468|r{n}"
        assert tuple(M.remote_poll(c)) == (cmd, "ok"), cmd
        if cmd == "loop":
            assert M.reh.loop and M.reh.loop.start == pytest.approx(ch[1]) and st.play == 1
        if cmd == "rate":
            assert st.rate == pytest.approx(0.9)
        if cmd == "loopoff":
            assert M.reh.loop is None and M.reh.on
    assert not M.reh.on and st.rate == pytest.approx(1.0)
    st.ext["remote"] = "rate|3|2468|r9"; assert tuple(M.remote_poll(c)) == ("rate", "bad")
    st.ext["remote"] = "loop|99999|2468|r10"; assert tuple(M.remote_poll(c)) == ("loop", "bad")


def test_window_rehearsal_no_auto_stop(concert):
    res = concert[0]
    L, g, M = setup(concert)
    gx = TL.window(L, g)
    st = g.state
    st.cursor = res.songs[1]["bar1"] + 1
    TL.frame(L, g); TL.frame(L, g)
    xy = TL.find_text(g, "Répétition"); assert xy
    TL.frame(L, g, (xy[0] + 3, xy[1] + 3)); TL.frame(L, g)
    T = TL.texts(g)
    assert any(t.startswith("RÉPÉTITION") for t in T) and "arrêt auto coupé (répétition)" in T, T
    # section « Solo » du morceau 2 : boucle
    xy = TL.find_text(g, "Solo"); assert xy
    TL.frame(L, g, (xy[0] + 5, xy[1] + 6))
    solo = [r for r in concert[1] if r[3] == "Second Demo · Solo"][0]
    assert st.play == 1 and st.cursor < solo[1]
    # la lecture franchit la fin du morceau : pas d'arrêt auto, la boucle reprend
    st.pos = solo[2] - 0.05; TL.frame(L, g)
    st.pos = solo[2] + 0.02; TL.frame(L, g)
    assert st.play == 1 and st.pos == pytest.approx(st.cursor) and st.pos < solo[1]
    TL.frame(L, g)
    assert any("boucle : Solo" in t for t in TL.texts(g))
    # vitesse 80 % puis Quitter la répétition
    xy = TL.find_text(g, "80 %"); TL.frame(L, g, (xy[0] + 3, xy[1] + 3)); assert st.rate == pytest.approx(0.8)
    xy = TL.find_text(g, "Quitter"); TL.frame(L, g, (xy[0] + 3, xy[1] + 3))
    assert st.rate == pytest.approx(1.0) and st.ext["rehearsal"].startswith("0|")
    TL.frame(L, g)
    assert "arrêt auto actif" in TL.texts(g)
    # hors répétition : arrêt auto en fin de morceau
    st.play = 1; st.pos = res.songs[1]["stop"] - 0.2; TL.frame(L, g)
    st.pos = res.songs[1]["stop"] + 0.05; TL.frame(L, g)
    assert st.play == 0
    st.atexit()
    assert st.ext["rehearsal"] == ""
