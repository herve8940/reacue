"""Serveur MCP ReaCue : prépare automatiquement un morceau dans REAPER."""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from .analysis import analyze, analyze_stems, resection, reference_index, assign_roles, Analysis
from .bridge import Bridge, BridgeError, BRIDGE_DIR
from .i18n import t, use_settings_lang, localize_analysis, get_lang
from .planner import Options, build_plan
from .settings import option_defaults
from .voice import Voice
from . import prompter
from . import chords
from . import lyrics
from . import drums
from .regions import regions_to_sections, same_structure

mcp = FastMCP(
    "reacue",
    instructions=(
        "Pilote REAPER pour préparer un morceau pour le live : à partir d'un MP3/WAV, détecte "
        "tempo, mesures et sections, puis crée la carte de tempo, les régions, les marqueurs de cue, "
        "une piste CUES et une piste CLICK. Outil principal : prepare_song. Après coup, utilise "
        "set_sections pour corriger les noms/limites si l'utilisateur le demande. Les numéros de mesure "
        "côté outils commencent à 1 (1re mesure du morceau, après le count-in). Les régions que "
        "l'utilisateur a modifiées à la main dans REAPER sont reprises automatiquement par prepare_song "
        "(morceau déjà préparé), update_options et rename_section ; set_sections et set_grid imposent "
        "la structure donnée et remplacent ces régions."
    ),
)
bridge = Bridge()
SESSION = BRIDGE_DIR / "last_session.json"


GENERATED_TRACKS = ("CLICK", "CUES", "VOIX", "VOICE")


def _new_options(**kw) -> Options:
    """Options initiales : reacue_settings.json, puis les paramètres explicitement donnés."""
    d = option_defaults()
    d.update({k: v for k, v in kw.items() if v is not None})
    return Options(**{k: v for k, v in d.items() if k in Options.__dataclass_fields__})


def _save(analysis: Analysis, item: dict, opts: Options, items: list[dict] | None = None):
    """items : positions ORIGINALES de tous les stems (jamais celles déjà déplacées par un apply)."""
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    d = {"analysis": analysis.to_dict(), "item": item, "options": asdict(opts),
         # réglages du fichier au moment de la préparation : la CLI n'en réapplique que les changements
         "settings": option_defaults()}
    if items:
        d["items"] = items
    SESSION.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def _load():
    if not SESSION.exists():
        raise BridgeError(t("no_session"))
    d = json.loads(SESSION.read_text(encoding="utf-8"))
    # options d'une autre version : clés inconnues ignorées, clés absentes = valeurs par défaut
    opts = Options(**{k: v for k, v in (d.get("options") or {}).items() if k in Options.__dataclass_fields__})
    return Analysis.from_dict(d["analysis"]), d["item"], opts, d.get("items")


def _bridge_version(info: dict) -> tuple:
    try:
        return tuple(int(x) for x in str(info.get("bridge", "0")).split(".")[:2])
    except ValueError:
        return (0, 0)


def _common_title(files: list[str]) -> str:
    stems = [Path(f).stem for f in files]
    pre = os.path.commonprefix(stems).rstrip(" -_.")
    return pre if len(pre) >= 3 else stems[0]


async def _apply(analysis: Analysis, item: dict, opts: Options, items: list[dict] | None = None) -> dict:
    render, render_count, vwarn = None, None, []
    info = None
    if items or opts.voice_cues or opts.voice_count_in:
        info = await bridge.call("ping")
    if items and _bridge_version(info) < (1, 2):
        raise BridgeError(t("old_bridge_stems"))
    if opts.voice_cues or opts.voice_count_in:
        if _bridge_version(info) < (1, 1):
            vwarn.append(t("old_bridge_voice"))
        else:
            v = await asyncio.to_thread(Voice, BRIDGE_DIR / "voice", opts.voice_name, 200, get_lang())
            vc = await asyncio.to_thread(Voice, BRIDGE_DIR / "voice", opts.count_voice,
                                         opts.count_rate, opts.count_lang)
            if v.available:
                render, render_count = v.render, vc.render
            vwarn = v.warnings + [w for w in vc.warnings if w not in v.warnings]
    # piste des appels vocaux : VOICE en anglais (pont ≥ 1.3, qui la reconnaît comme piste générée)
    vtrack = "VOICE" if get_lang() == "en" and info and _bridge_version(info) >= (1, 3) else "VOIX"
    plan, summary = await asyncio.to_thread(build_plan, analysis, item, opts, render, render_count, items,
                                            vtrack)
    timeline = plan.pop("prompter", None)
    await _check_items(plan, info)
    res = await bridge.call("apply_plan", plan, timeout=60)
    _save(analysis, item, opts, items)
    if timeline:
        try:
            summary["prompteur"] = await asyncio.to_thread(_publish_prompter, analysis, item, timeline, items)
        except Exception as e:          # le prompteur ne doit jamais bloquer la préparation
            summary.setdefault("warnings", []).append(t("prompter_not_updated", e=e))
    if analysis.stems:
        summary["stem_roles"] = analysis.stems
    summary["warnings"] += vwarn + res.get("warnings", [])
    summary["reaper"] = {"regions": len(res["state"]["regions"]), "markers": len(res["state"]["markers"]),
                         "tempo_markers": len(res["state"]["tempo"]),
                         "click_items": res.get("click_items"), "cue_items": res.get("cue_items"),
                         "voice_items": res.get("voice_items")}
    return summary


async def _check_items(plan: dict, info: dict | None):
    """Vérifie AVANT tout effacement que les items à caler existent dans le projet ouvert."""
    want = [m["guid"] for m in plan.get("items") or []] + ([plan["item"]["guid"]] if plan.get("item") else [])
    if not want:
        return
    if info is None:
        info = await bridge.call("ping")
    if _bridge_version(info) < (1, 2):
        return
    found = {d.get("guid") for d in (await bridge.call("get_audio_items")).get("items") or []}
    if any(g not in found for g in want):
        raise BridgeError(t("wrong_project"))


async def _same_song(item: dict, items: list[dict] | None) -> bool:
    """Les items audio du projet ouvert sont-ils ceux du dernier morceau préparé (GUID + fichier) ?"""
    try:
        found = (await bridge.call("get_audio_items")).get("items") or []
    except Exception:
        return False
    want = items or [item]
    key = lambda L: sorted((d.get("guid"), d.get("file")) for d in L)
    return bool(found) and key(found) == key(want)


async def _from_regions(a: Analysis, item: dict, opts: Options, items: list[dict] | None,
                        adopt: bool = True) -> tuple[Analysis, bool, list[str]]:
    """Structure lue dans les régions du projet REAPER, si elles ont été modifiées à la main.

    Seulement pour le MÊME morceau (mêmes items) : un autre projet ou un projet consolidé n'est jamais
    lu (il sera refusé ensuite par _check_items, rien n'est modifié). Renvoie (analyse, changé ?,
    avertissements). adopt=False : détecte seulement (l'analyse renvoyée est inchangée)."""
    if not await _same_song(item, items):
        return a, False, []
    try:
        regions = (await bridge.call("get_state")).get("regions")
    except Exception:
        return a, False, []
    if regions is None:
        return a, False, []
    plan, _ = await asyncio.to_thread(build_plan, a, item, opts, None, None, items)
    timeline = plan["prompter"]
    ignore = (plan["regions"][0]["name"],) if opts.song_region and plan["regions"] else ()
    secs, warns = regions_to_sections(regions, timeline["bar_times"], timeline["count_in_bars"], a.n_bars,
                                      a.sections, ignore)
    if not secs:
        return a, False, [t("regions_none")] if regions else []
    if same_structure(secs, a.sections):
        return a, False, []
    if not adopt:
        return a, True, warns
    return resection(a, secs), True, warns


async def _apply_from_regions(a, item, opts, items) -> dict:
    """Reprend les régions modifiées à la main (si besoin), puis reconstruit tout."""
    a, changed, warns = await _from_regions(a, item, opts, items)
    res = await _apply(a, item, opts, items)
    if changed:
        res["structure_from_regions"] = True
    res["warnings"] = warns + res.get("warnings", [])
    return res


async def _publish_only(analysis, item, opts, items) -> dict:
    """Met à jour le prompteur des musiciens (paroles, accords…) sans rien changer dans REAPER."""
    plan, summary = await asyncio.to_thread(build_plan, analysis, item, opts, None, None, items)
    timeline = plan.pop("prompter")
    out = await asyncio.to_thread(_publish_prompter, analysis, item, timeline, items)
    return {"prompteur": out, "reaper": t("unchanged"), "warnings": [],
            "sections": [{"name": s.name, "bars": f"{s.start_bar + 1}-{s.end_bar}"} for s in analysis.sections]}


def _publish_prompter(analysis, item, timeline, items):
    act = prompter.stem_activity(analysis, items)
    grid, chord_warn = None, None
    try:                                # les accords ne doivent jamais bloquer le prompteur
        names = [d["file"] for d in items] if items else [item.get("file", "")]
        grid = chords.cached_chords(analysis, items, prompter.key_from_names(names))
    except Exception as e:
        chord_warn = t("chords_failed", e=e)
    words, lyr_warn = None, None
    try:                                # les paroles non plus
        words = lyrics.cached_lyrics(analysis, items)
    except Exception as e:
        lyr_warn = t("lyrics_failed", e=e)
    kit, drum_warn = None, None
    try:                                # la batterie non plus
        if any(r == "drums" for r in assign_roles([d["file"] for d in items or []])) or "drums" in (analysis.stems or {}):
            kit = drums.cached_drums(analysis, items)
    except Exception as e:
        drum_warn = t("drums_failed", e=e)
    song = prompter.build_song(analysis, item, timeline, items, act, chords=grid, lyrics=words, drums=kit)
    out = prompter.publish(song)
    out["chords"] = bool(song.get("chords"))
    out["lyrics"] = len(song.get("lyrics") or [])
    out["drums"] = bool(song.get("drums"))
    warns = [w for w in (chord_warn, lyr_warn, drum_warn) if w]
    if warns:
        out["warning"] = " ; ".join(warns)
    out["url"] = t("prompter_url", page=prompter.PAGE_NAME)
    out["instruments"] = song["roles"]
    return out


@mcp.tool()
async def reaper_status() -> dict:
    """Vérifie que REAPER et le script ReaCue_Bridge.lua répondent."""
    use_settings_lang()
    ok, why = bridge.alive()
    if not ok:
        return {"connected": False, "reason": why, "bridge_dir": str(BRIDGE_DIR)}
    return {"connected": True, **(await bridge.call("ping"))}


@mcp.tool()
async def prepare_song(
    file_path: str | None = None,
    count_in_bars: int | None = None,
    tempo_mode: Literal["auto", "constant", "beatmap"] | None = None,
    beats_per_bar: int | None = None,
    bpm_hint: float | None = None,
    click: bool = True,
    click_to_master: bool | None = None,
    click_hw_output: int | None = None,
    cue_lead_bars: int | None = None,
    song_region: bool = False,
    voice_cues: bool | None = None,
    voice_count_in: bool | None = None,
    voice_count_each: bool | None = None,
    voice_name: str | None = None,
    reanalyse: bool = False,
) -> dict:
    """Prépare tout automatiquement dans REAPER pour le morceau importé.

    Utilise l'item audio sélectionné (sinon le premier du projet). Si file_path est donné,
    le fichier est d'abord importé sur une piste AUDIO.
    Étapes : analyse (BPM, mesures, sections) → calage de l'audio sur la grille → carte de tempo
    → régions colorées par section → marqueurs « → Section » N mesures avant → piste CUES → piste CLICK
    avec count-in → piste VOIX : appels vocaux (« Refrain », « Pont »…) cue_lead_bars mesure(s) avant
    chaque section et décompte sur le count-in (voix du système : macOS `say`, Windows SAPI ;
    voice_name pour choisir : Thomas, Amélie, Microsoft Hortense Desktop…). Remplace les marqueurs/régions/tempo et pistes CLICK/CUES existants.

    tempo_mode : "constant" (un seul tempo), "beatmap" (la grille suit le morceau mesure par mesure,
    pour un enregistrement joué sans click), "auto" choisit selon la stabilité.
    beats_per_bar : forcer 3 ou 4 si la détection se trompe. bpm_hint : tempo approximatif connu
    (corrige les erreurs de double/moitié). click_hw_output : sortie physique du click
    (0 = sorties 1/2, 2 = 3/4…), avec click_to_master=False pour qu'il n'aille pas en façade.
    Les paramètres non donnés prennent les valeurs de reacue_settings.json (count-in 2, annonce sur
    l'avant-dernière mesure, décompte anglais, langue des régions et annonces…).
    Morceau déjà préparé dont l'utilisateur a modifié les régions à la main dans REAPER (déplacées,
    renommées, ajoutées, supprimées) : ces régions deviennent la structure, sans réanalyse
    (résultat : structure_from_regions). reanalyse=True, bpm_hint ou beats_per_bar : analyse complète.
    """
    use_settings_lang()
    if not (file_path or reanalyse or bpm_hint or beats_per_bar):
        try:
            a, item0, opts0, items0 = _load()
        except Exception:
            a = None
        if a is not None:
            a, changed, warns = await _from_regions(a, item0, opts0, items0)
            if changed:
                given = dict(count_in_bars=count_in_bars, tempo_mode=tempo_mode, click_to_master=click_to_master,
                             click_hw_output=click_hw_output, cue_lead_bars=cue_lead_bars,
                             voice_cues=voice_cues, voice_count_in=voice_count_in,
                             voice_count_each=voice_count_each, voice_name=voice_name)
                for k, v in given.items():
                    if v is not None:
                        setattr(opts0, k, v)
                res = await _apply(a, item0, opts0, items0)
                res["structure_from_regions"] = True
                res["warnings"] = warns + res.get("warnings", [])
                return res
    items = None
    if file_path:
        p = Path(file_path).expanduser()
        if not p.exists():
            return {"error": t("file_not_found", path=p)}
        item = await bridge.call("import_file", {"file": str(p), "track_name": "AUDIO"})
    else:
        info = await bridge.call("ping")
        if _bridge_version(info) < (1, 2):
            # pont 1.1 : pas de get_audio_items ; plusieurs pistes "musique" = stems probables
            tracks = (await bridge.call("get_state"))["tracks"]
            if len([tr for tr in tracks if tr not in GENERATED_TRACKS]) > 1:
                return {"error": t("old_bridge_stems")}
            item = await bridge.call("get_audio_item")
        else:
            res = await bridge.call("get_audio_items")
            # plusieurs items = stems : on les prend TOUS, quelle que soit la sélection,
            # pour qu'ils restent synchronisés (déplacés du même décalage)
            found = res.get("items") or []
            if not found:
                return {"error": t("no_audio_item")}
            if len(found) == 1:
                item = found[0]
            else:
                items = found
    stem_warn = []
    if items:
        files = [d["file"] for d in items]
        ref = items[reference_index(files)]
        item = ref
        def t0(d):      # position sur la timeline du t=0 du fichier source
            return d["position"] - d.get("offset", 0.0) / (d.get("rate") or 1.0)
        stems = [{"file": d["file"], "shift": t0(d) - t0(ref)} for d in items]
        rates = {round(d.get("rate") or 1.0, 4) for d in items}
        if len(rates) > 1:
            stem_warn.append(t("stem_rates"))
        item["title"] = _common_title(files)
        analysis = await asyncio.to_thread(analyze_stems, stems, beats_per_bar, 4, bpm_hint)
    else:
        item["title"] = Path(item["file"]).stem
        analysis = await asyncio.to_thread(analyze, item["file"], beats_per_bar, 4, bpm_hint)
    localize_analysis(analysis)
    opts = _new_options(count_in_bars=count_in_bars, tempo_mode=tempo_mode, click=click,
                        click_to_master=click_to_master, click_hw_output=click_hw_output,
                        cue_lead_bars=cue_lead_bars, song_region=song_region,
                        voice_cues=voice_cues, voice_count_in=voice_count_in,
                        voice_count_each=voice_count_each, voice_name=voice_name)
    summary = await _apply(analysis, item, opts, items)
    summary["file"] = item["file"]
    summary["warnings"] = stem_warn + summary["warnings"]
    return summary


@mcp.tool()
async def analyze_audio(file_path: str, beats_per_bar: int | None = None, bpm_hint: float | None = None) -> dict:
    """Analyse seulement (sans toucher à REAPER) : BPM, mesure, stabilité du tempo, sections proposées."""
    use_settings_lang()
    a = await asyncio.to_thread(analyze, str(Path(file_path).expanduser()), beats_per_bar, 4, bpm_hint)
    localize_analysis(a)
    return {"bpm": a.bpm, "signature": f"{a.beats_per_bar}/{a.denominator}", "bars": a.n_bars,
            "tempo_stable": a.tempo_stable, "tempo_cv": a.tempo_cv, "first_downbeat_s": a.downbeats[0],
            "sections": [{"name": s.name, "group": s.label, "bars": f"{s.start_bar + 1}-{s.end_bar}"}
                         for s in a.sections], "warnings": a.warnings}


@mcp.tool()
async def set_sections(sections: list[dict]) -> dict:
    """Corrige la structure du dernier morceau préparé et reconstruit régions, cues et click.
    Prioritaire : la liste donnée remplace la structure, y compris les régions modifiées à la main.

    sections : liste complète, dans l'ordre, de {"start_bar": int, "name": str}. start_bar commence à 1
    (1re mesure du morceau). Chaque section va jusqu'au début de la suivante.
    Exemple : [{"start_bar":1,"name":"Intro"},{"start_bar":9,"name":"Couplet 1"},{"start_bar":25,"name":"Refrain 1"}]
    Option : un élément {"prompteur_seul": true} (seul ou avec des sections) met à jour uniquement le
    prompteur des musiciens (paroles, accords, structure) sans rien modifier dans REAPER.
    Option : ajouter un élément {"grid": {"bpm": 168, "bar1_s": 8.6, "n_bars": 185}} pour imposer en même
    temps une grille à tempo constant (bar1_s = début de la mesure 1 dans le fichier de référence).
    Les noms de sections sont libres, en français ou en anglais (Verse, Chorus…).
    """
    use_settings_lang()
    a, item, opts, items = _load()
    # option : {"prompteur_seul": true} = republier seulement le prompteur, sans toucher à REAPER
    only = any(isinstance(d, dict) and (d.get("prompteur_seul") or d.get("publish_only")) for d in sections)
    sections = [d for d in sections if not (isinstance(d, dict) and ("prompteur_seul" in d or "publish_only" in d))]
    # option : {"grid": {"bpm": 168, "bar1_s": 8.6, "n_bars": 185}} dans la liste = grille imposée
    grid = next((d["grid"] for d in sections if isinstance(d, dict) and "grid" in d), None)
    sections = [d for d in sections if not (isinstance(d, dict) and "grid" in d)]
    if grid:
        _impose_grid(a, opts, float(grid["bpm"]), float(grid["bar1_s"]),
                     grid.get("n_bars"), grid.get("beats_per_bar"))
    if sections:
        a = resection(a, sections)
    if only:
        if sections or grid:
            _save(a, item, opts, items)
            return await _publish_only(a, item, opts, items)
        # prompteur seul : les régions modifiées à la main ne sont PAS reprises ici (le prompteur doit
        # rester d'accord avec les annonces et le click déjà dans REAPER) ; on le signale seulement
        _, changed, _ = await _from_regions(a, item, opts, items, adopt=False)
        res = await _publish_only(a, item, opts, items)
        if changed:
            res["warnings"].append(t("regions_changed_publish"))
        return res
    return await _apply(a, item, opts, items)


def _impose_grid(a, opts, bpm, bar1_s, n_bars=None, beats_per_bar=None):
    m = int(beats_per_bar or a.beats_per_bar)
    bar = 60.0 * m / bpm * (4 / a.denominator)
    if n_bars is None:
        n_bars = max(1, int((a.duration - bar1_s) // bar))
    n_bars = int(n_bars)
    a.beats_per_bar = m
    a.downbeats = [round(bar1_s + k * bar, 6) for k in range(n_bars + 1)]
    a.beats = [round(bar1_s + k * bar / m, 6) for k in range(n_bars * m + 1)]
    a.bpm, a.tempo_stable, a.tempo_cv = round(bpm, 4), True, 0.0
    a.alt_bpm = None
    a.warnings = [w for w in a.warnings if "tempo" not in w.lower() and "pulsation" not in w.lower()]
    opts.tempo_mode = "constant"
    return n_bars


@mcp.tool()
async def set_grid(
    bpm: float,
    bar1_s: float,
    n_bars: int | None = None,
    beats_per_bar: int | None = None,
    sections: list[dict] | None = None,
) -> dict:
    """Impose une grille à tempo constant quand l'analyse automatique s'est trompée, puis reconstruit tout.

    bpm : tempo exact (noires/min). bar1_s : début de la mesure 1, en secondes DANS LE FICHIER audio de
    référence (la batterie en mode stems, sinon le fichier analysé). n_bars : nombre de mesures (défaut :
    jusqu'à la fin du fichier). beats_per_bar : garder la mesure actuelle si absent.
    sections : nouvelle structure dans la numérotation de CETTE grille (même format que set_sections) ;
    fortement conseillé, car les anciennes mesures ne correspondent plus.
    """
    use_settings_lang()
    a, item, opts, items = _load()
    n_bars = _impose_grid(a, opts, bpm, bar1_s, n_bars, beats_per_bar)
    if sections:
        a = resection(a, sections)
    else:
        for s in a.sections:            # au minimum, ne pas dépasser la nouvelle grille
            s.start_bar, s.end_bar = min(s.start_bar, n_bars - 1), min(s.end_bar, n_bars)
        a.sections = [s for s in a.sections if s.end_bar > s.start_bar]
    return await _apply(a, item, opts, items)


@mcp.tool()
async def rename_section(index: int, name: str) -> dict:
    """Renomme la section n° index (1 = première) du dernier morceau préparé."""
    use_settings_lang()
    a, item, opts, items = _load()
    a, changed, warns = await _from_regions(a, item, opts, items)     # numéros = régions actuelles
    if not 1 <= index <= len(a.sections):
        return {"error": t("n_sections", n=len(a.sections))}
    a.sections[index - 1].name = name
    res = await _apply(a, item, opts, items)
    if changed:
        res["structure_from_regions"] = True
    res["warnings"] = warns + res.get("warnings", [])
    return res


@mcp.tool()
async def update_options(
    count_in_bars: int | None = None,
    tempo_mode: Literal["auto", "constant", "beatmap"] | None = None,
    click: bool | None = None,
    click_to_master: bool | None = None,
    click_hw_output: int | None = None,
    cue_lead_bars: int | None = None,
    song_region: bool | None = None,
    voice_cues: bool | None = None,
    voice_count_in: bool | None = None,
    voice_count_each: bool | None = None,
    voice_name: str | None = None,
    count_lang: Literal["en", "fr"] | None = None,
    count_voice: str | None = None,
    count_rate: int | None = None,
    count_anticipation_ms: float | None = None,
) -> dict:
    """Change des réglages (appels vocaux et voix compris, count-in, mode de tempo, click…) et reconstruit sans réanalyser l'audio.
    Les régions modifiées à la main dans REAPER sont reprises comme structure (structure_from_regions)."""
    use_settings_lang()
    a, item, opts, items = _load()
    for k, v in locals().copy().items():
        if k not in ("a", "item", "opts") and v is not None and hasattr(opts, k):
            setattr(opts, k, v)
    return await _apply_from_regions(a, item, opts, items)


@mcp.tool()
async def get_project_state() -> dict:
    """Liste régions, marqueurs, marqueurs de tempo et pistes du projet REAPER courant."""
    return await bridge.call("get_state")


@mcp.tool()
async def goto_section(name: str | None = None, index: int | None = None) -> dict:
    """Place le curseur au début d'une région (par nom ou numéro de région REAPER)."""
    return await bridge.call("goto_region", {"name": name, "index": index})


@mcp.tool()
async def transport(action: Literal["play", "stop", "pause"]) -> dict:
    """Lecture / stop / pause dans REAPER."""
    return await bridge.call("transport", {"action": action})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
