# Changelog

## 0.12.0-beta — 2026-10

### Added / Ajouts
- **Check / Vérifier** (pre-show check) in the *ReaCue - Concert* window: audio files readable (not offline),
  spoken cue files present, songs prepared (structure and tempo), concert up to date (fingerprint — size and
  Adler-32 — of each song project stored at build time and compared), ReaCue bridge, REAPER web interface,
  network address, audio device running, click / cue outputs (existing hardware outputs, not muted, routed
  somewhere), prompter published, Stage control phones seen (the Stage control page writes
  `ReaCue/remote_seen` every few seconds). Green / orange / red summary; **Fix** buttons: set all media online,
  rebuild the concert, republish the prompter. Also available with no concert open (system part).
  Contrôle avant concert avec corrections en un clic.
- **Rehearsal mode / Mode répétition** (window and Stage control phone): automatic stop off; tap a section to
  **loop** it, a 2nd section of the same song to loop the range; **one bar of count-in** (click and spoken
  cues only, the other tracks muted during that bar) before the loop starts and before each repeat, at the
  tempo of that point (bar length from REAPER's tempo map); speed 100 / 90 / 80 / 70 % (master playrate,
  pitch preserved); *Loop off*; leaving the mode restores speed, automatic stop, REAPER's repeat, time
  selection and preserve-pitch option. Remote commands `reh`, `loop`, `loopoff`, `rate`; state published in
  `ReaCue/rehearsal` for the phones.
  Boucle avec une mesure de décompte avant chaque reprise, ralenti.
- Tests: `tests/test_check_rehearsal.py` (checks with offline / missing media, missing outputs, stale or old
  concert, unprepared song, fixes, window check view FR/EN; loop on a section and a range, count-in bar at the
  right tempo, muting, restart, stop during the count-in, speed, exit, remote commands, no auto stop in
  rehearsal), Stage control page extended (rehearsal, loop, speed, `remote_seen`) in FR and EN.

### Changed / Modifications
- Concert sidecar `.concert.lua` version 2: build time and a fingerprint of each song project.
- Concert window: tool row on its own line (status, then Check / Rehearsal / Setlist / PIN / QR); text
  truncation now cuts whole UTF-8 characters.
- `ReaCue_run.lua` exposes `bridge_alive`.
- Package version `0.12.0b1`.

## 0.11.0-beta — 2026-10

### Added / Ajouts
- **Concert mode / Mode concert**: several already prepared songs chained in one REAPER project, without
  re-analysis (stems, tempo map — fixed or beatmap —, validated structure, spoken cues and click taken from
  each song's own project, read-only). One track per instrument shared by all songs (localized names), one
  colour per song, regions “Song · Section”, a “Songs” ruler lane, a whole number of bars between songs.
  New `reacue_mcp/concert.py`; MCP tool `build_concert`, also reachable as
  `set_sections([{"concert": {"name": …, "songs": [...]}}])`; CLI `concert --name … --songs …` /
  `concert --setlist …` and `concert-extras` (chords, lyrics, drums per song, cached next to each song, in the
  background). Files `<name>.RPP`, `.setlist.json`, `.concert.lua`, `.prompteur.json` in the concerts folder.
  New settings `projects_dir` (default `<Documents>/REAPER Media`) and `concert_dir` (default
  `<projects folder>/Concerts`).
  Plusieurs morceaux préparés enchaînés dans un seul projet, sans réanalyse.
- **ReaCue - Concert window / fenêtre** (`reaper/ReaCue_Concert.lua`, `ReaCue_concert_lib.lua`): song x/N,
  tempo, key, section, bar, Playing/Paused/Stopped, progress and time left, concert time, next song; big
  Previous / Start / Play-Pause / Stop / Next buttons with a double tap during playback; clickable sections;
  setlist and *Rebuild the concert*; list of concerts to open in a new tab; compact docked view; **automatic
  stop at the end of each song** with the cursor on the next count-in. Actions *ReaCue - Next song* /
  *Previous song* for pedals and shortcuts. Registered by the installers (and removed on uninstall).
- **QR code** of the prompter address in the Concert window: IP computed on click (macOS `ipconfig getifaddr`,
  Windows `ipconfig` without console window, Linux `hostname -I`), port read from `reaper.ini`. Encoder:
  [luaqrcode](https://github.com/speedata/luaqrcode) (BSD, `reaper/ReaCue_qrcode.lua`, unchanged).
- **Stage control / Régie** role in the prompter (French and English): phone remote for the concert
  (Play/Pause, Stop, Previous / Start / Next, setlist, sections), 4-digit PIN generated on the first launch of
  the Concert window (changeable), replay protection, acknowledgement. Commands go through REAPER's web
  interface (`/_/SET/EXTSTATE/ReaCue/remote/…`) and are executed by the Concert window. The PIN guards against
  mistakes, not attacks.
- Prompter: concert files (`concert` + `songs`) — the page follows the current song, shows x/N and the next song.
- Tests: `tests/test_concert.py` (build, English names and VOICE track, settings folders, setlist rebuild,
  per-song caches, CLI, MCP and `set_sections`), `tests/test_concert_lua.py` (Lua 5.4 with a simulated REAPER:
  transport, double tap, sections, auto stop, remote PIN/nonce, IP parsing macOS/Windows/Linux, CLI launch
  macOS/Windows, window FR/EN, **QR decoded** with zxing-cpp, docked view, next/previous actions),
  `tests/test_regie_web.py` (real page in headless Chromium + fake REAPER web server running the real Lua
  library, FR and EN), installer test for the new actions. Demo projects are generated by
  `tools/concert_demo.py` (fictional songs, synthetic audio).
- Tutorials: new chapter 16 *Concert mode* (build, open, play, QR, Stage control, rebuild) and troubleshooting.

### Changed / Modifications
- `prompter.stem_activity(cache=…)`: one cache file per song in concert mode.
- Package version `0.11.0b1`.

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
