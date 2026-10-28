"""Analyse de structure pour ReaCue (SongFormer, en local) / Structure analysis for ReaCue (SongFormer, local).

Tourne dans l'environnement séparé .venv-structure (installé par install/install_structure_*), jamais dans
le .venv de ReaCue. Utilise SongFormer (ASLP-lab, licence CC BY 4.0, arXiv 2510.02797) téléchargé par
l'installateur dans <ReaCue>/structure/SongFormer (révision figée), avec ses dépendances MuQ et MusicFM.
Modèles : dans <ReaCue>/structure/SongFormer/src/SongFormer/ckpts et <ReaCue>/structure/hf (HF_HOME).

    <python> reacue_structure.py analyze --input <audio> --out <résultat.json> [--status <état.json>]
                                         [--window auto|420|120]
        -> {"segments": [{"start", "end", "label"}], "window_s", "seconds", "engine": "songformer"}
    <python> reacue_structure.py check [--lang fr|en]    # télécharge les modèles, teste, « STRUCTURE_OK »
    <python> reacue_structure.py reuse [--lang fr|en] [--from <dossier>]...
        # réutilise des modèles déjà téléchargés (copie ou lien, vérifiés par md5 / taille) au lieu de
        # les retélécharger : ckpts d'une autre installation de SongFormer (ex. ~/Documents/ReaCue-labo)
        # et cache Hugging Face par défaut (~/.cache/huggingface/hub, %USERPROFILE%/.cache/huggingface/hub).
        # Les sources ne sont jamais modifiées ni supprimées.

Fenêtre globale : 420 s (réglage du modèle) si la mémoire vive est >= 15 Go, sinon 120 s (moins précis
mais tient en ~4 Go). Calcul sur CUDA, Metal/MPS sur Mac compatible, sinon CPU.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
import types
from pathlib import Path

import reacue_performance

reacue_performance.configure()

import reacue_metal

reacue_metal.configure()

HERE = Path(__file__).resolve().parent
STRUCT_DIR = Path(os.environ.get("REACUE_STRUCTURE_DIR") or HERE / "structure")
REPO = STRUCT_DIR / "SongFormer"
LABELS = ("intro", "verse", "pre-chorus", "chorus", "bridge", "inst", "silence", "outro")


def ram_gb() -> float:
    """Mémoire vive totale (Go) : macOS / Linux (sysconf), Windows (GlobalMemoryStatusEx)."""
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 2 ** 30
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except Exception:
        return 8.0


def choose_window(window: str | int | None = "auto", ram: float | None = None) -> int:
    if str(window).isdigit():
        return max(30, int(window))
    ram = ram_gb() if ram is None else ram
    return 120 if reacue_performance.profile() == "fast" else (420 if ram >= 15 else 120)


def _write_status(path: Path | None, state: str, **kw):
    if not path:
        return
    d = {"state": state, "time": time.time(), "pid": os.getpid(), **kw}
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _stub_modules():
    """gradio (interface web de app.py) et msaf.eval (scores d'évaluation) : inutiles ici."""
    class _Any:
        def __init__(self, *a, **k): pass
        def __call__(self, *a, **k): return _Any()
        def __getattr__(self, n):
            if n.startswith("__"):
                raise AttributeError(n)
            return _Any()
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __iter__(self): return iter(())

    def _ga(n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _Any()
    gr = types.ModuleType("gradio")
    gr.__getattr__ = _ga
    sys.modules.setdefault("gradio", gr)
    msaf = types.ModuleType("msaf")
    ev = types.ModuleType("msaf.eval")
    ev.compute_results = lambda *a, **k: {}
    msaf.eval = ev
    sys.modules.setdefault("msaf", msaf)
    sys.modules.setdefault("msaf.eval", ev)


def load_app():
    """Importe app.py de SongFormer (sans son interface) ; renvoie le module."""
    if not (REPO / "app.py").is_file():
        raise FileNotFoundError(f"SongFormer introuvable / not found: {REPO}")
    os.environ.setdefault("HF_HOME", str(STRUCT_DIR / "hf"))
    os.chdir(REPO)
    sys.path.insert(0, str(REPO))
    _stub_modules()
    import app  # noqa: E402  (fait chdir dans src/SongFormer et ajoute third_party au chemin)
    return app


def init_models(app):
    app.download_all(use_mirror=False)
    app.initialize_models(model_name="SongFormer", checkpoint="SongFormer.safetensors",
                          config_path="SongFormer.yaml")
    import torch
    if reacue_metal.device(torch) == "mps":
        try:
            _move_models(app, "mps")
        except (RuntimeError, NotImplementedError, TypeError) as error:
            _move_models(app, "cpu")
            reacue_metal.cpu_fallback(error)


def _move_models(app, target):
    # Upstream initializes on CUDA/CPU and reads this global for input tensors.
    for name in ("muq_model", "musicfm_model", "msa_model"):
        getattr(app, name).to(target)
    app.device = target


def segments_from_app(app, audio: str, window: int) -> list[dict]:
    try:
        _, msa = app.process_audio(audio, win_size=window, hop_size=window)
    except (RuntimeError, NotImplementedError, TypeError) as error:
        if str(getattr(app, "device", "cpu")) != "mps":
            raise
        _move_models(app, "cpu")
        reacue_metal.cpu_fallback(error)
        _, msa = app.process_audio(audio, win_size=window, hop_size=window)
    msa = app.rule_post_processing(msa)
    return [{"start": float(s["start"]), "end": float(s["end"]), "label": str(s["label"])}
            for s in app.format_as_segments(msa)]


def analyze(audio: str, out: str, status: str | None = None, window: str = "auto") -> int:
    st = Path(status) if status else None
    audio = str(Path(audio).resolve())
    out = Path(out).resolve()
    t0 = time.time()
    try:
        if not Path(audio).is_file():
            raise FileNotFoundError(audio)
        win = choose_window(window)
        _write_status(st, "running", step="chargement des modèles / loading models", window_s=win)
        app = load_app()
        import torch
        reacue_performance.configure_torch(torch)
        init_models(app)
        _write_status(st, "running", step="analyse / analysing", window_s=win)
        segs = segments_from_app(app, audio, win)
        res = {"engine": "songformer", "segments": segs, "window_s": win, "seconds": round(time.time() - t0)}
        tmp = Path(str(out) + ".tmp")
        tmp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, out)
        _write_status(st, "done", seconds=res["seconds"])
        return 0
    except BaseException as e:                       # noqa: BLE001 - rapporté à ReaCue
        traceback.print_exc()
        _write_status(st, "error", message=f"{type(e).__name__}: {e}")
        return 1


# --------------------------------------------------------------------------- réutilisation des modèles
CKPTS = ("SongFormer.safetensors", "MusicFM/pretrained_msd.pt", "MusicFM/msd_stats.json")
HF_REPOS = ("models--OpenMuQ--MuQ-large-msd-iter", "models--facebook--wav2vec2-conformer-rope-large-960h-ft")


def ckpts_dir(struct_dir: Path | None = None) -> Path:
    return (struct_dir or STRUCT_DIR) / "SongFormer" / "src" / "SongFormer" / "ckpts"


def _md5(path: Path) -> str:
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def _md5_table(*dirs: Path) -> dict:
    """md5sum.txt de SongFormer (« <md5>  <chemin relatif> ») ; premier fichier trouvé."""
    for d in dirs:
        f = d / "md5sum.txt"
        if f.is_file():
            out = {}
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    out[parts[-1].replace("\\", "/")] = parts[0].lower()
            return out
    return {}


def ckpt_sources(extra: list | None = None, home: Path | None = None) -> list[Path]:
    """Dossiers ckpts candidats : --from / REACUE_REUSE_DIRS, puis ~/Documents/ReaCue-labo (laboratoire)."""
    home = home or Path.home()
    cands = [Path(x) for x in (extra or [])]
    cands += [Path(x) for x in os.environ.get("REACUE_REUSE_DIRS", "").split(os.pathsep) if x]
    cands.append(home / "Documents" / "ReaCue-labo" / "SongFormer" / "src" / "SongFormer" / "ckpts")
    out = []
    for c in cands:
        for d in (c, c / "src" / "SongFormer" / "ckpts", c / "SongFormer" / "src" / "SongFormer" / "ckpts"):
            if d.is_dir() and (d / CKPTS[0]).is_file() and d not in out:
                out.append(d)
                break
    return out


def hf_sources(home: Path | None = None) -> list[Path]:
    """Caches Hugging Face par défaut (macOS, Linux, Windows) : dossiers « hub »."""
    home = home or Path.home()
    cands = []
    if os.environ.get("REACUE_HF_SOURCE"):
        cands.append(Path(os.environ["REACUE_HF_SOURCE"]))
    if os.environ.get("HF_HUB_CACHE"):
        cands.append(Path(os.environ["HF_HUB_CACHE"]))
    if os.environ.get("HF_HOME"):
        cands.append(Path(os.environ["HF_HOME"]) / "hub")
    if os.environ.get("XDG_CACHE_HOME"):
        cands.append(Path(os.environ["XDG_CACHE_HOME"]) / "huggingface" / "hub")
    cands.append(home / ".cache" / "huggingface" / "hub")
    if os.environ.get("USERPROFILE"):
        cands.append(Path(os.environ["USERPROFILE"]) / ".cache" / "huggingface" / "hub")
    out = []
    for c in cands:
        if c.is_dir() and c not in out:
            out.append(c)
    return out


def _place(src: Path, dst: Path):
    """Lien physique si possible (même disque, aucune place en plus), sinon copie ; via un .part."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    if tmp.exists():
        tmp.unlink()
    try:
        os.link(src, tmp)
    except OSError:
        import shutil
        shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def _hf_repo_ok(repo: Path) -> bool:
    """Snapshot complet : au moins un fichier, tous non vides (liens résolus)."""
    snaps = repo / "snapshots"
    if not snaps.is_dir():
        return False
    files = [f for f in snaps.rglob("*") if not f.is_dir()]
    try:
        return bool(files) and all(f.exists() and f.stat().st_size > 0 for f in files)
    except OSError:
        return False


def reuse(sources: list | None = None, struct_dir: Path | None = None, hf_home: Path | None = None,
          home: Path | None = None, log=print, lang: str = "fr") -> dict:
    """Copie / lie les modèles déjà présents sur la machine vers l'emplacement attendu par ReaCue.
    Renvoie {"ckpts": [fichiers placés], "hf": [dépôts placés], "skipped": [(élément, raison)]}."""
    import shutil

    def t(fr, en):
        return en if lang == "en" else fr
    struct_dir = Path(struct_dir or STRUCT_DIR)
    dest = ckpts_dir(struct_dir)
    hf_hub = Path(hf_home or os.environ.get("HF_HOME") or struct_dir / "hf") / "hub"   # comme load_app
    res = {"ckpts": [], "hf": [], "skipped": []}
    srcs = ckpt_sources(sources, home)
    table = _md5_table(dest, *srcs)
    for rel in CKPTS:
        d = dest / rel
        want = table.get(rel)
        if d.is_file() and d.stat().st_size > 0 and (not want or _md5(d) == want):
            continue                                   # déjà en place et intact
        for s in srcs:
            f = s / rel
            if not f.is_file() or f.stat().st_size == 0:
                continue
            if want and _md5(f) != want:
                res["skipped"].append((str(f), "md5"))
                continue
            if d.exists() and d.resolve() == f.resolve():
                break
            _place(f, d)
            res["ckpts"].append(rel)
            log(t(f"  modèle réutilisé : {rel} (depuis {s})", f"  model reused: {rel} (from {s})"))
            break
    for repo in HF_REPOS:
        d = hf_hub / repo
        if _hf_repo_ok(d):
            continue
        for s in hf_sources(home):
            src = s / repo
            if d.exists() and src.resolve() == d.resolve():
                break
            if not _hf_repo_ok(src):
                if src.exists():
                    res["skipped"].append((str(src), "incomplete"))
                continue
            if d.exists():
                shutil.rmtree(d)                       # copie précédente incomplète (jamais la source)
            d.parent.mkdir(parents=True, exist_ok=True)
            tmp = d.with_name(d.name + ".part")
            if tmp.exists():
                shutil.rmtree(tmp)
            shutil.copytree(src, tmp, symlinks=True)
            os.replace(tmp, d)
            res["hf"].append(repo)
            log(t(f"  modèle réutilisé : {repo} (depuis {s})", f"  model reused: {repo} (from {s})"))
            break
    if not res["ckpts"] and not res["hf"]:
        log(t("  aucun modèle déjà téléchargé à réutiliser.", "  no already-downloaded model to reuse."))
    return res


def check(lang: str = "fr", seconds: int = 20) -> int:
    def t(fr, en):
        return en if lang == "en" else fr
    try:
        app = load_app()
        import numpy as np
        import torch
        import soundfile as sf
    except Exception as e:                           # noqa: BLE001
        print(t("ÉCHEC : SongFormer n'est pas importable : ", "FAILED: SongFormer cannot be imported: ") + repr(e))
        return 1
    reacue_performance.configure_torch(torch)
    win = choose_window("auto")
    print(f"  python {sys.version.split()[0]} | torch {torch.__version__} | numpy {np.__version__} | "
          f"RAM {ram_gb():.0f} Go/GB -> {t('fenêtre', 'window')} {win} s")
    print(t("  téléchargement des modèles (environ 2 Go la première fois)…",
            "  downloading the models (about 2 GB the first time)…"), flush=True)
    t0 = time.time()
    init_models(app)
    print(f"  device: {getattr(app, 'device', 'cpu')}")
    print(t(f"  modèles prêts ({time.time() - t0:.0f} s)", f"  models ready ({time.time() - t0:.0f} s)"), flush=True)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "test.wav"
        sr = 24000
        x = (np.random.default_rng(0).standard_normal(sr * seconds) * 0.05).astype(np.float32)
        sf.write(str(wav), x, sr)
        t0 = time.time()
        segments_from_app(app, str(wav), min(win, 120))
        per_song = (time.time() - t0) / seconds * 240 / 60
    print(t(f"  vitesse : environ {per_song:.0f} min pour un morceau de 4 min",
            f"  speed: about {per_song:.0f} min for a 4-minute song"))
    print("STRUCTURE_OK")
    return 0



def benchmark_threads(app, audio, counts, repeats=2, window=120, clock=time.perf_counter, progress=None):
    """Compare actual SongFormer CPU inference, excluding model load and warm-up."""
    import torch
    _move_models(app, "cpu")
    previous = torch.get_num_threads()
    results = []
    try:
        for count in counts:
            if progress:
                progress(f"Testing / Test : {count} threads…", flush=True)
            torch.set_num_threads(count)
            segments_from_app(app, str(audio), window)  # warm-up for this thread count
            times = []
            for _ in range(repeats):
                start = clock()
                segments_from_app(app, str(audio), window)
                times.append(clock() - start)
            results.append({"threads": count, "seconds": sum(times) / len(times)})
    finally:
        torch.set_num_threads(previous)
    return sorted(results, key=lambda row: row["seconds"])


def benchmark(args):
    import tempfile
    import numpy as np
    import soundfile as sf
    counts = sorted(set(int(x) for x in args.threads.split(",")))
    if not counts or any(x < 1 or x > (os.cpu_count() or 1) for x in counts):
        raise ValueError("Threads must be between 1 and the logical CPU count")
    if args.input and not Path(args.input).is_file():
        raise FileNotFoundError(args.input)
    os.environ["REACUE_DEVICE"] = "cpu"  # This benchmark intentionally calibrates CPU inference.
    print("CPU benchmark / Étalonnage CPU — SongFormer, model loaded once.", flush=True)
    print("This can take several minutes / Cela peut prendre plusieurs minutes.", flush=True)
    app = load_app()
    init_models(app)
    with tempfile.TemporaryDirectory() as tmp:
        audio = args.input
        if not audio:
            audio = str(Path(tmp) / "benchmark.wav")
            noise = np.random.default_rng(0).standard_normal(24000 * 20).astype(np.float32) * 0.05
            sf.write(audio, noise, 24000)
        results = benchmark_threads(app, audio, counts, progress=print)
    for row in results:
        print(f"  {row['threads']} threads: {row['seconds']:.3f} s")
    best = results[0]["threads"]
    print(f"Best on this sample / Meilleur sur cet extrait: {best} threads")
    if args.save:
        reacue_performance.save_threads(best)
        print("Saved for subsequent analyses / Enregistré pour les prochaines analyses.")
    print("Results depend on the audio and model / Résultat dépendant de l'audio et du modèle.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="reacue_structure")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--input", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--status")
    a.add_argument("--window", default="auto")
    c = sub.add_parser("check")
    c.add_argument("--lang", default="fr", choices=["fr", "en"])
    c.add_argument("--seconds", type=int, default=20)
    b = sub.add_parser("benchmark", help="Compare CPU threads using actual SongFormer inference")
    b.add_argument("--input", help="Optional representative audio excerpt (otherwise 20s synthetic audio)")
    b.add_argument("--threads", default=",".join(str(n) for n in (1, 2, 4, 8) if n <= (os.cpu_count() or 1)))
    b.add_argument("--save", action="store_true", help="Save fastest thread count to ReaCue settings")
    r = sub.add_parser("reuse")
    r.add_argument("--lang", default="fr", choices=["fr", "en"])
    r.add_argument("--from", dest="sources", action="append", default=[])
    args = ap.parse_args(argv)
    if args.cmd == "benchmark":
        return benchmark(args)
    if args.cmd == "analyze":
        return analyze(args.input, args.out, args.status, args.window)
    if args.cmd == "reuse":
        try:
            reuse(args.sources, lang=args.lang)
        except Exception as e:                       # noqa: BLE001 - jamais bloquant : on téléchargera
            print(("  réutilisation impossible : " if args.lang == "fr" else "  reuse failed: ") + repr(e))
        return 0
    return check(args.lang, args.seconds)


if __name__ == "__main__":
    sys.exit(main())
