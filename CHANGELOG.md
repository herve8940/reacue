# Changelog

## 0.10.0-beta — 2026-10

### Added / Ajouts
- **Stem separation inside REAPER** (optional): new action **ReaCue - Separate stems / Séparer les stems**.
  Splits the selected MP3/WAV into 6 stems (vocals, drums, bass, guitar, piano, other) with Demucs 4.0.1,
  locally, in the background with a progress bar; the stems are imported on one track each, aligned with the
  original item (position, length, offset, rate), and the original item is removed (one Undo). Results are
  cached next to the song (`<song>-stems/<model>/`): running it again imports immediately. Model chosen with
  the new `stems_model` setting (`htdemucs_6s` default, or `htdemucs` for 4 stems).
  Séparation de stems dans REAPER, en local, sans abonnement.
- Separate Python environment `.venv-demucs` (Demucs needs other torch/numpy versions than ReaCue), installed
  by `install/install_stems_mac.sh` / `install/install_stems_windows.ps1`: offered at the end of the main
  installers (`REACUE_STEMS=yes|no`, `-Stems yes|no|ask`), or later with `Install ReaCue Stems.command` /
  `.bat`. Downloads both models and measures the computer's speed. Pre-built packages only (except Demucs,
  pure Python). Pinned versions: Mac Intel torch/torchaudio 2.2.2 + numpy < 2 (last PyTorch for Intel Macs);
  elsewhere torch/torchaudio 2.5.1.
- `reacue_stems.py`: launcher run by the action (`separate`, status JSON + log read by REAPER) and installer
  check (`check`); `--repo` for offline/local models.
- Lyrics: for stems separated by ReaCue, the lyrics file can also sit next to the original song file.
- **Hand-edited regions are read back**: when the song is already prepared (same audio items), *Prepare*
  (and, with Claude, `prepare_song`, `update_options`, `rename_section`) reads the project's regions and,
  if they differ from the saved structure, adopts them: start → nearest bar (¼-bar tolerance, otherwise
  rounded with a warning), names kept (section type deduced from the name, FR/EN), added/deleted regions
  taken into account, regions before bar 1 / after the end / on a taken bar ignored with a warning. The
  final window says “Structure taken from your REAPER regions”. *Republish the prompter* does not adopt
  them (warning instead). `set_sections` / `set_grid` still win. Other projects (consolidated, other song)
  are never read. New `reacue_mcp/regions.py`, `prepare_song(reanalyse=…)`.
  Les régions modifiées à la main dans REAPER sont reprises à la préparation suivante.
- Step-by-step beginner tutorials: `docs/TUTORIEL_fr.md`, `docs/TUTORIAL_en.md` (including linking
  Claude Desktop and both ways of correcting the structure).
- Tests: `tests/test_regions.py` (moved, renamed, added, deleted, off-grid, out-of-song regions, publish
  only, Claude tools, other project protected), `tests/test_stems.py` (launcher with a fake Demucs, Lua action: paths, quoting macOS/Windows,
  progress, import and alignment, cache, messages), installer and script syntax tests extended.

### Changed / Modifications
- Installers in 5 steps; `--purge` on uninstall also deletes `.venv-demucs`; `status` reports it.
- README / LISEZMOI: stem separation section, OFFLINE files on macOS (Downloads folder), limitations.
- Package version `0.10.0b1`.

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
