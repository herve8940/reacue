"""Réglages utilisateur : <ressources REAPER>/ReaCueMCP/reacue_settings.json.

Le fichier est créé par l'installateur ; toute clé absente prend sa valeur par défaut, une clé
inconnue est ignorée. Lu à chaque préparation (pas besoin de redémarrer quoi que ce soit).
"""
from __future__ import annotations

import json
from pathlib import Path

from .bridge import BRIDGE_DIR

SETTINGS_NAME = "reacue_settings.json"

DEFAULTS: dict = {
    "language": "fr",            # "fr" | "en" : régions, annonces, prompteur, messages
    "announce_voice": None,      # voix des annonces (macOS : Thomas… ; Windows : Microsoft Hortense…) ; None = auto
    "count_voice": None,         # voix du décompte ; None = auto (voix anglaise si count_lang = "en")
    "count_lang": "en",          # langue du décompte : "en" (one two three four) | "fr" (un deux trois quatre)
    "count_in_bars": 2,          # mesures de click avant la mesure 1
    "cue_lead_bars": 2,          # annonce N mesures avant la section (2 = avant-dernière mesure)
    "voice_cues": True,          # annonces vocales (« Refrain »…)
    "voice_count_in": True,      # décompte sur la dernière mesure du count-in
    "voice_count_each": True,    # décompte sur la dernière mesure de chaque section
    "voice_volume": 0.8,
    "click_volume": 0.5,
    "click_to_master": True,     # False : click et voix seulement sur la sortie click_hw_output
    "click_hw_output": None,     # sortie physique (0 = 1/2, 2 = 3/4…) ; None = aucune
    "tempo_mode": "auto",        # auto | constant | beatmap
    "count_rate": 240,           # débit du décompte (mots/min)
    "stems_model": "htdemucs_6s",  # séparation de stems (action REAPER) : htdemucs_6s (6 stems) | htdemucs (4)
    "structure_engine": "auto",  # sections : "auto" (SongFormer s'il est installé, sinon ReaCue) | "reacue"
    "projects_dir": None,        # mode concert : dossier des projets des morceaux ; None = <Documents>/REAPER Media
    "concert_dir": None,         # mode concert : dossier des concerts ; None = <dossier des projets>/Concerts
    # paroles mot par mot (composant optionnel .venv-words)
    "words_engine": "auto",      # "auto" (calage mot par mot s'il est installé) | "off" (lignes seulement)
    "words_language": "auto",    # langue chantée : "auto" (déduite du texte des paroles) | "fr" | "en"
}

LANGS = ("fr", "en")


def settings_path() -> Path:
    return BRIDGE_DIR / SETTINGS_NAME


def load_settings(path: Path | None = None) -> dict:
    """Réglages fusionnés avec les valeurs par défaut (fichier absent ou illisible : défauts)."""
    out = dict(DEFAULTS)
    p = Path(path) if path else settings_path()
    try:
        raw = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raw = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in DEFAULTS:
                out[k] = v
    lang = str(out.get("language") or "fr").lower()[:2]
    out["language"] = lang if lang in LANGS else "fr"
    cl = str(out.get("count_lang") or "en").lower()[:2]
    out["count_lang"] = cl if cl in LANGS else "en"
    se = str(out.get("structure_engine") or "auto").lower()
    out["structure_engine"] = se if se in ("auto", "reacue") else "auto"
    we = str(out.get("words_engine") or "auto").lower()
    out["words_engine"] = we if we in ("auto", "off") else "auto"
    wl = str(out.get("words_language") or "auto").lower()[:4]
    out["words_language"] = wl if wl in ("auto", "fr", "en") else "auto"
    return out


def option_defaults(s: dict | None = None) -> dict:
    """Valeurs initiales des Options du planificateur tirées des réglages."""
    s = s or load_settings()
    return {
        "count_in_bars": int(s["count_in_bars"]),
        "cue_lead_bars": int(s["cue_lead_bars"]),
        "voice_cues": bool(s["voice_cues"]),
        "voice_count_in": bool(s["voice_count_in"]),
        "voice_count_each": bool(s["voice_count_each"]),
        "voice_volume": float(s["voice_volume"]),
        "click_volume": float(s["click_volume"]),
        "click_to_master": bool(s["click_to_master"]),
        "click_hw_output": None if s["click_hw_output"] is None else int(s["click_hw_output"]),
        "tempo_mode": s["tempo_mode"] if s["tempo_mode"] in ("auto", "constant", "beatmap") else "auto",
        "voice_name": s["announce_voice"] or None,
        "count_voice": s["count_voice"] or None,
        "count_lang": s["count_lang"],
        "count_rate": int(s["count_rate"]),
    }
