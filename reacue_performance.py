"""Shared performance settings for isolated workers (standard library only)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def settings_path():
    root = os.environ.get("REAPER_RESOURCE_PATH")
    if not root:
        if sys.platform == "darwin":
            root = Path.home() / "Library/Application Support/REAPER"
        elif os.name == "nt":
            root = Path(os.environ.get("APPDATA", Path.home())) / "REAPER"
        else:
            root = Path.home() / ".config/REAPER"
    return Path(root) / "ReaCueMCP/reacue_settings.json"


def settings():
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def profile():
    value = os.environ.get("REACUE_PERFORMANCE_PROFILE", settings().get("performance_profile", "standard"))
    return "fast" if value == "fast" else "standard"


def cpu_threads():
    try:
        value = int(os.environ.get("REACUE_CPU_THREADS", settings().get("cpu_threads", 0)))
    except (TypeError, ValueError):
        return 0
    return min(max(0, value), os.cpu_count() or 1)


def configure():
    count = cpu_threads()
    if count:
        # Called before importing torch / NumPy in the isolated worker.
        os.environ["OMP_NUM_THREADS"] = str(count)
        os.environ["MKL_NUM_THREADS"] = str(count)


def configure_torch(torch):
    torch.set_num_threads(cpu_threads() or max(1, os.cpu_count() or 1))


def demucs_args():
    return ["--shifts", "0", "--overlap", "0.1"] if profile() == "fast" else []


def whisper_options():
    # Greedy decoding, without the four-temperature retry ladder.
    return {"temperature": (0.0,), "beam_size": None, "best_of": None} if profile() == "fast" else {}


def save_threads(count):
    path = settings_path()
    data = settings()
    data["cpu_threads"] = int(count)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".performance.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
