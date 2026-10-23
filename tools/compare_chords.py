"""Compare les accords du modèle entraîné (Jiang et al. 2019) à la détection de ReaCue, mesure par mesure.

OUTIL DE DÉVELOPPEMENT / DE VÉRIFICATION (non utilisé par ReaCue). À lancer avec le Python de ReaCue
(le modèle, lui, tourne dans .venv-chords, installé par « Install ReaCue Chords ») :

    .venv/bin/python tools/compare_chords.py <dossier de stems | fichier audio> [...]
        [--bars 1-32]          # n'afficher que ces mesures
        [--full]               # vocabulaire complet (9e, 11e, 13e) au lieu de la version « live »
        [--json resultat.json] # enregistre les deux grilles

Un dossier = les stems d'un morceau (wav/flac/mp3/aif ; voix et batterie reconnues par leur nom) ; un
fichier = mode MP3. La grille (tempo, mesures) est calculée par l'analyse de ReaCue (nombre de BPM lu dans
le nom des fichiers s'il y est), la tonalité est lue dans le nom des fichiers (« …-E minor-… ») sinon
estimée. Affiche les accords seulement (jamais de paroles), le temps de calcul et le taux d'accord entre
les deux méthodes (même nom ; même fondamentale et même couleur majeur / mineur).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reacue_mcp import analysis as A  # noqa: E402
from reacue_mcp import chord_model as CM  # noqa: E402
from reacue_mcp import chords as CH  # noqa: E402
from reacue_mcp.prompter import key_from_names  # noqa: E402

AUDIO = (".wav", ".flac", ".mp3", ".aif", ".aiff", ".m4a", ".ogg")


def load_song(path: Path):
    """(Analysis, items, noms de fichiers) pour un dossier de stems ou un fichier."""
    if path.is_dir():
        files = sorted(str(f) for f in path.iterdir() if f.suffix.lower() in AUDIO and not f.name.startswith("."))
        if not files:
            raise SystemExit(f"aucun fichier audio / no audio file: {path}")
        if len(files) == 1:
            return A.analyze(files[0], bpm_hint=A.bpm_from_filenames(files)), None, files
        a = A.analyze_stems([{"file": f, "shift": 0.0} for f in files])
        items = [{"file": f, "position": 0.0, "offset": 0.0, "rate": 1.0} for f in files]
        return a, items, files
    return A.analyze(str(path), bpm_hint=A.bpm_from_filenames([str(path)])), None, [str(path)]


def _fam(name: str) -> tuple:
    """« F#m7/A » -> ("F#", "m") ; « N.C. » -> ("N.C.", "")."""
    m = re.match(r"([A-G][#b]?)(.*)", name or "")
    if not m:
        return (name, "")
    root, q = m.group(1), m.group(2).split("/")[0]
    col = "m" if q.startswith("m") and not q.startswith("maj") else "dim" if "dim" in q or "b5" in q else \
        "sus" if "sus" in q else "aug" if "aug" in q else ""
    pc = CH._PC.get(root, -1)
    return (pc, col)


def halves(grid: list[dict], m: int) -> dict[tuple, str]:
    """{(mesure, demi): accord} (deux demi-mesures en mesure paire)."""
    out = {}
    for e in grid:
        cs = sorted(e["chords"], key=lambda c: c["beat"])
        for h in (0, 1):
            beat = 1 + h * (m // 2)
            cur = cs[0]
            for c in cs:
                if c["beat"] <= beat:
                    cur = c
            out[(e["bar"], h)] = cur["chord"]
    return out


def compare(path: Path, bars: tuple | None, simple: bool) -> dict:
    t0 = time.time()
    a, items, files = load_song(path)
    t_grid = time.time() - t0
    key = key_from_names(files)
    print(f"\n=== {path.name}  ({a.n_bars} mes. / bars, {a.bpm:.2f} BPM, {a.beats_per_bar}/{a.denominator}, "
          f"tonalité / key: {key['chord'] if key else '?'})  grille / grid {t_grid:.0f} s")
    t0 = time.time()
    legacy = CH.detect_chords(a, items, key, simple=simple)
    t_legacy = time.time() - t0
    model, t_model, err = None, None, None
    if not CM.available():
        err = "modèle non installé / model not installed (Install ReaCue Chords)"
    else:
        try:
            t0 = time.time()
            segs, info = CM.model_segments(a, CH._sources(a, items))
            model = CH.chords_from_segments(a, segs, key, simple)
            t_model = time.time() - t0
            if info.get("cached"):
                print("  (modèle : résultat mémorisé / model: cached result)")
        except Exception as e:                       # noqa: BLE001
            err = str(e)
    print(f"  ReaCue : {t_legacy:.1f} s" + (f" | modèle / model : {t_model:.1f} s" if t_model is not None else ""))
    if err:
        print("  ! " + err)
    m = a.beats_per_bar
    hl, hm = halves(legacy, m), halves(model or [], m)
    lo, hi = bars or (1, a.n_bars)
    print(f"  {'mes.':>4}  {'ReaCue':<18} {'modèle / model':<18}")
    for e in legacy:
        b = e["bar"]
        if not lo <= b <= hi:
            continue
        lt = " ".join(c["chord"] for c in e["chords"])
        me = next((x for x in model or [] if x["bar"] == b), None)
        mt = " ".join(c["chord"] for c in me["chords"]) if me else "-"
        low = me and any(c["confidence"] < 0.5 for c in me["chords"])
        flag = "" if lt == mt else ("  ≠" + ("  (?)" if low else ""))
        print(f"  {b:>4}  {lt:<18} {mt:<18}{flag}")
    res = {"file": str(path), "n_bars": a.n_bars, "key": key, "legacy": legacy, "model": model,
           "seconds": {"grid": round(t_grid, 1), "legacy": round(t_legacy, 1),
                       "model": None if t_model is None else round(t_model, 1)}}
    if model:
        ks = [k for k in hl if k in hm]
        same = sum(hl[k] == hm[k] for k in ks)
        fam = sum(_fam(hl[k]) == _fam(hm[k]) for k in ks)
        n = max(1, len(ks))
        print(f"  accord / agreement : même nom / same name {100 * same / n:.0f} % ; "
              f"même fondamentale et couleur / same root and colour {100 * fam / n:.0f} % ({len(ks)} demi-mesures)")
        res["agreement"] = {"same_name": round(same / n, 3), "same_family": round(fam / n, 3)}
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="compare_chords")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--bars", help="ex. 1-32")
    ap.add_argument("--full", action="store_true", help="vocabulaire complet / full vocabulary")
    ap.add_argument("--json")
    ap.add_argument("--install-dir", help="dossier de ReaCue où est installé .venv-chords (défaut : ce dépôt)")
    args = ap.parse_args(argv)
    if args.install_dir:
        CM.ROOT = Path(args.install_dir).expanduser().resolve()
    bars = tuple(int(x) for x in args.bars.split("-", 1)) if args.bars else None
    out = [compare(Path(p).expanduser(), bars, not args.full) for p in args.paths]
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
