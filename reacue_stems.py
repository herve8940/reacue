"""Séparation de stems pour ReaCue (Demucs, en local) / Stem separation for ReaCue (Demucs, local).

Tourne dans l'environnement séparé .venv-demucs (installé par install/install_stems_*), jamais dans le
.venv de ReaCue : Demucs a besoin d'autres versions de torch / numpy. Bibliothèque standard + demucs.

Lancé par l'action REAPER « ReaCue - Séparer les stems » (ReaCue_stems.lua), en arrière-plan :
    <.venv-demucs python> reacue_stems.py separate --input <audio> --out <dossier> [--model htdemucs_6s]
        -> <dossier>/<model>/<nom du fichier>-<stem>.wav
        -> <dossier>/demucs.log (progression de Demucs) et <dossier>/demucs_status.json
           {"state": "running" | "done" | "error", "time", "pid", "model", "files": [...], "message"}
Modèles hors ligne : --repo <dossier> (fichiers .th de Demucs ; --model = nom du modèle dans ce dossier).
Vérification après installation (télécharge les modèles, mesure la vitesse) :
    <.venv-demucs python> reacue_stems.py check [--lang fr|en] [--seconds 10]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

MODELS = {   # stems produits par chaque modèle Demucs (ordre d'import dans REAPER)
    "htdemucs_6s": ("vocals", "drums", "bass", "guitar", "piano", "other"),
    "htdemucs": ("vocals", "drums", "bass", "other"),
    "htdemucs_ft": ("vocals", "drums", "bass", "other"),
}
DEFAULT_MODEL = "htdemucs_6s"
FILENAME = "{track}-{stem}.{ext}"     # le nom d'origine (tonalité, bpm) est gardé : ReaCue le lit


def stem_files(input_file: str | Path, out: str | Path, model: str) -> list[Path]:
    """Fichiers que Demucs écrira pour `input_file` (même convention que l'action REAPER)."""
    track = Path(input_file).name.rsplit(".", 1)[0]
    return [Path(out) / model / f"{track}-{s}.wav" for s in MODELS[model]]


def _write_status(path: Path, state: str, **kw):
    d = {"state": state, "time": time.time(), "pid": os.getpid(), **kw}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def separate(input_file: str, out: str, model: str = DEFAULT_MODEL, repo: str | None = None) -> int:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = out_dir / "demucs_status.json"
    log = open(out_dir / "demucs.log", "w", encoding="utf-8", buffering=1)
    old = sys.stdout, sys.stderr
    sys.stdout = log            # pythonw (Windows) : pas de console ; ailleurs : nohup
    sys.stderr = log            # tqdm (barre de progression de Demucs) écrit ici : lu par REAPER
    if model not in MODELS and not repo:
        model = DEFAULT_MODEL
    stems = MODELS.get(model, MODELS[DEFAULT_MODEL])
    track = Path(input_file).name.rsplit(".", 1)[0]
    files = [out_dir / model / f"{track}-{s}.wav" for s in stems]
    _write_status(status, "running", model=model, input=str(input_file))
    try:
        if not Path(input_file).is_file():
            raise FileNotFoundError(input_file)
        from demucs.separate import main as demucs_main
        try:
            demucs_main(["-n", model, "-o", str(out_dir), "--filename", FILENAME]
                        + (["--repo", str(repo)] if repo else []) + [str(input_file)])
        except SystemExit as e:              # Demucs appelle sys.exit en cas d'erreur
            if e.code not in (None, 0):
                raise RuntimeError(f"demucs exit {e.code}") from None
        missing = [str(f) for f in files if not f.is_file()]
        if missing:
            raise RuntimeError("missing: " + ", ".join(missing))
        _write_status(status, "done", model=model, files=[str(f) for f in files])
        return 0
    except BaseException as e:               # noqa: BLE001 - tout est rapporté à REAPER
        traceback.print_exc()
        _write_status(status, "error", model=model, message=f"{type(e).__name__}: {e}")
        return 1
    finally:
        sys.stdout, sys.stderr = old
        log.close()


def check(lang: str = "fr", seconds: int = 10) -> int:
    """Charge (et télécharge au besoin) les modèles, puis mesure la vitesse sur un signal de test."""
    def t(fr, en):
        return en if lang == "en" else fr
    try:
        import numpy
        import torch
        import torchaudio
        import demucs
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
    except Exception as e:                   # noqa: BLE001
        print(t("ÉCHEC : Demucs n'est pas importable : ", "FAILED: Demucs cannot be imported: ") + repr(e))
        return 1
    print(f"  python {sys.version.split()[0]} | numpy {numpy.__version__} | torch {torch.__version__} | "
          f"torchaudio {torchaudio.__version__} | demucs {demucs.__version__} | threads {torch.get_num_threads()}")
    x = torch.randn(1, 2, 44100 * seconds) * 0.1
    for name in ("htdemucs", "htdemucs_6s"):
        t0 = time.time()
        m = get_model(name)
        m.eval()
        print(t(f"  modèle {name} prêt ({time.time() - t0:.0f} s) : {', '.join(m.sources)}",
                f"  model {name} ready ({time.time() - t0:.0f} s): {', '.join(m.sources)}"))
        t0 = time.time()
        with torch.no_grad():
            apply_model(m, x, shifts=1, split=True, overlap=0.25, progress=False, device="cpu")
        per_song = (time.time() - t0) / seconds * 240 / 60
        print(t(f"  vitesse {name} : environ {per_song:.1f} min pour un morceau de 4 min",
                f"  speed {name}: about {per_song:.1f} min for a 4-minute song"))
    print("STEMS_OK")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="reacue_stems")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("separate")
    s.add_argument("--input", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--model", default=DEFAULT_MODEL)
    s.add_argument("--repo", help="dossier de modèles locaux (hors ligne) / local models folder (offline)")
    c = sub.add_parser("check")
    c.add_argument("--lang", default="fr", choices=["fr", "en"])
    c.add_argument("--seconds", type=int, default=10)
    a = ap.parse_args(argv)
    if a.cmd == "separate":
        return separate(a.input, a.out, a.model, a.repo)
    return check(a.lang, a.seconds)


if __name__ == "__main__":
    sys.exit(main())
