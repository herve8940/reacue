"""Analyse de structure pour ReaCue (SongFormer, en local) / Structure analysis for ReaCue (SongFormer, local).

Tourne dans l'environnement séparé .venv-structure (installé par install/install_structure_*), jamais dans
le .venv de ReaCue. Utilise SongFormer (ASLP-lab, licence CC BY 4.0, arXiv 2510.02797) téléchargé par
l'installateur dans <ReaCue>/structure/SongFormer (révision figée), avec ses dépendances MuQ et MusicFM.
Modèles : dans <ReaCue>/structure/SongFormer/src/SongFormer/ckpts et <ReaCue>/structure/hf (HF_HOME).

    <python> reacue_structure.py analyze --input <audio> --out <résultat.json> [--status <état.json>]
                                         [--window auto|420|120]
        -> {"segments": [{"start", "end", "label"}], "window_s", "seconds", "engine": "songformer"}
    <python> reacue_structure.py check [--lang fr|en]    # télécharge les modèles, teste, « STRUCTURE_OK »

Fenêtre globale : 420 s (réglage du modèle) si la mémoire vive est >= 15 Go, sinon 120 s (moins précis
mais tient en ~4 Go). Calcul sur CPU (GPU NVIDIA utilisé s'il est disponible).
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
    return 420 if ram >= 15 else 120


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


def segments_from_app(app, audio: str, window: int) -> list[dict]:
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
        torch.set_num_threads(max(1, os.cpu_count() or 1))
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
    win = choose_window("auto")
    print(f"  python {sys.version.split()[0]} | torch {torch.__version__} | numpy {np.__version__} | "
          f"RAM {ram_gb():.0f} Go/GB -> {t('fenêtre', 'window')} {win} s")
    print(t("  téléchargement des modèles (environ 2 Go la première fois)…",
            "  downloading the models (about 2 GB the first time)…"), flush=True)
    t0 = time.time()
    init_models(app)
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
    args = ap.parse_args(argv)
    if args.cmd == "analyze":
        return analyze(args.input, args.out, args.status, args.window)
    return check(args.lang, args.seconds)


if __name__ == "__main__":
    sys.exit(main())
