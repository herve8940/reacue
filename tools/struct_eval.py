"""Banc d'essai de la détection automatique de structure (sections + noms) de ReaCue.

OUTIL DE DÉVELOPPEMENT (non utilisé par ReaCue). Les morceaux de test et leur structure de
référence sont décrits dans un fichier JSON privé (non versionné), par défaut
tools/struct_eval_songs.json ; voir tools/struct_eval_songs.example.json pour le format.

    python3 tools/struct_eval.py [--songs fichier.json] [--cache dossier]
    python3 tools/struct_eval.py --refeat   # recalcule les caractéristiques par mesure (et chronomètre)
    python3 tools/struct_eval.py --full     # + analyse complète (chargement, grille) chronométrée
    python3 tools/struct_eval.py -v         # détail des structures
    python3 tools/struct_eval.py nom1 nom2  # seulement ces morceaux

Format d'un morceau : {"kind": "stems" | "mp3", "path": dossier des stems ou fichier,
"bpm": tempo exact ou null (grille automatique), "bar1": début de la mesure 1 (s), "n_bars": …,
"truth": [[mesure de début 1-based, "Nom"], …] ou null (plausibilité seulement)} ; variantes :
{"kind": "mixof", "base": "nom"} (mix des stems du morceau de base, comme un MP3) ou
{"kind": "stems", "base": "nom", "drop": ["vocals"]} (stems sans la voix).
Les noms de vérité peuvent être en français ou en anglais.
"""
from __future__ import annotations

import glob
import json
import os
import pickle

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reacue_mcp import analysis as A  # noqa: E402
from reacue_mcp.i18n import section_kind  # noqa: E402


def _arg(name, default):
    for a in sys.argv[1:]:
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    if name in sys.argv[1:]:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


SONGS_FILE = Path(_arg("--songs", str(ROOT / "tools" / "struct_eval_songs.json")))
CACHE = _arg("--cache", os.environ.get("REACUE_STRUCT_CACHE", str(Path.home() / ".cache" / "reacue" / "struct")))
FEAT_VERSION = 8          # à incrémenter quand _stems_inputs/_mix_inputs changent


def _load_songs() -> dict:
    if not SONGS_FILE.exists():
        raise SystemExit(f"Fichier des morceaux de test absent : {SONGS_FILE}\n"
                         f"(copie tools/struct_eval_songs.example.json et adapte-le)")
    raw = json.loads(SONGS_FILE.read_text(encoding="utf-8"))
    out = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        v = dict(v)
        if v.get("truth"):
            v["truth"] = [(int(a), str(b)) for a, b in v["truth"]]
        if v.get("drop"):
            v["drop"] = tuple(v["drop"])
        out[k] = v
    return out


SONGS: dict = {}


# --------------------------------------------------------------------------- caches
def _stem_files(path):
    return sorted(glob.glob(os.path.join(path, "*.wav")) + glob.glob(os.path.join(path, "*.mp3")))


def _resolve(key, cfg):
    """Variante : hérite de la config du morceau de base."""
    if "base" in cfg:
        b = dict(SONGS[cfg["base"]])
        b.update({k: v for k, v in cfg.items() if k != "base"})
        return cfg["base"], b
    return key, cfg


def _audio(key, cfg):
    """Signaux rééchantillonnés (mono, SR) en cache : {rôle: y}."""
    key, cfg = _resolve(key, cfg)
    if cfg["kind"] == "mixof":
        by, files = _audio(key, dict(cfg, kind="stems"))
        return {"mix": _mix(by)}, files
    out = {}
    if cfg["kind"] == "stems":
        files = _stem_files(cfg["path"])
        roles = A.assign_roles(files)
    else:
        files, roles = [cfg["path"]], ["mix"]
    for f, r in zip(files, roles):
        c = os.path.join(CACHE, f"audio_{key}_{r}.npy")
        if not os.path.exists(c):
            y = A.librosa.load(f, sr=A.SR, mono=True)[0]
            np.save(c, y.astype(np.float32))
        if r not in cfg.get("drop", ()):
            out[r] = np.load(c)
    return out, files


def _mix(by_role):
    if "mix" in by_role:
        return by_role["mix"]
    n = max(len(y) for y in by_role.values())
    mix = np.zeros(n, dtype=np.float32)
    for y in by_role.values():
        mix[:len(y)] += y
    return (mix / (np.abs(mix).max() + 1e-9)).astype(np.float32)


def _grid(key, cfg, by_role, mix):
    """Grille réelle (calculée une fois, en cache) puis, si connue, grille imposée."""
    c = os.path.join(CACHE, f"grid_{key}.pkl")
    if os.path.exists(c):
        g = pickle.load(open(c, "rb"))
    else:
        warnings = []
        dur = len(mix) / A.SR
        if cfg["kind"] == "stems":
            y_beat = by_role.get("drums", mix)
            y_harm = by_role.get("bass", mix)
            pre_src = [(r, p) for r, p in by_role.items() if r != "drums"]
            bpm_hint = A.bpm_from_filenames(_stem_files(cfg["path"]))
            res = A._build_grid(y_beat, mix, A.SR, dur, None, 4, bpm_hint, warnings, y_low=None,
                                start_bpm=150.0, y_drums=y_beat, y_harm=y_harm, preroll_sources=pre_src)
        else:
            res = A._build_grid(mix, mix, A.SR, dur, None, 4, None, warnings)
        beats, m, downbeats, bpm, stable, cv, ginfo = res
        g = dict(downbeats=np.asarray(downbeats), bpm=bpm, ginfo=ginfo, warnings=warnings)
        pickle.dump(g, open(c, "wb"))
    if cfg.get("bpm"):
        bar = 240.0 / cfg["bpm"]
        nb = cfg["n_bars"] + EXTRA          # mesures en plus pour tester la robustesse (+1, +2)
        nb = max(cfg["n_bars"], min(nb, int((len(mix) / A.SR - cfg["bar1"]) / bar) + 1))
        known = cfg["bar1"] + bar * np.arange(nb + 1)
        # pré-roll : nombre de mesures entre la 1re mesure connue et la 1re mesure de la grille réelle
        db = g["downbeats"]
        pre_real = g["ginfo"].get("pre_bars", 0)
        start_pulse = db[0] + pre_real * (db[1] - db[0])
        pre = int(round((start_pulse - known[0]) / bar))
        ginfo = dict(g["ginfo"], pre_bars=max(0, pre))
        return known, ginfo, g
    return g["downbeats"], g["ginfo"], g


def _inputs(key, cfg, refeat=False):
    c = os.path.join(CACHE, f"feat_{key}_v{FEAT_VERSION}.pkl")
    if os.path.exists(c) and not refeat:
        d = pickle.load(open(c, "rb"))
        return d["inp"], d["db"], d["t_feat"], d["g"]
    by_role, files = _audio(key, cfg)
    mix = _mix(by_role)
    bkey, bcfg = _resolve(key, cfg)
    if bkey != key:                     # variante : grille du morceau de base
        full, _ = _audio(bkey, dict(bcfg, kind="stems", drop=()))
        db, ginfo, g = _grid(bkey, bcfg, full, _mix(full))
        if cfg["kind"] == "mixof":
            ginfo = dict(ginfo, pre_bars=0)   # en MP3 la grille réelle part de l'entrée de la pulsation
    else:
        db, ginfo, g = _grid(key, cfg, by_role, mix)
    cfg = bcfg
    t = time.time()
    if cfg["kind"] == "stems":
        inp = A._stems_inputs(by_role, mix, db, ginfo)
        inp.pop("voc_act", None)
    else:
        inp = A._mix_inputs(mix, A.SR, db, ginfo)
    t_feat = time.time() - t
    pickle.dump(dict(inp=inp, db=db, t_feat=t_feat, g=g), open(c, "wb"))
    return inp, db, t_feat, g


# --------------------------------------------------------------------------- score
def norm_type(name):
    """Type de section, indépendant de la langue (français ou anglais)."""
    return section_kind(name)


def match(ref, est, tol):
    """Appariement glouton un-à-un des frontières à ±tol."""
    used, hit = set(), 0
    for r in ref:
        cands = [(abs(e - r), e) for e in est if e not in used and abs(e - r) <= tol]
        if cands:
            used.add(min(cands)[1])
            hit += 1
    return hit


def score(truth, n_bars, secs):
    tb = [s for s, _ in truth[1:]]                      # 1-based
    eb = [s.start_bar + 1 for s in secs[1:]]
    out = {}
    for tol in (0, 1, 2):
        h = match(tb, eb, tol)
        p = h / max(1, len(eb))
        r = h / max(1, len(tb))
        out[f"F{tol}"] = 2 * p * r / max(1e-9, p + r)
        out[f"h{tol}"] = h
    # noms : par mesure (type)
    ttype = np.empty(n_bars, dtype=object)
    starts = [s - 1 for s, _ in truth] + [n_bars]
    for (s, nm), a, b in zip(truth, starts[:-1], starts[1:]):
        ttype[a:b] = norm_type(nm)
    etype = np.empty(n_bars, dtype=object)
    for s in secs:
        etype[s.start_bar:min(s.end_bar, n_bars)] = norm_type(s.name)
    out["name_bars"] = float(np.mean(ttype == etype))
    # noms : par section de vérité (type majoritaire détecté sur ses mesures)
    ok = 0
    for (s, nm), a, b in zip(truth, starts[:-1], starts[1:]):
        vals, cnt = np.unique(etype[a:b].astype(str), return_counts=True)
        ok += vals[np.argmax(cnt)] == norm_type(nm)
    out["name_secs"] = ok / len(truth)
    out["n_true"], out["n_est"] = len(truth), len(secs)
    out["global"] = (out["F1"] + out["name_bars"]) / 2
    return out


def show(secs, truth=None):
    tmap = {s: nm for s, nm in (truth or [])}
    for s in secs:
        L = s.end_bar - s.start_bar
        flag = "" if L % 4 == 0 else "  *"
        t = tmap.get(s.start_bar + 1, "")
        print(f"    {s.start_bar + 1:4d}-{s.end_bar:<4d} ({L:3d}) {s.label:2s} {s.name:18s} {s.energy_db:6.1f}"
              f"  {('= ' + t) if t else ''}{flag}")
    if truth:
        miss = [f"{s}:{nm}" for s, nm in truth if s - 1 not in {x.start_bar for x in secs}]
        if miss:
            print("    vérité non trouvée exacte :", ", ".join(miss))


SEC = A._sections
EXTRA = 2
PERTURB = (-2, -1, 1, 2)       # écarts de longueur testés (mesures en fin de morceau)


def _trim(inp, nb):
    out = {k: (v[:nb] if isinstance(v, np.ndarray) else v) for k, v in inp.items() if k != "feats"}
    out["feats"] = {k: v[:nb] for k, v in inp["feats"].items()}
    return out


def main():
    global SEC, SONGS
    SONGS = _load_songs()
    os.makedirs(CACHE, exist_ok=True)
    args = sys.argv[1:]
    mod = next((a.split("=", 1)[1] for a in args if a.startswith("--mod=")), None)
    if "--orig" in args:
        mod = f"{CACHE}/analysis_orig.py"
    if mod:                               # autre version de la segmentation (mêmes caractéristiques)
        import importlib.util
        import inspect
        spec = importlib.util.spec_from_file_location("analysis_orig", mod)
        O = importlib.util.module_from_spec(spec)
        sys.modules["analysis_orig"] = O
        spec.loader.exec_module(O)
        params = inspect.signature(O._sections).parameters
        SEC = lambda **kw: O._sections(**{k: v for k, v in kw.items() if k in params})
    refeat, full, verbose = "--refeat" in args, "--full" in args, "-v" in args
    skip_vals = {_arg("--songs", None), _arg("--cache", None)}
    only = [a for a in args if not a.startswith("-") and a not in skip_vals]
    rows, glob_scores = [], []
    for key, cfg0 in SONGS.items():
        if only and key not in only:
            continue
        inp, db, t_feat, g = _inputs(key, cfg0, refeat)
        cfg = _resolve(key, cfg0)[1]
        n_bars = cfg.get("n_bars") or len(db) - 1
        full_inp = inp
        inp = _trim(full_inp, n_bars)
        t = time.time()
        secs = SEC(min_section_bars=4, **inp)
        t_sec = time.time() - t
        pert = []
        if cfg["truth"] and "--noperturb" not in args:
            for d in PERTURB:
                nb = n_bars + d
                if nb <= len(full_inp["feats"]["E"]):
                    sp = SEC(min_section_bars=4, **_trim(full_inp, nb))
                    pert.append(score(cfg["truth"], n_bars, sp)["global"])
        t_full = None
        if full and "base" not in cfg0:
            t0 = time.time()
            if cfg["kind"] == "stems":
                files = _stem_files(cfg["path"])
                A.analyze_stems([{"file": f, "shift": 0.0} for f in files])
            else:
                A.analyze(cfg["path"])
            t_full = time.time() - t0
        if verbose or not cfg["truth"]:
            print(f"\n== {key}  ({n_bars} mesures, grille {'connue' if cfg.get('bpm') else 'auto'} ; "
                  f"pré-roll {inp.get('n_pre', 0)} mes. '{inp.get('pre_name')}')")
            show(secs, cfg["truth"])
        lens = [x.end_bar - x.start_bar for x in secs]
        plaus = (max(lens) <= 32, len(secs) >= max(3, round(n_bars / 24)))
        if not all(plaus):
            print(f"  !! {key} : plausibilité KO (section max {max(lens)}, {len(secs)} sections "
                  f"pour {n_bars} mesures)")
        if cfg["truth"]:
            sc = score(cfg["truth"], n_bars, secs)
            if pert:
                sc["pmean"] = float(np.mean(pert + [sc["global"]]))
                sc["pmin"] = float(min(pert + [sc["global"]]))
            if not cfg.get("indicative"):
                glob_scores.append(sc.get("pmean", sc["global"]))
            else:
                key = key + " (ind.)"
            rows.append((key, sc, t_feat, t_sec, t_full))
        else:
            lens = [s.end_bar - s.start_bar for s in secs]
            odd = sum(1 for L in lens if L % 4)
            rows.append((key, {"n_est": len(secs), "odd": odd}, t_feat, t_sec, t_full))
    print("\nmorceau     | exact  ±1    ±2    | noms/mes noms/sec | n vrai/est | global (perturb. moy/min) | t_feat t_sect t_full")
    for key, sc, tf, ts, tfull in rows:
        tfs = f"{tfull:6.1f}" if tfull else "     -"
        if "F0" in sc:
            print(f"{key:11s} | {sc['h0']:2d}/{sc['n_true']-1:<2d} {sc['h1']:2d}    {sc['h2']:2d}    | "
                  f"{sc['name_bars']:.2f}     {sc['name_secs']:.2f}     | {sc['n_true']:3d}/{sc['n_est']:<3d}   "
                  f"| {sc['global']:.3f} ({sc.get('pmean', 0):.3f}/{sc.get('pmin', 0):.3f}) "
                  f"| {tf:5.1f}  {ts:5.2f} {tfs}")
        else:
            print(f"{key:11s} | (pas de vérité) {sc['n_est']} sections, {sc['odd']} hors carrure de 4"
                  f"{'':14s}| {tf:5.1f}  {ts:5.2f} {tfs}")
    if glob_scores:
        print(f"\nSCORE GLOBAL (moyenne sur les longueurs perturbées de (F±1 + noms/mesure)/2) : "
              f"{np.mean(glob_scores):.3f}")


if __name__ == "__main__":
    main()
