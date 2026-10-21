"""Régions modifiées à la main dans REAPER : reprises comme structure à la préparation suivante."""
import json

import pytest

from reacue_mcp import cli, server, i18n
from reacue_mcp.analysis import Section
from reacue_mcp.regions import regions_to_sections, same_structure

from test_cli import FakeBridge, env as _env, fake_analysis, status  # noqa: F401  (fixture)

# grille de test (fake_analysis) : mesure k du morceau = 4.0 + 2 k s sur la timeline (count-in 2 mesures)
BT = [0.0, 2.0] + [4.0 + 2 * k for k in range(41)]
OLD = [Section(0, 8, "A", "Intro"), Section(8, 24, "B", "Couplet 1"), Section(24, 32, "C", "Refrain 1"),
       Section(32, 36, "D", "Pont"), Section(36, 40, "C", "Refrain 2")]


def reg(start, name, end=None):
    return {"start": start, "end": end if end is not None else start + 4, "name": name, "idx": 1}


def bar(k):          # début de la mesure k (1-based) sur la timeline
    return 4.0 + 2 * (k - 1)


def test_unchanged_regions():
    regs = [reg(bar(1), "Intro"), reg(bar(9), "Couplet 1"), reg(bar(25), "Refrain 1"), reg(bar(33), "Pont"),
            reg(bar(37), "Refrain 2")]
    secs, w = regions_to_sections(regs, BT, 2, 40, OLD)
    assert w == [] and same_structure(secs, OLD)


def test_move_rename_add_delete():
    regs = [reg(bar(1), "Intro"), reg(bar(9) + 0.3, "Couplet 1"),          # 0.3 s = 0,15 mesure : toléré
            reg(bar(21), "Pré-refrain"),                                    # ajoutée
            reg(bar(25), "Chorus 1"),                                       # renommée
            reg(bar(37), "Refrain 2")]                                      # Pont supprimé
    secs, w = regions_to_sections(regs, BT, 2, 40, OLD)
    assert w == []
    assert [(d["start_bar"], d["name"]) for d in secs] == [(1, "Intro"), (9, "Couplet 1"), (21, "Pré-refrain"),
                                                           (25, "Chorus 1"), (37, "Refrain 2")]
    assert [d["label"] for d in secs] == ["A", "B", "?", "C", "C"]          # groupes gardés (nom, puis mesure)
    assert not same_structure(secs, OLD)


def test_off_grid_outside_and_duplicates(lang):
    lang("fr")
    regs = [reg(0.5, "Avant"),                                              # dans le count-in
            reg(bar(1), "Intro"), reg(bar(9) + 1.0, "Couplet 1"),           # une demi-mesure : arrondie
            reg(bar(9) + 0.2, "Doublon"),
            reg(bar(41) + 1, "Après"), reg(bar(30), "")]                    # sans nom
    secs, w = regions_to_sections(regs, BT, 2, 40, OLD)
    assert [(d["start_bar"], d["name"]) for d in secs] == [(1, "Intro"), (9, "Doublon"), (30, "Section 3")]
    text = " | ".join(w)
    assert "« Avant » avant la mesure 1" in text and "« Après » après la fin" in text
    assert "même mesure (9)" in text


def test_rounding_warning_and_first_bar(lang):
    lang("en")
    secs, w = regions_to_sections([reg(bar(9) + 0.8, "Verse 1"), reg(bar(25), "Chorus 1")], BT, 2, 40, OLD)
    assert [(d["start_bar"], d["name"]) for d in secs] == [(9, "Verse 1"), (25, "Chorus 1")]
    assert any("between two bars: moved to the start of bar 9" in x for x in w)
    assert any("bars 1 to 8 are joined to “Verse 1”" in x for x in w)


def test_song_region_ignored():
    regs = [reg(bar(1), "Demo", end=bar(41)), reg(bar(1), "Intro"), reg(bar(9), "Couplet 1")]
    secs, w = regions_to_sections(regs, BT, 2, 40, OLD, ignore_names=("Demo",))
    assert [d["name"] for d in secs] == ["Intro", "Couplet 1"] and w == []


# --------------------------------------------------------------------------- #
# Avec le faux pont : CLI (bouton « Préparer ») et outils MCP
# --------------------------------------------------------------------------- #
class RegionBridge(FakeBridge):
    """Le projet garde les régions du dernier plan appliqué ; le test peut les modifier « à la main »."""
    regions = None

    async def call(self, cmd, args=None, timeout=30.0):
        if cmd == "apply_plan":
            self.regions = [dict(r, idx=i + 1) for i, r in enumerate(args["regions"])]
        if cmd == "get_state":
            return {"tracks": ["Drums", "Bass"], "regions": [dict(r) for r in (self.regions or [])],
                    "markers": [], "tempo": []}
        return await super().call(cmd, args, timeout)


@pytest.fixture
def rb(monkeypatch, _env):
    b = RegionBridge(items=_env.items)
    monkeypatch.setattr(server.bridge, "call", b.call)
    return b


def plan_regions(b):
    return [(r["name"], r["start"]) for r in b.plans[-1]["regions"]]


def test_cli_adopts_hand_edited_regions(rb, lang, bridge_dir, resdir):
    lang("fr")
    assert cli.main(["prepare"]) == 0
    assert status(bridge_dir)["message"].startswith("Morceau préparé")
    # rien de modifié : comportement habituel
    assert cli.main(["prepare"]) == 0
    assert status(bridge_dir)["message"].startswith("Morceau reconstruit (structure conservée)")
    # à la main : Refrain 1 avancé à la mesure 21, Pont renommé Solo, Refrain 2 supprimé
    regs = rb.regions
    regs[2]["start"] = bar(21)
    regs[3]["name"] = "Solo"
    del regs[4]
    assert cli.main(["prepare"]) == 0
    msg = status(bridge_dir)["message"]
    assert msg.startswith("Structure reprise de tes régions REAPER")
    assert "21-32  Refrain 1" in msg and "33-40  Solo" in msg
    assert [n for n, _ in plan_regions(rb)] == ["Intro", "Couplet 1", "Refrain 1", "Solo"]
    plan = rb.plans[-1]
    assert [r["color"] for r in plan["regions"]][3] == list(i18n.section_color("Solo"))   # recolorée
    assert "→ Solo" in [m["name"] for m in plan["markers"]]
    assert any(v["name"] == "Solo" for v in plan["voice"]["items"])                       # annonce
    song = json.loads((resdir / "reaper_www_root" / "reacue_song.json").read_text(encoding="utf-8"))
    assert [s["name"] for s in song["sections"]] == ["Intro", "Couplet 1", "Refrain 1", "Solo"]
    sess = json.loads((bridge_dir / "last_session.json").read_text(encoding="utf-8"))
    assert [s["name"] for s in sess["analysis"]["sections"]][-1] == "Solo"
    # la fois suivante : plus de différence
    assert cli.main(["prepare"]) == 0
    assert status(bridge_dir)["message"].startswith("Morceau reconstruit")


def test_cli_off_grid_region_rounded_with_warning(rb, lang, bridge_dir):
    lang("en")
    assert cli.main(["prepare"]) == 0
    rb.regions.append({"start": bar(13) + 0.9, "end": bar(15), "name": "Guitar break", "idx": 9})
    rb.regions.append({"start": 0.2, "end": 1.0, "name": "Count", "idx": 10})
    assert cli.main(["prepare"]) == 0
    msg = status(bridge_dir)["message"]
    assert msg.startswith("Structure taken from your REAPER regions")
    assert "13-24  Guitar break" in msg
    assert "moved to the start of bar 13" in msg and "“Count” before bar 1: ignored" in msg


def test_publish_only_does_not_adopt_but_warns(rb, lang, bridge_dir):
    lang("fr")
    assert cli.main(["prepare"]) == 0
    n = len(rb.plans)
    rb.regions[1]["name"] = "Couplet A"
    assert cli.main(["publish"]) == 0
    msg = status(bridge_dir)["message"]
    assert msg.startswith("Prompteur republié") and "Tes régions REAPER ont changé" in msg
    assert len(rb.plans) == n                                       # REAPER non modifié
    sess = json.loads((bridge_dir / "last_session.json").read_text(encoding="utf-8"))
    assert sess["analysis"]["sections"][1]["name"] == "Couplet 1"   # structure enregistrée gardée


def test_other_project_protected(rb, lang, bridge_dir):
    """Projet consolidé / autre morceau : les régions ne sont pas lues, rien n'est modifié."""
    lang("fr")
    assert cli.main(["prepare"]) == 0
    n = len(rb.plans)
    rb.regions[1]["name"] = "Autre morceau"
    rb.items = [dict(rb.items[0], guid="{X}", file="/songs/Other/mix.wav")]
    a, item, opts, items = server._load()
    import asyncio
    assert asyncio.run(server._from_regions(a, item, opts, items)) == (a, False, [])
    with pytest.raises(server.BridgeError):                          # Claude : refusé par _check_items
        asyncio.run(server.update_options())
    assert len(rb.plans) == n


def test_mcp_prepare_song_and_rename_use_regions(rb, lang, bridge_dir):
    import asyncio
    lang("fr")
    asyncio.run(server.prepare_song())
    rb.regions[3]["start"] = bar(31)                                  # Pont avancé de 2 mesures
    res = asyncio.run(server.prepare_song())                          # pas de réanalyse : régions reprises
    assert res["structure_from_regions"] is True
    assert [s["bars"] for s in res["sections"]][2:4] == ["25-30", "31-36"]
    rb.regions[0]["name"] = "Intro guitare"
    res = asyncio.run(server.rename_section(5, "Refrain final"))      # numéros = régions actuelles
    assert [s["name"] for s in res["sections"]] == ["Intro guitare", "Couplet 1", "Refrain 1", "Pont",
                                                    "Refrain final"]
    # set_sections reste prioritaire : la liste donnée remplace tout
    rb.regions[1]["name"] = "Ignoré"
    res = asyncio.run(server.set_sections([{"start_bar": 1, "name": "Intro"}, {"start_bar": 17, "name": "Couplet"}]))
    assert [s["name"] for s in res["sections"]] == ["Intro", "Couplet"] and "structure_from_regions" not in res
    # reanalyse=True : analyse complète, régions ignorées
    rb.regions[1]["name"] = "Autre"
    res = asyncio.run(server.prepare_song(reanalyse=True))
    assert "structure_from_regions" not in res and res["sections"][1]["name"] == "Couplet 1"
