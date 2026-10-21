"""Mode concert, côté Python : construction à partir de projets de démonstration GÉNÉRÉS (fictifs),
CLI, outil MCP et passage par set_sections. Aucun REAPER, aucun projet réel."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import concert_demo as D  # noqa: E402
from reacue_mcp import concert as C, i18n  # noqa: E402


@pytest.fixture
def demo(tmp_path):
    return D.write_demo(tmp_path / "projects")


def build(demo, tmp_path, lang="fr", **kw):
    i18n.set_lang(lang)
    try:
        return C.build_concert("Concert test", [str(p) for p in demo], 4.0, out_dir=tmp_path / "Concerts",
                               publish=False, **kw)
    finally:
        i18n.set_lang("fr")


def test_build_concert_timeline(demo, tmp_path):
    res = build(demo, tmp_path)
    assert not res.warnings, res.warnings
    titles = [d["title"] for d in res.songs]
    assert titles == ["Demo Song", "Second Demo", "Third Demo"]
    for k, (d, s) in enumerate(zip(res.songs, res.song_srcs)):
        # chaque morceau commence sur une barre de mesure, après le précédent ; décompte de 2 mesures
        assert d["countin"] == pytest.approx(d["start"]) and d["bar1"] > d["start"]
        assert d["stop"] > d["song_end"] >= d["bar1"]
        if k:
            assert d["start"] == pytest.approx(res.songs[k - 1]["next"])
            assert d["start"] - res.songs[k - 1]["stop"] >= 4.0 - 1e-6
    assert res.songs[0]["bars"] == 24 and res.songs[2]["beatmap"] is True and res.songs[0]["beatmap"] is False
    txt = res.rpp.read_text(encoding="utf-8")
    root = C.parse_rpp(txt)
    names = [C.tokens(t.first("NAME"))[1] for t in root.blocks("TRACK")]
    assert names == ["Chant", "Batterie", "Basse", "Guitares", "Guitare solo", "Mix", "CUES", "VOIX", "CLICK"]
    # régions « Titre · Section », marqueurs de morceaux, lignes de règle
    assert '"Second Demo · Refrain 1"' in txt and '"1 · Demo Song"' in txt and "RULERLANE 1 0 Morceaux" in txt
    # carte de tempo : marqueurs de chaque morceau décalés ; tempo variable du 3e morceau conservé
    pts = [C.tokens(p) for p in root.blocks("TEMPOENVEX")[0].lines("PT")]
    starts = [float(p[1]) for p in pts]
    assert starts == sorted(starts) and len(pts) >= 3 + 16
    assert any(abs(float(p[1]) - res.songs[1]["start"]) < 1e-6 and float(p[2]) == 150.0 for p in pts)
    # items : déplacés, GUID neufs, fichiers en chemins absolus
    items = [it for tr_ in root.blocks("TRACK") for it in tr_.blocks("ITEM")]
    files = [C._source_file(it) for it in items if C._source_file(it)]
    assert files and all(Path(f).is_absolute() for f in files)
    guids = [it.first("GUID") for it in items if it.first("GUID")]
    assert len(guids) == len(set(guids))
    # fichiers compagnons
    side = res.sidecar.read_text(encoding="utf-8")
    assert side.startswith("-- ReaCue") and "return {" in side
    sl = json.loads(res.setlist.read_text(encoding="utf-8"))
    assert [e["title"] for e in sl["songs"]] == titles and sl["gap_s"] == 4.0
    pj = json.loads(res.prompter.read_text(encoding="utf-8"))
    assert pj["concert"]["n"] == 3 and len(pj["songs"]) == 3 and pj["language"] == "fr"
    s2 = pj["songs"][1]
    assert s2["start_t"] == pytest.approx(res.songs[1]["start"]) and s2["next_title"] == "Third Demo"
    assert s2["bar_times"][0] == pytest.approx(res.songs[1]["start"])
    assert len(s2["bar_times"]) == s2["n_bars"] + s2["count_in_bars"] + 1
    assert pj["songs"][2]["next_title"] is None


def test_build_concert_english_and_voice_track(tmp_path):
    ps = D.write_demo(tmp_path / "p", voice_track="VOICE")
    res = build(ps, tmp_path, lang="en")
    txt = res.rpp.read_text(encoding="utf-8")
    names = [C.tokens(t.first("NAME"))[1] for t in C.parse_rpp(txt).blocks("TRACK")]
    assert names[:4] == ["Vocals", "Drums", "Bass", "Guitars"] and "VOICE" in names and "VOIX" not in names
    assert "RULERLANE 1 0 Songs" in txt
    assert json.loads(res.prompter.read_text(encoding="utf-8"))["language"] == "en"


def test_find_project_by_name_and_settings_dirs(demo, tmp_path, lang):
    lang("fr", projects_dir=str(tmp_path / "projects"))
    assert C.media_dir() == tmp_path / "projects"
    assert C.concert_dir() == tmp_path / "projects" / "Concerts"
    assert C.find_project("second demo") == demo[1].resolve()
    with pytest.raises(FileNotFoundError):
        C.find_project("does not exist")
    lang("en", projects_dir=str(tmp_path / "projects"), concert_dir=str(tmp_path / "Shows"))
    assert C.concert_dir() == tmp_path / "Shows"


def test_song_without_regions_warns(tmp_path):
    p = D.write_song(tmp_path / "x", "Bare", 120.0, [("Intro", 4, (1, 2, 3))], ["Drums"])
    txt = re.sub(r"\n\s*MARKER \d+ [\d.]+ \"(Intro|)\" 1[^\n]*", "", p.read_text(encoding="utf-8"))
    p.write_text(txt, encoding="utf-8")
    res = build([p], tmp_path)
    assert any("Bare" in w and "région" in w for w in res.warnings)


def test_rebuild_from_setlist_and_reload(demo, tmp_path):
    res = build(demo, tmp_path)
    again = C.build_from_setlist(res.setlist, publish=False)
    assert [d["start"] for d in again.songs] == [d["start"] for d in res.songs]
    back = C._reload(res.setlist)
    assert [d["stop"] for d in back.songs] == pytest.approx([d["stop"] for d in res.songs])


def test_extras_use_per_song_caches(demo, tmp_path, monkeypatch):
    """Accords, paroles, batterie : un cache par morceau, un échec ne bloque pas les autres."""
    from reacue_mcp import chords, lyrics, drums, prompter
    res = build(demo, tmp_path)
    seen = []
    monkeypatch.setattr(prompter, "stem_activity", lambda a, items, cache=None: seen.append(Path(cache).name) or {})
    monkeypatch.setattr(chords, "cached_chords", lambda a, items, key=None, cache=None: [])
    monkeypatch.setattr(lyrics, "cached_lyrics", lambda a, items, cache=None: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(drums, "cached_drums", lambda a, items, cache=None: None)
    data = C.concert_prompter(res, extras=True)
    assert len(data["songs"]) == 3
    assert len(set(seen)) == 3                       # un cache par morceau
    assert any("lyrics" in w for w in data["songs"][0].get("warnings", []))


def test_cli_concert(demo, tmp_path, bridge_dir, lang, monkeypatch):
    from reacue_mcp import cli
    lang("en", concert_dir=str(tmp_path / "Shows"))
    monkeypatch.setattr(C, "extras_from_setlist", lambda p, log=None: {})
    rc = cli.main(["concert", "--name", "Show", "--songs"] + [str(p) for p in demo])
    st = json.loads((bridge_dir / "cli_status.json").read_text(encoding="utf-8"))
    assert rc == 0 and st["state"] == "done" and st["cmd"] == "concert", st
    assert "Concert “Show” built" in st["message"] and "2. Second Demo" in st["message"]
    assert (tmp_path / "Shows" / "Show.RPP").exists()
    rc = cli.main(["concert", "--setlist", str(tmp_path / "Shows" / "Show.setlist.json")])
    assert rc == 0
    rc = cli.main(["concert"])                          # ni setlist ni morceaux : erreur claire
    st = json.loads((bridge_dir / "cli_status.json").read_text(encoding="utf-8"))
    assert rc == 1 and st["state"] == "error" and "--setlist" in st["message"]


def test_mcp_build_concert_and_set_sections(demo, tmp_path, bridge_dir, lang, monkeypatch):
    import asyncio
    from reacue_mcp import server
    lang("fr", concert_dir=str(tmp_path / "Shows"))
    spawned = []
    monkeypatch.setattr(server, "_spawn_concert_extras", lambda p: spawned.append(p))
    monkeypatch.setattr(C.prompter if hasattr(C, "prompter") else __import__("reacue_mcp.prompter").prompter,
                        "publish", lambda data, www=None: {"page": "x"})
    out = asyncio.run(server.build_concert("Concert MCP", [str(p) for p in demo]))
    assert out["concert"] == "Concert MCP" and len(out["morceaux"]) == 3 and spawned
    assert "ReaCue - Concert" in out["ouvrir"]
    # passage par set_sections (liste d'outils figée dans une conversation) : même résultat
    out2 = asyncio.run(server.set_sections([{"concert": {"name": "Concert MCP 2", "songs": [str(demo[0])]}}]))
    assert out2["concert"] == "Concert MCP 2" and (tmp_path / "Shows" / "Concert MCP 2.RPP").exists()
    bad = asyncio.run(server.build_concert("X", ["nope"]))
    assert "error" in bad


def test_live_profile_build_rebuild_and_edit(demo, tmp_path):
    """« Joué en live » : profil enregistré dans la setlist, gardé à la reconstruction, modifiable sans
    reconstruire ; noms FR/EN acceptés ; exceptions par morceau nettoyées."""
    res = build(demo, tmp_path, live=["Batterie", "bass", "Guitares"],
                live_exceptions={"Second Demo": {"Basse": "stem"}, "3": ["keys"]})
    d = json.loads(res.setlist.read_text(encoding="utf-8"))
    assert d["live"] == ["drums", "bass", "guitars"]
    assert d["live_exceptions"] == {"Second Demo": {"bass": "stem"}, "Third Demo": {"keys": "live"}}
    s = res.summary()
    assert s["joue_en_live"] == ["Batterie", "Basse", "Guitares"] and "Second Demo" in s["exceptions_par_morceau"]
    # reconstruction depuis la setlist : profil gardé
    res2 = C.build_from_setlist(res.setlist, publish=False)
    assert json.loads(res2.setlist.read_text(encoding="utf-8"))["live"] == ["drums", "bass", "guitars"]
    # reconstruction sans profil donné (build_concert) : celui déjà enregistré est repris
    res3 = build(demo, tmp_path)
    assert json.loads(res3.setlist.read_text(encoding="utf-8"))["live_exceptions"]["Second Demo"] == {"bass": "stem"}
    # modification sans reconstruire
    out = C.set_live_profile(res.setlist, live=["Drums"], exceptions={"Second Demo": None, "Demo Song": {"vocals": "live"}})
    d = json.loads(res.setlist.read_text(encoding="utf-8"))
    assert d["live"] == ["drums"] and d["live_exceptions"] == {"Demo Song": {"vocals": "live"}, "Third Demo": {"keys": "live"}}
    assert out["joue_en_live"] == ["Batterie"] and "reconstruire" in out["info"]
    out = C.set_live_profile(res.setlist, exceptions={}, replace_exceptions=True)
    assert json.loads(res.setlist.read_text(encoding="utf-8"))["live_exceptions"] == {}
    with pytest.raises(ValueError):
        C.set_live_profile(res.setlist, live=["trombone"])
    with pytest.raises(ValueError):
        C.set_live_profile(res.setlist, exceptions={"Nope": {"bass": "stem"}})
    with pytest.raises(FileNotFoundError):
        C.set_live_profile(tmp_path / "missing.setlist.json")


def test_mcp_live_profile(demo, tmp_path, bridge_dir, lang, monkeypatch):
    import asyncio
    from reacue_mcp import server
    lang("en", concert_dir=str(tmp_path / "Shows"))
    monkeypatch.setattr(server, "_spawn_concert_extras", lambda p: None)
    out = asyncio.run(server.build_concert("Gig", [str(p) for p in demo], 4.0, ["Drums", "Bass"]))
    assert out["joue_en_live"] == ["Drums", "Bass"]
    sl = tmp_path / "Shows" / "Gig.setlist.json"
    out = asyncio.run(server.set_live_profile("Gig", ["vocals"], {"Second Demo": {"keys": "live"}}))
    assert out["joue_en_live"] == ["Vocals"] and "rebuild" in out["info"]
    assert json.loads(sl.read_text(encoding="utf-8"))["live_exceptions"] == {"Second Demo": {"keys": "live"}}
    # même chose par set_sections (liste d'outils figée)
    out = asyncio.run(server.set_sections([{"concert_live": {"concert": "Gig", "live": []}}]))
    assert out["joue_en_live"] == [] and json.loads(sl.read_text(encoding="utf-8"))["live"] == []
    out = asyncio.run(server.set_sections([{"concert": {"name": "Gig 2", "songs": [str(demo[0])], "live": ["keys"]}}]))
    assert json.loads((tmp_path / "Shows" / "Gig 2.setlist.json").read_text(encoding="utf-8"))["live"] == ["keys"]
    bad = asyncio.run(server.set_live_profile("Nope"))
    assert "error" in bad
