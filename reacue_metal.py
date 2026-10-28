"""Optional macOS Metal inference; no torch import until a worker needs it.

CPU remains the default on Intel and other platforms. A failed MPS operation is
retried once on CPU and that model stays on CPU for the rest of the process.
"""
from __future__ import annotations

import os
import sys
import warnings


def configure():
    # PyTorch reads this at import time. Preserve an explicit user choice.
    if sys.platform == "darwin":
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


def device(torch):
    """Return MPS only when the installed runtime actually supports it."""
    if sys.platform == "darwin" and os.environ.get("REACUE_DEVICE", "auto").lower() != "cpu":
        mps = getattr(getattr(torch, "backends", None), "mps", None)
        if mps is not None and mps.is_available():
            return "mps"
    return "cpu"


def cpu_fallback(error):
    warnings.warn(f"Metal (MPS) unavailable for this model; retrying on CPU: {error}",
                  RuntimeWarning, stacklevel=2)
    import torch
    torch.mps.empty_cache()


def forward(model, inputs):
    """Run a float32 audio model; return CPU outputs for NumPy / CTC consumers."""
    import torch
    target = "cpu" if getattr(model, "_reacue_cpu", False) else device(torch)
    try:
        model.to(target)
        with torch.inference_mode():
            result = model(inputs.to(target))
    except (RuntimeError, NotImplementedError, TypeError) as error:
        if target != "mps":
            raise
        model.to("cpu")
        model._reacue_cpu = True
        cpu_fallback(error)
        with torch.inference_mode():
            result = model(inputs.to("cpu"))
    if isinstance(result, tuple):
        return tuple(x.cpu() if hasattr(x, "cpu") else x for x in result)
    return result.cpu()
