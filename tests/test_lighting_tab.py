"""Onglet « Lumière » / “Lighting” de la fenêtre ReaCue (Lua 5.4 via lupa, API REAPER simulée) : cues et
timecode (export publié ou régions), réglages gma3_* écrits dans reacue_settings.json (autres clés gardées),
actions (CLI timecode / publish / concert-lighting, dossier grandMA3), test de communication (sortie LTC,
périphérique MIDI, pistes TIMECODE, générateur réglé) et envoi de 10 s de test (solo des pistes TIMECODE,
état rétabli à l'identique). Côté Python : commande « timecode » (pont ≥ 1.5) et « concert-lighting ».
Données entièrement fictives."""
import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("lupa")

import test_concert_lua as TL  # noqa: E402
import test_reacue_window as W  # noqa: E402
import test_timecode as TT  # noqa: E402
from reacue_mcp import i18n, lighting as LG, settings, timecode as TC  # noqa: E402

# API REAPER simulée : carte son à 8 sorties nommées, sorties MIDI (une désactivée), solo / mute / « solo
# defeat » des pistes, items des pistes TIMECODE (bloc <SOURCE LTC>), P_EXT
EXTRA = r"""
NOUT = 8
MIDI = { [0] = {"Network Session 1", true}, [2] = {"IAC Driver Bus 1", true}, [3] = {"USB MIDI Out", false} }
reaper.GetOutputChannelName = function(i) return "Out " .. (i + 1) end
reaper.GetMaxMIDIOutputs = function() return 4 end
reaper.GetMIDIOutputName = function(i, b) local d = MIDI[i]; if d then return d[2], d[1] end return false, "" end
reaper.GetMediaTrackInfo_Value = function(tr, k)
  if k == "B_MUTE" then return tr.mute or 0 elseif k == "I_SOLO" then return tr.solo or 0
  elseif k == "B_SOLO_DEFEAT" then return tr.defeat or 0 elseif k == "B_MAINSEND" then return tr.main or 1 end
  return 0 end
reaper.SetMediaTrackInfo_Value = function(tr, k, v)
  if k == "B_MUTE" then tr.mute = v; table.insert(state.mutelog, {tr.name, v})
  elseif k == "I_SOLO" then tr.solo = v end end
reaper.GetSetMediaTrackInfo_String = function(tr, k, v, set)
  local e = k:match("^P_EXT:(.+)$")
  if e then tr.ext = tr.ext or {}; if set then tr.ext[e] = v end return true, tr.ext[e] or "" end
  return true, tr.name end
reaper.CountTrackMediaItems = function(tr) return tr.its and #tr.its or 0 end
reaper.GetTrackMediaItem = function(tr, i) return tr.its[i + 1] end
reaper.GetItemStateChunk = function(it) return it.chunk ~= nil, it.chunk or "" end
"""
GEN = "<ITEM\nPOSITION 0\n<SOURCE LTC\nUSER 1\n>\n>"


@pytest.fixture(scope="module")
def concert(tmp_path_factory):
    return TL.make_concert(tmp_path_factory.mktemp("light"))


@pytest.fixture(autouse=True)
def clean_templates():
    import shutil
    shutil.rmtree(TC.template_dir(), ignore_errors=True)
    yield
    shutil.rmtree(TC.template_dir(), ignore_errors=True)


def settings_file(g):
    return Path(g.RES) / "ReaCueMCP" / "reacue_settings.json"


def write_settings(g, **kw):
    settings_file(g).write_text(json.dumps(kw), encoding="utf-8")


def read_settings(g):
    return json.loads(settings_file(g).read_text(encoding="utf-8"))


def demo_song_json(title="Song One-A minor-120bpm", tc="01:00:00:00", fps=25):
    """prompteur publié pour le morceau de démonstration (régions à 4, 12 et 30 s), avec son bloc « lighting »"""
    song = {"version": 1, "title": title, "count_in_bars": 0, "bar_times": [4.0 + 2.0 * k for k in range(22)],
            "sections": [{"name": "Intro", "start_bar": 1}, {"name": "Couplet 1", "start_bar": 5},
                         {"name": "Refrain 1", "start_bar": 14}]}
    cfg = LG.config({**settings.DEFAULTS, "gma3_tc_start": tc, "gma3_fps": fps})
    song["lighting"] = LG.web_data(LG.show_from_songs([song]), cfg)
    return song


def song_rt(concert, tmp_path, lang="fr", publish=True, **sets):
    L, g, res = W.song_runtime(concert, tmp_path, lang=lang)
    L.execute(EXTRA)
    write_settings(g, language=lang, custom_key="garde-moi", **sets)
    www = Path(g.RES) / "reaper_www_root" / "reacue_song.json"       # dossier partagé par le module
    if publish:
        www.write_text(json.dumps(demo_song_json()), encoding="utf-8")
    else:
        www.unlink(missing_ok=True)
    return L, g, res


def open_lighting(L, g):
    gx = W.open_window(L, g)
    W.frame(L, g); W.frame(L, g)
    L.execute('REACUE_CTX.goto_tab("lighting")')
    W.frame(L, g)
    return gx


def tab(L):
    return L.globals().REACUE_CTX.tabs.lighting


def add_tc_tracks(L, kinds=("LTC",), key=None, gen=True):
    for k in kinds:
        its = "{ {chunk=[[" + GEN + "]]} }" if gen else "{}"
        ext = f'{{reacue_tc_key="{key}"}}' if key else "{}"
        L.execute(f'table.insert(TRACKS, {{name="TIMECODE {k}", main=0, its={its}, ext={ext}}})')


def press_in_row(L, g, row_label, text):
    """clic sur le texte `text` de la ligne de réglage `row_label` (même hauteur)"""
    _, y = W.text_xy(g, row_label)
    for o in g.state.ops.values():
        o = list(o.values())
        if o[0] == "text" and o[3] == text and abs(o[2] - y) < 10:
            TL.frame(L, g, (o[1] + 3, o[2] + 3))
            return
    raise AssertionError((row_label, text, TL.texts(g)))


def tracks(g):
    return {t.name: t for t in g.TRACKS.values()}


# ------------------------------------------------------------------------------------------- onglet
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_tab_present_cues_timecode_and_pills(concert, tmp_path, lang):
    L, g, _ = song_rt(concert, tmp_path, lang=lang, gma3_ltc_output=7, gma3_mtc_output="iac driver",
                      gma3_tc_start="01:00:00:00", gma3_tc_slot=3)
    open_lighting(L, g)
    T = TL.texts(g)
    fr = lang == "fr"
    assert ("Lumière" if fr else "Lighting") in T and ("Réglages" if fr else "Settings") in T, T
    assert g.state.persist["tab"] == "lighting"
    # cues exportés : n°, timecode (départ 01:00:00:00, 25 i/s), nom ; timecode actuel
    assert any(t.endswith("exportés" if fr else "exported") for t in T), T
    for s in ("01:00:04:00", "01:00:12:00", "01:00:30:00", "Intro", "Couplet 1", "Refrain 1"):
        assert s in T, (s, T)
    assert "01:00:00:00" in T and any(t.startswith("temps projet 0:00 + départ" if fr else "project time 0:00 + start")
                                      for t in T), T
    # pastilles : sortie 7 existe, IAC trouvé et activé, pistes absentes, générateur à régler
    for p in (("Sortie LTC 7 ✓", "MTC ✓", "Pistes TIMECODE absentes", "Générateur à régler") if fr else
              ("LTC output 7 ✓", "MTC ✓", "TIMECODE tracks missing", "Generator to set")):
        assert p in T, (p, T)
    assert any(("TC Slot 3" in t) for t in T), T                         # texte explicatif : slot réglé
    assert ("Envoyer 10 s de test" if fr else "Send a 10 s test") in T
    # aide au survol d'une pastille
    gx = L.globals().gfx
    x, y = W.text_xy(g, "MTC ✓")
    gx.mouse_x, gx.mouse_y = x + 2, y + 2
    W.frame(L, g)
    assert any("IAC Driver Bus 1" in t for t in TL.texts(g)), TL.texts(g)
    gx.mouse_x, gx.mouse_y = 0, 0
    # pistes créées (générateur, mêmes réglages) puis réglage mémorisé : tout au vert
    M = tab(L)
    add_tc_tracks(L, ("LTC", "MTC"), key=None)
    g.state.t += 2; W.frame(L, g)
    assert ("Pistes TIMECODE ✓" if fr else "TIMECODE tracks ✓") in TL.texts(g), TL.texts(g)
    for kind in ("ltc", "mtc"):
        p = Path(M.template_path(kind))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("<SOURCE LTC\nUSER 1\n>\n", encoding="utf-8")
    g.state.t += 2; W.frame(L, g)
    assert ("Générateur réglé ✓" if fr else "Generator set ✓") in TL.texts(g), TL.texts(g)
    # cue en cours surligné pendant la lecture
    g.state.play, g.state.pos = 1, 13.0
    W.frame(L, g)
    assert M.current(M.load().cues, 13.0) == 2
    x, y = W.text_xy(g, "Couplet 1")
    rects = [list(o.values()) for o in g.state.ops.values() if list(o.values())[0] == "rect"]
    hl = [r for r in rects if r[2] <= y <= r[2] + r[4] and round(r[5] * 255) == 29 and round(r[6] * 255) == 158]
    assert hl, "ligne du cue en cours non surlignée"
    assert "01:00:13:00" in TL.texts(g)                                  # timecode actuel = temps projet + départ
    g.state.play = 0


def test_cues_from_regions_message_and_stale(concert, tmp_path):
    L, g, _ = song_rt(concert, tmp_path, publish=False, gma3_fps=30)
    open_lighting(L, g)
    T = TL.texts(g)
    assert any(t.endswith("calculés depuis les régions") for t in T), T
    assert any(t.startswith("Rien n'est encore exporté") for t in T), T
    assert "00:00:04:00" in T and "Refrain 1" in T
    # régions avec noms en double : numérotées comme l'export (Refrain, Refrain (2))
    L.execute('REGIONS[3][4] = "Couplet 1"')
    M = tab(L)
    names = [q.name for q in M.load(True).cues.values()]
    assert names == ["Intro", "Couplet 1", "Couplet 1 (2)"]
    # export publié avec d'autres réglages (25 i/s) : signalé
    (Path(g.RES) / "reaper_www_root" / "reacue_song.json").write_text(json.dumps(demo_song_json()), encoding="utf-8")
    g.state.t += 3; W.frame(L, g); W.frame(L, g)
    assert any(t.startswith("Réglages ou structure modifiés depuis l'export") for t in TL.texts(g)), TL.texts(g)
    # export désactivé
    write_settings(g, language="fr", gma3_export=False)
    L.execute("REACUE_CTX.tabs.settings.load()")
    g.state.t += 3; W.frame(L, g)
    assert any(t.startswith("Export grandMA3 désactivé") for t in TL.texts(g)), TL.texts(g)


def test_concert_cues_from_published_prompter(concert):
    res = concert[0]
    L, g = W.rt(concert)
    L.execute(EXTRA)
    open_lighting(L, g)
    T = TL.texts(g)
    assert any(t.endswith("exportés") for t in T), T
    M = tab(L)
    cues = list(M.load().cues.values())
    data = json.loads(res.prompter.read_text(encoding="utf-8"))
    assert [(q.n, q.name) for q in cues] == [(q["n"], q["name"]) for q in data["lighting"]["cues"]]
    assert any(t.startswith("Demo Song  ·  ") for t in T), T          # concert : nom du morceau au 1er cue
    # sans export (prompteur sans bloc lighting) : régions, numérotées par morceau, sans le préfixe « Titre · »
    reg = list(M.cues_from_regions(L.globals().REACUE_CTX.c, True).values())
    assert reg[0].n == 1 and " · " not in reg[0].name and reg[0].song == "Demo Song"
    assert [q.n for q in reg if q.song == "Second Demo"][0] == 1


# ------------------------------------------------------------------------------------- configuration
def test_config_writes_settings_keeping_other_keys(concert, tmp_path):
    L, g, _ = song_rt(concert, tmp_path)
    open_lighting(L, g)
    st = g.state
    press_in_row(L, g, "Images par seconde", "30")
    d = read_settings(g)
    assert d["gma3_fps"] == 30 and d["custom_key"] == "garde-moi" and d["language"] == "fr"
    W.frame(L, g)
    press_in_row(L, g, "Images par seconde", "29,97")
    assert read_settings(g)["gma3_fps"] == 29.97
    W.frame(L, g)
    # départ du timecode : normalisé ; illisible : refusé
    st.inputs = "1:0:0:5"
    press_in_row(L, g, "Départ du timecode", "00:00:00:00")
    assert read_settings(g)["gma3_tc_start"] == "01:00:00:05"
    W.frame(L, g)
    st.inputs = "01:00:00:30"                                   # 30 images à 29,97 i/s : impossible
    press_in_row(L, g, "Départ du timecode", "01:00:00:05")
    assert read_settings(g)["gma3_tc_start"] == "01:00:00:05" and "HH:MM:SS:FF" in st.msgbox
    st.inputs = None
    W.frame(L, g)
    # TC Slot : pas à pas 1 → 2
    x, y = W.text_xy(g, "Slot 1")
    tri = [list(o.values()) for o in st.ops.values() if list(o.values())[0] == "tri" and abs(list(o.values())[2] - (y + 7)) < 14]
    TL.frame(L, g, (max(tri, key=lambda t_: t_[1])[1], y + 7))
    assert read_settings(g)["gma3_tc_slot"] == 2
    W.frame(L, g)
    # sortie LTC : menu (aucune, sorties 1 à 8, puis paires) ; paire 7/8 puis sortie 3 seule
    st.menu = 13
    W.press_text(L, g, "aucune", exact=True)
    menu = list(st.menus.values())[-1]
    assert menu.startswith("!aucune|1 · Out 1|") and "8 · Out 8||1/2 · Out 1 / Out 2" in menu, menu
    assert read_settings(g)["gma3_ltc_output"] == "7/8"
    W.frame(L, g)
    st.menu = 4
    W.press_text(L, g, "7/8", exact=True)
    assert read_settings(g)["gma3_ltc_output"] == 3
    W.frame(L, g)
    # périphérique MTC : sorties MIDI de REAPER (désactivée signalée)
    st.menu = 3
    W.press_text(L, g, "aucun", exact=True)
    menu = list(st.menus.values())[-1]
    assert menu == "!aucun|Network Session 1|IAC Driver Bus 1|USB MIDI Out (désactivé)", menu
    assert read_settings(g)["gma3_mtc_output"] == "IAC Driver Bus 1"
    W.frame(L, g)
    st.menu = 1                                                 # « aucun » : clé retirée
    W.press_text(L, g, "IAC Driver Bus 1", exact=True)
    assert "gma3_mtc_output" not in read_settings(g)
    W.frame(L, g)
    # concert : blanc (vide = setlist) et créneau
    st.inputs = "6"
    W.press_text(L, g, "celui de la setlist", exact=True)
    assert read_settings(g)["gma3_song_gap"] == 6
    W.frame(L, g)
    st.inputs = ""
    W.press_text(L, g, "6 s", exact=True)
    assert "gma3_song_gap" not in read_settings(g)
    W.frame(L, g)
    st.inputs = "600"
    press_in_row(L, g, "Créneau de départ", "non")
    assert read_settings(g)["gma3_song_slot"] == 600
    W.frame(L, g)
    # export : non
    press_in_row(L, g, "Export grandMA3", "non")
    d = read_settings(g)
    assert d["gma3_export"] is False and d["custom_key"] == "garde-moi"
    # Python relit les mêmes clés
    s = settings.load_settings(settings_file(g))
    assert (s["gma3_fps"], s["gma3_tc_start"], s["gma3_tc_slot"], s["gma3_ltc_output"], s["gma3_song_slot"]) == \
        (29.97, "01:00:00:05", 2, 3, 600)
    assert s["gma3_export"] is False


# ---------------------------------------------------------------------------------------- actions
def test_actions_cli_and_folder(concert, tmp_path):
    L, g, _ = song_rt(concert, tmp_path, gma3_ltc_output=7)
    W.install(g, tmp_path)
    open_lighting(L, g)
    W.press_text(L, g, "Créer / mettre à jour les pistes timecode", exact=True)
    assert "-m reacue_mcp.cli timecode" in list(g.state.shell.values())[-1]
    W.frame(L, g)
    assert any(t.startswith("Pistes timecode…") for t in TL.texts(g)), TL.texts(g)
    W.status(g, state="done", cmd="timecode", message="Pistes timecode mises à jour")
    W.frame(L, g)
    assert "Terminé" in TL.texts(g) and "Pistes timecode mises à jour" in TL.texts(g)
    W.press_text(L, g, "OK", exact=True)
    # pont trop ancien : explication + bouton
    W.clear_status(g)
    W.press_text(L, g, "Créer / mettre à jour les pistes timecode", exact=True)
    W.status(g, state="error", cmd="timecode", message=i18n.t("cli_error", "fr", e=i18n.t("tc_old_bridge", "fr")))
    W.frame(L, g)
    T = TL.texts(g)
    assert "Le pont ReaCue de REAPER est trop ancien pour cette fonction." in T and "Ouvrir le dossier" in T, T
    W.press_text(L, g, "OK", exact=True)
    # exporter maintenant (morceau) = mettre à jour les téléphones (export lumière compris)
    W.clear_status(g)
    W.press_text(L, g, "Exporter maintenant", exact=True)
    assert "-m reacue_mcp.cli publish" in list(g.state.shell.values())[-1]
    W.status(g, state="done", cmd="publish", message="ok")
    W.frame(L, g); W.press_text(L, g, "OK", exact=True)
    # dossier grandMA3 : absent (message), puis ouvert
    n = len(g.state.shell)
    W.press_text(L, g, "Ouvrir le dossier grandMA3", exact=True)
    W.frame(L, g)
    assert any(t.startswith("Pas encore de dossier grandMA3") for t in TL.texts(g)), TL.texts(g)
    W.press_text(L, g, "OK", exact=True)
    (tmp_path / "grandMA3").mkdir()
    (tmp_path / "grandMA3" / "Song_One_Sequence.xml").write_text("<GMA3/>", encoding="utf-8")
    W.press_text(L, g, "Ouvrir le dossier grandMA3", exact=True)
    cmds = list(g.state.shell.values())[n:]
    assert any(str(tmp_path / "grandMA3") in c and c.startswith("open ") for c in cmds), cmds


def test_concert_export_and_folder(concert):
    res = concert[0]
    L, g = W.rt(concert)
    L.execute(EXTRA)
    inst = res.rpp.parent.parent / "inst"
    (inst / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
    (inst / ".venv" / "bin" / "python").write_text("")
    g.state.ext["install_dir"] = str(inst)
    open_lighting(L, g)
    W.press_text(L, g, "Exporter maintenant", exact=True)
    sh = list(g.state.shell.values())[-1]
    assert f"-m reacue_mcp.cli concert-lighting --setlist '{res.setlist}'" in sh, sh
    W.status(g, state="done", cmd="concert-lighting", message="ok")
    W.frame(L, g); W.press_text(L, g, "OK", exact=True)
    n = len(g.state.shell)
    W.press_text(L, g, "Ouvrir le dossier grandMA3", exact=True)
    want = res.rpp.parent / "grandMA3" / LG.clean_name(res.name)
    assert want.is_dir() and any(str(want) in c for c in list(g.state.shell.values())[n:])


# ----------------------------------------------------------------------------- test de 10 s : état rétabli
def test_ten_second_test_restores_exact_state(concert, tmp_path):
    L, g, _ = song_rt(concert, tmp_path, gma3_ltc_output=7)
    add_tc_tracks(L, ("LTC",))
    L.execute('TRACKS[1].solo = 1; TRACKS[2].defeat = 1; TRACKS[3].mute = 1; TRACKS[4].mute = 1')
    open_lighting(L, g)
    st, M = g.state, tab(L)
    before = {n: (t.solo or 0, t.mute or 0) for n, t in tracks(g).items()}
    # lecture en cours : 1er appui = armé (« encore ? »), rien ne change
    st.play, st.pos, st.cursor = 1, 20.0, 8.0
    W.press_text(L, g, "Envoyer 10 s de test", exact=True)
    W.frame(L, g)
    assert not M.test_active() and "encore ?" in TL.texts(g)
    st.t += 0.3
    W.press_text(L, g, "encore ?", exact=True)
    assert M.test_active()
    tr = tracks(g)
    assert tr["TIMECODE LTC"].solo == 1 and tr["TIMECODE LTC"].mute == 0
    assert tr["Chant"].solo == 0 and tr["Batterie"].mute == 1 and tr["CLICK"].mute == 1
    assert st.play == 1 and st.pos == pytest.approx(20.0) and st.stopped >= 1     # part de la position de lecture
    W.frame(L, g)
    assert any(t.startswith("Arrêter le test") for t in TL.texts(g)), TL.texts(g)
    # pendant le test : les mutes des instruments ne sont pas réappliqués, ni l'arrêt automatique
    assert L.globals().REACUE_CTX.tc_test
    # 10 s plus tard : tout est rétabli, la lecture reprend où elle était
    st.t += 10.5
    W.frame(L, g)
    assert not M.test_active()
    assert {n: (t.solo or 0, t.mute or 0) for n, t in tracks(g).items()} == before
    assert st.play == 1 and st.pos == pytest.approx(20.0) and st.cursor == pytest.approx(8.0)
    assert any(t.startswith("Test terminé") for t in TL.texts(g)), TL.texts(g)
    # à l'arrêt, depuis le début : le Stop de REAPER arrête le test et rétablit tout
    st.play, st.cursor = 0, 8.0
    W.press_text(L, g, "depuis le début", exact=True)
    assert st.persist["light_from"] == "start"
    W.frame(L, g)
    W.press_text(L, g, "Envoyer 10 s de test", exact=True)
    assert M.test_active() and st.play == 1 and st.pos == pytest.approx(0.0)
    st.play = 0
    st.t += 0.5
    W.frame(L, g)
    assert not M.test_active() and st.play == 0 and st.cursor == pytest.approx(8.0)
    assert {n: (t.solo or 0, t.mute or 0) for n, t in tracks(g).items()} == before
    # 2e appui sur le bouton : arrêt immédiat
    W.press_text(L, g, "Envoyer 10 s de test", exact=True)
    assert M.test_active()
    W.frame(L, g)
    W.press_text(L, g, "Arrêter le test")
    assert not M.test_active() and st.play == 0
    assert {n: (t.solo or 0, t.mute or 0) for n, t in tracks(g).items()} == before
    # fenêtre fermée pendant le test : rétabli aussi
    M.test_start(False)
    assert tracks(g)["Chant"].solo == 0
    st.atexit()
    assert not M.test_active() and {n: (t.solo or 0, t.mute or 0) for n, t in tracks(g).items()} == before


def test_ten_second_test_refused_without_tracks_or_in_rehearsal(concert, tmp_path):
    L, g, _ = song_rt(concert, tmp_path, gma3_ltc_output=7)
    open_lighting(L, g)
    W.press_text(L, g, "Envoyer 10 s de test", exact=True)
    W.frame(L, g)
    assert any(t.startswith("Pas de piste TIMECODE dans le projet") for t in TL.texts(g)), TL.texts(g)
    assert not tab(L).test_active() and g.state.play == 0
    W.press_text(L, g, "OK", exact=True)
    add_tc_tracks(L)
    g.state.play = 5                                            # enregistrement
    ok, why = tab(L).test_start(False)
    assert not ok and "Enregistrement" in why
    g.state.play = 0


# ------------------------------------------------------------------------------ fonctions (faux objets)
def test_lua_helpers_match_python(concert, tmp_path):
    L, g, _ = song_rt(concert, tmp_path)
    open_lighting(L, g)
    M = tab(L)
    for fps in (24, 25, 29.97, 30):
        for sec in (0, 0.02, 1.5, 59.999, 61.2, 3599.98, 3600, 7322.47):
            assert M.smpte(sec, fps) == LG.seconds_to_smpte(sec, fps), (sec, fps)
    for v in (7, "7", "7/8", "7-8", " 1 + 2 ", 3.0, "3/3", None, "", 0, "0", False, True, "off", "7/9", "x", -2, 2.5, "0/1"):
        lua, py = M.parse_ltc(v), TC.parse_audio_output(v)
        assert (lua is None) == (py is None), v
        if py:
            assert lua.label == py["label"], v
    for tc in ("01:00:00:00", "00:00:00:00", "10:20:30:12"):
        for fps in (25, 29.97, 30):
            write_settings(g, language="fr", gma3_tc_start=tc, gma3_fps=fps)
            L.execute("REACUE_CTX.tabs.settings.load()")
            c = TC.config(settings.load_settings(settings_file(g)))
            assert M.template_key("ltc") == TC.template_key("ltc", c) and M.template_key("mtc") == TC.template_key("mtc", c)
            assert tuple(M.tc_start()) == (c["tc_start"], pytest.approx(c["offset_s"]))
    for s in ("01:00:00:00", "1:2:3", "01;00;00;24", "1:60:00:00", "01:00:00:25", "x"):
        py = LG.parse_tc(s, 25.0)
        lua = M.parse_tc(s, 25)
        assert (lua is None) == (py is None) and (py is None or abs(lua - py) < 1e-9), s
    for name in ("Démo du soir", "42 nuits", "Été à Noël", "", "Concert test", "Ça va ?"):
        assert M.clean_name(name, "Concert") == LG.clean_name(name, "Concert"), name


def test_communication_checks_on_fake_objects(concert, tmp_path):
    L, g, _ = song_rt(concert, tmp_path, gma3_ltc_output="9/10", gma3_mtc_output="USB MIDI")
    open_lighting(L, g)
    M = tab(L)
    c = M.checks(True)
    assert c.ltc.st == "bad" and "9/10" in c.ltc.lab and "8" in c.ltc.detail          # 8 sorties seulement
    assert c.mtc.st == "warn" and c.mtc.prefs                                         # présent, pas activé
    assert c.tracks.st == "bad" and "TIMECODE LTC" in c.tracks.detail and "TIMECODE MTC" in c.tracks.detail
    assert c.gen.st == "warn" and c.gen.memo
    memo = M.memo()
    assert "Send MIDI (MTC)" in memo and "25 i/s" in memo and "00:00:00:00" in memo
    # périphérique inconnu ; pas de sortie réglée : gris
    write_settings(g, language="fr", gma3_mtc_output="Absent")
    L.execute("REACUE_CTX.tabs.settings.load()")
    c = M.checks(True)
    assert c.mtc.st == "bad" and c.ltc.st is False and c.gen.st == "warn"
    write_settings(g, language="fr")
    L.execute("REACUE_CTX.tabs.settings.load()")
    c = M.checks(True)
    assert (c.ltc.st, c.mtc.st, c.tracks.st, c.gen.st) == (False, False, False, False)
    # piste restée alors que plus rien n'est réglé : à mettre à jour
    add_tc_tracks(L, ("LTC",))
    assert M.checks(True).tracks.st == "warn"
    # piste sans générateur, piste créée avec d'autres réglages (clé)
    write_settings(g, language="fr", gma3_ltc_output=7)
    L.execute("REACUE_CTX.tabs.settings.load()")
    assert M.checks(True).tracks.st == "warn" or M.checks(True).tracks.st is True
    L.execute("TRACKS[#TRACKS].its = {}")
    assert M.checks(True).tracks.st == "bad"
    L.execute(f"TRACKS[#TRACKS].its = {{ {{chunk=[[{GEN}]]}} }}; TRACKS[#TRACKS].ext = {{reacue_tc_key='ltc_30_00-00-00-00'}}")
    assert M.checks(True).tracks.st == "warn"
    L.execute("TRACKS[#TRACKS].ext = {reacue_tc_key='ltc_25_00-00-00-00'}")
    assert M.checks(True).tracks.st is True


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_robust_without_settings_project_or_bridge(concert, tmp_path, lang):
    """réglages absents ou illisibles, aucun projet, pas de pont, API incomplète, fenêtre étroite / ancrée"""
    L, g = W.rt(concert, lang=lang, proj=tmp_path / "rien.RPP", tracks=False, heartbeat=False)
    if lang == "fr":
        settings_file(g).unlink()                  # fichier absent : défauts (français)
    else:
        write_settings(g, language="en")           # aucune clé gma3_*
    (Path(g.RES) / "ReaCueMCP" / "heartbeat.txt").unlink(missing_ok=True)      # pont arrêté
    L.execute('PROJFILE = ""; REGIONS = {}; reaper.GetMIDIOutputName = nil; reaper.GetOutputChannelName = nil')
    open_lighting(L, g)
    T = TL.texts(g)
    assert any(t.startswith("Ouvre un morceau ou un concert" if lang == "fr" else "Open a prepared song") for t in T), T
    assert ("LTC non réglé" if lang == "fr" else "LTC not set") in T
    if lang == "fr":
        settings_file(g).write_text("{pas du json", encoding="utf-8")
        L.execute("REACUE_CTX.tabs.settings.load()")
        g.state.t += 3; W.frame(L, g)
        assert "LTC non réglé" in TL.texts(g)
    # pont arrêté : « Créer les pistes » explique quoi faire
    W.install(g, tmp_path)
    W.press_text(L, g, "Créer / mettre à jour les pistes timecode" if lang == "fr" else "Create / update the timecode tracks",
                 exact=True)
    W.frame(L, g)
    assert ("Démarrer le pont" if lang == "fr" else "Start the bridge") in TL.texts(g), TL.texts(g)
    L.execute("REACUE_CTX.overlay = nil")
    gx = L.globals().gfx
    for w, dock in ((340, 0), (300, 1)):
        g.state.dock = dock
        gx.w, gx.h = w, 700
        W.frame(L, g); W.frame(L, g)
        T = TL.texts(g)
        assert ("Test de communication" if lang == "fr" else "Communication test") in T, (w, T)
        assert all(gx.w >= 0 for _ in T)


# ----------------------------------------------------------------------------------------- Python
def test_bridge_timecode_tracks_only(tmp_path):
    R = TT.Reaper(tmp_path)
    c = TT.cfg(gma3_ltc_output=7, gma3_mtc_output="IAC")
    R.g.PROJLEN = 40.0
    blk = TC.plan_block(c, 0.0)
    blk["tail"] = TC.TAIL_S
    res = R.call("timecode_tracks", blk)["timecode"]
    assert res["length"] == pytest.approx(40.0 + TC.TAIL_S)
    assert [t.name for t in R.tracks()] == ["Drums", "TIMECODE LTC", "TIMECODE MTC"]
    # réglage fait à la main gardé, jamais de doublon, le reste du projet intact
    R.track("TIMECODE LTC").its[1].chunk = "<ITEM\n<SOURCE LTC\nUSER 9\n>\n>"
    for _ in range(2):
        res = R.call("timecode_tracks", blk)["timecode"]
        assert [t.name for t in R.tracks()] == ["Drums", "TIMECODE LTC", "TIMECODE MTC"]
    assert res["tracks"][0]["origin"] == "kept" and "USER 9" in R.track("TIMECODE LTC").its[1].chunk
    summ, warns = TC.handle_result(res, c)
    assert summ["pistes"][0]["generateur_regle"] is True
    # réglages vidés : pistes retirées
    R.call("timecode_tracks", dict(TC.plan_block(TT.cfg(), 0.0), tail=8))
    assert [t.name for t in R.tracks()] == ["Drums"]


def test_server_and_cli_timecode(monkeypatch, lang, bridge_dir, resdir, tmp_path):
    import test_cli as TCLI
    from reacue_mcp import cli, server
    lang("fr", gma3_ltc_output="7/8")

    class FB(TCLI.FakeBridge):
        async def call(self, cmd, args=None, timeout=30.0):
            if cmd == "timecode_tracks":
                self.plans.append(args)
                return {"timecode": {"tracks": [{"name": "TIMECODE LTC", "kind": "ltc", "key": args["tracks"][0]["key"],
                                                 "origin": "default", "block": "<SOURCE LTC\nD\n>", "item": True,
                                                 "label": "7/8", "length": 98.0}], "warnings": [], "length": 98.0}}
            return await super().call(cmd, args, timeout)
    fb = FB(version="1.5.0")
    monkeypatch.setattr(server.bridge, "call", fb.call)
    res = asyncio.run(server.update_timecode_tracks())
    assert fb.plans[-1]["tail"] == TC.TAIL_S and fb.plans[-1]["tracks"][0]["name"] == "TIMECODE LTC"
    assert res["enabled"] and res["timecode"]["pistes"][0]["sortie"] == "7/8"
    assert any("Propriétés de la source" in w for w in res["warnings"])
    msg = cli._message(dict(res, _x=1), i18n.t("tc_tracks_title"))
    assert "TIMECODE LTC → 7/8 · 98 s · générateur à régler" in msg and "! TIMECODE LTC" in msg
    # pont trop ancien : erreur claire
    fb.version = "1.4.0"
    res = asyncio.run(server.update_timecode_tracks())
    assert res["error"] == i18n.t("tc_old_bridge", "fr")
    # CLI : état écrit pour la fenêtre
    fb.version = "1.5.0"
    assert cli.main(["timecode"]) == 0
    st = json.loads((bridge_dir / "cli_status.json").read_text(encoding="utf-8"))
    assert st["state"] == "done" and st["cmd"] == "timecode" and st["message"].startswith("Pistes timecode mises à jour")


def test_cli_concert_lighting(lang, bridge_dir, resdir, tmp_path):
    import concert_demo as D
    from reacue_mcp import cli, concert as C, prompter
    lang("fr", gma3_fps=30, gma3_tc_start="01:00:00:00")
    ps = D.write_demo(tmp_path / "projects")
    res = C.build_concert("Concert démo", [str(p) for p in ps], 4.0, out_dir=tmp_path / "Concerts", publish=False)
    before = json.loads(res.prompter.read_text(encoding="utf-8"))
    assert before["lighting"]["fps"] == 30
    lang("fr", gma3_fps=25, gma3_tc_start="02:00:00:00")
    assert cli.main(["concert-lighting", "--setlist", str(res.setlist)]) == 0
    st = json.loads((bridge_dir / "cli_status.json").read_text(encoding="utf-8"))
    assert st["state"] == "done" and st["cmd"] == "concert-lighting" and "Concert démo" in st["message"], st
    data = json.loads(res.prompter.read_text(encoding="utf-8"))
    assert data["lighting"]["fps"] == 25 and data["lighting"]["tc_start"] == "02:00:00:00"
    assert data["lighting"]["cues"][0]["tc"].startswith("02:00:") and data["id"] != before["id"]
    folder = tmp_path / "Concerts" / "grandMA3" / LG.clean_name("Concert démo")
    tcx = (folder / f"{LG.clean_name('Concert démo')}_Timecode.xml").read_text(encoding="utf-8")
    assert "Duration=" in tcx and (folder / LG.PLUGIN_DIR / "ReaCue.xml").exists()
    assert any(p.name.startswith(LG.WEB_PREFIX) for p in prompter.WWW_DIR.glob("*"))
    # export désactivé ; prompteur absent : message clair
    lang("fr", gma3_export=False)
    assert cli.main(["concert-lighting", "--setlist", str(res.setlist)]) == 0
    st = json.loads((bridge_dir / "cli_status.json").read_text(encoding="utf-8"))
    assert "désactivé" in st["message"]
    res.prompter.unlink()
    assert cli.main(["concert-lighting", "--setlist", str(res.setlist)]) == 1
    st = json.loads((bridge_dir / "cli_status.json").read_text(encoding="utf-8"))
    assert st["state"] == "error" and "reconstruis le concert" in st["message"]


def test_song_tab_pills_with_lighting_block(concert, tmp_path):
    """régression : le bloc « lighting » d'un morceau contient "concert": false, ce n'est pas un concert"""
    L, g, _ = song_rt(concert, tmp_path)
    W.install(g, tmp_path, structure=True)
    W.open_window(L, g)
    W.frame(L, g); W.frame(L, g)
    assert "Prompteur publié ✓" in TL.texts(g), TL.texts(g)
