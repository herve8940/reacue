"""Synthèse vocale : macOS (say) et Windows (SAPI via PowerShell) simulés."""
import base64
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from reacue_mcp import voice as V


class FakeRun:
    """Remplace subprocess.run : enregistre les appels, simule les sorties."""

    def __init__(self, list_out=b"", write_wav=True):
        self.calls = []
        self.list_out = list_out
        self.write_wav = write_wav

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        out = b""
        if "-EncodedCommand" in cmd:
            script = base64.b64decode(cmd[cmd.index("-EncodedCommand") + 1]).decode("utf-16-le")
            if "GetInstalledVoices" in script:
                out = self.list_out
            elif self.write_wav:
                env = kw["env"]
                _wav(Path(env["REACUE_TTS_OUT"]))
        elif cmd[1:3] == ["-v", "?"]:
            return subprocess.CompletedProcess(cmd, 0, self.list_out.decode(), "")
        elif "-o" in cmd and self.write_wav:
            _wav(Path(cmd[cmd.index("-o") + 1]))
        return subprocess.CompletedProcess(cmd, 0, out, b"")


def _wav(p: Path, sr=22050):
    y = np.zeros(int(0.6 * sr), dtype="float32")
    y[int(0.2 * sr):int(0.45 * sr)] = 0.5 * np.sin(np.arange(int(0.25 * sr)) * 0.1)
    sf.write(str(p), y, sr)


SAPI_LIST = "Microsoft David Desktop|en-US\nMicrosoft Hortense Desktop|fr-FR\nMicrosoft Zira Desktop|en-US\n".encode()


def test_windows_sapi_voice_choice_and_command(tmp_path, monkeypatch):
    fake = FakeRun(SAPI_LIST)
    monkeypatch.setattr(V, "_run", fake)
    v = V.Voice(tmp_path, None, 240, "fr", backend=("sapi", r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"))
    assert v.voice == "Microsoft Hortense Desktop" and not v.warnings
    en = V.Voice(tmp_path, None, 240, "en", backend=("sapi", "powershell.exe"))
    assert en.voice == "Microsoft Zira Desktop"
    f = v.render("Refrain", max_len=None)
    assert f and Path(f).exists() and Path(f).suffix == ".wav"
    cmd, kw = fake.calls[-1]
    assert cmd[:6] == [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-NoProfile",
                       "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand"]
    script = base64.b64decode(cmd[6]).decode("utf-16-le")
    assert "System.Speech" in script and "SetOutputToWaveFile($env:REACUE_TTS_OUT" in script
    assert "Speak($env:REACUE_TTS_TEXT)" in script and "SelectVoice($env:REACUE_TTS_VOICE)" in script
    env = kw["env"]
    assert env["REACUE_TTS_TEXT"] == "Refrain" and env["REACUE_TTS_VOICE"] == "Microsoft Hortense Desktop"
    assert env["REACUE_TTS_RATE"] == "2"           # 240 mots/min -> +2
    # le texte n'est jamais dans la ligne de commande (accents, guillemets)
    assert all("Refrain" not in c for c in cmd)


def test_windows_text_with_quotes_and_accents(tmp_path, monkeypatch):
    fake = FakeRun(SAPI_LIST)
    monkeypatch.setattr(V, "_run", fake)
    v = V.Voice(tmp_path, None, 200, "fr", backend=("sapi", "powershell.exe"))
    assert v.render('Pré-refrain "x" ; $(rm)') is not None
    env = fake.calls[-1][1]["env"]
    assert env["REACUE_TTS_TEXT"] == 'Pré-refrain "x" ; $(rm)'


def test_windows_missing_language_voice_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "_run", FakeRun("Microsoft Zira Desktop|en-US\n".encode()))
    v = V.Voice(tmp_path, None, 200, "fr", backend=("sapi", "powershell.exe"))
    assert v.voice is None and any("fr" in w for w in v.warnings)
    monkeypatch.setattr(V, "_run", FakeRun(SAPI_LIST))
    v = V.Voice(tmp_path, "Microsoft Inconnue", 200, "en", backend=("sapi", "powershell.exe"))
    assert v.voice == "Microsoft Zira Desktop" and v.warnings


def test_sapi_rate():
    assert V.sapi_rate(200) == 0 and V.sapi_rate(240) == 2 and V.sapi_rate(500) == 10 and V.sapi_rate(0) == -10


def test_macos_say_unchanged(tmp_path, monkeypatch):
    out = ("Thomas              fr_FR    # Bonjour\nSamantha            en_US    # Hello\n").encode()
    fake = FakeRun(out)
    monkeypatch.setattr(V, "_run", fake)
    v = V.Voice(tmp_path, None, 200, "fr", backend=("say", "/usr/bin/say"))
    assert v.voice == "Thomas" and v.say == "/usr/bin/say"
    f = v.render("Refrain")
    cmd = fake.calls[-1][0]
    assert cmd[:2] == ["/usr/bin/say", "-r"] and cmd[-1] == "Refrain" and ["-v", "Thomas"] == cmd[-3:-1]
    # même nom de fichier qu'avant (cache existant de l'auteur réutilisé)
    import hashlib
    key = hashlib.md5("v2|Thomas|200|0|Refrain".encode()).hexdigest()[:10]
    assert Path(f).name == f"Refrain_{key}.wav"


def test_no_engine_warns_and_returns_none(tmp_path):
    v = V.Voice(tmp_path, None, 200, "en", backend=(None, None))
    assert not v.available and v.render("Chorus") is None
    assert v.warnings and "speech" in v.warnings[0].lower() or "synthèse" in v.warnings[0].lower()


def test_detect_backend(monkeypatch):
    monkeypatch.setattr(V.shutil, "which", lambda n: {"say": "/usr/bin/say", "powershell": "C:/ps.exe",
                                                      "espeak-ng": "/usr/bin/espeak-ng"}.get(n))
    assert V.detect_backend("darwin") == ("say", "/usr/bin/say")
    assert V.detect_backend("win32") == ("sapi", "C:/ps.exe")
    assert V.detect_backend("linux") == ("espeak", "/usr/bin/espeak-ng")
    monkeypatch.setattr(V.shutil, "which", lambda n: None)
    monkeypatch.delenv("SystemRoot", raising=False)
    assert V.detect_backend("win32") == (None, None)


def test_tighten_trims_and_bounds(tmp_path):
    src, dst = tmp_path / "a.wav", tmp_path / "b.wav"
    _wav(src)
    d = V.tighten(src, dst, max_len=0.1)
    assert abs(d - 0.1) < 0.01
    y, _ = sf.read(str(dst))
    assert abs(np.abs(y).max() - 0.89) < 0.01


def test_windows_no_console_flag(monkeypatch):
    seen = {}
    monkeypatch.setattr(V.sys, "platform", "win32")
    monkeypatch.setattr(V.subprocess, "run", lambda cmd, **kw: seen.update(kw))
    V._run(["x"])
    assert seen["creationflags"] == V.CREATE_NO_WINDOW
