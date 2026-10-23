#!/usr/bin/env python3
"""Avant / après du calage mot par mot sur un morceau préparé (outil de développement, à lancer sur le Mac).

Reprend le dernier morceau préparé par ReaCue (last_session.json : grille, sections, stems) et son fichier de
paroles, puis compare :
  - AVANT : calage par ligne seul (mots répartis régulièrement dans la ligne, comme la grille PDF d'avant) ;
  - APRÈS : calage mot par mot (composant .venv-words, install/install_words_*).
N'affiche JAMAIS le texte des paroles : seulement des numéros de ligne / de mot, des positions sur la grille
(mesure:temps) et des durées.

    .venv/bin/python tools/compare_words.py [--session <last_session.json>] [--lyrics <paroles.txt>]
                                            [--lang fr|en] [--clicks <sortie.wav>] [-v]

--clicks : écrit un WAV « stem voix + clic à chaque début de mot calé » (temps du fichier de référence) pour
vérifier à l'oreille ; le fichier reste sur ta machine (ne pas le partager : il contient la voix).
-v : détail mot par mot (numéro du mot, début, durée, probabilité), toujours sans texte.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reacue_mcp import lyrics as LY  # noqa: E402
from reacue_mcp import words as W  # noqa: E402
from reacue_mcp.analysis import Analysis  # noqa: E402


def _pos(a, t: float) -> str:
    bar, beat, pos = LY._bar_pos(a, t)
    return f"{bar}:{pos + 1:.2f}"


def _even_bars(a, o) -> list[int]:
    """Mesure de chaque mot avec la répartition régulière d'avant (sheet.bar_lyrics sans "words")."""
    n = len(str(o["text"]).split())
    t0, t1 = float(o["t"]), max(float(o["end"]), float(o["t"]) + 0.01)
    return [LY._bar_pos(a, t0 + (k + 0.5) / n * (t1 - t0))[0] for k in range(n)]


def _word_bars(a, o) -> list[int]:
    out = []
    for w in o["words"]:
        d = max(0.0, w["end"] - w["t"])
        b = LY._bar_pos(a, w["t"] + min(0.05, 0.25 * d))[0]
        out += [b] * len(str(w["w"]).split())
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", help="last_session.json (défaut : celui de ReaCue)")
    ap.add_argument("--lyrics", help="fichier de paroles (défaut : cherché à côté des stems)")
    ap.add_argument("--lang", choices=["fr", "en"], help="langue chantée (défaut : déduite du texte)")
    ap.add_argument("--clicks", help="WAV de contrôle : voix + clic à chaque début de mot")
    ap.add_argument("-v", action="store_true", help="détail mot par mot (sans texte)")
    args = ap.parse_args(argv)

    if args.session:
        sess = Path(args.session)
    else:
        from reacue_mcp.bridge import BRIDGE_DIR
        sess = BRIDGE_DIR / "last_session.json"
    d = json.loads(sess.read_text(encoding="utf-8"))
    a, items = Analysis.from_dict(d["analysis"]), d.get("items")
    files = [x["file"] for x in items] if items else [a.file] + list((a.stems or {}).values())
    path = Path(args.lyrics) if args.lyrics else LY.find_lyrics_file(files)
    if not path:
        print("Pas de fichier de paroles à côté des stems (paroles.txt / lyrics.txt).")
        return 1
    if not W.available():
        print("Composant « paroles mot par mot » non installé : bash install/install_words_mac.sh")
        return 1
    if args.lang:
        os.environ["REACUE_WORDS_LANG"] = args.lang

    # AVANT : calage par ligne seul (recalculé dans un cache temporaire, comme ReaCue le ferait)
    old = os.environ.get("REACUE_WORDS_ENGINE")
    os.environ["REACUE_WORDS_ENGINE"] = "off"
    try:
        with tempfile.TemporaryDirectory(prefix="reacue_cmp_") as tmp:
            before = LY.cached_lyrics(a, items, cache=Path(tmp) / "lines.json", path=path) or []
    finally:
        if old is None:
            os.environ.pop("REACUE_WORDS_ENGINE", None)
        else:
            os.environ["REACUE_WORDS_ENGINE"] = old
    if not before:
        print("Aucune ligne calée.")
        return 1
    lang = W.song_language(before)
    jobs = W.make_jobs(before)
    print(f"Morceau : {len(before)} lignes calées, {sum(len(o['text'].split()) for o in before)} mots, "
          f"{a.bpm:.1f} BPM, langue {lang} ({W.MODELS[lang]})")

    # APRÈS : alignement forcé (sous-processus .venv-words)
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="reacue_cmp_") as tmp:
        wav = W.write_voice(a, items, Path(tmp) / "voice16k.wav")
        res = W.run_engine(wav, jobs, lang, Path(tmp))
    dt = time.time() - t0
    after, n_ok = W.merge(a, before, res)
    by_id = {ln.get("id"): ln for ln in res["lines"]}
    print(f"Calage mot par mot : {n_ok}/{len(before)} lignes en {dt:.0f} s "
          f"(seuil de probabilité {W.MIN_LINE_SCORE})")

    # tableau par ligne (aucun texte)
    print()
    print(f"{'ligne':>5} {'mots':>4} {'prob':>5}  {'avant début':>11} {'fin':>8}  {'après début':>11} {'fin':>8}"
          f"  {'Δdébut':>7} {'Δfin':>6}  mots changés de mesure")
    moved_total, words_total, scores = 0, 0, []
    order = sorted(range(len(before)), key=lambda i: before[i]["t"])
    for i in order:
        b = before[i]
        r = by_id.get(i) or {}
        sc = r.get("score")
        if sc is not None:
            scores.append(sc)
        o = next((x for x in after if x["i"] == b["i"] and x.get("copy") == b.get("copy")
                  and abs(x["t"] - b["t"]) < 2.5 and x.get("words")), None)
        n = len(b["text"].split())
        words_total += n
        if not o:
            why = r.get("error", "") or ("prob. trop faible" if sc is not None else "")
            print(f"{b['line']:>5} {n:>4} {sc if sc is not None else '-':>5}  {_pos(a, b['t']):>11} "
                  f"{_pos(a, b['end']):>8}  {'—':>11} {'':>8}  {'':>7} {'':>6}  {why[:40]}")
            continue
        moved = sum(x != y for x, y in zip(_even_bars(a, b), _word_bars(a, o)))
        moved_total += moved
        print(f"{b['line']:>5} {n:>4} {sc:>5.2f}  {_pos(a, b['t']):>11} {_pos(a, b['end']):>8}  "
              f"{_pos(a, o['t']):>11} {_pos(a, o['end']):>8}  {o['t'] - b['t']:>+7.2f} {o['end'] - b['end']:>+6.2f}"
              f"  {moved}")
        if args.v:
            for k, w in enumerate(o["words"]):
                rw = (r.get("words") or [{}] * len(o["words"]))[k]
                print(f"{'':>11} mot {k + 1:>2} : {_pos(a, w['t']):>9}  durée {w['end'] - w['t']:.2f} s  "
                      f"prob {rw.get('score', 0):.2f}")
    print()
    if scores:
        print(f"Probabilité moyenne par ligne : médiane {statistics.median(scores):.2f}, "
              f"min {min(scores):.2f}, max {max(scores):.2f}")
    durs = [w["end"] - w["t"] for o in after for w in o.get("words", [])]
    if durs:
        print(f"Durée des mots : médiane {statistics.median(durs):.2f} s, min {min(durs):.2f} s, max {max(durs):.2f} s")
    print(f"Grille PDF : {moved_total}/{words_total} mots changent de mesure par rapport à la répartition régulière.")

    if args.clicks:
        import numpy as np
        import soundfile as sf
        with tempfile.TemporaryDirectory(prefix="reacue_cmp_") as tmp:
            y, sr = sf.read(str(W.write_voice(a, items, Path(tmp) / "v.wav")), dtype="float32")
        n = np.arange(int(0.012 * sr))
        click = (0.6 * np.sin(2 * np.pi * 2000 * n / sr) * np.exp(-n / (0.003 * sr))).astype(np.float32)
        for o in after:
            for w in o.get("words", []):
                s = int(w["t"] * sr)
                if 0 <= s < len(y) - len(click):
                    y[s:s + len(click)] += click
        sf.write(args.clicks, np.clip(y, -1, 1), sr, subtype="PCM_16")
        print(f"WAV de contrôle écrit : {args.clicks} (temps du fichier de référence)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
