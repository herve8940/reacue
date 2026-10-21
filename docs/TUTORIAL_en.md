# ReaCue tutorial — step by step

*[Version française : TUTORIEL_fr.md](TUTORIEL_fr.md)*

This tutorial takes you from installation to rehearsing with the band. It assumes you can start REAPER and
play a song, nothing more. Each step tells you **where to click**, **what you should see** and **what to do
if it does not work**.

At the end, for each song, you will have in REAPER:

- a tempo map locked to the song, named and coloured regions (Intro, Verse 1, Chorus…);
- a **CLICK** track with a 2-bar count-in, a **VOICE** track that says “Chorus” before each section and
  counts “one two three four”;
- a **prompter** on every musician's phone: structure, chords, lyrics, drums.

Time needed: 30 to 45 minutes the first time (installation included), then 5 to 10 minutes per song.

---

## Contents

1. [What you need](#1-what-you-need)
2. [Download ReaCue](#2-download-reacue)
3. [Get REAPER ready for the installation](#3-get-reaper-ready-for-the-installation)
4. [Run the installer](#4-run-the-installer)
5. [Check in REAPER](#5-check-in-reaper)
6. [Enable REAPER's web interface (once)](#6-enable-reapers-web-interface-once)
7. [Create a project for a song](#7-create-a-project-for-a-song)
8. [Import the audio: stems or a single MP3](#8-import-the-audio-stems-or-a-single-mp3)
9. [Split an MP3 into stems](#9-split-an-mp3-into-stems)
10. [Prepare the song](#10-prepare-the-song)
11. [Check the structure](#11-check-the-structure)
12. [Add the lyrics](#12-add-the-lyrics)
13. [Open the prompter on the phones](#13-open-the-prompter-on-the-phones)
14. [Set up the click, the spoken cues and the in-ears](#14-set-up-the-click-the-spoken-cues-and-the-in-ears)
15. [Link Claude Desktop (optional)](#15-link-claude-desktop-optional)
16. [At rehearsal](#16-at-rehearsal)
17. [Troubleshooting](#17-troubleshooting)
18. [Cheat sheet: a new song](#18-cheat-sheet-a-new-song)

---

## 1. What you need

| Item | Details |
|---|---|
| Computer | Mac (macOS 12 or later, Intel or Apple Silicon) or Windows 10/11 PC (Windows: beta) |
| REAPER | Version 7 or later, already installed ([reaper.fm](https://www.reaper.fm/)) |
| Disk space | 1.5 GB for ReaCue, + 1.5 GB if you install stem separation |
| Internet | Only during installation |
| Audio | The stems of a song (one file per instrument), **or** a single MP3/WAV |
| Phones | On the **same Wi-Fi** as the computer, with a browser (Safari, Chrome…) |

> Stems give the best results. If you only have the MP3, ReaCue can split it into stems on your computer
> (step 9).

---

## 2. Download ReaCue

1. On the project's GitHub page, click the green **Code** button, then **Download ZIP**.
2. Open the downloaded ZIP file: a `reacue-main` folder appears.
3. **Move this folder to its final place**, for example in *Documents*, and rename it `ReaCue`.

**You should see** in the `ReaCue` folder: `Install ReaCue.command`, `Install ReaCue.bat`,
`Install ReaCue Stems.command`, `Install ReaCue Stems.bat`, `README.md`, `LISEZMOI.md` and the folders
`reacue_mcp`, `reaper`, `install`, `docs`.

> ⚠️ Do not move this folder after installation. If you have to, run the installer again from the new place.

---

## 3. Get REAPER ready for the installation

1. **Start REAPER once**, then **quit it** (macOS: *REAPER → Quit REAPER*; Windows: *File → Quit*).

Why: on its first start REAPER creates its settings folder, and the installer can only register the ReaCue
actions while REAPER is **closed**.

---

## 4. Run the installer

### On a Mac

1. In the `ReaCue` folder, **double-click `Install ReaCue.command`**.
2. If macOS says it cannot be opened because it is from an unidentified developer: click **OK**, then
   **right-click** (or Ctrl-click) `Install ReaCue.command` → **Open** → **Open**.
   On recent macOS versions you may have to go to *System Settings → Privacy & Security*, scroll down and
   click **Open Anyway**.
3. A Terminal window opens.

### On Windows

1. In the `ReaCue` folder, **double-click `Install ReaCue.bat`**.
2. If Windows shows “Windows protected your PC” (SmartScreen): click **More info**, then **Run anyway**.
3. A black console window opens.

### The questions (Mac and Windows)

| Question | What to answer |
|---|---|
| `Langue / Language [fr/en]` | `en` then Enter |
| `Register ReaCue in Claude Desktop …? [y/N]` | `n` if you don't use Claude Desktop (you can do it later) |
| `Install stem separation …? [y/N]` | `y` if you have songs as MP3 only (about 1 GB to download, 5 to 15 minutes); otherwise `n` |

**You should see** 5 steps scroll by (`== 1/5 Checks` … `== 5/5 Stem separation`):

- at the end of step 4: a line `Likely IP address(es) of this computer: …` → **write this address down**
  (e.g. `192.168.1.20`), you will need it for the phones; then `Installation complete. Restart REAPER…`
  (ReaCue is installed);
- in step 5, if you answered `y`: PyTorch and Demucs being downloaded, two `model … ready` lines, two
  `speed … about N min for a 4-minute song` lines, then `Stem separation installed`.

Press Enter to close the window.

**If it does not work:**

| Message | Solution |
|---|---|
| `REAPER folder not found` | Start REAPER once, quit it, run the installer again |
| `could not install uv (internet?)` | Check the internet connection, run the installer again |
| `REAPER is running: the actions cannot be registered` | No problem: quit REAPER and run the installer again, or load the actions by hand (step 5) |
| `stem separation not installed` | The rest of ReaCue works. Try again later with `Install ReaCue Stems.command` / `.bat` |

> You can run the installer as many times as you like: it repairs the installation and keeps your settings.

---

## 5. Check in REAPER

1. Start REAPER.
2. Menu **Actions → Show action list…**
3. In the **Filter** box at the top, type `ReaCue`.

**You should see** three actions:

- `Custom: ReaCue - Prepare the song`
- `Custom: ReaCue - Republish the prompter`
- `Custom: ReaCue - Separate stems`

**Tip: toolbar buttons.** Right-click the main toolbar (top left) → **Customize toolbar…** → **Add…** →
filter `ReaCue` → pick the action → **Select/close**. Repeat for the other actions, then **Save**.

**If the actions are missing** (REAPER was open during installation):

1. In the action list, click **New action… → Load ReaScript…**
2. Go to the scripts folder: menu *Options → Show REAPER resource path in explorer/finder*, then
   `Scripts` → `ReaCue`.
3. Pick `ReaCue_Preparer.lua` → **Open**. Do the same with `ReaCue_Republier_prompteur.lua` and
   `ReaCue_Separer_stems.lua`.

---

## 6. Enable REAPER's web interface (once)

The phones' prompter goes through the small web server built into REAPER.

1. Mac: menu **REAPER → Settings…**; Windows: menu **Options → Preferences…**
2. In the list on the left, at the bottom: **Control/OSC/web**.
3. Click **Add**.
4. **Control surface mode**: choose **Web browser interface**.
5. **Port**: `8080` (keep this value if you can).
6. Leave everything else as is, click **OK**, then **OK** to close the preferences.

**To check:** on the computer, open a browser at `http://localhost:8080/`: a REAPER page should appear.

**If it does not work:** another program may be using port 8080 → start again with `8081` (and use that
port everywhere below). On Windows, if the firewall asks about REAPER, tick **Private networks** and click
**Allow**.

---

## 7. Create a project for a song

**One REAPER project per song.** ReaCue replaces the regions, the tempo map and the CLICK / CUES / VOICE
tracks every time it prepares a song: do not put several songs in the same project.

1. Create a folder for the song, for example `Documents/REAPER Media/Demo Song/`.
2. **Copy the song's audio files into it** (stems or MP3).
   > ⚠️ On a Mac, avoid leaving the files in *Downloads*: macOS may prevent REAPER from reading them (the
   > item then shows “OFFLINE”).
3. In REAPER: **File → New project**.
4. **File → Save project as…**, pick the song's folder, name the project (`Demo Song`) and tick **Copy all
   media into project directory** if the option is offered. **Save**.

---

## 8. Import the audio: stems or a single MP3

### Case A: you have the stems

1. Select all the stem files in the Finder / File Explorer.
2. **Drag them together** into REAPER's track area, at the very beginning (left).
3. If REAPER asks how to place several files, choose **“One per track”**.

**You should see** one track per stem, all items starting at the same place.

File names matter: ReaCue recognises the role of each stem from words in the name:

| Role | Words recognised in the file name |
|---|---|
| Drums | `drum`, `batterie`, `kick`, `perc` |
| Bass | `bass`, `basse` |
| Guitar | `guitar`, `guitare`, `gtr` (`lead` or `solo` = lead guitar) |
| Vocals | `vocal`, `voice`, `vox`, `chant`, `voix` |
| Other | anything else (keys…) |

> Bonus: the key and tempo in the name (e.g. `Demo Song-A minor-112bpm-drums.wav`) improve the chords and
> avoid double/half tempo mistakes.

Go straight to **step 10**.

### Case B: you only have an MP3 (or a WAV)

1. Drag the file into REAPER's track area, at the very beginning.

You can prepare the song right away (step 10), but with less detail (no drum view, no per-instrument
entries/rests, less reliable chords and sections). **Better: split it into stems first (step 9).**

---

## 9. Split an MP3 into stems

*Needs stem separation installed (answer `y` in step 4, or `Install ReaCue Stems`).*

1. **Click the MP3 item** in REAPER to select it (it becomes lighter).
2. Run **ReaCue - Separate stems** (toolbar button, or *Actions → Show action list…* → filter `ReaCue` →
   select the action → **Run**).
3. A **“Separating stems: N %”** window appears with a progress bar.
   - Count **5 to 8 minutes for a 4-minute song** on an Intel Mac, less on a recent Mac.
   - You can close this window and keep working: the import happens by itself at the end.
   - Do not quit REAPER during the separation.
4. At the end, a **“Stems imported”** message appears.

**You should see** six new tracks below the original track: **Vocals, Drums, Bass, Guitar, Piano, Other**,
aligned exactly like the MP3. The MP3 item was removed from the project (the file itself is still on disk;
*Edit → Undo* brings it back).

The stem files are stored next to the MP3, in `<song name>-stems/htdemucs_6s/`. If you run the action again
on the same MP3, the import is immediate (no new separation).

> Listen to the tracks solo (**S** button): vocals, drums and bass are usually very clean; guitar and piano
> may keep a bit of the other instruments. That is normal and good enough for ReaCue. An almost empty track
> (for example Piano in a song without keys) is not a problem.

**If it does not work:**

| Message | Solution |
|---|---|
| “Select the song's audio item” | Click the MP3 item, then run the action again |
| “Audio file not found… OFFLINE” | The file cannot be read: see [Troubleshooting](#17-troubleshooting) |
| “Stem separation is not installed” | Double-click `Install ReaCue Stems.command` / `.bat` in the ReaCue folder |
| “The separation failed” | Read the end of the log shown; the full log is `…-stems/demucs.log` |
| The window stays at 0 % for a while | Normal during the first minute (model loading) |

---

## 10. Prepare the song

1. Run **ReaCue - Prepare the song**. (No need to select anything.)
2. A **“Preparing the song”** window spins for about 20 seconds to 1 minute.
3. A result window appears: tempo, number of bars, **structure** (bars and length of each section), what
   was published for the prompter (chords, lyrics, drums).

**You should see** in the project:

- coloured **regions** at the top (Intro, Verse 1, Chorus 1…);
- **“→ Chorus”** markers before each section;
- three new tracks: **CUES**, **VOICE**, **CLICK**;
- the audio moved by 2 bars to make room for the count-in.

Press **Space**: you hear 2 bars of click with “one two three four”, then the song, the click and the cues.

> Save the project (**Cmd+S** / **Ctrl+S**).

**If it does not work:**

| Message | Solution |
|---|---|
| “The ReaCue bridge is not running in REAPER” | Restart REAPER; otherwise run the installer again (REAPER closed) |
| “ReaCue program not found” | The ReaCue folder was moved: run the installer again from its new place |
| “A preparation is already running” | Wait for the previous one to finish (1 minute max) |
| The tempo is double or half the real one | Put the tempo in the file names (e.g. `-94bpm`) and run *Prepare* again |

---

## 11. Check the structure

Read the structure in the result window and at the top of the project. Things to look at:

- **unusual lengths**: a section that is not 4, 8 or 16 bars long is often a mistake (two sections glued
  together, or one section cut in two);
- **the names**: verse and chorus can be swapped, a pre-chorus can be glued to the chorus;
- the ending: a long “Outro” may contain a last chorus or a solo.

Listen to the section starts: **click in the ruler** (the timeline at the top) at the beginning of a region to
put the cursor there, then **Space**.

**To fix it, two ways (you can mix them):**

**Way 1 — by hand in REAPER, then “Prepare”** (no Claude needed)

1. Fix the regions in the region lane (top of the window):
   - **rename** or **change the start**: double-click the region → change *Name* or *Start* → **OK**;
   - **move the start**: you can also drag the region's left edge;
   - **add**: make a time selection (drag in the ruler) starting where the new section starts, then menu
     *Markers → Insert region from time selection* (default shortcut Shift+R), and name it;
   - **delete**: right-click the region → *Remove region*.
2. Run **ReaCue - Prepare the song**.
3. The final window starts with **“Structure taken from your REAPER regions”**, with the new table. The
   regions are recoloured, and the “→” markers, the cues, the click and the prompter follow.

Good to know:

- only the **start** of each region counts: a section lasts until the next region starts (no need to fix
  the ends);
- a start placed between two bars is moved to the nearest bar line (a warning tells you if it was more than
  a quarter of a bar away);
- the name sets the colour and the cue: “Chorus 2” or “Refrain 2” makes a chorus, “Solo” a solo…;
- a region before bar 1, after the end of the song or on the same bar as another one is ignored (warning);
- if you changed nothing, *Prepare* keeps the saved structure, as before;
- *Republish the prompter* does not take edited regions: it shows a warning asking you to run *Prepare*.

**Way 2 — with Claude Desktop** (optional, see [step 15](#15-link-claude-desktop-optional))

Just say “chorus 1 starts at bar 37” or “rename section 6 to Solo”: everything is rebuilt (regions, click,
cues, prompter). What you tell Claude replaces regions edited by hand.

---

## 12. Add the lyrics

ReaCue never downloads lyrics: **you provide the text**.

1. Open a text editor:
   - Mac: **TextEdit**, then menu **Format → Make Plain Text** (important: plain text);
   - Windows: **Notepad**.
2. Type (or paste) the lyrics: **one line = one sung phrase**, an empty line between blocks (verse,
   chorus…). Lines like `[Chorus]` or `Verse 2:` are ignored. `(x2)` at the end of a line repeats it.
3. Save the file as **`lyrics.txt`** (**UTF-8** encoding), **in the stems folder**. For an MP3 split by
   ReaCue, you can put it **next to the original MP3** (or in the `…-stems/htdemucs_6s/` folder).
4. In REAPER, run **ReaCue - Republish the prompter** (nothing in the project is changed).

**You should see** in the final window: `Prompter published: … N lyric lines`. On the phone, in the
**Vocals** view, the lines scroll with the song.

The lines are aligned automatically on the vocal stem. If a line is off, you can place it by hand with a
timing file `lyrics_timing.json` (see the *Lyrics* section of the README).

---

## 13. Open the prompter on the phones

1. Connect the phone to the **same Wi-Fi** as the computer.
2. Find the computer's IP address (if you did not write it down in step 4):
   - Mac: *System Settings → Wi-Fi → Details…* (next to the connected network) → **IP address**;
   - Windows: *Settings → Network & Internet → Wi-Fi → network properties* → **IPv4 address**.
3. On the phone, open the browser and type: **`http://<IP address>:8080/prompteur.html`**
   (example: `http://192.168.1.20:8080/prompteur.html`). Careful: `http`, not `https`.
4. Pick your role: **Drums**, **Bass**, **Rhythm gtr**, **Lead gtr**, **Vocals** or **Overview** (the choice
   is remembered on this phone; the **Role** button changes it).
5. Start playback in REAPER: the prompter follows the position (section, bar, beat).

**You should see** a green dot (link with REAPER alive), the current section and the next one.

Tips:

- **Home screen**: iPhone: *Share → Add to Home Screen*; Android: menu **⋮ → Add to Home screen**. The page
  then opens full screen, like an app.
- **Screen sleep**: tap the **⛶** button (full screen), which asks the phone to stay awake. If the screen
  still turns off, disable auto-lock during rehearsal (iPhone: *Settings → Display & Brightness → Auto-Lock →
  Never*; Android: *Display → Screen timeout*).
- **Changing address**: the router may give the computer a different IP address from one day to the next,
  and the phones' bookmarks stop working. In your router's settings, look for **“DHCP reservation”** (or
  “static lease”, “fixed IP”) and reserve the current address for the computer. At gigs, a small travel
  router dedicated to the band avoids any surprise.
- The **FR/EN** button switches the prompter language on that phone.

---

## 14. Set up the click, the spoken cues and the in-ears

The settings are in the file **`reacue_settings.json`**, in REAPER's resource folder: menu *Options → Show
REAPER resource path in explorer/finder* → folder **`ReaCueMCP`**.

1. Open `reacue_settings.json` with TextEdit (Mac) or Notepad (Windows).
2. Change the values you want **keeping the syntax**: quotes around text, `true` / `false` / `null` without
   quotes, a comma after each line except the last one.
3. Save, then run **ReaCue - Prepare the song** again (the validated structure is kept).

Common examples:

| I want… | Setting |
|---|---|
| A single bar of count-in | `"count_in_bars": 1` |
| The count in French | `"count_lang": "fr"` |
| No spoken cues, only the click | `"voice_cues": false` |
| A louder click | `"click_volume": 0.8` |
| Click and voice only in the in-ears (outputs 3/4 of the audio interface), not front of house | `"click_hw_output": 2` and `"click_to_master": false` |
| 4 stems instead of 6 | `"stems_model": "htdemucs"` |

For `click_hw_output`: `0` = outputs 1/2, `2` = outputs 3/4, `4` = outputs 5/6, and so on.

For the cue voices (`announce_voice`), see the *Settings* section of the README.

---

## 15. Link Claude Desktop (optional)

All of ReaCue works without Claude. Linking [Claude Desktop](https://claude.ai/download) also lets you drive
ReaCue in plain English: fix the structure, change a setting, move around the song.

**Requirements**

- Claude Desktop installed on **the same computer** as REAPER and signed in to your Claude account (a paid
  plan may be needed depending on the offer: check the current terms on claude.ai);
- ReaCue installed (step 4) and REAPER open, with the bridge running.

**Link ReaCue to Claude Desktop**

1. If you answered `y` to “Register ReaCue in Claude Desktop” in step 4, it is already done. Otherwise
   **run the installer again** (`Install ReaCue.command` / `.bat`) and answer `y` to that question. The
   installer adds the `reacue` server to Claude Desktop's configuration (a backup of the previous
   configuration is kept).
2. **Quit Claude Desktop completely** and start it again (Mac: menu *Claude → Quit*, not just closing the
   window; Windows: right-click the Claude icon near the clock → *Quit*, if it is there).
3. **Start a new conversation.**

**Check that the ReaCue tools are there**

Depending on your version of Claude Desktop, the tools of linked servers are behind a tools icon or a
“connectors” / “tools” menu near the message box. You should see **reacue** with its tools (`prepare_song`,
`set_sections`, `reaper_status`…). The simplest test: type “check that REAPER is responding”. Claude uses
`reaper_status` (it may ask for permission the first time) and should answer that REAPER and the bridge are
connected.

**Example requests**

| You say | What happens |
|---|---|
| “Prepare the song open in REAPER” | New song: full analysis. Already prepared song whose regions you edited: your regions are taken. Already prepared song with no edit: **new analysis** (the validated structure is replaced) — to only rebuild, use the *Prepare* button instead |
| “Chorus 1 starts at bar 37” | Structure fixed, everything rebuilt |
| “Rename section 6 to Solo” | Region renamed, recoloured, cue changed |
| “Only republish the prompter” | Prompter updated, nothing changes in REAPER |
| “Go to chorus 2” | REAPER's cursor jumps to the start of the region |
| “Just one bar of count-in” | Setting changed, click and cues rebuilt |

**What updates by itself**: after each of these requests, the regions, markers, CUES / VOICE / CLICK tracks
in REAPER and the phones' prompter (which reloads its data every 2 seconds). Nothing to restart.

**If it does not work**

| Problem | Solution |
|---|---|
| reacue does not show in the tools | Run the installer again answering `y`, then quit Claude Desktop completely and start it again |
| Claude says REAPER is not responding | REAPER must be open; restart it to restart the bridge; a dialog left open in REAPER also blocks the bridge |
| ReaCue's new features are not visible | Tools are loaded when a conversation starts: after updating ReaCue, **start a new conversation** (and restart Claude Desktop) |
| “the project open in REAPER no longer contains the tracks of the last prepared song” | You switched projects (or consolidated): ask “prepare the song open in REAPER” to analyse it |

---

## 16. At rehearsal

- Open the song's project, put the cursor at the very beginning (**Home**), press **Space**.
- The musicians hear (or see on the prompter) the count-in, then the cues before each section.
- To restart at a section: **click in the ruler** at the start of its region, then **Space**. The prompter
  follows.
- To loop a part: click the region (region lane at the top) to select it, then turn repeat on (**R**, or
  the loop button of the transport).
- Only REAPER needs to run during rehearsal: ReaCue and Claude are not needed.

---

## 17. Troubleshooting

| Symptom | Likely cause | Solution |
|---|---|---|
| The item shows **OFFLINE** (Mac) | REAPER is not allowed to read the file, often in *Downloads* | Copy the file into the project folder, then drag it into REAPER again (or right-click the item → *Item properties…* → *Choose new file*). Alternatively: *System Settings → Privacy & Security → Files and Folders → REAPER*, enable the folder, restart REAPER |
| “The ReaCue bridge is not running” | The bridge did not start | Restart REAPER; a dialog left open in REAPER can also block it |
| The prompter says “REAPER is not responding” | Wrong Wi-Fi, wrong address, web interface not enabled, firewall | Check step 6 and step 13; try `http://localhost:8080/` on the computer |
| The phones cannot find the page any more | The computer's IP address changed | New address (step 13), then a DHCP reservation |
| No spoken cues | Voice missing | Mac: *System Settings → Accessibility → Spoken Content*; Windows: *Settings → Time & language → Speech* |
| Stem separation very slow | Busy processor | Close other applications; count 1.5 to 2 times the song length |
| Wrong structure | Automatic detection is not perfect | Step 11: edit the regions in REAPER then *Prepare*, or ask Claude; wrong tempo: tempo in the file names |
| Logs | — | Preparation: `ReaCueMCP/cli.log` (REAPER resource folder); separation: `…-stems/demucs.log` next to the song |

---

## 18. Cheat sheet: a new song

1. Song folder in `Documents/REAPER Media/`, audio files copied into it.
2. REAPER: *File → New project*, then *File → Save project as…* in that folder.
3. Drag the stems (one per track) **or** the MP3.
4. MP3 only: select the item → **ReaCue - Separate stems** (5 to 8 min).
5. **ReaCue - Prepare the song**.
6. Check the structure (unusual lengths, names); if needed fix the regions by hand and run *Prepare* again.
7. Optional: `lyrics.txt` next to the files → **ReaCue - Republish the prompter**.
8. Save the project (**Cmd+S** / **Ctrl+S**).
9. Phones: `http://<IP>:8080/prompteur.html`, pick your role.
