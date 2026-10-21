# ReaCue

**Live-ready songs in REAPER, in one click — and a prompter on every musician's phone.**

*[Version française : LISEZMOI.md](LISEZMOI.md)*

ReaCue is for bands that play live with REAPER. From the stems of a song (or a single MP3), it detects
the tempo, the bar grid and the structure, then builds everything in your REAPER project: tempo map,
named and coloured regions, a click with count-in, spoken cues (“Chorus”…) and a “one two three four”
count before each section. It also publishes a **web prompter** that each musician opens on their phone,
served by REAPER's built-in web interface: structure, chords (bass / guitars), timed lyrics (vocals) and a
dedicated drummer view with the transcribed grooves and fills.

Everything runs locally: no AI and no internet once installed. An optional mode lets you drive it in plain
language with Claude (MCP server).

> **Status: 0.9.0 beta.** Developed and used on macOS. Windows support is new and has **not yet been
> tested on a real machine** — feedback welcome.

| Drums | Bass | Vocals | Guitar |
|---|---|---|---|
| <img src="docs/images/prompter_drums_en.png" width="190"> | <img src="docs/images/prompter_bass_en.png" width="190"> | <img src="docs/images/prompter_vocals_en.png" width="190"> | <img src="docs/images/prompter_guitars_en.png" width="190"> |

<img src="docs/images/prompter_drums_en_tablet.png" width="780">

*(Screenshots of a made-up “Demo Song”: structure, chords, lyrics and drums are all invented.)*

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Enable REAPER's web interface (prompter)](#enable-reapers-web-interface-prompter)
- [Usage](#usage)
- [Lyrics](#lyrics)
- [Settings](#settings)
- [Optional: drive ReaCue with Claude (MCP)](#optional-drive-reacue-with-claude-mcp)
- [Known limitations](#known-limitations)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Uninstall](#uninstall)
- [For developers](#for-developers)
- [Credits and licence](#credits-and-licence)

## Features

In REAPER, from the audio already in your project:

- **Tempo map** locked to the song: fixed tempo when the recording is quantised, or one tempo marker per
  bar when it was played without a click (the click then follows the band). The audio is moved so that
  bar 1 falls exactly on a bar line.
- **One region per section**, named and coloured (Intro, Verse 1, Pre-chorus, Chorus, Bridge, Solo,
  Break, Outro, Main Riff…), in English or French.
- **CLICK track** (REAPER's native click source) with a 2-bar **count-in**, optionally routed to a
  dedicated hardware output for in-ears.
- **VOICE track**: a spoken cue (“Chorus”) on the second-to-last bar of each section and “one two three
  four” on the last bar, routed like the click. Uses the system voices (macOS `say`, Windows SAPI).
- **CUES track** and “→ Chorus” markers, readable at a glance.

On the musicians' phones and tablets (web prompter):

- current section, bar and beat, bars left, next section, count-down on the last bar;
- **Bass / guitars**: current and next chord with a count-down, chord chart of the section, key;
- **Vocals**: scrolling lyrics in time with the song, next line and count-down before each entry;
- **Drums**: groove of the section, 16-step grid of the current bar, fills, crashes, stops and re-entries;
- per-instrument entries and rests detected from the stems (“STOP next bar”, “Come in in 2 bars”);
- French / English, follows REAPER's play cursor (REAPER is the only thing that needs to run on stage).

## How it works

```
 REAPER action “ReaCue - Prepare the song”          Claude (optional, MCP)
                 │                                         │
                 ▼                                         ▼
        ReaCue program (Python): audio analysis, tempo, sections, chords, lyrics, drums
                 │  drops data (never code) into <REAPER resources>/ReaCueMCP/
                 ▼
        ReaCue_Bridge.lua (runs in the background inside REAPER) ──> REAPER API
                 │
                 └──> reaper_www_root/prompteur.html + reacue_song.json ──> phones (Wi-Fi)
```

## Requirements

- **REAPER 7** or later (6.x probably works but is not tested).
- **macOS 12+** (Intel or Apple Silicon) or **Windows 10/11** (beta).
- About 1.5 GB of disk space (Python environment and libraries).
- **Internet only during installation** (to download Python and the libraries). Nothing is sent anywhere
  afterwards; lyrics are never downloaded.
- For the prompter: the phones and the computer on the same Wi-Fi network.

## Installation

1. Download the project (green **Code** button → *Download ZIP*) and unzip it **where you will keep it**,
   for example `Documents/ReaCue`. Do not move the folder afterwards (or run the installer again if you do).
2. Start REAPER once (so that its settings folder exists), then **quit REAPER**: the installer can then
   register the actions for you.
3. Run the installer:
   - **macOS**: double-click **`Install ReaCue.command`**. If macOS refuses to open it (“unidentified
     developer”), right-click it → *Open* → *Open*. Alternative in Terminal: `bash "Install ReaCue.command"`.
   - **Windows**: double-click **`Install ReaCue.bat`**. If SmartScreen shows a warning, click
     *More info* → *Run anyway*.
4. Answer the questions: language (`fr` / `en`) and whether to register ReaCue in Claude Desktop
   (optional, answer *no* if you don't use Claude).
5. Start REAPER. The bridge starts by itself and two actions are available in *Actions → Show action list*:
   - **ReaCue - Prepare the song**
   - **ReaCue - Republish the prompter**

   Tip: add them to a toolbar (right-click a toolbar → *Customize toolbar* → *Add*).

The installer can be run again at any time (to change the language or repair an installation): your
settings and prepared songs are kept.

What it does: installs [uv](https://docs.astral.sh/uv/) (Astral's Python manager) if needed, creates a
private Python 3.12 environment in the `.venv` folder (pre-built packages only, no compiler needed), copies
the REAPER scripts into `<REAPER resources>/Scripts/ReaCue/`, adds the bridge to `Scripts/__startup.lua`,
registers the two actions in `reaper-kb.ini` (only when REAPER is closed), and writes
`<REAPER resources>/ReaCueMCP/reacue_settings.json`. Nothing else in your system is modified.

If REAPER was open during installation, load the actions by hand once: *Actions → Show action list →
New action → Load ReaScript…* → pick `ReaCue_Preparer.lua` and `ReaCue_Republier_prompteur.lua` in
`<REAPER resources>/Scripts/ReaCue/`. (*Options → Show REAPER resource path* opens that folder.)

## Enable REAPER's web interface (prompter)

This is done once, by hand (REAPER does not offer a safe way to do it from a script):

1. REAPER → *Options → Preferences* (macOS: *REAPER → Settings*) → **Control/OSC/web** → **Add**.
2. Control surface mode: **Web browser interface**. Port: **8080** (or any free port). Leave the rest as is.
3. OK, OK.

On each phone or tablet, open: **`http://<computer IP>:8080/prompteur.html`**, then pick your role.

Finding the computer's IP address:

- **macOS**: *System Settings → Wi-Fi → Details…* next to the network → *IP address* (e.g. `10.0.1.23`).
- **Windows**: *Settings → Network & Internet → Wi-Fi → (network) properties → IPv4 address*,
  or type `ipconfig` in a command prompt.
- The installer also prints the likely address at the end.

Tips:

- **Reserve the IP address** of the computer in your router (DHCP reservation, sometimes called
  “static lease”), so the address never changes and the phones' bookmarks keep working. On a gig, a small
  dedicated travel router works great.
- Add the page to the home screen (iOS: *Share → Add to Home Screen*; Android: *⋮ → Add to Home screen*)
  for a full-screen app-like view. The ⛶ button also switches to full screen.
- The **FR/EN** button switches the prompter language on that phone (remembered).
- The green dot means the link with REAPER is alive.

## Usage

1. **Import the song** into a REAPER project, one stem per track, all starting at the same time (drag and
   drop the files). A single MP3/WAV also works, with less detail.
   - The role of each stem is read from its **file name**: `drum`/`batterie`/`kick`/`perc`, `bass`/`basse`,
     `guitar`/`guitare`/`gtr` (`lead`/`solo` = lead guitar), `vocal`/`voice`/`vox`/`chant`/`voix`;
     anything else counts as keys/other.
   - Optional: key and tempo in the file names (e.g. `Demo Song-A minor-112bpm-drums.wav`) help the chords
     and the tempo octave.
2. Run **ReaCue - Prepare the song**. A small window shows the progress (from 20 s to about 1 min); you can
   close it, the result appears at the end: tempo, structure (bars and lengths), what was published.
3. Check the structure (regions) and play the song. Regions edited by hand in REAPER are **not** read
   back by ReaCue: to correct the structure, use the Claude mode (`set_sections`, see below). Running
   *Prepare* again on the same project **keeps the validated structure** and rebuilds everything (click,
   cues, prompter), applying the settings file if you changed it in the meantime.
4. After adding or editing a lyrics file, run **ReaCue - Republish the prompter** (nothing in the REAPER
   project is changed).

Each preparation **replaces** the regions, markers, tempo map and the CLICK / CUES / VOICE tracks of the
project (one *Undo* goes back). Use one project per song.

## Lyrics

ReaCue **never downloads lyrics**: you provide your own text file, next to the stems (same folder):

- name starting with `lyrics`, `paroles` or `parole`, extension `.txt` (UTF-8) or `.rtf`;
- one line = one sung phrase; an empty line separates blocks (verse, chorus…);
- label lines such as `[Chorus]` or `Verse 2:` are ignored; `(x2)` or `bis` at the end of a line repeats it;
- a chorus written once is found again automatically when it is sung again (needs a vocal stem).

The lines are aligned automatically on the vocal stem. To fix a line, add a **timing file** next to the
lyrics: `lyrics_timing.json` (or `paroles_calage.json`). It contains no text, only line numbers and
positions on the bar grid:

```json
{
  "_comment": "keys starting with _ are ignored",
  "1": "9:1.5",
  "2": "11:1.5-12:4",
  "5#2": "47:2.75",
  "8": null
}
```

- key `"12"` = line 12 (1-based, counting non-empty lines, labels excluded), first time it is sung;
  `"12#2"` = second time it is sung (repeated chorus);
- value `"45"` = bar 45, beat 1; `"45:2.75"` = bar 45, beat 2.75 (beats are 1-based, decimals allowed);
  `"45:2.75-49:1.5"` = start and end; `{"start": "45:2.75", "end": "49:1.5"}` is the same;
  `null` = line never shown.
- If **every** line has an anchor (or `null`), automatic alignment is skipped entirely.

Then run *Republish the prompter*.

## Settings

File: `<REAPER resources>/ReaCueMCP/reacue_settings.json` (created by the installer; edit it with any text
editor; missing keys take their default value). Taken into account at the next *Prepare*, including for
an already prepared song (its validated structure is kept). The `language` setting names the sections of
newly analysed songs; section names you validated yourself are kept as they are.

| Key | Default | Meaning |
|---|---|---|
| `language` | `"fr"` | `"fr"` or `"en"`: region names, spoken cues, prompter, messages |
| `count_in_bars` | `2` | bars of click before bar 1 |
| `cue_lead_bars` | `2` | spoken cue N bars before the section (2 = second-to-last bar) |
| `voice_cues` | `true` | spoken section names |
| `voice_count_in` / `voice_count_each` | `true` | “one two three four” on the count-in / before every section |
| `count_lang` | `"en"` | language of the count (`"en"` or `"fr"`) |
| `announce_voice` / `count_voice` | `null` | system voice name (macOS: `Thomas`, `Samantha`… Windows: `Microsoft Hortense Desktop`, `Microsoft Zira Desktop`…); `null` = automatic |
| `count_rate` | `240` | count speed (words per minute) |
| `voice_volume` / `click_volume` | `0.8` / `0.5` | track volumes |
| `click_to_master` | `true` | `false` = click and voice only on `click_hw_output` (in-ears) |
| `click_hw_output` | `null` | hardware output index (0 = outputs 1/2, 2 = 3/4…) |
| `tempo_mode` | `"auto"` | `auto`, `constant` (one tempo) or `beatmap` (one tempo per bar) |

Voices: on Windows, extra voices (e.g. French) are added in *Settings → Time & language → Speech*. Only
voices visible to SAPI (“Desktop” voices) are used. If no voice is available, everything works except the
spoken cues (a warning is shown).

## Optional: drive ReaCue with Claude (MCP)

If you use [Claude Desktop](https://claude.ai/download), answer *yes* during installation (or run the
installer again). The `reacue` server is added to Claude Desktop's configuration (a backup is kept as
`claude_desktop_config.json.bak-reacue`). Restart Claude Desktop, then ask for example:

- “Prepare the song in REAPER.”
- “The chorus starts at bar 29, not 25.” → `set_sections`
- “Rename section 6 to Guitar solo.” → `rename_section`
- “1 bar of count-in, click only on outputs 3/4.” → `update_options`
- “It's 94 BPM, not 188.” → `prepare_song` with `bpm_hint`

| Tool | Role |
|---|---|
| `reaper_status` | Are REAPER and the bridge answering? |
| `prepare_song` | Full preparation (optionally imports a file) |
| `analyze_audio` | Analysis only, without touching the project |
| `set_sections` / `rename_section` | Fix the structure; everything is rebuilt (names can be in English or French) |
| `set_grid` | Impose a fixed-tempo grid when the detection is wrong |
| `update_options` | Count-in, tempo mode, click, cues, voices… without re-analysing |
| `get_project_state`, `goto_section`, `transport` | Project state, navigation, play/stop |

Both modes share the same memory of the last prepared song: you can prepare with the button and fine-tune
with Claude, or the other way round.

## Known limitations

- **Structure detection is not perfect**: it depends on the song. Section boundaries are usually right
  within a bar; names (verse vs chorus, pre-chorus glued to the chorus…) need checking. Lengths that are not
  4, 8 or 16 bars are worth a look.
- **A single MP3 is less precise than stems**: no per-instrument entries/rests, no drum transcription,
  less reliable section names and chords.
- **Drums**: kick, snare and hi-hat are reliable; toms and ride are approximate. Fills are detected as
  bars that differ from the section's groove.
- **Chords**: triads, sevenths, sus and power chords; complex jazz voicings are simplified.
- Without Claude, the detected structure cannot be edited yet (only re-analysed); manual region edits in
  REAPER are overwritten by the next preparation.
- Time signatures in x/4 only (4/4 and 3/4 detected).
- **Windows: beta, not yet tested on a real machine.** In particular the background launch from REAPER,
  the SAPI voices and paths with accents should be checked. Please report issues.
- Linux: not packaged (the code runs; spoken cues need `espeak-ng`).

## Troubleshooting / FAQ

**“The ReaCue bridge is not running in REAPER.”** The bridge starts with REAPER through
`Scripts/__startup.lua`. Restart REAPER. If it still fails, run the action `ReaCue_Bridge.lua` by hand
(*Actions → Load ReaScript*), and check that `__startup.lua` contains the ReaCue line (run the installer
again to restore it). A modal window open in REAPER also blocks the bridge.

**“ReaCue program not found.”** The folder was moved or deleted: run the installer again from its new
location.

**The prompter says “REAPER is not responding”.** Check that the phone is on the same Wi-Fi as the
computer, that the web interface is enabled (see above) and that the address/port are right. A firewall
may block port 8080: allow REAPER (Windows: *Allow an app through Windows Defender Firewall*).

**The IP address changed and the phones lost the page.** Reserve the computer's IP address in the router
(DHCP reservation), see above.

**The phone's screen goes to sleep.** Tap ⛶ (full screen): the page then asks the phone to stay awake
(Screen Wake Lock, Chrome/Safari recent versions). Otherwise, disable auto-lock during the gig
(iOS: *Settings → Display & Brightness → Auto-Lock*; Android: *Display → Screen timeout*).

**No spoken cues.** macOS: check that the voices exist in *System Settings → Accessibility → Spoken
Content*. Windows: install a voice for your language (*Settings → Time & language → Speech*). The warning in
the final window tells which voice was missing.

**Wrong tempo (double or half).** Put the tempo in the stem file names (e.g. `-94bpm`), or use Claude
(`bpm_hint`).

**Where are the logs?** `<REAPER resources>/ReaCueMCP/cli.log`.

## Uninstall

Double-click **`Uninstall ReaCue.command`** (macOS) or **`Uninstall ReaCue.bat`** (Windows), with REAPER
closed. This removes the REAPER scripts, the bridge start-up line, the actions and the Claude Desktop entry.
Your settings and the last prepared song are kept in `<REAPER resources>/ReaCueMCP/` (add `--purge` to the
uninstall script to delete them). Then delete the ReaCue folder.

## For developers

```bash
uv pip install -r requirements-dev.txt     # pytest, lupa, playwright
python -m pytest tests                     # light tests: no audio, no REAPER
python tools/make_screenshots.py           # regenerates docs/images (Playwright + Chromium)
```

Project layout:

| Path | Content |
|---|---|
| `reacue_mcp/` | Python package: analysis, planner, bridge client, prompter, chords, lyrics, drums, voice, i18n, settings, CLI, MCP server |
| `reacue_mcp/web/prompteur.html` | The prompter page (single file) |
| `reaper/` | REAPER scripts: bridge and the two actions |
| `install/` | Installers (macOS, Windows) and the shared `reacue_setup.py` |
| `tests/` | pytest suite (fake REAPER bridge, Lua run through `lupa`, installer, prompter page) |
| `tools/` | **Development tools only** (not used by ReaCue): `struct_eval.py` (structure detection benchmark on your own songs, configured by a private JSON file), `asr_anchor.py` (lyrics timing file from speech recognition, heavy models, Linux), `make_screenshots.py` |

## Credits and licence

ReaCue by Hervé Naessens. MIT licence, see [LICENSE](LICENSE).

Built on [librosa](https://librosa.org/), [NumPy](https://numpy.org/), [SciPy](https://scipy.org/),
[soundfile](https://github.com/bastibe/python-soundfile), the
[Model Context Protocol](https://modelcontextprotocol.io/) Python SDK, [uv](https://docs.astral.sh/uv/)
and, of course, [REAPER](https://www.reaper.fm/) by Cockos. ReaCue is not affiliated with Cockos or
Anthropic.
