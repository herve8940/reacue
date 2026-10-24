"""Compare la transcription de batterie de ReaCue : règles (avant) / modèle ADTOF (après).

OUTIL DE DÉVELOPPEMENT. À lancer sur la machine où ReaCue et le composant « batterie » sont installés :

    .venv/bin/python tools/compare_drums.py <stem batterie> [--all] [--bpm 120] [--bars]

  --all   analyse la grille avec tous les stems du dossier (comme « Analyser et préparer ») au lieu du seul
          stem batterie ;
  --bpm   tempo connu (sinon détecté) ;
  --bars  détail mesure par mesure (grilles côte à côte).

Affiche, pour chaque moteur : temps de calcul, pas par mesure (16 = double-croches, 12 = triolets),
voies, grooves (grille « x » par voie), fills et crashs par section, puis l'accord entre les deux moteurs.
N'affiche que des coups de batterie (aucune parole, aucun audio).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

AUDIO = (".wav", ".mp3", ".flac", ".aif", ".aiff", ".ogg", ".m4a")


def grid_line(steps_set, steps, per_beat):
    return "".join(("x" if s in steps_set else ".") + (" " if (s + 1) % per_beat == 0 else "")
                   for s in range(steps)).rstrip()


def hits_set(e):
    return {(lane, s) for lane, st in (e.get("hits") or {}).items() for s in st}


def show(name, out, secs, sec_of, beats_per_bar, verbose):
    from reacue_mcp import drums as D
    steps = out["steps"]
    per_beat = max(1, steps // beats_per_bar)
    print(f"\n=== {name} : moteur {out.get('engine')} · {out['_seconds']:.1f} s · {steps} pas/mesure"
          f" ({'triolets' if per_beat == 3 else 'double-croches' if per_beat == 4 else f'{per_beat} par temps'})"
          f" · décalage {out.get('offset_ms')} ms")
    if out.get("warning"):
        print("  ! " + out["warning"])
    print("  voies : " + ", ".join(out["lanes"]))
    for k, p in out["patterns"].items():
        print(f"  {p['name']}")
        for lane in D.LANES:
            if lane in p["hits"]:
                print(f"    {lane:3s} {grid_line(set(p['hits'][lane]), steps, per_beat)}")
    print("  sections :")
    for si, s in enumerate(secs):
        bars = [e for e in out["bars"] if sec_of.get(e["bar"] - 1) == si]
        pats = {}
        for e in bars:
            if e.get("pattern"):
                pats[e["pattern"]] = pats.get(e["pattern"], 0) + 1
        fills = [e["bar"] for e in bars if e.get("fill") and not e.get("rest")]
        crash = [e["bar"] for e in bars if e.get("crash")]
        rest = sum(1 for e in bars if e.get("rest"))
        print(f"    {s.name:16s} m.{s.start_bar + 1:>3}-{s.end_bar:<3} grooves {pats or '-'}"
              f"  fills {fills or '-'}  crashs {crash or '-'}" + (f"  silences {rest}" if rest else ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="compare_drums")
    ap.add_argument("stem")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--bars", action="store_true")
    args = ap.parse_args(argv)
    from reacue_mcp import analysis as A, drums as D
    stem = Path(args.stem).resolve()
    if not stem.is_file():
        print(f"introuvable : {stem}")
        return 2
    t0 = time.time()
    if args.all:
        files = sorted(p for p in stem.parent.iterdir() if p.suffix.lower() in AUDIO)
        a = A.analyze_stems([{"file": str(p), "shift": 0.0} for p in files], bpm_hint=args.bpm)
    else:
        a = A.analyze(str(stem), bpm_hint=args.bpm)
    a.stems = {**(a.stems or {}), "drums": str(stem)}
    print(f"grille : {a.bpm} BPM, {a.beats_per_bar}/{a.denominator}, {a.n_bars} mesures, "
          f"{len(a.sections)} sections ({time.time() - t0:.1f} s)")
    sec_of = {b: si for si, s in enumerate(a.sections) for b in range(s.start_bar, s.end_bar)}
    outs = {}
    for name, eng in (("AVANT (règles)", "reacue"), ("APRÈS (ADTOF)", "auto")):
        if eng == "auto" and not D.available():
            print("\n=== APRÈS (ADTOF) : composant non installé (Install ReaCue Drums.command)")
            continue
        t1 = time.time()
        out = D.detect_drums(a, None, engine=eng)
        out["_seconds"] = time.time() - t1
        outs[eng] = out
        show(name, out, a.sections, sec_of, int(a.beats_per_bar), args.bars)
    if len(outs) == 2:
        r, m = outs["reacue"], outs["auto"]
        same = r["steps"] == m["steps"]
        js = []
        for er, em in zip(r["bars"], m["bars"]):
            u, v = hits_set(er), hits_set(em)
            if u or v:
                js.append(len(u & v) / len(u | v) if same else 0.0)
        print(f"\n=== accord : {sum(js) / max(1, len(js)):.0%} des coups communs (moyenne par mesure)"
              + ("" if same else " — grilles différentes (16 / 12 pas)"))
        for lane in D.LANES:
            nr = sum(len((e.get("hits") or {}).get(lane, [])) for e in r["bars"])
            nm = sum(len((e.get("hits") or {}).get(lane, [])) for e in m["bars"])
            if nr or nm:
                print(f"    {lane:3s} règles {nr:5d}   ADTOF {nm:5d}")
        print(f"    fills  règles {sum(1 for e in r['bars'] if e.get('fill'))}   ADTOF {sum(1 for e in m['bars'] if e.get('fill'))}")
        print(f"    crashs règles {sum(1 for e in r['bars'] if e.get('crash'))}   ADTOF {sum(1 for e in m['bars'] if e.get('crash'))}")
        if args.bars:
            pb_r = max(1, r["steps"] // int(a.beats_per_bar))
            pb_m = max(1, m["steps"] // int(a.beats_per_bar))
            for er, em in zip(r["bars"], m["bars"]):
                print(f"\n  mesure {er['bar']}  règles: {er.get('pattern') or ('F' if er.get('fill') else '-')}"
                      f"  ADTOF: {em.get('pattern') or ('F' if em.get('fill') else '-')}")
                for lane in D.LANES:
                    hr = set((er.get("hits") or {}).get(lane, []))
                    hm = set((em.get("hits") or {}).get(lane, []))
                    if hr or hm:
                        print(f"    {lane:3s} {grid_line(hr, r['steps'], pb_r):24s} | {grid_line(hm, m['steps'], pb_m)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
