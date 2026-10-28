"""Performance profiles, real-inference calibration orchestration, and cache boundaries."""
import json
import sys
from types import SimpleNamespace

import pytest

import reacue_performance as perf


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("REAPER_RESOURCE_PATH", str(tmp_path))
    monkeypatch.delenv("REACUE_CPU_THREADS", raising=False)
    monkeypatch.delenv("REACUE_PERFORMANCE_PROFILE", raising=False)


def write_settings(data):
    p = perf.settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))


def test_standard_preserves_quality():
    assert perf.profile() == "standard"
    assert perf.demucs_args() == [] and perf.whisper_options() == {}
    assert perf.cpu_threads() == 0


def test_fast_profile_and_environment_override(monkeypatch):
    write_settings({"performance_profile": "fast"})
    assert perf.demucs_args() == ["--shifts", "0", "--overlap", "0.1"]
    assert perf.whisper_options() == {"temperature": (0.0,), "beam_size": None, "best_of": None}
    monkeypatch.setenv("REACUE_PERFORMANCE_PROFILE", "standard")
    assert perf.profile() == "standard" and perf.demucs_args() == []


@pytest.mark.parametrize("value,expected", [(None, 0), ("bad", 0), (-2, 0), (999, 4), (2, 2)])
def test_thread_count_validation(monkeypatch, value, expected):
    monkeypatch.setattr(perf.os, "cpu_count", lambda: 4)
    write_settings({"cpu_threads": value})
    assert perf.cpu_threads() == expected


def test_explicit_threads_reach_torch_and_native_libraries(monkeypatch):
    write_settings({"cpu_threads": 1})
    monkeypatch.setenv("REACUE_CPU_THREADS", "2")
    monkeypatch.setattr(perf.os, "cpu_count", lambda: 4)
    monkeypatch.setenv("OMP_NUM_THREADS", "7")
    monkeypatch.setenv("MKL_NUM_THREADS", "7")
    perf.configure()
    calls = []
    perf.configure_torch(SimpleNamespace(set_num_threads=calls.append))
    assert calls == [2]
    assert perf.os.environ["OMP_NUM_THREADS"] == perf.os.environ["MKL_NUM_THREADS"] == "2"


def test_save_threads_keeps_user_choices():
    write_settings({"performance_profile": "standard", "stems_model": "htdemucs_6s", "custom": 42})
    perf.save_threads(2)
    assert perf.settings() == {"performance_profile": "standard", "stems_model": "htdemucs_6s",
                               "custom": 42, "cpu_threads": 2}


def test_fast_window_respects_explicit_choice():
    import reacue_structure as structure
    write_settings({"performance_profile": "fast"})
    assert structure.choose_window("auto", ram=64) == 120
    assert structure.choose_window("420", ram=64) == 420


def test_output_changing_profile_invalidates_caches(tmp_path):
    from reacue_mcp import structure, lyrics_auto
    from reacue_mcp.analysis import Analysis
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"audio")
    a = Analysis(file=str(audio), duration=5, bpm=120, beats_per_bar=4, denominator=4,
                 tempo_stable=True, tempo_cv=0, beats=[], downbeats=[0, 2, 4], sections=[])
    regular = structure.cache_key([str(audio)]), lyrics_auto.memo_key(a, None, "fr", tmp_path)
    write_settings({"cpu_threads": 1})
    assert regular == (structure.cache_key([str(audio)]), lyrics_auto.memo_key(a, None, "fr", tmp_path))
    write_settings({"performance_profile": "fast"})
    assert all(a != b for a, b in zip(regular, (structure.cache_key([str(audio)]),
                                              lyrics_auto.memo_key(a, None, "fr", tmp_path))))


def test_benchmark_excludes_warmup_and_restores_threads(monkeypatch):
    import reacue_structure as structure
    state = {"threads": 8, "time": 0}
    fake = SimpleNamespace(get_num_threads=lambda: state["threads"],
                           set_num_threads=lambda n: state.update(threads=n))
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(structure, "_move_models", lambda app, device: None)
    calls = []
    def infer(*args):
        calls.append(state["threads"])
        state["time"] += {1: 3, 2: 1, 4: 2}[state["threads"]]
    monkeypatch.setattr(structure, "segments_from_app", infer)
    results = structure.benchmark_threads(None, "audio.wav", [1, 2, 4], clock=lambda: state["time"])
    assert results == [{"threads": 2, "seconds": 1}, {"threads": 4, "seconds": 2},
                       {"threads": 1, "seconds": 3}]
    assert calls == [1, 1, 1, 2, 2, 2, 4, 4, 4] and state["threads"] == 8


def test_benchmark_does_not_save_when_inference_fails(monkeypatch):
    import reacue_structure as structure
    state = {"threads": 8}
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(get_num_threads=lambda: 8,
                       set_num_threads=lambda n: state.update(threads=n)))
    monkeypatch.setattr(structure, "_move_models", lambda *args: None)
    def fail(*args):
        raise RuntimeError("model failure")
    monkeypatch.setattr(structure, "segments_from_app", fail)
    with pytest.raises(RuntimeError, match="model failure"):
        structure.benchmark_threads(None, "audio.wav", [1])
    assert state["threads"] == 8 and not perf.settings_path().exists()
