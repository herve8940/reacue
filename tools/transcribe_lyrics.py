#!/usr/bin/env python3
"""Paroles automatiques (Whisper) sur un morceau, à la main (outil de développement, à lancer sur le Mac).

Transcrit le stem voix du dernier morceau préparé par ReaCue (last_session.json), ou d'un fichier voix donné,
avec le composant .venv-words (Whisper, install/install_words_*), puis affiche SEULEMENT des statistiques :
langue, nombre de lignes, de mots, de blocs, segments retirés par le nettoyage, durée chantée, temps de calcul.
N'affiche JAMAIS le texte transcrit.

    .venv/bin/python tools/transcribe_lyrics.py [--session <last_session.json> | --voice <stem voix>]
                                                [--lang auto|fr|en] [--write]

--write : écrit aussi le brouillon « paroles (auto).txt » dans le dossier du morceau, s'il n'existe pas déjà
(jamais écrasé) ; sans --write, rien n'est écrit (le texte n'existe que le temps du calcul).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reacue_mcp import lyrics_auto as LA  # noqa: E402
from reacue_mcp import words as W  # noqa: E402


def _voice_wav(args, tmp: Path):
    """(wav 16 kHz mono, analyse ou None, fichiers du morceau)."""
    if args.voice:
        import librosa
        import soundfile as sf
        y = librosa.load(args.voice, sr=LA.SR, mono=True)[0]
        wav = tmp / "voice16k.wav"
        sf.write(str(wav), y, LA.SR, subtype="PCM_16")
        return wav, None, None, [args.voice]
    from reacue_mcp.analysis import Analysis
    if args.session:
        sess = Path(args.session)
    else:
        from reacue_mcp.bridge import BRIDGE_DIR
        sess = BRIDGE_DIR / "last_session.json"
    d = json.loads(sess.read_text(encoding="utf-8"))
    a, items = Analysis.from_dict(d["analysis"]), d.get("items")
    files = [x["file"] for x in items] if items else [a.file] + list((a.stems or {}).values())
    return W.write_voice(a, items, tmp / "voice16k.wav"), a, items, files


def stats(res: dict, lines: list[dict], gap: float) -> dict:
    segs = res.get("segments") or []
    kept = sum(1 for s in segs if LA.keep_segment(s))
    blocks = 1 + sum(1 for p, q in zip(lines, lines[1:]) if q["t"] - p["end"] > gap) if lines else 0
    sung = sum(x["end"] - x["t"] for x in lines)
    return {"language": res.get("language"), "language_prob": res.get("language_prob"),
            "model": res.get("model"), "voiced_s": res.get("voiced_s"), "clips": res.get("clips"),
            "segments": len(segs), "segments_removed": len(segs) - kept, "lines": len(lines),
            "words": sum(len(x["text"].split()) for x in lines), "blocks": blocks,
            "words_per_line": round(sum(len(x["text"].split()) for x in lines) / max(1, len(lines)), 1),
            "sung_s": round(sung, 1), "engine_s": res.get("seconds")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", help="last_session.json (défaut : celui de ReaCue)")
    ap.add_argument("--voice", help="fichier du stem voix (au lieu du dernier morceau préparé)")
    ap.add_argument("--lang", default="auto", choices=["auto", "fr", "en"], help="langue chantée (défaut : auto)")
    ap.add_argument("--write", action="store_true", help="écrire « paroles (auto).txt » s'il n'existe pas")
    args = ap.parse_args(argv)
    why = LA.missing_reason()
    if why:
        print(f"Whisper non installé ({why}) : bash install/install_words_mac.sh")
        return 1
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="reacue_whisper_") as tmp:
        wav, a, items, files = _voice_wav(args, Path(tmp))
        res = LA.run_engine(wav, Path(tmp), args.lang)
    lines = LA.segments_to_lines(res.get("segments") or [])
    gap = LA.block_gap(a) if a is not None else 4.0
    st = stats(res, lines, gap)
    st["total_s"] = round(time.time() - t0, 1)
    print("Paroles automatiques (Whisper) — statistiques, sans texte :")
    for k, v in st.items():
        print(f"  {k:18} {v}")
    if args.write:
        if not lines:
            print("Aucune ligne : rien n'est écrit.")
        else:
            have = LA.find_auto_file(files)
            folder = LA.target_folder(files)
            if have:
                print(f"Brouillon déjà présent (non écrasé) : {have}")
            elif folder is None:
                print("Dossier du morceau introuvable : rien n'est écrit.")
            else:
                p = LA.write_draft(folder, LA.format_draft(lines, gap, st["model"] or LA.MODEL,
                                                           st["language"] or args.lang))
                print(f"Brouillon écrit : {p}" if p else "Brouillon déjà présent (non écrasé).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
