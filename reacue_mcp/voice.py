"""Appels vocaux (cues audio) générés par la synthèse vocale du système.

  - macOS   : commande `say` (voix Thomas, Amélie, Samantha…) ;
  - Windows : SAPI via PowerShell (System.Speech.Synthesis.SpeechSynthesizer -> WAV), voix fr-FR /
              en-US installées (Microsoft Hortense, Zira, David…), sinon voix par défaut ;
  - Linux   : espeak-ng (ou espeak) s'il est installé ;
  - aucune  : avertissement, pas d'annonces ni de décompte parlés, le reste fonctionne.

Chaque fichier est recalé : le silence de tête est coupé pour que l'attaque du mot tombe
pile sur la position de l'item, et la durée peut être bornée (décompte : le mot ne doit
pas déborder sur le temps suivant).
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from .i18n import t, cue_text  # noqa: F401  (cue_text : réexporté pour compatibilité)

COUNT_WORDS = {
    "fr": ["un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit"],
    "en": ["one", "two", "three", "four", "five", "six", "seven", "eight"],
}
COUNT_FR = COUNT_WORDS["fr"]  # compatibilité

PREFERRED = {   # voix macOS
    "fr": ("Thomas", "Amélie", "Audrey", "Aurélie"),
    "en": ("Samantha", "Daniel", "Alex", "Karen", "Moira"),
}
PREFERRED_WIN = {   # voix SAPI (Windows 10/11)
    "fr": ("Microsoft Hortense Desktop", "Microsoft Julie", "Microsoft Paul"),
    "en": ("Microsoft Zira Desktop", "Microsoft David Desktop", "Microsoft Mark"),
}
CULTURE = {"fr": "fr-FR", "en": "en-US"}

CREATE_NO_WINDOW = 0x08000000   # Windows : pas de fenêtre console pour PowerShell


def _run(cmd, **kw):
    """subprocess.run sans fenêtre console sous Windows."""
    if sys.platform.startswith("win"):
        kw.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kw)


def tighten(src: Path, dst: Path, max_len: float | None, threshold_db: float = -35.0) -> float:
    """Coupe le silence de tête (attaque à ~2 ms près) et borne la durée avec un fondu.
    Retourne la durée finale en secondes."""
    y, sr = sf.read(str(src), dtype="float32", always_2d=True)
    mono = np.abs(y).max(axis=1)
    peak = float(mono.max()) or 1.0
    thr = peak * 10 ** (threshold_db / 20)
    above = np.where(mono > thr)[0]
    start = max(0, int(above[0]) - int(0.002 * sr)) if len(above) else 0
    end_sig = int(above[-1]) + int(0.03 * sr) if len(above) else len(y)
    end = min(len(y), end_sig)
    if max_len:
        end = min(end, start + int(max_len * sr))
    out = y[start:end].copy()
    fade = min(len(out), int(0.012 * sr))
    if fade > 1:
        out[-fade:] *= np.linspace(1.0, 0.0, fade, dtype="float32")[:, None]
    # normalisation à -1 dBFS : décompte et annonces au même niveau
    m = float(np.abs(out).max()) or 1.0
    out *= 0.89 / m
    sf.write(str(dst), out, sr, subtype="PCM_16")
    return len(out) / sr


# --------------------------------------------------------------------------- #
# Windows : SAPI via PowerShell
# --------------------------------------------------------------------------- #
# Le texte, la voix et le fichier passent par des variables d'environnement (Unicode, aucun
# problème de guillemets ni d'encodage de la ligne de commande) ; le script lui-même passe en
# -EncodedCommand (base64 UTF-16LE).
PS_LIST = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
foreach ($v in $s.GetInstalledVoices()) {
  if ($v.Enabled) { [Console]::WriteLine($v.VoiceInfo.Name + "|" + $v.VoiceInfo.Culture.Name) }
}
$s.Dispose()
"""

PS_SPEAK = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
if ($env:REACUE_TTS_VOICE) { try { $s.SelectVoice($env:REACUE_TTS_VOICE) } catch { } }
$s.Rate = [int]$env:REACUE_TTS_RATE
$s.Volume = 100
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile($env:REACUE_TTS_OUT, $fmt)
$s.Speak($env:REACUE_TTS_TEXT)
$s.SetOutputToNull()
$s.Dispose()
"""


def ps_encode(script: str) -> str:
    """Script PowerShell -> argument de -EncodedCommand."""
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def powershell_cmd(ps: str, script: str) -> list[str]:
    return [ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", ps_encode(script)]


def sapi_rate(wpm: int) -> int:
    """Débit `say` (mots/min, ~200 = normal) -> Rate SAPI (-10..10, 0 = normal)."""
    return int(max(-10, min(10, round((int(wpm) - 200) / 20))))


def _find_powershell() -> str | None:
    for name in ("powershell", "powershell.exe", "pwsh", "pwsh.exe"):
        p = shutil.which(name)
        if p:
            return p
    root = os.environ.get("SystemRoot")
    if root:
        p = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if p.exists():
            return str(p)
    return None


# --------------------------------------------------------------------------- #
# Synthèse
# --------------------------------------------------------------------------- #
def detect_backend(platform: str | None = None) -> tuple[str | None, str | None]:
    """(moteur, exécutable) : ("say", …), ("sapi", powershell), ("espeak", …) ou (None, None)."""
    platform = platform or sys.platform
    if platform == "darwin":
        p = shutil.which("say")
        return ("say", p) if p else (None, None)
    if platform.startswith("win"):
        p = _find_powershell()
        return ("sapi", p) if p else (None, None)
    for name in ("espeak-ng", "espeak"):
        p = shutil.which(name)
        if p:
            return "espeak", p
    return None, None


class Voice:
    def __init__(self, cache_dir: Path, voice: str | None = None, rate: int = 200, lang: str = "fr",
                 backend: tuple[str | None, str | None] | None = None):
        self.cache = Path(cache_dir)
        self.rate = rate
        self.lang = lang if lang in COUNT_WORDS else "fr"
        self.warnings: list[str] = []
        self.engine, self.exe = backend if backend is not None else detect_backend()
        self.say = self.exe if self.engine == "say" else None        # compatibilité
        self.voice = None
        if not self.engine:
            self.warnings.append(t("tts_none"))
        else:
            self.voice = self._pick(voice)

    @property
    def available(self) -> bool:
        return bool(self.engine)

    # -- voix installées : [(nom, langue « fr_FR » / « fr-FR » / « fr »)]
    def _voices(self) -> list[tuple[str, str]]:
        if self.engine == "say":
            out = _run([self.exe, "-v", "?"], capture_output=True, text=True).stdout
            res = []
            for line in out.splitlines():
                m = re.match(r"^(.+?)\s+([a-z]{2,3}_[A-Z0-9]{2,3})\s+#", line)
                if m:
                    res.append((m.group(1).strip(), m.group(2)))
            return res
        if self.engine == "sapi":
            r = _run(powershell_cmd(self.exe, PS_LIST), capture_output=True, timeout=30)
            out = r.stdout.decode("utf-8", errors="replace")
            res = []
            for line in out.splitlines():
                if "|" in line:
                    n, c = line.rsplit("|", 1)
                    res.append((n.strip(), c.strip()))
            return res
        if self.engine == "espeak":
            return [(self.lang, self.lang)]         # espeak : la langue sert de voix
        return []

    def _pick(self, wanted: str | None) -> str | None:
        try:
            voices = self._voices()
        except (OSError, subprocess.SubprocessError):
            return None
        names = {n.lower(): n for n, _ in voices}
        if wanted and wanted.lower() in names:
            return names[wanted.lower()]
        if wanted and self.engine != "espeak":
            self.warnings.append(t("tts_voice_missing", voice=wanted))
        if self.engine == "espeak":
            return wanted or self.lang
        prefs = PREFERRED_WIN if self.engine == "sapi" else PREFERRED
        for pref in prefs.get(self.lang, ()):
            for n in names:
                if n.startswith(pref.lower()):
                    return names[n]
        for n, lang in voices:
            if re.match(rf"^{self.lang}[_-]", lang, re.I) or lang.lower() == self.lang:
                return n
        self.warnings.append(t("tts_no_lang_voice", code=self.lang))
        return None

    def command(self, text: str, raw: Path) -> tuple[list[str], dict | None]:
        """Commande de synthèse de `text` dans `raw` : (argv, environnement ou None)."""
        if self.engine == "say":
            cmd = [self.exe, "-r", str(self.rate), "-o", str(raw)]
            if self.voice:
                cmd += ["-v", self.voice]
            return cmd + [text], None
        if self.engine == "sapi":
            env = dict(os.environ, REACUE_TTS_TEXT=text, REACUE_TTS_OUT=str(raw),
                       REACUE_TTS_VOICE=self.voice or "", REACUE_TTS_RATE=str(sapi_rate(self.rate)))
            return powershell_cmd(self.exe, PS_SPEAK), env
        if self.engine == "espeak":
            # espeak : ~175 mots/min par défaut, comme say
            return [self.exe, "-v", self.voice or self.lang, "-s", str(int(self.rate)), "-w", str(raw), text], None
        raise RuntimeError("no speech engine")

    def render(self, text: str, max_len: float | None = None) -> str | None:
        if not self.engine:
            return None
        self.cache.mkdir(parents=True, exist_ok=True)
        ml = round(max_len, 3) if max_len else 0
        key = hashlib.md5(f"v2|{self.engine}|{self.voice}|{self.rate}|{ml}|{text}".encode()).hexdigest()[:10]
        if self.engine == "say":    # même clé qu'avant : le cache existant reste valable sur macOS
            key = hashlib.md5(f"v2|{self.voice}|{self.rate}|{ml}|{text}".encode()).hexdigest()[:10]
        slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:30] or "cue"
        path = self.cache / f"{slug}_{key}.wav"
        if path.exists():
            return str(path)
        raw = self.cache / (f"_raw_{key}.aiff" if self.engine == "say" else f"_raw_{key}.wav")
        cmd, env = self.command(text, raw)
        try:
            r = _run(cmd, capture_output=True, env=env, timeout=60)
            err = (r.stderr or b"").decode("utf-8", errors="replace").strip()
            ok = r.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            ok, err = False, str(e)
        if not ok or not raw.exists():
            self.warnings.append(t("tts_failed", text=text, err=err[-300:]))
            return None
        try:
            tighten(raw, path, max_len)
        except Exception as e:  # fichier brut utilisable quand même
            self.warnings.append(t("tts_tighten", text=text, e=e))
            return str(raw)
        raw.unlink(missing_ok=True)
        return str(path)
