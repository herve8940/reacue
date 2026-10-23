"""Accords par modèle entraîné (composant facultatif) : nommage, calage sur les mesures, repli, sous-processus,
cache, script du modèle (fonctions pures, modèle simulé), installateurs. Le vrai modèle n'est jamais lancé.
Chord model (optional component): naming, bar alignment, fallback, subprocess, cache, runner, installers."""
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pytest

from reacue_mcp import chord_model as CM
from reacue_mcp import chords as CH
from reacue_mcp.analysis import Analysis

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import reacue_chords as RC  # noqa: E402


def _analysis(n_bars=4, bar=2.0, m=4, t0=0.5, file="/x/song.wav", stems=None):
    db = [t0 + k * bar for k in range(n_bars + 1)]
    beats = [t0 + k * bar / m for k in range(n_bars * m + 1)]
    return Analysis(file=file, duration=db[-1] + 1, bpm=60 * m / bar, beats_per_bar=m, denominator=4,
                    tempo_stable=True, tempo_cv=0.0, beats=beats, downbeats=db, stems=stems or {})


def _seg(start, end, label, conf=0.9):
    return {"start": start, "end": end, "label": label, "confidence": conf}


def _names(grid):
    return [[c["chord"] for c in e["chords"]] for e in grid]


# --------------------------------------------------------------------------- nommage
@pytest.mark.parametrize("label,expected", [
    ("C:maj", (0, "maj", 0)), ("A:min/b3", (9, "min", 0)), ("Eb:7", (3, "7", 3)), ("F#:maj/3", (6, "maj", 10)),
    ("G:maj/5", (7, "maj", 2)), ("Bb:sus4(b7)", (10, "sus4(b7)", 10)), ("N", None), ("X", None), ("", None),
])
def test_parse_harte(label, expected):
    assert CH.parse_harte(label) == expected


def test_suffixes_full_and_simple():
    assert CH._suffix("min7", False) == "m7" and CH._suffix("hdim7", False) == "m7b5"
    assert CH._suffix("maj9", False) == "maj9" and CH._suffix("maj9", True) == "maj7"
    assert CH._suffix("9", True) == "7" and CH._suffix("min9", True) == "m7" and CH._suffix("13", True) == "7"
    assert CH._suffix("sus4(b7)", True) == "7sus4" and CH._suffix("11", True) == "7sus4"
    assert CH._suffix("sus2", True) == "sus2" and CH._suffix("aug", True) == "aug" and CH._suffix("dim7", True) == "dim7"
    assert CH._suffix("min11", True) == "m"                      # inconnue : couleur de la tierce


def test_speller_follows_key():
    d = CH.speller((2, False))                                  # Ré majeur
    assert [d(p) for p in (6, 1, 10, 3)] == ["F#", "C#", "Bb", "Eb"]   # gamme ; emprunts (bVI, b2) en bémol
    assert d(8) == "G#"                                         # #IV (E/G#) : dièse
    am = CH.speller((9, True))                                  # La mineur : sensible G#, E/G#
    assert am(8) == "G#" and am(10) == "Bb" and am(1) == "C#" and am(3) == "D#"
    f = CH.speller((5, False))                                  # Fa majeur
    assert f(10) == "Bb" and f(3) == "Eb" and f(11) == "B"
    em = CH.speller((4, True))                                  # Mi mineur
    assert em(6) == "F#" and em(3) == "D#" and em(0) == "C" and em(10) == "A#"


def test_inversion_bass_spelled_as_chord_tone():
    assert CH.spell_above("E", 4) == "G#" and CH.spell_above("Bb", 4) == "D" and CH.spell_above("F#", 3) == "A"
    assert CH.spell_above("Eb", 7) == "Bb" and CH.spell_above("C", 10) == "Bb" and CH.spell_above("Ab", 4) == "C"
    assert CH.spell_above("D", 2) == "E" and CH.spell_above("Db", 4) == "F"
    a = _analysis(2)
    # Fa majeur : D/F# (et non D/Gb), C/E
    g = CH.chords_from_segments(a, [_seg(0.5, 2.5, "D:maj/3"), _seg(2.5, 4.5, "C:maj/3")], "F")
    assert _names(g) == [["D/F#"], ["C/E"]] and g[0]["chords"][0]["bass"] == "F#"
    # Do majeur : Ab/C, E/G#
    g = CH.chords_from_segments(a, [_seg(0.5, 2.5, "Ab:maj/3"), _seg(2.5, 4.5, "E:maj/3")], "C")
    assert _names(g) == [["Ab/C"], ["E/G#"]]


# --------------------------------------------------------------------------- calage sur les mesures
def test_one_chord_per_bar_and_format():
    a = _analysis(4)
    segs = [_seg(0, 0.5, "N"), _seg(0.5, 2.5, "E:min"), _seg(2.5, 4.5, "C:maj7", 0.6), _seg(4.5, 6.5, "G:maj"),
            _seg(6.5, 8.5, "D:maj/3")]
    g = CH.chords_from_segments(a, segs, {"chord": "Em"})
    assert [e["bar"] for e in g] == [1, 2, 3, 4]
    assert _names(g) == [["Em"], ["Cmaj7"], ["G"], ["D/F#"]]
    c = g[3]["chords"][0]
    assert c == {"beat": 1, "chord": "D/F#", "bass": "F#", "confidence": 0.9}
    assert g[1]["chords"][0]["confidence"] == 0.6 and g[0]["chords"][0]["bass"] == "E"
    json.dumps(g)                                                 # sérialisable (cache, prompteur)


def test_two_chords_on_beat_three_only_when_clear():
    a = _analysis(3)
    segs = [_seg(0.5, 1.5, "A:min"), _seg(1.5, 2.5, "F:maj"),                 # mesure 1 : Am | F (temps 3)
            _seg(2.5, 4.3, "C:maj"), _seg(4.3, 4.5, "G:maj"),                 # mesure 2 : anticipation brève
            _seg(4.5, 5.5, "G:maj"), _seg(5.5, 6.5, "G:maj", 0.2)]            # mesure 3 : même accord
    g = CH.chords_from_segments(a, segs, "Am")
    assert g[0]["chords"] == [{"beat": 1, "chord": "Am", "bass": "A", "confidence": 0.9},
                              {"beat": 3, "chord": "F", "bass": "F", "confidence": 0.9}]
    assert _names(g)[1:] == [["C"], ["G"]]
    # 2e accord trop incertain : un seul accord (le plus long sur la mesure)
    segs2 = [_seg(0.5, 1.5, "A:min"), _seg(1.5, 2.5, "F:maj", 0.2)]
    assert _names(CH.chords_from_segments(_analysis(1), segs2, "Am")) == [["Am"]]


def test_no_chord_and_odd_meter():
    a = _analysis(2, bar=1.5, m=3)
    g = CH.chords_from_segments(a, [_seg(0.5, 2.0, "N", 0.8), _seg(2.0, 2.4, "G:7"), _seg(2.4, 3.5, "C:maj")], "C")
    assert g[0]["chords"] == [{"beat": 1, "chord": "N.C.", "bass": None, "confidence": 0.8}]
    assert _names(g)[1] == ["C"]                                 # 3/4 : un seul accord, le plus long
    g = CH.chords_from_segments(_analysis(1), [], "C")           # rien : N.C.
    assert g[0]["chords"][0]["chord"] == "N.C."


def test_simple_vocabulary_and_full():
    a = _analysis(2)
    segs = [_seg(0.5, 2.5, "G:9"), _seg(2.5, 4.5, "C:maj9/3")]
    assert _names(CH.chords_from_segments(a, segs, "G")) == [["G7"], ["Cmaj7/E"]]
    assert _names(CH.chords_from_segments(a, segs, "G", simple=False)) == [["G9"], ["Cmaj9/E"]]


def test_key_estimated_from_model_chords_uses_flats():
    a = _analysis(4)
    segs = [_seg(0.5, 2.5, "F:maj"), _seg(2.5, 4.5, "Bb:maj"), _seg(4.5, 6.5, "C:7"), _seg(6.5, 8.5, "F:maj")]
    g = CH.chords_from_segments(a, segs, None)
    assert _names(g) == [["F"], ["Bb"], ["C7"], ["F"]]
    # même chose avec une étiquette en dièse (A#) : réécrite selon la tonalité
    segs[1]["label"] = "A#:maj"
    assert _names(CH.chords_from_segments(a, segs, None))[1] == ["Bb"]


def test_grid_compatible_with_prompter_and_sheet():
    from reacue_mcp import sheet
    a = _analysis(2)
    g = CH.chords_from_segments(a, [_seg(0.5, 1.5, "E:min"), _seg(1.5, 2.5, "D:maj"), _seg(2.5, 4.5, "C:maj")], "Em")
    assert sheet.bar_chords({"chords": g}) == {1: ["Em", "D"], 2: ["C"]}


# --------------------------------------------------------------------------- choix du moteur, repli, cache
def test_engine_setting(monkeypatch):
    from reacue_mcp import settings as S
    assert CM.engine_setting() == "reacue"                       # tests : jamais le vrai modèle
    monkeypatch.delenv("REACUE_CHORDS_ENGINE")
    assert S.DEFAULTS["chords_engine"] == "auto"
    monkeypatch.setattr("reacue_mcp.settings.load_settings", lambda: {"chords_engine": "reacue"})
    assert CM.engine_setting() == "reacue"
    monkeypatch.setattr("reacue_mcp.settings.load_settings", lambda: {"chords_engine": "bogus"})
    assert CM.engine_setting() == "auto"


def test_settings_normalised(tmp_path):
    from reacue_mcp import settings as S
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"chords_engine": "Nope"}), encoding="utf-8")
    assert S.load_settings(p)["chords_engine"] == "auto"
    p.write_text(json.dumps({"chords_engine": "REACUE"}), encoding="utf-8")
    assert S.load_settings(p)["chords_engine"] == "reacue"


def test_available(tmp_path):
    assert not CM.available(tmp_path)
    (tmp_path / ".venv-chords" / "bin").mkdir(parents=True)
    (tmp_path / ".venv-chords" / "bin" / "python").write_text("")
    (tmp_path / "reacue_chords.py").write_text("")
    m = tmp_path / "chords" / "model"
    (m / "cache_data").mkdir(parents=True)
    assert not CM.available(tmp_path)
    (m / "chordnet_ismir_naive.py").write_text("")
    assert CM.available(tmp_path)
    assert CM.chords_python(tmp_path, windows=True).parts[-3:] == (".venv-chords", "Scripts", "python.exe")


def test_harmonic_sources():
    srcs = [("guitars", "g.wav", 0.0), ("vocals", "v.wav", 0.0), ("drums", "d.wav", 0.1), ("bass", "b.wav", 0.0),
            ("keys", "k.wav", 0.0), ("vocals_2", "v2.wav", 0.0)]
    assert [s[0] for s in CM.harmonic_sources(srcs)] == ["guitars", "bass", "keys"]
    assert CM.harmonic_sources([("mix", "m.wav", 0.0)]) == [("mix", "m.wav", 0.0)]
    assert CM.harmonic_sources([("vocals", "v.wav", 0.0), ("drums", "d.wav", 0.0)])   # rien d'autre : tout


def test_beats_payload():
    p = CM.beats_payload(_analysis(2, bar=2.0, m=4, t0=0.5))
    assert p["beats_per_bar"] == 4 and p["downbeats"] == [0.5, 2.5, 4.5]
    assert p["beats"] == [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]


@pytest.fixture
def model_on(monkeypatch, tmp_path):
    """Moteur « auto » et composant déclaré installé ; segments simulés (aucun sous-processus)."""
    monkeypatch.setenv("REACUE_CHORDS_ENGINE", "auto")
    monkeypatch.setattr(CM, "available", lambda install_dir=None: True)
    calls = []

    def fake_segments(a, srcs, install_dir=None, timeout=CM.TIMEOUT_S):
        calls.append(srcs)
        if fake_segments.error:
            raise RuntimeError(fake_segments.error)
        return [_seg(a.downbeats[0], a.downbeats[-1], "A:maj/3", 0.8)], {"engine": CM.ENGINE, "cached": False}
    fake_segments.error = None
    monkeypatch.setattr(CM, "model_segments", fake_segments)
    legacy = []
    monkeypatch.setattr(CH, "detect_chords", lambda a, items=None, key=None, **k: legacy.append(1) or [
        {"bar": 1, "chords": [{"beat": 1, "chord": "A", "bass": "A", "confidence": 0.5}]}])
    return fake_segments, calls, legacy


def test_cached_chords_uses_model(model_on, tmp_path):
    fake, calls, legacy = model_on
    a = _analysis(1, file=str(tmp_path / "song.wav"))
    cache = tmp_path / "c.json"
    g = CH.cached_chords(a, None, "A", cache=cache)
    assert g == [{"bar": 1, "chords": [{"beat": 1, "chord": "A/C#", "bass": "C#", "confidence": 0.8}]}]
    assert CM.LAST["engine"] == CM.ENGINE and "message" in CM.LAST and not legacy
    assert CH.cached_chords(a, None, "A", cache=cache) == g and len(calls) == 1      # cache
    assert CM.LAST == {"engine": CM.ENGINE, "cached": True}


def test_cached_chords_falls_back(model_on, tmp_path, capsys):
    fake, calls, legacy = model_on
    fake.error = "boom"
    a = _analysis(1, file=str(tmp_path / "song.wav"))
    g = CH.cached_chords(a, None, "A", cache=tmp_path / "c.json")
    assert g[0]["chords"][0]["chord"] == "A" and legacy == [1]
    assert CM.LAST["engine"] == "reacue" and CM.LAST["fallback"] and "boom" in CM.LAST["message"]
    assert "boom" in capsys.readouterr().err
    # le modèle revient : la grille du modèle remplace celle de ReaCue (clés de cache distinctes)
    fake.error = None
    g2 = CH.cached_chords(a, None, "A", cache=tmp_path / "c.json")
    assert g2[0]["chords"][0]["chord"] == "A/C#"


def test_cached_chords_reacue_setting_never_calls_model(model_on, tmp_path, monkeypatch):
    fake, calls, legacy = model_on
    monkeypatch.setenv("REACUE_CHORDS_ENGINE", "reacue")
    CH.cached_chords(_analysis(1), None, "A", cache=tmp_path / "c.json")
    assert not calls and legacy == [1] and CM.LAST == {"engine": "reacue"}


def test_legacy_cache_key_unchanged():
    a = _analysis(2)
    assert CH.chords_cache_key(a, None, "Em") == CH.chords_cache_key(a, None, "Em", "reacue")
    assert CH.chords_cache_key(a, None, "Em", CM.ENGINE) != CH.chords_cache_key(a, None, "Em")


# --------------------------------------------------------------------------- model_segments (cache disque)
def _stems(tmp_path):
    d = tmp_path / "song"
    d.mkdir()
    files = {}
    import soundfile as sf
    for r in ("guitars", "bass", "vocals", "drums"):
        f = d / f"Demo-{r}.wav"
        sf.write(str(f), np.zeros(22050 * 3, dtype=np.float32), 22050)
        files[r] = str(f)
    return files


def test_model_segments_cache_and_failure_memory(tmp_path, monkeypatch):
    files = _stems(tmp_path)
    a = _analysis(2, bar=1.0, file=files["guitars"], stems=files)
    srcs = CH._sources(a, None)
    runs, mixes = [], []

    def fake_run(audio, out_json, beats=None, probs=None, key=None, install_dir=None, timeout=0, **k):
        runs.append({"audio": audio, "beats": beats, "probs": probs, "key": key})
        if fake_run.error:
            raise RuntimeError("model crashed")
        probs.parent.mkdir(parents=True, exist_ok=True)
        np.savez(str(probs), key=np.array(key), p0=np.zeros(1))
        return {"segments": [_seg(0.5, 2.5, "C:maj")]}
    fake_run.error = None
    real_mix = CM.write_mix
    monkeypatch.setattr(CM, "write_mix", lambda hs, n, wav, sr=22050: mixes.append([s[0] for s in hs]) or real_mix(hs, n, wav))
    monkeypatch.setattr(CM, "run_engine", fake_run)
    segs, info = CM.model_segments(a, srcs)
    assert segs == [_seg(0.5, 2.5, "C:maj")] and info["engine"] == CM.ENGINE and not info["cached"]
    assert sorted(mixes[0]) == ["bass", "guitars"]                     # ni voix ni batterie
    assert runs[0]["beats"]["beats_per_bar"] == 4 and runs[0]["key"] == CM.audio_key(CM.harmonic_sources(srcs))
    seg_path, probs_path = CM.cache_paths(files["guitars"])
    assert seg_path.parent.name == ".reacue" and probs_path.is_file()
    # même audio, même grille : cache, sans sous-processus
    assert CM.model_segments(a, srcs)[1]["cached"] and len(runs) == 1
    # nouvelle grille : décodage seul (probabilités en cache : pas de mix réécrit)
    b = _analysis(2, bar=1.1, file=files["guitars"], stems=files)
    CM.model_segments(b, srcs)
    assert len(runs) == 2 and len(mixes) == 1 and runs[1]["audio"] in files.values()
    # échec mémorisé : pas de nouvel essai pendant RETRY_AFTER_S
    fake_run.error = True
    c = _analysis(2, bar=1.2, file=files["guitars"], stems=files)
    with pytest.raises(RuntimeError, match="crashed"):
        CM.model_segments(c, srcs)
    with pytest.raises(RuntimeError, match="crashed"):
        CM.model_segments(c, srcs)
    assert len(runs) == 3


# --------------------------------------------------------------------------- sous-processus (faux modèle)
FAKE = r'''
import json, sys, time
a = sys.argv[1:]
g = lambda k: a[a.index(k) + 1] if k in a else None
mode = open(g("--input")).read().strip()
if mode == "sleep":
    time.sleep(30)
if mode == "fail":
    open(g("--status"), "w").write(json.dumps({"state": "error", "message": "RuntimeError: no model"}))
    sys.exit(1)
beats = json.load(open(g("--beats"))) if g("--beats") else None
res = {"engine": "jiang2019", "segments": [{"start": 0, "end": 1, "label": "C:maj", "confidence": 0.9}],
       "argv": a, "beats": beats}
open(g("--out"), "w").write(json.dumps(res))
'''


def _fake_engine(tmp_path, mode):
    sc = tmp_path / "fake_chords.py"
    sc.write_text(FAKE)
    audio = tmp_path / "in.txt"
    audio.write_text(mode)
    return sc, audio


def test_run_engine_protocol(tmp_path):
    sc, audio = _fake_engine(tmp_path, "ok")
    res = CM.run_engine(str(audio), tmp_path / "o" / "r.json", {"beats": [0, 1], "downbeats": [0], "beats_per_bar": 4},
                        tmp_path / "p.npz", "k123", tmp_path, python=sys.executable, script=str(sc))
    assert res["segments"][0]["label"] == "C:maj" and res["beats"]["beats"] == [0, 1]
    argv = res["argv"]
    assert argv[0] == "analyze" and "--vocab" in argv and argv[argv.index("--key") + 1] == "k123"
    assert argv[argv.index("--probs") + 1].endswith("p.npz")


def test_run_engine_error_and_timeout(tmp_path):
    sc, audio = _fake_engine(tmp_path, "fail")
    with pytest.raises(RuntimeError, match="no model"):
        CM.run_engine(str(audio), tmp_path / "o" / "r.json", python=sys.executable, script=str(sc))
    audio.write_text("sleep")
    with pytest.raises(RuntimeError, match="min"):
        CM.run_engine(str(audio), tmp_path / "o" / "r.json", python=sys.executable, script=str(sc), timeout=1)


# --------------------------------------------------------------------------- script du modèle (sans torch)
def test_runner_beat_array():
    dt = RC.HOP / RC.SR
    beats = {"beats": [k * 0.5 for k in range(9)], "downbeats": [0.0, 2.0, 4.0], "beats_per_bar": 4}
    n = int(5.0 / dt)
    arr = RC.beat_array(n, beats)
    f = lambda t: int(round(t / dt))
    assert arr[f(0.0)] == 2 and arr[f(2.0)] == 2 and arr[f(1.0)] == 3 and arr[f(3.0)] == 3
    assert arr[f(0.5)] == 4 and arr[f(1.5)] == 4
    assert arr[f(0.25)] == 0 and arr[f(3.7)] == 0                 # entre deux temps : pas de changement
    assert arr[f(4.5)] == 1                                       # après la grille : libre
    assert (RC.beat_array(10, None) == 1).all()


def test_runner_family():
    assert RC.family("A:min7/b7") == ("A", "min") and RC.family("C:maj/3") == ("C", "maj")
    assert RC.family("B:hdim7") == ("B", "dim") and RC.family("D:sus4(b7)") == ("D", "sus")
    assert RC.family("G:13") == ("G", "maj") and RC.family("N") == ("N", "")


class _FakeHMM:
    """Décodeur simulé (même interface que XHMMDecoder du dépôt)."""
    NAMES = ["N", "C:maj", "C:maj7", "A:min"]

    def __init__(self, diff_trans_penalty, beat_trans_penalty, template_file):
        assert beat_trans_penalty == (RC.PEN_DOWNBEAT, RC.PEN_HALF, RC.PEN_BEAT)
        assert template_file.endswith("submission_chord_list.txt")

    def get_chord_tag_obs(self, probs):
        return self.NAMES, np.log(np.asarray(probs[0]))

    def decode(self, probs, beat_arr):
        return [self.NAMES[i] for i in np.argmax(probs[0], 1)]


def test_runner_decode_segments_and_family_confidence():
    p = np.array([[0.1, 0.5, 0.3, 0.1]] * 4 + [[0.1, 0.1, 0.1, 0.7]] * 4)
    segs = RC.decode([p] + [None] * 5, _FakeHMM)
    assert [s["label"] for s in segs] == ["C:maj", "A:min"]
    assert segs[0]["confidence"] == pytest.approx(0.8)              # C:maj + C:maj7 (même famille)
    assert segs[1]["confidence"] == pytest.approx(0.7)
    assert segs[0]["start"] == 0 and segs[1]["start"] == pytest.approx(4 * RC.HOP / RC.SR, abs=1e-3)


def test_runner_analyze_with_probs_cache(tmp_path, monkeypatch):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    monkeypatch.setattr(RC, "load_repo", lambda: (object, _FakeHMM))
    torch_stub = type(sys)("torch")
    torch_stub.set_num_threads = lambda n: None
    monkeypatch.setitem(sys.modules, "torch", torch_stub)
    computed = []
    p = np.array([[0.1, 0.8, 0.05, 0.05]] * 3)
    monkeypatch.setattr(RC, "probabilities", lambda a, net, st=None: computed.append(a) or [p] * 6)
    beats = tmp_path / "b.json"
    beats.write_text(json.dumps({"beats": [0, 0.5], "downbeats": [0], "beats_per_bar": 4}))
    out, pc = tmp_path / "r.json", tmp_path / "p.npz"
    assert RC.analyze(str(audio), str(out), str(tmp_path / "s.json"), str(beats), probs_cache=str(pc), key="K") == 0
    r = json.loads(out.read_text())
    assert r["engine"] == "jiang2019" and r["segments"][0]["label"] == "C:maj" and not r["probs_cached"]
    assert pc.is_file() and len(computed) == 1
    assert RC.analyze(str(audio), str(out), None, str(beats), probs_cache=str(pc), key="K") == 0
    assert json.loads(out.read_text())["probs_cached"] and len(computed) == 1
    assert RC.analyze(str(audio), str(out), None, None, probs_cache=str(pc), key="other") == 0
    assert len(computed) == 2                                       # autre audio : recalcul
    st = tmp_path / "s2.json"
    assert RC.analyze(str(tmp_path / "missing.wav"), str(out), str(st)) == 1
    assert json.loads(st.read_text())["state"] == "error"


def test_runner_synth_is_deterministic():
    y, beats = RC.synth(["C:maj", "A:min/b3"], bpm=120, beats_per_chord=2)
    y2, _ = RC.synth(["C:maj", "A:min/b3"], bpm=120, beats_per_chord=2)
    assert np.allclose(y, y2) and len(beats) == 5 and beats[1] == 0.5 and np.abs(y).max() <= 0.81


# --------------------------------------------------------------------------- installateurs, licences
def test_installers_syntax_and_pinned_revision():
    for p in (ROOT / "install" / "install_chords_mac.sh", ROOT / "Install ReaCue Chords.command"):
        r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert os.access(p, os.X_OK)
    ps = (ROOT / "install" / "install_chords_windows.ps1").read_bytes()
    assert ps.startswith(b"\xef\xbb\xbf") and b"\r\n" in ps
    bat = (ROOT / "Install ReaCue Chords.bat").read_bytes()
    bat.decode("ascii")
    assert b"\r\n" in bat and b"-ExecutionPolicy Bypass -File" in bat and b"%~dp0install\\install_chords_windows.ps1" in bat
    for p in (ROOT / "install" / "install_chords_mac.sh", ROOT / "install" / "install_chords_windows.ps1"):
        t = p.read_text(encoding="utf-8-sig")
        assert CM.MODEL_REV in t and CM.MODEL_REPO in t
        assert ".venv-chords" in t and "requirements-chords.txt" in t and "reacue_chords.py" in t and "check" in t
        assert "MIT" in t and "THIRD_PARTY_NOTICES.md" in t and "--only-binary" in t
    req = (ROOT / "requirements-chords.txt").read_text(encoding="utf-8")
    assert 'torch==2.2.2 ; sys_platform == "darwin" and platform_machine == "x86_64"' in req and "numpy<2" in req


def test_powershell_parses():
    ps = os.environ.get("PWSH") or shutil.which("pwsh")
    if not ps:
        pytest.skip("pwsh absent")
    path = ROOT / "install" / "install_chords_windows.ps1"
    cmd = ("$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
           f"'{path}', [ref]$null, [ref]$e); if ($e.Count) {{ $e | % {{ $_.ToString() }}; exit 1 }}")
    r = subprocess.run([ps, "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_mac_installer_end_to_end_simulated(tmp_path):
    """Faux uname (Darwin), faux curl (archive du « dépôt »), faux uv (crée un python qui répond CHORDS_OK)."""
    inst = tmp_path / "ReaCue"
    (inst / "install").mkdir(parents=True)
    shutil.copy(ROOT / "install" / "install_chords_mac.sh", inst / "install")
    shutil.copy(ROOT / "requirements-chords.txt", inst)
    (inst / "reacue_chords.py").write_text("")
    src = tmp_path / "repo-src"
    (src / "cache_data").mkdir(parents=True)
    (src / "chordnet_ismir_naive.py").write_text("# faux\n")
    tgz = tmp_path / "repo.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        tf.add(src, arcname="ISMIR2019-x")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    calls = tmp_path / "calls.txt"
    fakepy = tmp_path / "fakepy"
    fakepy.write_text(f'#!/bin/bash\necho py "$@" >> "{calls}"\necho CHORDS_OK\n')
    fakepy.chmod(0o755)
    uv = (f'echo uv "$@" >> "{calls}"\n'
          f'if [ "$1" = venv ]; then mkdir -p "$2/bin"; cp "{fakepy}" "$2/bin/python"; fi')
    for name, body in (("uname", 'if [ "$1" = -m ]; then echo x86_64; else echo Darwin; fi'),
                       ("uv", uv), ("curl", f'echo curl "$@" >> "{calls}"; cat "{tgz}"'), ("git", "exit 1")):
        f = bin_ / name
        f.write_text("#!/bin/bash\n" + body + "\n")
        f.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_}:/usr/bin:/bin", HOME=str(tmp_path))
    r = subprocess.run(["bash", str(inst / "install" / "install_chords_mac.sh"), "en"], env=env, capture_output=True,
                       text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MIT" in r.stdout and "CHORDS_OK" in r.stdout
    assert (inst / "chords" / "model" / "chordnet_ismir_naive.py").is_file()
    assert (inst / "chords" / "model" / ".reacue_rev").read_text().strip() == CM.MODEL_REV
    log = calls.read_text()
    assert f"codeload.github.com/{CM.MODEL_REPO}/tar.gz/{CM.MODEL_REV}" in log
    assert "uv venv .venv-chords --python 3.12" in log and "--only-binary :all: -r requirements-chords.txt" in log
    assert "py reacue_chords.py check --lang en" in log
    # relance : modèle déjà là (pas de nouveau téléchargement), venv conservé
    calls.write_text("")
    r = subprocess.run(["bash", str(inst / "install" / "install_chords_mac.sh"), "fr"], env=env, capture_output=True,
                       text=True, timeout=60)
    assert r.returncode == 0 and "curl" not in calls.read_text() and "uv venv" not in calls.read_text()


def test_no_chord_model_tracked_and_notices():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".venv-chords/" in gi and "/chords/" in gi and "*.sdict" in gi
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert not [f for f in files if f.endswith(".sdict") or f.startswith("chords/")]
    txt = " ".join((ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").split())
    assert "ISMIR2019-Large-Vocabulary-Chord-Recognition" in txt and "Junyan Jiang" in txt


# --------------------------------------------------------------------------- outil de comparaison
def test_compare_tool(monkeypatch, capsys, tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import compare_chords as T
    assert T._fam("F#m7/A") == (6, "m") and T._fam("Gbmaj7") == (6, "") and T._fam("N.C.") == ("N.C.", "")
    a = _analysis(2)
    monkeypatch.setattr(T, "load_song", lambda p: (a, None, ["Demo-A minor-120bpm.wav"]))
    monkeypatch.setattr(T.CH, "detect_chords", lambda a, items, key, simple=True: [
        {"bar": 1, "chords": [{"beat": 1, "chord": "Am", "bass": "A", "confidence": 1.0}]},
        {"bar": 2, "chords": [{"beat": 1, "chord": "C", "bass": "C", "confidence": 1.0}]}])
    monkeypatch.setattr(T.CM, "available", lambda install_dir=None: True)
    monkeypatch.setattr(T.CM, "model_segments", lambda a, srcs: (
        [_seg(0.5, 2.5, "A:min7"), _seg(2.5, 3.5, "C:maj"), _seg(3.5, 4.5, "G:maj/3")], {"cached": False}))
    out = tmp_path / "r.json"
    assert T.main(["song", "--json", str(out)]) == 0
    txt = capsys.readouterr().out
    assert "Am7" in txt and "C G/B" in txt and "same name 25 %" in txt and "same root and colour 75 %" in txt
    r = json.loads(out.read_text())[0]
    assert r["agreement"] == {"same_name": 0.25, "same_family": 0.75} and r["key"]["chord"] == "Am"
