"""Metal selection, CPU fallback and device boundaries, without Mac hardware/models."""
import sys
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

import reacue_metal as metal


class Tensor:
    def __init__(self, device="cpu"):
        self.device = device

    def to(self, device):
        return Tensor(device)

    def cpu(self):
        return self.to("cpu")


class Model:
    def __init__(self, failure=None):
        self.device = "cpu"
        self.failure = failure
        self.calls = []

    def to(self, device):
        self.device = device
        return self

    def __call__(self, x):
        assert x.device == self.device
        self.calls.append(x.device)
        if self.failure and x.device == "mps":
            raise self.failure
        return Tensor(x.device), None


@pytest.fixture
def torch_stub(monkeypatch):
    cleared = []
    stub = SimpleNamespace(set_num_threads=lambda n: None, backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
                           inference_mode=nullcontext,
                           mps=SimpleNamespace(empty_cache=lambda: cleared.append(True)))
    monkeypatch.setitem(sys.modules, "torch", stub)
    monkeypatch.setattr(metal.sys, "platform", "darwin")
    monkeypatch.delenv("REACUE_DEVICE", raising=False)
    return stub, cleared


def test_mps_selection_uses_runtime_not_architecture(torch_stub, monkeypatch):
    torch, _ = torch_stub
    assert metal.device(torch) == "mps"
    torch.backends.mps.is_available = lambda: False
    assert metal.device(torch) == "cpu"
    torch.backends = SimpleNamespace()
    assert metal.device(torch) == "cpu"


def test_cpu_override_and_other_platforms(torch_stub, monkeypatch):
    torch, _ = torch_stub
    monkeypatch.setenv("REACUE_DEVICE", "cpu")
    assert metal.device(torch) == "cpu"
    monkeypatch.delenv("REACUE_DEVICE")
    monkeypatch.setattr(metal.sys, "platform", "win32")
    assert metal.device(torch) == "cpu"


def test_configure_preserves_explicit_fallback(torch_stub, monkeypatch):
    monkeypatch.delenv("PYTORCH_ENABLE_MPS_FALLBACK", raising=False)
    metal.configure()
    assert metal.os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] == "1"
    monkeypatch.setenv("PYTORCH_ENABLE_MPS_FALLBACK", "0")
    metal.configure()
    assert metal.os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] == "0"


def test_forward_moves_inputs_and_returns_cpu_for_ctc(torch_stub):
    model = Model()
    out, length = metal.forward(model, Tensor())
    assert model.calls == ["mps"]
    assert out.device == "cpu" and length is None


@pytest.mark.parametrize("error", [RuntimeError("MPS out of memory"),
                                        NotImplementedError("MPS kernel"), TypeError("unsupported dtype")])
def test_mps_failure_retries_once_and_sticks_to_cpu(torch_stub, error):
    model = Model(error)
    with pytest.warns(RuntimeWarning, match="retrying on CPU"):
        metal.forward(model, Tensor())
    metal.forward(model, Tensor())
    assert model.calls == ["mps", "cpu", "cpu"]
    assert torch_stub[1] == [True]


def test_cpu_errors_are_not_hidden(torch_stub, monkeypatch):
    class Broken(Model):
        def __call__(self, x):
            raise RuntimeError("invalid model")
    monkeypatch.setenv("REACUE_DEVICE", "cpu")
    with pytest.raises(RuntimeError, match="invalid model"):
        metal.forward(Broken(), Tensor())


def test_songformer_moves_all_models_and_retries(torch_stub):
    import reacue_structure as structure
    models = {name: Model() for name in ("muq_model", "musicfm_model", "msa_model")}
    calls = []
    app = SimpleNamespace(**models)
    def process(audio, **kw):
        calls.append(app.device)
        assert all(m.device == app.device for m in models.values())
        if app.device == "mps":
            raise RuntimeError("MPS unsupported operation")
        return None, [{"start": 0, "end": 2, "label": "intro"}]
    app.process_audio = process
    app.rule_post_processing = lambda x: x
    app.format_as_segments = lambda x: x
    structure._move_models(app, "mps")
    with pytest.warns(RuntimeWarning):
        result = structure.segments_from_app(app, "song.wav", 120)
    assert calls == ["mps", "cpu"] and result[0]["label"] == "intro"


def test_demucs_retries_mps_on_cpu(torch_stub, monkeypatch, tmp_path):
    import reacue_stems
    import test_stems
    calls = test_stems._fake_demucs(monkeypatch)
    original = sys.modules["demucs.separate"].main
    attempts = []
    def run(args):
        attempts.append(args[:])
        if args[args.index("-d") + 1] == "mps":
            raise RuntimeError("MPS kernel unsupported")
        original(args)
    sys.modules["demucs.separate"].main = run
    torch_stub[0].cuda = SimpleNamespace(is_available=lambda: False)
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"audio")
    with pytest.warns(RuntimeWarning, match="retrying on CPU"):
        assert reacue_stems.main(["separate", "--input", str(audio), "--out", str(tmp_path / "out")]) == 0
    assert [args[args.index("-d") + 1] for args in attempts] == ["mps", "cpu"]
    assert len(calls) == 1


def test_forward_single_output_for_drums(torch_stub):
    class DrumModel(Model):
        def __call__(self, x):
            assert x.device == self.device
            return Tensor(x.device)
    assert metal.forward(DrumModel(), Tensor()).device == "cpu"


def test_songformer_initialization_selects_mps(torch_stub):
    import reacue_structure as structure
    models = {name: Model() for name in ("muq_model", "musicfm_model", "msa_model")}
    app = SimpleNamespace(**models, device="cpu", download_all=lambda **kw: None,
                          initialize_models=lambda **kw: None)
    structure.init_models(app)
    assert app.device == "mps" and all(m.device == "mps" for m in models.values())


def test_songformer_partial_transfer_rolls_all_models_back(torch_stub):
    import reacue_structure as structure
    class CpuOnly(Model):
        def to(self, target):
            if target == "mps":
                raise TypeError("unsupported dtype")
            return super().to(target)
    app = SimpleNamespace(muq_model=Model(), musicfm_model=CpuOnly(), msa_model=Model(),
                          device="cpu", download_all=lambda **kw: None,
                          initialize_models=lambda **kw: None)
    with pytest.warns(RuntimeWarning, match="retrying on CPU"):
        structure.init_models(app)
    assert app.device == "cpu"
    assert app.muq_model.device == app.musicfm_model.device == app.msa_model.device == "cpu"
