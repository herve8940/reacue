"""Syntaxe des scripts d'installation (bash -n, analyseur PowerShell si pwsh est présent)."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SH = [ROOT / "install" / "install_mac.sh", ROOT / "install" / "uninstall_mac.sh",
      ROOT / "install" / "install_stems_mac.sh",
      ROOT / "Install ReaCue.command", ROOT / "Uninstall ReaCue.command", ROOT / "Install ReaCue Stems.command"]
PS1 = [ROOT / "install" / "install_windows.ps1", ROOT / "install" / "uninstall_windows.ps1",
       ROOT / "install" / "install_stems_windows.ps1"]
BAT = [ROOT / "Install ReaCue.bat", ROOT / "Uninstall ReaCue.bat", ROOT / "Install ReaCue Stems.bat"]


@pytest.mark.parametrize("path", SH, ids=lambda p: p.name)
def test_bash_syntax_and_exec_bit(path):
    r = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    if path.suffix == ".command":
        assert os.access(path, os.X_OK)


def _pwsh():
    return os.environ.get("PWSH") or shutil.which("pwsh")


@pytest.mark.parametrize("path", PS1, ids=lambda p: p.name)
def test_powershell_syntax_and_bom(path):
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "UTF-8 avec BOM requis pour Windows PowerShell 5.1"
    assert b"\r\n" in raw
    ps = _pwsh()
    if not ps:
        pytest.skip("pwsh absent")
    cmd = ("$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
           f"'{path}', [ref]$null, [ref]$e); if ($e.Count) {{ $e | % {{ $_.ToString() }}; exit 1 }}")
    r = subprocess.run([ps, "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("path", BAT, ids=lambda p: p.name)
def test_bat_launchers(path):
    raw = path.read_bytes()
    raw.decode("ascii")                                  # pas d'accents dans un .bat
    assert b"\r\n" in raw and b"-ExecutionPolicy Bypass -File" in raw and b"%~dp0install\\" in raw


def test_setup_runs_with_old_python_syntax():
    # reacue_setup.py peut tourner avec le python3 système de macOS (3.9) pour la désinstallation
    import ast
    src = (ROOT / "install" / "reacue_setup.py").read_text(encoding="utf-8")
    ast.parse(src, feature_version=(3, 9))


def test_stems_installers_use_separate_env_and_binaries():
    for p in (ROOT / "install" / "install_stems_mac.sh", ROOT / "install" / "install_stems_windows.ps1"):
        t = p.read_text(encoding="utf-8-sig")
        assert ".venv-demucs" in t and "requirements-stems.txt" in t and "--no-binary demucs" in t
        assert "reacue_stems.py" in t and "check" in t
    assert "install_stems_mac.sh" in (ROOT / "install" / "install_mac.sh").read_text(encoding="utf-8")
    assert "install_stems_windows.ps1" in (ROOT / "install" / "install_windows.ps1").read_text(encoding="utf-8-sig")
