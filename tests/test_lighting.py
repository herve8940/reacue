"""Export lumière grandMA3 (lighting.py) : XML identiques à la référence validée sur console, noms nettoyés,
temps projet, concert (gap / créneau / départ du timecode), réglages, génération non bloquante, onglet
Lumière du prompteur. Données entièrement fictives."""
import asyncio
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import concert_demo as D  # noqa: E402
from reacue_mcp import concert as C, i18n, lighting as LG, settings  # noqa: E402

PAGE = (ROOT / "reacue_mcp" / "web" / "prompteur.html").read_text(encoding="utf-8")
GUID = r"(?:[0-9A-F]{2} ){15}[0-9A-F]{2}"


def song(title="Demo Song", sections=None, ci=2, bar=2.0):
    """Morceau au format du prompteur : mesure k (1-based) à (ci + k - 1) * bar s sur la timeline."""
    sections = sections or [("Intro", 1, 4), ("Couplet 1", 5, 12), ("Refrain 1", 13, 20), ("Outro", 21, 24)]
    n = max(b for _, _, b in sections)
    return {"title": title, "count_in_bars": ci, "n_bars": n, "bpm": 120.0, "beats_per_bar": 4,
            "bar_times": [round(k * bar, 4) for k in range(n + ci + 1)],
            "sections": [{"name": nm, "start_bar": a, "end_bar": b} for nm, a, b in sections]}


def cfg(**kw):
    return LG.config({**settings.DEFAULTS, **kw})


def parse(xml: str):
    assert xml.startswith("\ufeff<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    return ET.fromstring(xml.lstrip("\ufeff").encode("utf-8"))


# --------------------------------------------------------------------------- noms, effets, timecode
@pytest.mark.parametrize("raw,clean", [
    ("Démo du soir", "Demo_du_soir"), ("Ça va (démo) !", "Ca_va_demo"), ("  Démo 2 ", "Demo_2"),
    ("l'Été — démo", "l_Ete_demo"), ("", "Song"), ("???", "Song"), ("42", "Seq_42"),
])
def test_clean_name(raw, clean):
    assert LG.clean_name(raw) == clean


def test_unique_names():
    assert LG.unique(["Refrain", "Couplet", "Refrain", "Refrain"]) == ["Refrain", "Couplet", "Refrain (2)", "Refrain (3)"]
    assert LG.unique(["A", "A"], "{}_{}") == ["A", "A_2"]


@pytest.mark.parametrize("name,ctype", [
    ("Intro", "intro"), ("Intro guitare", "intro"), ("Couplet 2", "verse"), ("Verse 1", "verse"),
    ("Pré-refrain 1", "build"), ("Pre-chorus", "build"), ("Refrain 3", "chorus"), ("Chorus 1", "chorus"),
    ("Pont", "bridge"), ("Bridge", "bridge"), ("Solo", "inst"), ("Break", "breakdown"), ("Interlude", "inst"),
    ("Outro", "outro"), ("Coda", "outro"), ("Truc", "custom"),
])
def test_cue_type_from_section_names(name, ctype):
    assert LG.cue_type(name) == ctype


def test_effect_library_fr_en_same_shape():
    fr, en = LG.EFFECT_LIBRARY["fr"], LG.EFFECT_LIBRARY["en"]
    assert fr.keys() == en.keys() == LG.TYPE_LABELS.keys()
    assert all(len(fr[k]) == len(en[k]) for k in fr)
    assert LG.effect_for("chorus", 0, "fr") == "Effet plein, toutes les têtes en mouvement"
    assert LG.effect_for("nope", 0, "en") == "Cue to customise"
    assert LG.effect_for("verse", 4, "fr") == fr["verse"][1]           # rotation comme effectFor()


@pytest.mark.parametrize("sec,fps,tc", [
    (0, 25, "00:00:00:00"), (4.0, 25, "00:00:04:00"), (61.2, 25, "00:01:01:05"), (3600 + 0.5, 25, "01:00:00:13"),
    (1.0 / 30 * 29, 30, "00:00:00:29"), (59.999, 24, "00:01:00:00"), (10.0, 29.97, "00:00:10:00"), (-3, 25, "00:00:00:00"),
])
def test_smpte(sec, fps, tc):
    assert LG.seconds_to_smpte(sec, fps) == tc


def test_parse_tc_and_config():
    assert LG.parse_tc("01:00:00:00") == 3600 and LG.parse_tc("00:00:01:12", 25) == pytest.approx(1.48)
    assert LG.parse_tc("00:00:00:25", 25) is None and LG.parse_tc("bad") is None
    c = cfg()
    assert c == {"export": True, "fps": 25.0, "tc_start": "00:00:00:00", "offset_s": 0.0, "gap_s": None, "slot_s": 0.0}
    c = cfg(gma3_fps="30", gma3_tc_start="01:00:00:00", gma3_song_gap=2, gma3_song_slot=600, gma3_export=False)
    assert (c["fps"], c["offset_s"], c["gap_s"], c["slot_s"], c["export"]) == (30.0, 3600.0, 2.0, 600.0, False)
    c = cfg(gma3_fps=50, gma3_tc_start="xx", gma3_song_gap=-1, gma3_song_slot="n")
    assert (c["fps"], c["tc_start"], c["offset_s"], c["gap_s"], c["slot_s"]) == (25.0, "00:00:00:00", 0.0, None, 0.0)


# --------------------------------------------------------------------------- XML Sequence / Timecode
def test_show_times_are_project_times():
    sh = LG.show_from_songs([song()])
    assert sh["name"] == "Demo_Song" and not sh["concert"]
    tr = sh["tracks"][0]
    # count-in 2 mesures de 2 s : la mesure 1 commence à 4 s du début du projet
    assert [c["time"] for c in tr["cues"]] == [4.0, 12.0, 28.0, 44.0]
    assert [c["n"] for c in tr["cues"]] == [1, 2, 3, 4] and tr["start"] == 0 and tr["duration"] == 52.0
    assert tr["cues"][2]["effect"]["en"] == "Full effect, all heads moving"


def test_sequence_xml_matches_reference():
    sh = LG.show_from_songs([song("Démo du soir", [("Intro", 1, 2), ("Refrain", 3, 4), ("Refrain", 5, 6),
                                                      ("Rock & 'roll' <fin>", 7, 8)])])
    tr = sh["tracks"][0]
    xml = LG.build_sequence_xml(tr["seq"], tr["cues"], "fr")
    root = parse(xml)
    assert root.tag == "GMA3" and root.attrib == {"DataVersion": "2.4.2.2"}
    seq = root.find("Sequence")
    assert seq.get("Name") == "Demo_du_soir" and re.fullmatch(GUID, seq.get("Guid"))
    assert seq.get("ExecutorDisplayMode") == "Data and\rAppearance" and seq.get("Action") == "Pool Default"
    assert 'ExecutorDisplayMode="Data and&#xD;Appearance"' in xml
    cues = seq.findall("Cue")
    assert [c.get("Name") for c in cues] == ["OffCue", "CueZero", "Intro", "Refrain", "Refrain (2)", "Rock & 'roll' <fin>"]
    assert cues[0].get("No") is None and cues[0].get("Release") == "Yes" and cues[0].get("TrigType") == ""
    assert [c.get("No") for c in cues[1:]] == ["  0", "  1", "  2", "  3", "  4"]       # 3 caractères
    assert all(c.find("Part").get("Action") == "Pool Default" and c.find("Part").get("Mode") == "0" for c in cues)
    assert '<Cue Name="Rock &amp; &apos;roll&apos; &lt;fin&gt;" No="  4" AllowDuplicates="">' in xml
    assert "        <!-- Effet suggéré : Wash tamisé, teintes chaudes -->\n        <Cue Name=\"Intro\"" in xml
    assert "Suggested effect: Calm wash" not in xml
    assert "<!-- Suggested effect: Dimmed wash" in LG.build_sequence_xml(tr["seq"], tr["cues"], "en")


def test_timecode_xml_matches_reference():
    s1, s2 = song("Demo Song"), song("Second Demo", [("Intro", 1, 4), ("Chorus", 5, 8)])
    s1.update(start_t=0.0, stop_t=50.0)
    s2.update(start_t=60.0, stop_t=80.0, bar_times=[60.0 + t for t in s2["bar_times"]])
    sh = LG.show_from_songs([s1, s2], "Concert d'été")
    assert sh["name"] == "Concert_d_ete" and sh["concert"]
    xml = LG.build_timecode_xml(LG._tc_tracks(sh, 0.0), "fr")
    root = parse(xml)
    tc = root.find("Timecode")
    assert tc.get("Name") == "" and tc.get("FrameReadout") == "Seconds" and tc.get("TCSlot") == "-1"
    assert tc.get("Duration") == tc.get("Cursor") == "80.00" and tc.get("SwitchOff") == "Keep Playbacks"
    grp = tc.find("TrackGroup")
    assert grp.find("MarkerTrack").get("Name") == "Marker"
    tracks = grp.findall("Track")
    assert [t.get("Name") for t in tracks] == ["Demo_Song", "Second_Demo"]
    for idx, (t, st) in enumerate(zip(tracks, sh["tracks"])):
        assert t.get("Target") == f"ShowData.DataPools.Default.Sequences.{st['seq']}"
        assert "'" not in t.get("Target") and '"' not in t.get("Target")
        rng = t.find("TimeRange")
        assert rng.get("Duration") == "To End" and rng.get("Start") == "0.000"
        evs = rng.find("CmdSubTrack").findall("CmdEvent")
        assert [e.get("CueDestination") for e in evs] == [c["name"] for c in st["cues"]]
        for n, (e, c) in enumerate(zip(evs, st["cues"]), 1):
            assert e.get("Name") == "Goto" and e.get("Time") == f"{st['start'] + c['time']:.3f}"
            rc = e.find("RealtimeCmd")
            assert rc.get("Object") == f"13.13.0.5.{idx}" and rc.get("ExecToken") == "Goto"
            assert rc.get("ValCueDestination") == f"0.5.{idx}.{n * 1000}"
            assert rc.get("FromLocalHardwareFader") == "1" and rc.get("IssuedByTimecode") == "0"
    times = [e.get("Time") for e in tracks[1].iter("CmdEvent")]
    assert times == ["64.000", "72.000"]                       # temps projet du 2e morceau
    assert "Target=\"ShowData.DataPools.Default.Sequences.Second_Demo\">" in xml
    assert xml.count("<!-- Effet suggéré : ") == 6


def test_js_rounding_like_reference():
    assert LG._fixed(1.0005, 3) == "1.001" and LG._fixed(2.5, 0) == "3" and LG._fixed(0.125, 2) == "0.13"
    assert LG._js_round(2.5) == 3 and LG._js_round(-0.5) == 0


def test_conduite_csv():
    sh = LG.show_from_songs([song(sections=[("Intro", 1, 4), ("Pont, \"bis\"", 5, 8)])])
    csv = LG.build_conduite_csv(sh, 25, 3600.0, "fr")
    lines = csv.lstrip("\ufeff").splitlines()
    assert lines[0] == "Timecode,Cue,Libellé,Type,Effet suggéré"
    assert lines[1] == '01:00:04:00,Cue 1,Intro,Intro,"Wash tamisé, teintes chaudes"'
    assert lines[2] == '01:00:12:00,Cue 2,"Pont, ""bis""",Pont,"Rupture d\'ambiance, nouvelle couleur"'
    en = LG.build_conduite_csv(sh, 25, 0, "en").lstrip("\ufeff").splitlines()
    assert en[0] == "Timecode,Cue,Label,Type,Suggested effect" and en[1].startswith("00:00:04:00,Cue 1,Intro,Intro,")


# --------------------------------------------------------------------------- morceau seul
def test_export_song_files_and_web(tmp_path):
    proj = tmp_path / "Demo Song" / "Demo Song.RPP"
    proj.parent.mkdir()
    proj.write_text("<REAPER_PROJECT\n>\n")
    www = tmp_path / "www"
    www.mkdir()
    (www / "reacue_gma3_Old_Song_Sequence.xml").write_text("old")            # morceau précédent : retiré
    (www / "reacue_gma3_Gig__Gig_Timecode.xml").write_text("concert")       # fichiers d'un concert : gardés
    s = song("Démo : Song")
    s["id"] = "x"
    res = LG.export_song(s, str(proj), www, cfg(gma3_tc_start="01:00:00:00"))
    out = proj.parent / "grandMA3"
    names = sorted(p.name for p in out.iterdir())
    assert names == ["Demo_Song_Sequence.xml", "Demo_Song_Timecode.xml", "Demo_Song_conduite.csv"]
    assert res["cues"] == 4 and res["dir"] == str(out)
    assert sorted(p.name for p in www.iterdir()) == ["reacue_gma3_Demo_Song_Sequence.xml",
                                                      "reacue_gma3_Demo_Song_Timecode.xml",
                                                      "reacue_gma3_Demo_Song_conduite.csv",
                                                      "reacue_gma3_Gig__Gig_Timecode.xml"]
    assert (out / "Demo_Song_Timecode.xml").read_bytes() == (www / "reacue_gma3_Demo_Song_Timecode.xml").read_bytes()
    assert (out / "Demo_Song_Sequence.xml").read_bytes().startswith(b"\xef\xbb\xbf<?xml")
    tc = parse((out / "Demo_Song_Timecode.xml").read_text(encoding="utf-8"))
    assert [e.get("Time") for e in tc.iter("CmdEvent")] == ["3604.000", "3612.000", "3628.000", "3644.000"]
    L = s["lighting"]
    assert s["id"] != "x" and L["fps"] == 25 and L["tc_start"] == "01:00:00:00" and L["offset_s"] == 3600
    assert [c["tc"] for c in L["cues"]][:2] == ["01:00:04:00", "01:00:12:00"]
    assert [c["t"] for c in L["cues"]] == [4.0, 12.0, 28.0, 44.0]
    assert [f["url"] for f in L["files"]] == ["reacue_gma3_Demo_Song_Sequence.xml", "reacue_gma3_Demo_Song_Timecode.xml",
                                              "reacue_gma3_Demo_Song_conduite.csv"]


def test_export_song_disabled_or_unsaved(tmp_path):
    s = song()
    assert LG.export_song(s, str(tmp_path / "x.RPP"), tmp_path, cfg(gma3_export=False)) is None
    assert "lighting" not in s and not (tmp_path / "grandMA3").exists()
    res = LG.export_song(s, None, tmp_path / "www", cfg())          # projet non enregistré : dossier web seul
    assert res["files"] == [] and len(res["web"]) == 3 and s["lighting"]["cues"]


# --------------------------------------------------------------------------- réglages
def test_settings_defaults_documented_and_installer(tmp_path):
    s = settings.load_settings(tmp_path / "absent.json")
    assert (s["gma3_export"], s["gma3_fps"], s["gma3_tc_start"], s["gma3_song_gap"], s["gma3_song_slot"]) == \
        (True, 25, "00:00:00:00", None, 0)
    import reacue_setup as RS
    for k in ("gma3_export", "gma3_fps", "gma3_tc_start", "gma3_song_gap", "gma3_song_slot"):
        assert RS.SETTINGS_DEFAULTS[k] == settings.DEFAULTS[k]
        for doc in ("README.md", "LISEZMOI.md"):
            assert f"`{k}`" in (ROOT / doc).read_text(encoding="utf-8"), (doc, k)
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"gma3_export": "false"}))
    assert settings.load_settings(p)["gma3_export"] is False


def test_docs_recommend_timecode_from_reaper():
    for doc, words in (("README.md", ("MTC", "LTC", "grandMA3")), ("LISEZMOI.md", ("MTC", "LTC", "grandMA3")),
                       ("docs/TUTORIAL_en.md", ("MTC", "LTC", "Lighting")),
                       ("docs/TUTORIEL_fr.md", ("MTC", "LTC", "Lumière"))):
        txt = (ROOT / doc).read_text(encoding="utf-8")
        assert all(w in txt for w in words), doc


# --------------------------------------------------------------------------- concert
def build(tmp_path, gap=4.0, **kw):
    demo = D.write_demo(tmp_path / "projects")
    i18n.set_lang("fr")
    return C.build_concert("Concert test", [str(p) for p in demo], gap, out_dir=tmp_path / "Concerts",
                           publish=False, **kw)


def _bar_grid(res):
    root = C.parse_rpp(res.rpp.read_text(encoding="utf-8"))
    pts = [C.tokens(p) for p in root.blocks("TEMPOENVEX")[0].lines("PT")]
    return C.compute_bar_lines(pts, res.songs[-1]["stop"] + 60)[0], pts


def test_concert_default_layout_unchanged(tmp_path):
    res = build(tmp_path)
    for k, d in enumerate(res.songs[1:], 1):
        assert d["start"] == pytest.approx(res.songs[k - 1]["next"])
        assert 4.0 - 1e-6 <= d["start"] - res.songs[k - 1]["stop"]
    sl = json.loads(res.setlist.read_text(encoding="utf-8"))
    assert "layout" not in sl and sl["gap_s"] == 4.0                     # setlist inchangée par défaut
    out = tmp_path / "Concerts" / "grandMA3" / "Concert_test"
    assert sorted(p.name for p in out.iterdir()) == ["Concert_test_Timecode.xml", "Concert_test_conduite.csv",
                                                     "Demo_Song_Sequence.xml", "Second_Demo_Sequence.xml",
                                                     "Third_Demo_Sequence.xml"]
    tc = parse((out / "Concert_test_Timecode.xml").read_text(encoding="utf-8"))
    tracks = tc.find("Timecode/TrackGroup").findall("Track")
    assert [t.get("Name") for t in tracks] == ["Demo_Song", "Second_Demo", "Third_Demo"]
    pj = json.loads(res.prompter.read_text(encoding="utf-8"))
    regions = [r for r in C.parse_rpp(res.rpp.read_text(encoding="utf-8")).lines("MARKER") if " 1 " in r]
    for idx, (t, sg, side) in enumerate(zip(tracks, pj["songs"], res.songs)):
        evs = list(t.iter("CmdEvent"))
        assert {e.find("RealtimeCmd").get("Object") for e in evs} == {f"13.13.0.5.{idx}"}
        assert [e.find("RealtimeCmd").get("ValCueDestination") for e in evs] == \
            [f"0.5.{idx}.{n * 1000}" for n in range(1, len(evs) + 1)]
        # temps = début des régions du projet concert (temps projet REAPER)
        starts = [round(sg["bar_times"][s["start_bar"] - 1 + sg["count_in_bars"]], 3) for s in sg["sections"]]
        assert [float(e.get("Time")) for e in evs] == pytest.approx(starts, abs=1e-3)
        assert float(evs[0].get("Time")) == pytest.approx(side["bar1"], abs=1e-3)
    txt = res.rpp.read_text(encoding="utf-8")
    first = float(next(C.tokens(r)[2] for r in txt.splitlines() if "Second Demo · Intro" in r))
    assert float(tracks[1].find(".//CmdEvent").get("Time")) == pytest.approx(first, abs=1e-3)
    seq = parse((out / "Second_Demo_Sequence.xml").read_text(encoding="utf-8"))
    assert [c.get("Name") for c in seq.find("Sequence").findall("Cue")][2:] == ["Intro", "Couplet 1", "Refrain 1", "Solo"]
    assert pj["lighting"]["concert"] is True and len(pj["lighting"]["cues"]) == 11
    assert res.summary()["grandma3"]["cues"] == 11


def test_concert_gap_setting(tmp_path, lang):
    lang("fr", gma3_song_gap=12)
    res = build(tmp_path)
    for k, d in enumerate(res.songs[1:], 1):
        assert d["start"] - res.songs[k - 1]["stop"] >= 12.0 - 1e-6
    sl = json.loads(res.setlist.read_text(encoding="utf-8"))
    assert sl["layout"] == {"gap_s": 12.0, "slot_s": 0.0} and sl["gap_s"] == 4.0
    grid, _ = _bar_grid(res)
    assert all(min(abs(g - d["start"]) for g in grid) < 1e-4 for d in res.songs)


def test_concert_slot_and_tc_start(tmp_path, lang):
    lang("fr", gma3_song_slot=60, gma3_tc_start="01:00:00:00", gma3_fps=30)
    res = build(tmp_path)
    assert [d["start"] for d in res.songs] == [0.0, 60.0, 120.0]
    assert [d["next"] for d in res.songs[:2]] == [60.0, 120.0]
    grid, pts = _bar_grid(res)
    # chaque morceau commence sur une barre de mesure du projet (grille juste, blanc en mesures entières)
    assert all(min(abs(g - d["start"]) for g in grid) < 1e-4 for d in res.songs)
    assert any(abs(float(p[1]) - res.songs[0]["stop"]) < 6 and len(p) == 4 for p in pts)     # tempo du blanc
    # bar1 du 2e morceau = 60 s + count-in ; le timecode ajoute 1 h
    out = tmp_path / "Concerts" / "grandMA3" / "Concert_test"
    tc = parse((out / "Concert_test_Timecode.xml").read_text(encoding="utf-8"))
    t2 = float(tc.find("Timecode/TrackGroup").findall("Track")[1].find(".//CmdEvent").get("Time"))
    assert t2 == pytest.approx(3600 + res.songs[1]["bar1"], abs=1e-3)
    csv = (out / "Concert_test_conduite.csv").read_text(encoding="utf-8").lstrip("\ufeff").splitlines()
    assert csv[0].startswith("Morceau,Timecode,") and csv[5].startswith("Second_Demo,01:01:0")
    # le .concert.lua (action ReaCue - Concert) et le prompteur suivent le même placement
    side = res.sidecar.read_text(encoding="utf-8")
    assert re.search(r'\["start"\]=60(\.0)?[,}]', side) and re.search(r'\["start"\]=120(\.0)?[,}]', side)
    pj = json.loads(res.prompter.read_text(encoding="utf-8"))
    assert [s["start_t"] for s in pj["songs"]] == [0.0, 60.0, 120.0]
    assert pj["lighting"]["fps"] == 30 and pj["lighting"]["slot_s"] == 60
    # la phase lente (accords, paroles) relit le placement enregistré, même si les réglages ont changé
    lang("fr")
    again = C._reload(res.setlist)
    assert [d["start"] for d in again.songs] == [0.0, 60.0, 120.0]


def test_place_songs_slot_skips_too_short_gap():
    class S:          # morceau factice : 4/4 à 120 BPM, fin à 55 s
        def __init__(self, end):
            self.bar_lines = [k * 2.0 for k in range(100)]
            self.i0, self.n_bars, self.beats_per_bar, self.denominator = 0, int(end / 2), 4, 4
            self.next_start = end
    pl = C.place_songs([S(59.9), S(10.0)], slot_s=60)
    # 0,1 s jusqu'à 60 s : tempo du blanc impossible -> créneau suivant (120 s)
    assert pl[1]["shift"] == 120.0 and pl[0]["fill"][1] >= 1 and pl[0]["fill"][0] <= C.MAX_FILL_BPM
    assert C.place_songs([S(60.0), S(10.0)], slot_s=60)[1]["shift"] == 60.0


# --------------------------------------------------------------------------- non bloquant
def test_concert_export_failure_never_blocks(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("disque plein")
    monkeypatch.setattr(LG, "export_concert", boom)
    res = build(tmp_path)
    assert res.rpp.exists() and res.prompter.exists()
    assert any("grandMA3" in w and "disque plein" in w for w in res.warnings)


def test_prepare_song_export_and_failure_never_blocks(monkeypatch, lang, bridge_dir, resdir, tmp_path):
    import test_cli as TC
    from reacue_mcp import cli, server
    fb = TC.FakeBridge()
    proj = tmp_path / "Demo" / "Demo.RPP"
    proj.parent.mkdir()
    proj.write_text("x")
    orig = fb.call

    async def call(cmd, args=None, timeout=30.0):
        if cmd == "ping":
            return dict(await orig(cmd, args, timeout), project=str(proj))
        return await orig(cmd, args, timeout)
    monkeypatch.setattr(server.bridge, "call", call)
    monkeypatch.setattr(server.bridge, "alive", fb.alive)
    monkeypatch.setattr(server, "analyze_stems", lambda *a, **k: TC.fake_analysis())
    monkeypatch.setattr(server, "analyze", lambda *a, **k: TC.fake_analysis())
    monkeypatch.setattr(server, "Voice", TC.FakeVoice)
    monkeypatch.setattr(server.chords, "cached_chords", lambda *a, **k: None)
    monkeypatch.setattr(server.lyrics, "cached_lyrics", lambda *a, **k: None)
    monkeypatch.setattr(server.drums, "cached_drums", lambda *a, **k: None)
    monkeypatch.setattr(server.prompter, "stem_activity", lambda *a, **k: {})
    (bridge_dir / "last_session.json").unlink(missing_ok=True)
    lang("en")
    assert cli.main(["prepare"]) == 0
    msg = TC.status(bridge_dir)["message"]
    assert "grandMA3 lighting: 5 cues" in msg
    files = sorted(p.name for p in (proj.parent / "grandMA3").iterdir())
    assert files == ["Demo_Sequence.xml", "Demo_Timecode.xml", "Demo_conduite.csv"]
    pub = json.loads((resdir / "reaper_www_root" / "reacue_song.json").read_text(encoding="utf-8"))
    assert [c["name"] for c in pub["lighting"]["cues"]] == ["Intro", "Verse 1", "Chorus 1", "Bridge", "Chorus 2"]
    assert pub["lighting"]["cues"][0]["t"] == pytest.approx(pub["bar_times"][pub["count_in_bars"]])
    assert (resdir / "reaper_www_root" / "reacue_gma3_Demo_Timecode.xml").exists()
    # échec de l'export : la préparation réussit quand même (avertissement)
    monkeypatch.setattr(LG, "export_song", lambda *a, **k: (_ for _ in ()).throw(OSError("read-only")))
    res = asyncio.run(server.set_sections([{"prompteur_seul": True}]))
    assert "read-only" in res["prompteur"]["warning"] and "grandMA3" in res["prompteur"]["warning"]
    (bridge_dir / "last_session.json").unlink(missing_ok=True)


# --------------------------------------------------------------------------- page du prompteur
def test_prompter_page_has_light_role_fr_en():
    assert '<button data-role="light"></button>' in PAGE and 'id="light"' in PAGE
    assert 'regie: "Régie", light: "Lumière"' in PAGE and 'regie: "Stage control", light: "Lighting"' in PAGE
    assert 'light: ["Lumière", "cues grandMA3' in PAGE and 'light: ["Lighting", "grandMA3 cues' in PAGE
    for k in ("lCurK", "lCues", "lFiles", "lNote", "lCfg", "lNone"):
        assert PAGE.count(f"{k}:") == 2, k                     # une traduction FR et une EN
    assert "MTC" in PAGE and "LTC" in PAGE
    low = PAGE.lower()                                                      # aucune dépendance internet
    assert "://cdn" not in low and "jszip" not in low and 'src="http' not in low
    assert "song.lighting" in PAGE and "concert.lighting" in PAGE


def test_page_smpte_matches_python():
    """La fonction smpte() de la page fait le même calcul que lighting.seconds_to_smpte."""
    js = re.search(r"function smpte\(sec, fps\) \{(.+?)\n\}", PAGE, re.S).group(1)
    assert "Math.round(sec * fps)" in js and "% Math.round(fps)" in js and "Math.floor(tf / fps)" in js


def test_page_light_tab_renders(tmp_path):
    pytest.importorskip("playwright")
    import make_screenshots as M
    from playwright.sync_api import sync_playwright
    srv, base = M.serve()
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                pytest.skip(f"Chromium non disponible : {e}")
            for lg, cur, label in (("fr", "Refrain 1", "Lumière"), ("en", "Chorus 1", "Lighting")):
                for data, pos in ((M.demo_song(lg), M.bar_time(31, 0.5)), (M.demo_concert(lg), None)):
                    M.FakeReaper.song = data
                    if pos is None:      # concert : 2e morceau, refrain
                        s2 = data["songs"][1]
                        pos = M.bar_time(31, 0.5, s2["bpm"], s2["start_t"])
                    M.FakeReaper.pos = pos
                    page = browser.new_page(viewport=M.PHONE)
                    errs = []
                    page.on("pageerror", lambda e: errs.append(str(e)))
                    page.goto(f"{base}/prompteur.html?role=light&lang={lg}")
                    page.wait_for_selector("#lCues .row.cur", timeout=8000)
                    assert page.text_content("#roleBtn") == label
                    assert page.text_content("#lCues .row.cur .nm") == cur
                    assert page.text_content("#lCurV") == cur
                    hrefs = page.eval_on_selector_all("#lFiles a", "a => a.map(x => x.getAttribute('href'))")
                    assert any(h.endswith("_Timecode.xml") for h in hrefs) and all(h.startswith("reacue_gma3_") for h in hrefs)
                    assert re.fullmatch(r"01:\d\d:\d\d:\d\d", page.text_content("#lTc"))
                    assert not errs, errs
                    page.close()
            browser.close()
    finally:
        srv.shutdown()
