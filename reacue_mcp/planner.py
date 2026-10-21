"""Transforme une analyse en plan REAPER : position de l'item, tempo, régions, cues, click."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .analysis import Analysis
from .i18n import t, section_color


@dataclass
class Options:
    count_in_bars: int = 2          # mesures de click avant la 1re mesure du morceau
    tempo_mode: str = "auto"        # auto | constant | beatmap
    click: bool = True
    click_to_master: bool = True    # False pour un click uniquement dans les in-ears
    click_hw_output: int | None = None  # index de sortie physique (0 = 1/2, 2 = 3/4…)
    click_volume: float = 0.5
    cue_markers: bool = True        # marqueurs « → Refrain » avant chaque section
    cue_track: bool = True          # piste CUES avec items texte
    cue_lead_bars: int = 2          # annonce N mesures avant la section (2 = avant-dernière mesure)
    song_region: bool = False       # région englobant tout le morceau en plus
    voice_cues: bool = True         # appels vocaux « Refrain »… sur la piste VOIX
    voice_count_in: bool = True     # « un, deux, trois, quatre » sur la dernière mesure de count-in
    voice_count_each: bool = True   # idem sur la dernière mesure de chaque section (avant chaque changement)
    voice_name: str | None = None   # voix des annonces (macOS : Thomas… ; Windows : Microsoft Hortense…) ; None = auto
    voice_volume: float = 0.8
    count_lang: str = "en"          # langue du décompte : "en" (one two three four) ou "fr"
    count_voice: str | None = None  # voix du décompte ; None = auto (Samantha, Microsoft Zira…)
    count_rate: int = 240           # débit du décompte (mots/min), plus rapide = attaques plus franches
    count_anticipation_ms: float = 15.0  # le mot démarre un poil avant le temps (perception)


def build_plan(a: Analysis, item: dict, o: Options, render=None, render_count=None,
               items: list[dict] | None = None, voice_track: str = "VOIX") -> tuple[dict, dict]:
    """render(text) / render_count(text, max_len) -> chemin d'un fichier audio parlé, ou None.
    items : tous les items audio (stems) ; `item` est la référence, les autres sont déplacés du même delta.
    voice_track : nom de la piste des appels vocaux (VOIX en français, VOICE en anglais)."""
    m, den = a.beats_per_bar, a.denominator
    offset = float(item.get("offset", 0.0))
    rate = float(item.get("rate", 1.0) or 1.0)
    db = np.array(a.downbeats)               # temps du fichier source
    n = len(db) - 1
    mode = o.tempo_mode
    if mode == "auto":
        mode = "constant" if a.tempo_stable else "beatmap"

    warnings = list(a.warnings)
    if abs(rate - 1.0) > 1e-6:
        warnings.append(t("item_rate", rate=rate))
    db = (db - offset) / rate                # secondes depuis le début de l'item

    if mode == "constant":
        # droite de régression : minimise la dérive sur tout le morceau
        k = np.arange(n + 1)
        bar, anchor = np.polyfit(k, db, 1)
        bar = float(bar)
        song_start = float(anchor)
    else:
        bar = float(db[1] - db[0])
        song_start = float(db[0])

    pre = max(o.count_in_bars, math.ceil(max(0.0, song_start) / bar - 1e-6))
    t0 = pre * bar                           # timeline : début de la mesure 1
    item_pos = t0 - song_start

    if mode == "constant":
        bpm = 60.0 * m / bar * (den / 4)
        tempo = [{"time": 0.0, "bpm": round(bpm, 4), "num": m, "den": den}]
        def bar_time(k):
            return t0 + k * bar
    else:
        times = item_pos + db
        tempo = [{"time": 0.0, "bpm": round(60.0 * m / bar * (den / 4), 4), "num": m, "den": den}]
        for k in range(n):
            d = times[k + 1] - times[k]
            tempo.append({"time": round(float(times[k]), 6),
                          "bpm": round(60.0 * m / d * (den / 4), 4), "num": m, "den": den})
        def bar_time(k):
            return float(times[min(k, n)])

    song_end = bar_time(n)

    def tl(k):
        """Début de la mesure k sur la timeline (k < 0 : mesures de count-in / pré-roll)."""
        return bar_time(k) if k >= 0 else t0 + k * bar

    counting_in = o.voice_count_in and o.count_in_bars >= 1
    counting = counting_in or o.voice_count_each
    # avec un décompte sur la dernière mesure, l'annonce ne peut pas être sur cette même mesure
    lead_bars = max(o.cue_lead_bars, 2) if counting and render else max(1, o.cue_lead_bars)
    count_bars = set()
    if counting_in:
        count_bars.add(-1)
    if o.voice_count_each:
        count_bars.update(sec.start_bar - 1 for sec in a.sections if sec.start_bar > 0)
    announce_bar = {}
    for sec in a.sections:
        k = sec.start_bar - lead_bars
        while k in count_bars:          # section très courte : on recule l'annonce
            k -= 1
        announce_bar[id(sec)] = k
    regions, markers, cue_items = [], [], []
    for s in a.sections:
        col = list(section_color(s.name))
        regions.append({"start": round(bar_time(s.start_bar), 6), "end": round(bar_time(s.end_bar), 6),
                        "name": s.name, "color": col})
        cue_pos = max(tl(announce_bar[id(s)]), 0.0)
        cue_end = bar_time(s.start_bar)
        if o.cue_markers:
            markers.append({"pos": round(cue_pos, 6), "name": "→ " + s.name, "color": col})
        if o.cue_track and cue_end > cue_pos:
            cue_items.append({"pos": round(cue_pos, 6), "len": round(cue_end - cue_pos, 6),
                              "name": s.name, "color": col})
    if o.song_region:
        regions.insert(0, {"start": round(t0, 6), "end": round(song_end, 6),
                           "name": item.get("title") or t("song"), "color": [200, 200, 200]})
    click_start = t0 - o.count_in_bars * bar
    markers.insert(0, {"pos": round(click_start, 6), "name": "Count-in", "color": [255, 255, 255]})

    # appels vocaux --------------------------------------------------------
    voice_items = []
    if render and (o.voice_cues or counting):
        from .voice import COUNT_WORDS
        from .i18n import cue_text
        beat = bar / m
        words = COUNT_WORDS.get(o.count_lang, COUNT_WORDS["en"])
        rc = render_count or (lambda t, max_len=None: render(t))
        ahead = o.count_anticipation_ms / 1000.0
        for k in sorted(count_bars):
            for b in range(m):
                f = rc(words[b] if b < len(words) else str(b + 1), max_len=0.85 * beat)
                if f:
                    voice_items.append({"pos": round(max(0.0, tl(k) + b * beat - ahead), 6),
                                        "file": f, "name": f"count {b + 1}"})
        if o.voice_cues:
            for sec in a.sections:
                pos = tl(announce_bar[id(sec)])
                if pos < click_start - 1e-6:
                    warnings.append(t("no_room_cue", name=sec.name))
                    continue
                f = render(cue_text(sec.name))
                if f:
                    voice_items.append({"pos": round(pos, 6), "file": f, "name": sec.name})
        voice_items.sort(key=lambda v: v["pos"])

    plan = {"clear": True}
    if items:
        delta = item_pos - float(item.get("position", 0.0))
        plan["items"] = [{"guid": it["guid"], "position": round(float(it["position"]) + delta, 6)}
                         for it in items]
    else:
        plan["item"] = {"guid": item["guid"], "position": round(item_pos, 6)}
    plan.update({
        "tempo": tempo,
        "regions": regions,
        "markers": markers,
        "cues": {"enabled": o.cue_track, "track_name": "CUES", "items": cue_items},
        "click": {"enabled": o.click, "track_name": "CLICK", "volume": o.click_volume,
                  "to_master": o.click_to_master,
                  "hw_output": -1 if o.click_hw_output is None else o.click_hw_output,
                  "ranges": [[round(click_start, 6), round(song_end, 6)]]},
        # même routage que le click : les appels vont là où va le click (in-ears)
        "voice": {"enabled": bool(voice_items), "track_name": voice_track, "volume": o.voice_volume,
                  "to_master": o.click_to_master,
                  "hw_output": -1 if o.click_hw_output is None else o.click_hw_output,
                  "items": voice_items},
    })
    # pour le prompteur des musiciens (retiré du plan avant l'envoi à REAPER)
    plan["prompter"] = {
        "bpm": round(60.0 * m / bar * (den / 4), 3) if mode == "constant" else a.bpm,
        "tempo_mode": mode,
        "count_in_bars": o.count_in_bars,
        "bar_times": [round(tl(k), 4) for k in range(-o.count_in_bars, n + 1)],
    }
    summary = {
        "tempo_mode": mode,
        "bpm": round(60.0 * m / bar * (den / 4), 2) if mode == "constant" else a.bpm,
        "signature": f"{m}/{den}",
        "bars": n,
        "count_in_bars": o.count_in_bars,
        "item_position_s": round(item_pos, 3),
        "song_start_s": round(t0, 3),
        "song_end_s": round(song_end, 3),
        "tempo_markers": len(tempo),
        "announce_lead_bars": lead_bars,
        "count_bars": len(count_bars),
        "voice_calls": [{"at_s": v["pos"], "say": v["name"]} for v in voice_items
                        if not v["name"].startswith("count")],
        "sections": [{"#": i + 1, "name": s.name, "group": s.label,
                      "bars": f"{s.start_bar + 1}-{s.end_bar}", "length_bars": s.end_bar - s.start_bar,
                      "start_s": round(bar_time(s.start_bar), 2)} for i, s in enumerate(a.sections)],
        "warnings": warnings,
    }
    if items:
        summary["stems"] = len(items)
    if a.alt_bpm:
        summary["alt_bpm"] = a.alt_bpm
    return plan, summary
