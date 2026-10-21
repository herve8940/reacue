# Changelog

## 0.9.0-beta — 2026-10

First public (private-repository) release / Première version publique (dépôt privé).

### Added / Ajouts
- **Windows support (beta, not yet tested on real hardware)**: SAPI voices through PowerShell (no console
  window), background launch from REAPER with `reaper.ExecProcess` and `pythonw.exe`, `%APPDATA%\REAPER`
  paths, `.venv\Scripts` interpreter, `Install ReaCue.bat` / `Uninstall ReaCue.bat`.
  Support Windows (bêta, non testé sur machine réelle).
- **French / English**: `language` setting; region names, spoken cues, end-of-preparation window, REAPER
  bridge messages, main warnings and the web prompter (FR/EN button, remembered on each phone). Section
  names are recognised in both languages (colours, cue text, prompter roles).
  Bilingue français / anglais.
- **One-click installers** for macOS (`Install ReaCue.command`) and Windows: uv + Python 3.12, pre-built
  packages only, REAPER scripts, bridge auto-start, actions registered in `reaper-kb.ini` when REAPER is
  closed, settings file, optional Claude Desktop entry (with backup). Idempotent; uninstallers included.
  Installateurs clé en main, désinstallation.
- `reacue_settings.json` user settings (language, voices, count-in, cue lead, volumes, routing, tempo mode).
  Settings changed after a preparation are applied the next time the song is prepared (structure kept).
- `lyrics_timing.json` accepted as an alias of `paroles_calage.json`; `lyrics*.txt` files.
- Linux: spoken cues through `espeak-ng` when available; without any speech engine, a clear warning and
  everything else still works.
- Test suite (`tests/`): i18n, voices (macOS/Windows mocked), Windows paths, CLI with a fake REAPER bridge,
  Lua scripts run with Lua 5.4 (status JSON parsing, command quoting, bridge requests), installer,
  shell/PowerShell syntax, prompter page without console errors in FR and EN.
- Documentation (README / LISEZMOI), screenshots of a fictional demo song, migration note.

### Changed / Modifications
- REAPER bridge 1.3.0: VOICE track (English) recognised as generated, localized messages.
- `ReaCue_run.lua`: the install folder is found from the ExtState, the `reacue_install.txt` file written by
  the installer, or the script location; no more hard-coded `~/Documents/reacue-mcp` (kept as last resort).
- `textutil` (RTF) only used on macOS.
- Development tools moved to `tools/` (no private paths; `struct_eval.py` reads its songs from a private JSON).
- Package version `0.9.0b1`.
