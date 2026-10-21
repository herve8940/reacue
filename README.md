# ReaCue

**Live-ready songs in REAPER, in one click — and a prompter on every musician's phone.**

*[Version française : LISEZMOI.md](LISEZMOI.md)*

ReaCue is for bands that play live with REAPER. From the stems of a song (or a single MP3, which it can
split into stems itself, locally), it detects
the tempo, the bar grid and the structure, then builds everything in your REAPER project: tempo map,
named and coloured regions, a click with count-in, spoken cues (“Chorus”…) and a “one two three four”
count before each section. It also publishes a **web prompter** that each musician opens on their phone,
served by REAPER's built-in web interface: structure, chords (bass / guitars), timed lyrics (vocals) and a
dedicated drummer view with the transcribed grooves and fills.

Everything runs locally: no AI and no internet once installed. An optional mode lets you drive it in plain
language with Claude (MCP server).

> **New to ReaCue? Follow the step-by-step tutorial: [docs/TUTORIAL_en.md](docs/TUTORIAL_en.md)**
> (French: [docs/TUTORIEL_fr.md](docs/TUTORIEL_fr.md)).

> **Status: 0.12.0 beta.** Developed and used on macOS. Windows support is new and has **not yet been
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
- [Stem separation (optional)](#stem-separation-optional)
- [Usage](#usage)
- [Concert mode](#concert-mode)
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
- **Stem separation** (optional): turns a single MP3/WAV into 6 stems (vocals, drums, bass, guitar,
  piano, other) with [Demucs](https://github.com/facebookresearch/demucs), on your computer, no
  subscription and no upload — then ReaCue prepares the song from the stems.
- **Concert mode**: several prepared songs chained in one project, automatic stop at the end of each song,
  a *ReaCue - Concert* window to drive the show, a **QR code** for the musicians and a **Stage control**
  remote on a phone (PIN code); a **Check** button (pre-show check with one-click fixes) and a
  **Rehearsal** mode: loop a section or a range with a one-bar count-in before each repeat, 100–70 % speed.

On the musicians' phones and tablets (web prompter):

- current section, bar and beat, bars left, next section, count-down on the last bar;
- **Bass / guitars**: current and next chord with a count-down, chord chart of the section, key;
- **Vocals**: scrolling lyrics in time with the song, next line and count-down before each entry;
- **Drums**: groove of the section, 16-step grid of the current bar, fills, crashes, stops and re-entries;
- per-instrument entries and rests detected from the stems (“STOP next bar”, “Come in in 2 bars”);
- French / English, follows REAPER's play cursor (REAPER is the only thing that needs to run on stage);
- in concert mode: song x/N and the next song; **Stage control** role to drive the concert from a phone.

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
- About 1.5 GB of disk space (Python environment and libraries), plus about 1.5 GB for the optional stem
  separation.
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
4. Answer the questions: language (`fr` / `en`), whether to register ReaCue in Claude Desktop
   (optional, answer *no* if you don't use Claude) and whether to install **stem separation** (optional,
   about 1 GB to download, 5 to 15 minutes; see [Stem separation](#stem-separation-optional)).
5. Start REAPER. The bridge starts by itself and three actions are available in *Actions → Show action list*:
   - **ReaCue - Prepare the song**
   - **ReaCue - Republish the prompter**
   - **ReaCue - Separate stems** (works once stem separation is installed)

   Tip: add them to a toolbar (right-click a toolbar → *Customize toolbar* → *Add*).

The installer can be run again at any time (to change the language or repair an installation): your
settings and prepared songs are kept.

What it does: installs [uv](https://docs.astral.sh/uv/) (Astral's Python manager) if needed, creates a
private Python 3.12 environment in the `.venv` folder (pre-built packages only, no compiler needed), copies
the REAPER scripts into `<REAPER resources>/Scripts/ReaCue/`, adds the bridge to `Scripts/__startup.lua`,
registers the actions in `reaper-kb.ini` (only when REAPER is closed), and writes
`<REAPER resources>/ReaCueMCP/reacue_settings.json`. Nothing else in your system is modified.

If REAPER was open during installation, load the actions by hand once: *Actions → Show action list →
New action → Load ReaScript…* → pick `ReaCue_Preparer.lua`, `ReaCue_Republier_prompteur.lua` and
`ReaCue_Separer_stems.lua` in
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

## Stem separation (optional)

ReaCue works best with stems (one file per instrument). If you only have the MP3 of a song, ReaCue can split
it for you with [Demucs](https://github.com/facebookresearch/demucs) (Meta AI research, MIT licence), entirely
on your computer: nothing is uploaded, no subscription.

**Install** (once): answer *yes* to the stem separation question of the installer, or later double-click
**`Install ReaCue Stems.command`** (macOS) / **`Install ReaCue Stems.bat`** (Windows). It creates a separate
Python environment `.venv-demucs` in the ReaCue folder (PyTorch + Demucs, about 1 GB), downloads the two
models and measures the speed of your computer. ReaCue's own environment is not touched.

**Use**:

1. Drag the MP3 (or WAV) into an empty REAPER project and click it to select it.
2. Run **ReaCue - Separate stems**. A window shows the progress (you can close it).
3. At the end, six tracks appear (Vocals, Drums, Bass, Guitar, Piano, Other), exactly aligned with the
   original item, which is removed from the project (one *Undo* brings it back; the file stays on disk).
4. Run **ReaCue - Prepare the song** as usual.

Details:

- Duration: about **5 to 8 minutes for a 4-minute song** on a recent Intel Mac (4 cores), faster on Apple
  Silicon. The computer's processor does the work (no graphics card needed).
- The stems are written next to the original file, in `<song name>-stems/htdemucs_6s/`, and keep the
  original file name (key and tempo in the name are still read by ReaCue). Running the action again on the
  same file imports them immediately, without separating again.
- `stems_model` in the settings: `"htdemucs_6s"` (6 stems, default) or `"htdemucs"` (4 stems: vocals,
  drums, bass, other — guitar and keys stay together in “other”).
- Quality: vocals, drums and bass are very good; guitar and especially piano are less clean than with
  commercial services (some bleed). Lead and rhythm guitars are not separated, so the solo detection
  that relies on a lead-guitar stem is not available.
- Mac Intel: PyTorch stopped supporting Intel Macs after version 2.2.2; the installer pins the right
  versions automatically.

## Usage

1. **Import the song** into a REAPER project, one stem per track, all starting at the same time (drag and
   drop the files). A single MP3/WAV also works, with less detail — or split it first with
   **ReaCue - Separate stems** (see above).
   - The role of each stem is read from its **file name**: `drum`/`batterie`/`kick`/`perc`, `bass`/`basse`,
     `guitar`/`guitare`/`gtr` (`lead`/`solo` = lead guitar), `vocal`/`voice`/`vox`/`chant`/`voix`;
     anything else counts as keys/other.
   - Optional: key and tempo in the file names (e.g. `Demo Song-A minor-112bpm-drums.wav`) help the chords
     and the tempo octave.
2. Run **ReaCue - Prepare the song**. A small window shows the progress (from 20 s to about 1 min); you can
   close it, the result appears at the end: tempo, structure (bars and lengths), what was published.
3. Check the structure (regions) and play the song. To correct it, **edit the regions by hand in REAPER**
   (move, rename, add, delete), then run *Prepare* again: see [Correcting the structure](#correcting-the-structure).
   Running *Prepare* again on the same project **keeps the validated structure** (or takes your edited
   regions) and rebuilds everything (click, cues, prompter), applying the settings file if you changed it
   in the meantime.
4. After adding or editing a lyrics file, run **ReaCue - Republish the prompter** (nothing in the REAPER
   project is changed).

Each preparation **replaces** the regions, markers, tempo map and the CLICK / CUES / VOICE tracks of the
project (one *Undo* goes back). Use one project per song.

### Correcting the structure

Two ways, which can be mixed:

- **By hand in REAPER, then *Prepare*.** Double-click a region in the region lane (top of the
  window) to change its name or its start; add one with a time selection and *Markers → Insert region from
  time selection* (Shift+R); delete one with right-click → *Remove region*; or simply drag its edges, then run **ReaCue - Prepare the song**.
  When the song was already prepared (same audio items), ReaCue reads the project's regions and, if they
  differ from the saved structure, **adopts them as the new structure**; the final window then says
  “Structure taken from your REAPER regions”. Rules:
  - only the **start** of each region counts: a section lasts until the next region starts;
  - the start is moved to the nearest bar line (within a quarter of a bar it is silent; further away it
    is rounded with a warning);
  - names are kept as typed (French or English); the section type — colour, spoken cue, prompter role — is
    deduced from the name (“Chorus 2”, “Refrain”, “Solo”…);
  - regions before bar 1, after the end of the song, or on the same bar as another one are ignored with a
    warning; if no region starts on bar 1, the first bars are joined to the first region;
  - regions, colours, “→” markers, CUES, VOICE, CLICK and the prompter are then rebuilt.
  If no region was changed, nothing changes (structure kept). In another project (consolidated, other
  song), the regions are never read and nothing is modified.
- **With Claude** (optional mode, below): “chorus 1 starts at bar 37”, “rename section 6 to Solo”.

*Republish the prompter* does **not** take edited regions (the prompter must stay in line with the cues and
the click already in REAPER): it shows a warning asking you to run *Prepare*.

## Concert mode

Chain several songs that are **already prepared** (each in its own project) in one REAPER project, and
drive the whole show from one window or from a phone.

1. **Build the concert** — with Claude: *“concert “Saturday”: Demo Song, Second Demo, Third Demo”*
   (tool `build_concert`), or from the command line:
   `python -m reacue_mcp.cli concert --name "Saturday" --songs "Demo Song" "Second Demo"`
   (macOS/Linux, from the ReaCue folder with `.venv/bin/python`; Windows: `.venv\Scripts\python reacue_cli.py concert …`).
   Songs are found by project name in the projects folder (setting `projects_dir`, default
   `<Documents>/REAPER Media`) or given as `.RPP` paths. Nothing is re-analysed: each song keeps its stems,
   tempo map (fixed or one tempo per bar), validated structure, spoken cues and click.
2. **Open it** — REAPER action **ReaCue - Concert**: with no concert open, the window lists the concerts
   (folder: setting `concert_dir`, default `<projects folder>/Concerts`); one click opens it in a **new
   project tab** (your current project stays open).
3. **Play** — one project: one track per instrument shared by all songs (Vocals, Drums, Bass, Guitars…,
   one colour per song), CLICK / VOICE / CUES at the bottom, regions “Song · Chorus 1”, a “Songs” ruler
   lane with “1 · Demo Song” markers. Playback **stops by itself at the end of each song** and the cursor
   waits on the next song's count-in: press Space when the band is ready.

Files written next to each other: `<name>.RPP` (the concert), `<name>.setlist.json` (order, reusable),
`<name>.concert.lua` (song times, read by the window), `<name>.prompteur.json` (prompter for the whole
show). Edit a song in **its own project**, then *Rebuild the concert* (Setlist button): changes made
directly in the concert project are overwritten.

**The ReaCue - Concert window** (dockable: right-click) shows “2 / 6 · Song”, tempo, key, section,
“bar x / N”, a Playing / Paused / Stopped badge, song progress and time left, concert time and the next
song; big **Previous / Start / Play-Pause / Stop / Next** buttons (during playback Stop, Previous and Next
need a **double tap** within 2 s, to avoid accidents); the song's **sections** as coloured pills (click =
go there, playback continues); **Setlist**, **PIN** and **QR** buttons. Docked low, it shrinks to one line
(state + transport + QR). Extra actions *ReaCue - Next song* / *Previous song* for a pedal or a shortcut.
The automatic stop and the phone remote only work while this window is open (even docked).

**QR code for the musicians** — the QR button shows, large, the prompter address
`http://<this computer's IP>:<port>/prompteur.html`: the IP is computed when you click (macOS `ipconfig`,
Windows `ipconfig`, Linux `hostname -I`) and the port is read from REAPER's web interface settings
(`reaper.ini`). Musicians scan it with the phone camera (same Wi-Fi). QR encoder:
[luaqrcode](https://github.com/speedata/luaqrcode) (BSD licence).

**Stage control (phone remote)** — in the prompter, choose the role **Stage control**: Play/Pause, Stop,
Previous / Next, Start of song, clickable setlist and sections, with a ✓ when REAPER executed the command.
It asks once for the **4-digit PIN** shown in the Concert window (generated on first launch, changeable
with the PIN button, remembered on the phone). Commands go through REAPER's web interface
(`/_/SET/EXTSTATE/ReaCue/remote/…`) and are checked by the Concert window (PIN, replay protection).
⚠️ The PIN prevents mistakes, **not attacks**: anyone on the same network can reach REAPER's web interface
(`/_/…`) directly. Use a Wi-Fi reserved for the band at gigs.

**Check (pre-show check)** — the **Check** button of the Concert window lists, with a green / orange / red
dot: audio files readable (no “OFFLINE”), spoken cue files present, songs prepared (structure and tempo),
concert up to date (no song project changed since the concert was built — fingerprint stored at build
time), ReaCue bridge, REAPER web interface, network address, audio device running, click and cue outputs
(hardware outputs that exist, track not muted), prompter published, Stage control phones seen. A **Fix**
button appears when possible: set all media online, rebuild the concert, republish the prompter. Also
available with no concert open (system part only).

**Rehearsal mode** — the **Rehearsal** button (window or Stage control phone) turns the automatic stop off.
Tap a section to **loop** it; tap a second section of the same song to loop the whole range (e.g. Verse 2 →
Chorus 2). Before the loop starts and **before each repeat, one bar of count-in** is played with the click
and the spoken cues only (the other tracks are muted during that bar), at the tempo of that point of the
song. **Speed** 100 / 90 / 80 / 70 % (pitch preserved; click, cues and prompter follow). *Loop off* stops
looping; *Exit* (or leaving rehearsal from the phone) restores everything: speed 100 %, automatic stop,
REAPER's repeat and time selection as they were.

Step by step: [tutorial, concert chapter](docs/TUTORIAL_en.md#16-concert-mode-several-songs-in-one-project).

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
| `stems_model` | `"htdemucs_6s"` | stem separation model: `"htdemucs_6s"` (6 stems) or `"htdemucs"` (4 stems) |
| `projects_dir` | `null` | concert mode: folder searched for song projects by name; `null` = `<Documents>/REAPER Media` |
| `concert_dir` | `null` | concert mode: folder of the concerts; `null` = `<projects folder>/Concerts` |

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
- “I moved the regions in REAPER, take them.” → `prepare_song` (regions adopted, no re-analysis)

| Tool | Role |
|---|---|
| `reaper_status` | Are REAPER and the bridge answering? |
| `prepare_song` | Full preparation (optionally imports a file) |
| `analyze_audio` | Analysis only, without touching the project |
| `set_sections` / `rename_section` | Fix the structure; everything is rebuilt (names can be in English or French). `set_sections` **wins** over regions edited by hand; `rename_section` first takes them (numbers = current regions) |
| `set_grid` | Impose a fixed-tempo grid when the detection is wrong |
| `update_options` | Count-in, tempo mode, click, cues, voices… without re-analysing |
| `get_project_state`, `goto_section`, `transport` | Project state, navigation, play/stop |

Both modes share the same memory of the last prepared song: you can prepare with the button and fine-tune
with Claude, or the other way round.

Regions edited by hand in REAPER are taken by `prepare_song` (song already prepared; `reanalyse=true`,
`bpm_hint` or `beats_per_bar` force a full analysis instead), `update_options` and `rename_section`.
On an already prepared song whose regions were not edited, `prepare_song` still runs a new analysis (the
*Prepare* button keeps the structure instead).
`set_sections` and `set_grid` impose the structure they are given and replace those regions. Claude's
tools are loaded when a conversation starts: after updating ReaCue, start a new conversation.

## Known limitations

- **Structure detection is not perfect**: it depends on the song. Section boundaries are usually right
  within a bar; names (verse vs chorus, pre-chorus glued to the chorus…) need checking. Lengths that are not
  4, 8 or 16 bars are worth a look.
- **A single MP3 is less precise than stems**: no per-instrument entries/rests, no drum transcription,
  less reliable section names and chords. Use *Separate stems* first.
- **Stem separation**: guitar and piano stems have some bleed; separation takes several minutes per song
  on the processor (once per song: the result is kept).
- **Drums**: kick, snare and hi-hat are reliable; toms and ride are approximate. Fills are detected as
  bars that differ from the section's groove.
- **Chords**: triads, sevenths, sus and power chords; complex jazz voicings are simplified.
- Hand-edited regions: only their starts and names are read (not their ends); a full re-analysis of an
  already prepared song is only available through Claude (`reanalyse`) or the command line
  (`reacue_cli.py prepare --reanalyse`).
- Time signatures in x/4 only (4/4 and 3/4 detected).
- **Windows: beta, not yet tested on a real machine.** In particular the background launch from REAPER,
  the SAPI voices and paths with accents should be checked. Please report issues.
- Linux: not packaged (the code runs; spoken cues need `espeak-ng`).
- **Concert mode**: the automatic stop and the phone remote need the *ReaCue - Concert* window open;
  Previous / Next / Start stop playback and place the cursor (press Play again); *Rebuild* overwrites
  changes made directly in the concert project. The Stage control PIN is not a security barrier.
- **Rehearsal loop**: driven by the Concert window (not REAPER's own loop), so a repeat jumps back with
  REAPER's usual seek latency (a few milliseconds); the instrument tracks are muted during the count-in bar
  by the window (if REAPER quits during that bar, unmute them by hand). Speeds below 100 % use REAPER's
  playrate with pitch preservation (quality depends on the stretch mode of the project).
- **Check**: “concert up to date” compares each song project with the fingerprint taken when the concert
  was built — saving a song project without musical changes can still mark it as changed; offline media are
  detected from the file and its sample rate (REAPER does not expose the OFFLINE flag directly).

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

**The audio item shows “OFFLINE” in REAPER (macOS).** REAPER cannot read the file. This happens in
particular with files left in *Downloads*: macOS may deny REAPER access to that folder. Move or copy the file
into your project folder (for example `Documents/REAPER Media/<song>/`), then in REAPER right-click the item
→ *Item properties…* → *Choose new file*, or simply drag the file again. Alternatively, allow REAPER in
*System Settings → Privacy & Security → Files and Folders* and restart REAPER. *Separate stems* needs the
file to be readable too.

**“Stem separation is not installed.”** Double-click `Install ReaCue Stems.command` / `.bat` in the ReaCue
folder (internet needed once).

**The separation is slow / the progress stays at 0 %.** The first percent can take a minute (model
loading). Count 1.5 to 2 times the song length on an Intel Mac. Close other heavy applications. The log is
`<song name>-stems/demucs.log`, next to the original file.

**Concert: “No concert in this project”.** The current tab is not a concert. Undock the Concert window
(right-click) to see the list of concerts, or open `<concerts folder>/<name>.RPP` with *File → Open project*.
A song shows no sections in the concert: its project was saved before *Prepare* — prepare it, save it
(Cmd/Ctrl+S), then *Rebuild the concert*.

**Stage control: “Open the ReaCue - Concert window…”.** The phone talks to REAPER through that window:
open the *ReaCue - Concert* action on the computer. “Wrong PIN code”: type the code shown by the PIN
button of the window. The QR shows no address: the computer is not on a network.

**Where are the logs?** `<REAPER resources>/ReaCueMCP/cli.log` (preparation, concert) and
`<song name>-stems/demucs.log` (stem separation).

## Uninstall

Double-click **`Uninstall ReaCue.command`** (macOS) or **`Uninstall ReaCue.bat`** (Windows), with REAPER
closed. This removes the REAPER scripts, the bridge start-up line, the actions and the Claude Desktop entry.
Your settings and the last prepared song are kept in `<REAPER resources>/ReaCueMCP/` (add `--purge` to the
uninstall script to delete them; `--purge` also deletes the stem separation environment `.venv-demucs`). Then
delete the ReaCue folder. Demucs models are kept in PyTorch's cache (`~/.cache/torch/hub/checkpoints`, a few
hundred MB): delete that folder if you no longer need them. Separated stems stay next to your songs.

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
| `reaper/` | REAPER scripts: bridge and the actions (`ReaCue_stems.lua`: stem separation; `ReaCue_Concert.lua`, `ReaCue_concert_lib.lua`: concert window and Stage control; `ReaCue_qrcode.lua`: QR encoder, luaqrcode, BSD) |
| `reacue_stems.py`, `requirements-stems.txt` | Stem separation launcher (runs in `.venv-demucs`) and its pinned dependencies |
| `install/` | Installers (macOS, Windows) and the shared `reacue_setup.py` |
| `tests/` | pytest suite (fake REAPER bridge, Lua run through `lupa`, installer, prompter page) |
| `tools/` | **Development tools only** (not used by ReaCue): `concert_demo.py` (fictional demo projects for the concert tests), `struct_eval.py` (structure detection benchmark on your own songs, configured by a private JSON file), `asr_anchor.py` (lyrics timing file from speech recognition, heavy models, Linux), `make_screenshots.py` |

## Credits and licence

ReaCue by Hervé Naessens. MIT licence, see [LICENSE](LICENSE).

Stem separation by [Demucs](https://github.com/facebookresearch/demucs) (Alexandre Défossez, Meta AI, MIT
licence) on [PyTorch](https://pytorch.org/).

QR codes by [luaqrcode](https://github.com/speedata/luaqrcode) (Patrick Gundlach and contributors,
3-clause BSD licence; the licence header is kept in `reaper/ReaCue_qrcode.lua`).

Built on [librosa](https://librosa.org/), [NumPy](https://numpy.org/), [SciPy](https://scipy.org/),
[soundfile](https://github.com/bastibe/python-soundfile), the
[Model Context Protocol](https://modelcontextprotocol.io/) Python SDK, [uv](https://docs.astral.sh/uv/)
and, of course, [REAPER](https://www.reaper.fm/) by Cockos. ReaCue is not affiliated with Cockos or
Anthropic.
