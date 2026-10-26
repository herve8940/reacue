"""Bibliothèque de ReaCue Studio (écran BIBLIO) et notes de section (écran GROUPE), côté Python :
reacue_library.json (projets du dossier des morceaux + morceaux des concerts, composants, structure), étapes
du parcours (calcul automatique, réglage manuel lu dans l'état durable écrit par la fenêtre ReaCue), notes
recopiées dans le prompteur publié (morceau seul et concert), morceau ouvert depuis BIBLIO, CLI. Projets fictifs."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import concert_demo as D  # noqa: E402
from reacue_mcp import concert as C, i18n, library as LB, prompter  # noqa: E402


@pytest.fixture
def demo(tmp_path, bridge_dir, monkeypatch):
    """Dossier des projets fictif (3 morceaux), un concert construit, une setlist pas construite."""
    i18n.set_lang("fr")
    root = tmp_path / "REAPER Media"
    ps = D.write_demo(root)
    (root / "Demo Song" / "Demo Song-bak.RPP").write_text("x", encoding="utf-8")          # sauvegarde : ignorée
    stems = root / "Demo Song-stems"
    stems.mkdir()
    (stems / "x.RPP").write_text("x", encoding="utf-8")                                   # dossier de stems : ignoré
    cdir = root / "Concerts"
    C.build_concert("Concert test", [str(p) for p in ps[:2]], 4.0, out_dir=cdir, publish=False)
    (cdir / "Plus tard.setlist.json").write_text(json.dumps({"name": "Plus tard", "songs": [str(ps[2])]}), encoding="utf-8")
    www = tmp_path / "www"
    monkeypatch.setattr(prompter, "WWW_DIR", www)
    monkeypatch.setattr(C, "media_dir", lambda: root)
    monkeypatch.setattr(C, "concert_dir", lambda: cdir)
    state = bridge_dir / LB.STATE_NAME
    yield {"root": root, "cdir": cdir, "ps": ps, "www": www, "state": state}
    state.unlink(missing_ok=True)


def write_state(demo, songs):
    demo["state"].write_text(json.dumps({"version": 1, "songs": songs}), encoding="utf-8")


def test_library_lists_projects_and_concerts(demo):
    d = LB.build_library()
    titles = [s["title"] for s in d["songs"]]
    assert titles == ["Demo Song", "Second Demo", "Third Demo"]                      # sans sauvegarde ni stems
    a, b, c = d["songs"]
    assert a["bpm"] == 120 and a["sig"] == "4/4" and a["bars"] == 24 and a["duration_s"] == pytest.approx(48.0)
    assert [x["name"] for x in a["sections"]] == ["Intro", "Verse 1", "Chorus 1", "Outro"]
    assert [x["bars"] for x in a["sections"]] == [4, 8, 8, 4] and all(x["color"].startswith("#") for x in a["sections"])
    assert a["prepared"] and a["components"]["stems"] == 4 and c["components"]["stems"] == 0     # mix seul
    assert a["concerts"] == ["Concert test"] and c["concerts"] == ["Plus tard"]
    assert {s["stage"] for s in d["songs"]} == {"new"} and a["stage_manual"] is None
    assert [x["name"] for x in d["concerts"]] == ["Concert test", "Plus tard"]
    assert d["concerts"][0]["built"] and not d["concerts"][1]["built"]
    assert d["concerts"][0]["songs"] == [a["key"], b["key"]]
    assert a["key"] == LB.song_key(a["path"]) and a["key"] == a["key"].lower() and "\\" not in a["key"]
    assert d["stages"] == ["new", "solo", "band", "stage"] and d["rules"]["stage_days"] == 2
    assert d["id"] == LB.build_library()["id"]                                      # stable (sauf « generated »)


def test_auto_stages_and_manual_override(demo):
    a, b, c = (str(p) for p in demo["ps"])
    write_state(demo, {
        LB.song_key(a): {"solo_s": 400, "band_s": 900, "days": {"2026-10-20": 300, "2026-10-26": 600}},
        LB.song_key(b): {"solo_s": 310, "band_s": 100},
        LB.song_key(c): {"solo_s": 0, "band_s": 200, "days": {"2026-10-26": 200}, "stage": "stage"},
    })
    d = {s["title"]: s for s in LB.build_library()["songs"]}
    assert d["Demo Song"]["stage"] == "stage" and d["Demo Song"]["practice"]["band_days"] == 2
    assert d["Second Demo"]["stage"] == "solo" and d["Second Demo"]["practice"]["solo_min"] == pytest.approx(5.2)
    assert d["Third Demo"]["stage_auto"] == "band" and d["Third Demo"]["stage_manual"] == "stage"
    assert d["Third Demo"]["stage"] == "stage"
    # règles
    assert LB.auto_stage({}, True) == "new"
    assert LB.auto_stage({"solo_s": 299}, True) == "new" and LB.auto_stage({"solo_s": 300}, True) == "solo"
    assert LB.auto_stage({"band_s": 180}, False) == "band"
    two_days = {"band_s": 500, "days": {"d1": 130, "d2": 120}}
    assert LB.auto_stage(two_days, True) == "stage" and LB.auto_stage(two_days, False) == "band"   # préparé exigé
    assert LB.auto_stage({"band_s": 500, "days": {"d1": 400, "d2": 60}}, True) == "band"         # 2e jour trop court
    assert LB.stage_of({"stage": "bidon"}, True) == ("new", "new", None)
    # état illisible : rien ne casse
    demo["state"].write_text("{pas du json", encoding="utf-8")
    assert {s["stage"] for s in LB.build_library()["songs"]} == {"new"}


def test_published_summary_completes_components(demo):
    p = demo["ps"][0]
    song = LB.song_from_project(p)
    song["chords"] = [{"bar": 1, "chords": [{"beat": 1, "chord": "Am"}]}]
    song["lyrics"] = [{"i": 0, "text": "la"}] * 12
    song["key"] = {"chord": "Am", "fr": "La mineur", "en": "A minor"}
    LB.record_song(song, p, lighting=True)
    s = next(x for x in LB.build_library()["songs"] if x["title"] == "Demo Song")
    assert s["components"]["chords"] and s["components"]["lyrics"] == 12 and s["components"]["lighting"]
    assert s["key_name"]["chord"] == "Am" and s["published"]


def test_attach_notes_and_song_from_project(demo):
    p = str(demo["ps"][0])
    write_state(demo, {LB.song_key(p): {"notes": {"5": "Tout le monde s'arrête sur le 4", "13": ""}}})
    song = LB.song_from_project(p)
    assert song["project"] == p and song["title"] == "Demo Song"
    notes = {x["start_bar"]: x["notes"] for x in song["sections"]}
    assert notes == {1: "", 5: "Tout le monde s'arrête sur le 4", 13: "", 21: ""}
    assert song["bar_times"][0] == pytest.approx(0.0) and song["count_in_bars"] == 2
    old = song["id"]
    LB.attach(song, p, {"songs": {LB.song_key(p): {"notes": {"5": "autre"}}}})
    assert song["sections"][1]["notes"] == "autre" and song["id"] != old
    with pytest.raises(ValueError):                                                 # pas préparé : pas de régions
        bare = demo["root"] / "Nu.RPP"
        bare.write_text('<REAPER_PROJECT 0.1 "7.0" 0 0\n  TEMPO 120 4 4 0\n>\n', encoding="utf-8")
        LB.song_from_project(bare)


def test_notes_republished_single_and_concert(demo):
    a = str(demo["ps"][0])
    single = LB.song_from_project(a)
    prompter.publish(single, demo["www"])
    assert (demo["www"] / LB.LIBRARY_NAME).exists()                                # publication -> bibliothèque
    write_state(demo, {LB.song_key(a): {"notes": {"5": "Crash sur le 1"}}})
    out = LB.apply_notes_published(demo["www"])
    pub = json.loads((demo["www"] / "reacue_song.json").read_text(encoding="utf-8"))
    assert out["updated"] and pub["sections"][1]["notes"] == "Crash sur le 1" and pub["id"] != single["id"]
    assert not LB.apply_notes_published(demo["www"])["updated"]                     # rien de nouveau
    # concert : reacue_song.json et <concert>.prompteur.json (sinon la fenêtre republierait l'ancien)
    res = C.build_from_setlist(demo["cdir"] / "Concert test.setlist.json", publish=True)
    data = json.loads((demo["www"] / "reacue_song.json").read_text(encoding="utf-8"))
    assert data["concert"]["name"] == "Concert test"
    assert [s["project"] for s in data["songs"]] == [str(p.resolve()) for p in demo["ps"][:2]]
    assert data["songs"][0]["sections"][1]["notes"] == "Crash sur le 1"            # notes reprises à la construction
    b = data["songs"][1]["project"]
    write_state(demo, {LB.song_key(a): {"notes": {"5": "Crash sur le 1"}}, LB.song_key(b): {"notes": {"13": "Solo de basse"}}})
    out = LB.apply_notes_published(demo["www"])
    pub = json.loads((demo["www"] / "reacue_song.json").read_text(encoding="utf-8"))
    side = json.loads(res.prompter.read_text(encoding="utf-8"))
    assert out["concert_file"] == str(res.prompter)
    assert pub["songs"][1]["sections"][2]["notes"] == "Solo de basse" and pub["id"] != data["id"]
    assert side == pub


def test_cli_library_notes_and_open_song(demo, capsys):
    from reacue_mcp import cli
    assert cli.main(["library"]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out == {"songs": 3, "concerts": 2}
    lib = json.loads((demo["www"] / LB.LIBRARY_NAME).read_text(encoding="utf-8"))
    assert len(lib["songs"]) == 3
    # ouverture depuis BIBLIO : prompteur publié avec le projet (structure, puis extras)
    p = str(demo["ps"][1])
    assert cli.main(["open-song", "--project", p]) == 0
    pub = json.loads((demo["www"] / "reacue_song.json").read_text(encoding="utf-8"))
    assert pub["title"] == "Second Demo" and pub["project"] == p and "concert" not in pub
    assert LB.song_key(LB.published_project()) == LB.song_key(p)
    assert cli.main(["open-song"]) == 2
    write_state(demo, {LB.song_key(p): {"notes": {"5": "On ralentit"}}})
    assert cli.main(["notes"]) == 0
    pub = json.loads((demo["www"] / "reacue_song.json").read_text(encoding="utf-8"))
    assert pub["sections"][1]["notes"] == "On ralentit"


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_library_language(demo, lang, bridge_dir):
    (bridge_dir / "reacue_settings.json").write_text(json.dumps({"language": lang}), encoding="utf-8")
    try:
        i18n.set_lang(lang)
        assert LB.build_library()["language"] == lang
    finally:
        (bridge_dir / "reacue_settings.json").unlink(missing_ok=True)
        i18n.set_lang("fr")
