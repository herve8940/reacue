"""Projets REAPER de démonstration pour le mode concert (tests et captures d'écran).

Tout est fictif : trois morceaux inventés (« Demo Song », « Second Demo », « Third Demo »), audio de
synthèse très court, projets .RPP écrits comme ReaCue les prépare (carte de tempo, régions, marqueurs
« → Section », pistes CUES / VOIX / CLICK). Aucun projet ni fichier audio réel.

    python tools/concert_demo.py <dossier>      # écrit les projets et l'audio dans <dossier>
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import numpy as np

SR = 8000

# (titre, tempo(s) par mesure ou constant, sections [(nom, mesures, couleur RVB)], instruments)
SONGS = [
    ("Demo Song", 120.0, [("Intro", 4, (120, 120, 120)), ("Verse 1", 8, (60, 120, 220)),
                          ("Chorus 1", 8, (220, 60, 60)), ("Outro", 4, (120, 120, 120))],
     ["Vocals", "Drums", "Bass", "Guitar"]),
    ("Second Demo", 150.0, [("Intro", 4, (120, 120, 120)), ("Couplet 1", 8, (60, 120, 220)),
                            ("Refrain 1", 8, (220, 60, 60)), ("Solo", 4, (240, 160, 48))],
     ["Vocals", "Drums", "Bass", "Lead Guitar"]),
    # tempo variable (joué sans click) : un marqueur par mesure
    ("Third Demo", [100.0 + (k % 5) for k in range(2 + 16 + 2)], [("Intro", 4, (120, 120, 120)),
                                                                  ("Verse 1", 8, (60, 120, 220)),
                                                                  ("Chorus 1", 4, (220, 60, 60))],
     ["mix"]),
]
COUNT_IN = 2


def g() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def native(rgb) -> int:
    r, gg, b = rgb
    return (r << 16 | gg << 8 | b) | 0x1000000


def bar_lines(tempo, n_bars: int) -> list[float]:
    out, t = [0.0], 0.0
    for k in range(n_bars):
        bpm = tempo[k] if isinstance(tempo, list) else tempo
        t += 60.0 / bpm * 4
        out.append(round(t, 6))
    return out


def _wav(path: Path, seconds: float, freq: float):
    import soundfile as sf
    t = np.arange(int(seconds * SR)) / SR
    y = (0.2 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sf.write(str(path), y, SR)


def write_song(folder: Path, title, tempo, sections, instruments, voice_track="VOIX") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    n_bars = COUNT_IN + sum(n for _, n, _ in sections)
    lines = bar_lines(tempo, n_bars + 2)
    song_end = lines[n_bars]
    audio_len = song_end + 1.0
    first_bpm = tempo[0] if isinstance(tempo, list) else tempo
    rpp = ['<REAPER_PROJECT 0.1 "7.0" 0 0', f"  TEMPO {first_bpm} 4 4 0", "  <TEMPOENVEX", "    ACT 0 -1"]
    if isinstance(tempo, list):
        for k, bpm in enumerate(tempo[:n_bars]):
            rpp.append(f"    PT {lines[k]:.6f} {bpm} 1" + (" 262148 0 1" if k == 0 else ""))
    else:
        rpp.append(f"    PT 0 {tempo} 1 262148 0 1")
    rpp.append("  >")
    # marqueurs : count-in, « → Section » une mesure avant, régions
    idx = 1
    rpp.append(f'  MARKER {idx} 0 Count-in 0 {native((255, 255, 255))} 1')
    k = COUNT_IN
    for name, n, col in sections:
        idx += 1
        rpp.append(f'  MARKER {idx} {lines[k - 1]:.6f} "→ {name}" 0 {native(col)} 1')
        k += n
    k = COUNT_IN
    for r, (name, n, col) in enumerate(sections, 1):
        rpp.append(f'  MARKER {r} {lines[k]:.6f} "{name}" 1 {native(col)} 1')
        rpp.append(f'  MARKER {r} {lines[k + n]:.6f} "" 1')
        k += n
    for i, inst in enumerate(instruments):
        f = folder / f"{title}-{inst}.wav"
        _wav(f, audio_len, 110.0 * (i + 1))
        rpp += [f"  <TRACK {g()}", f'    NAME "{title}-{inst}"', "    VOLPAN 1 0 -1 -1 1", "    MUTESOLO 0 0 0",
                "    <ITEM", "      POSITION 0", f"      LENGTH {audio_len:.6f}", "      SOFFS 0",
                "      PLAYRATE 1 1 0 -1 0 0.0025", f"      GUID {g()}", "      <SOURCE WAVE",
                f'        FILE "{f.name}"', "      >", "    >", "  >"]
    # pistes générées par ReaCue
    rpp += [f"  <TRACK {g()}", "    NAME CUES", "    <ITEM", "      POSITION 0", "      LENGTH 1",
            f"      GUID {g()}", "    >", "  >"]
    vf = folder / "count.wav"
    _wav(vf, 0.3, 880.0)
    rpp += [f"  <TRACK {g()}", f"    NAME {voice_track}", "    <ITEM", f"      POSITION {lines[1]:.6f}",
            "      LENGTH 0.3", f"      GUID {g()}", "      <SOURCE WAVE", f'        FILE "{vf}"', "      >",
            "    >", "  >"]
    rpp += [f"  <TRACK {g()}", "    NAME CLICK", "    <ITEM", "      POSITION 0", f"      LENGTH {song_end:.6f}",
            f"      GUID {g()}", "      <SOURCE CLICK", "      >", "    >", "  >", ">"]
    path = folder / f"{title}.RPP"
    path.write_text("\n".join(rpp) + "\n", encoding="utf-8")
    return path


def write_demo(root: Path, voice_track="VOIX") -> list[Path]:
    """Écrit les trois projets dans <root>/<titre>/ ; renvoie leurs chemins."""
    root = Path(root)
    return [write_song(root / title, title, tempo, secs, inst, voice_track) for title, tempo, secs, inst in SONGS]


if __name__ == "__main__":
    for p in write_demo(Path(sys.argv[1] if len(sys.argv) > 1 else "demo_projects")):
        print(p)
