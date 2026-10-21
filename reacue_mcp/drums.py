"""Transcription de la batterie par mesure pour le prompteur des musiciens (vue « batteur »).

Méthode (librosa / numpy uniquement, quelques secondes) :
  1. stem batterie (obligatoire : sur un mix, la transcription n'est pas fiable) placé dans le temps
     du stem de référence ; STFT fine (hop 128 à 22 050 Hz, ~6 ms) ;
  2. grille à la double-croche (16 pas par mesure en 4/4) ; décalage global attaque/grille estimé ;
     à chaque pas, « saut » d'énergie (dB, max après − niveau juste avant) par bande :
       grosse caisse 40-110 Hz, corps caisse claire/toms 120-450 Hz, timbre caisse claire 1,5-5 kHz,
       cymbales 7-11 kHz ;
  3. classement : BD = saut grave ; SD = saut médium + bruit aigu ; tom = saut médium-grave sans bruit
     (hauteur → T1/T2/FT) ; cymbale = saut 7-11 kHz, crash si la décroissance est lente et le coup fort,
     ride si la cymbale longue est jouée en continu, charley sinon ; seuils relatifs au niveau du stem ;
  4. motifs : distance entre mesures (BD/SD/toms comptent double des cymbales) ; groove d'une section =
     vote majoritaire des mesures proches de sa mesure médiane ; grooves identiques entre sections =
     même lettre ; mesure éloignée du groove de sa section (ou avec des toms) = fill.
"""
from __future__ import annotations

import re

import numpy as np

from .analysis import Analysis, SR, _place, assign_roles

VERSION = "drums-1"
LANES = ["CR", "HH", "RD", "SD", "T1", "T2", "FT", "BD"]
GM = {"BD": 36, "SD": 38, "HH": 42, "CR": 49, "RD": 51, "T1": 48, "T2": 45, "FT": 43}
H = 128                       # pas d'analyse (≈ 5,8 ms)
NFFT = 1024


def _drum_source(a: Analysis, items):
    """(fichier, décalage) du stem batterie, ou None."""
    if items:
        from .prompter import _shifts
        files = [d["file"] for d in items]
        sh = _shifts(items)
        for r, f in zip(assign_roles(files), files):
            if r == "drums":
                return f, sh[f]
        return None
    if a.stems and "drums" in a.stems:
        return a.stems["drums"], 0.0
    return None


def _band_db(P, fr, lo, hi):
    m = (fr >= lo) & (fr < hi)
    return 10 * np.log10(P[m].mean(0) + 1e-12)


def _features(y):
    import librosa
    P = np.abs(librosa.stft(y, n_fft=NFFT, hop_length=H)) ** 2
    fr = librosa.fft_frequencies(sr=SR, n_fft=NFFT)
    bands = {
        "bd": _band_db(P, fr, 40, 110),
        "body": _band_db(P, fr, 120, 450),
        "snr": _band_db(P, fr, 1500, 5000),
        "cym": _band_db(P, fr, 7000, 11000),
    }
    lowspec = P[(fr >= 60) & (fr < 500)]
    lowfr = fr[(fr >= 60) & (fr < 500)]
    broad = np.log10(P[(fr >= 40) & (fr < 11000)].sum(0) + 1e-12)
    return bands, lowspec, lowfr, broad


def _offset(broad, grid_t):
    """Décalage (s) entre attaques et grille : maximise le flux à large bande sur les pas."""
    flux = np.maximum(0, np.diff(broad, prepend=broad[0]))
    best, bo = -1, 0.0
    for lag in np.arange(-0.04, 0.0401, 0.002):
        idx = np.round((grid_t + lag) * SR / H).astype(int)
        idx = idx[(idx > 0) & (idx < len(flux))]
        v = flux[idx].sum()
        if v > best:
            best, bo = v, lag
    return bo


def _jump(e, i):
    """Saut (dB) au pas d'indice i : max de [i-3, i+5] − moyenne de [i-10, i-4] ; niveau atteint."""
    a0, a1 = max(0, i - 3), min(len(e), i + 6)
    b0, b1 = max(0, i - 10), max(1, i - 4)
    pk = e[a0:a1].max()
    return pk - e[b0:b1].mean(), pk, a0 + int(np.argmax(e[a0:a1]))


def transcribe(y, downbeats, steps=16, offset=None):
    """Coups par mesure : liste (n_bars) de {voie: {pas: force dB}} ; plus diagnostic."""
    bands, lowspec, lowfr, broad = _features(y)
    nb = len(downbeats) - 1
    db = np.asarray(downbeats, float)
    grid = np.concatenate([db[k] + (db[k + 1] - db[k]) * np.arange(steps) / steps for k in range(nb)])
    off = _offset(broad, grid) if offset is None else offset
    idx = np.round((grid + off) * SR / H).astype(int)
    n = len(bands["bd"])
    ref = {k: np.percentile(v, 99) for k, v in bands.items()}
    J = {k: np.zeros(len(idx)) for k in bands}
    L = {k: np.full(len(idx), -120.0) for k in bands}
    pki = np.zeros(len(idx), int)
    for j, i in enumerate(idx):
        if i < 12 or i >= n - 60:
            continue
        for k, e in bands.items():
            J[k][j], pk, p = _jump(e, i)
            L[k][j] = pk - ref[k]
            if k == "cym":
                pki[j] = p
    # cymbales : vraies attaques (montée sur ~35 ms), quantifiées au pas le plus proche — un crash
    # arrive souvent entre deux pas (frappe ample, retard du stem séparé)
    cym = bands["cym"]
    dly = int(0.18 * SR / H)
    lo = np.array([cym[max(0, t - 6):t + 1].min() for t in range(n)])
    rise = np.r_[cym[2:], cym[-1:], cym[-1:]] - lo
    from scipy.signal import find_peaks
    pk_, _ = find_peaks(rise, height=3.0, distance=max(1, int(0.045 * SR / H)))
    CY = {}                                   # indice de pas -> (niveau, montée, décroissance)
    t_step = grid + off
    for t in pk_:
        p = t + int(np.argmax(cym[t:t + 6]))
        lc, jc = cym[p] - ref["cym"], rise[t]
        dec = cym[min(n - 1, p + dly)] - cym[p]
        j = int(np.argmin(np.abs(t_step - t * H / SR)))
        if abs(t_step[j] - t * H / SR) > 0.6 * (grid[1] - grid[0]) or not ((jc > 6 and lc > -15) or (jc > 3 and lc > -6)):
            continue
        if j not in CY or CY[j][0] < lc:
            CY[j] = (lc, jc, dec)
    out = []
    for b in range(nb):
        bar = {}
        for s in range(steps):
            j = b * steps + s
            jb, js, jbody, jc = J["bd"][j], J["snr"][j], J["body"][j], J["cym"][j]
            lb, ls, lbody, lc = L["bd"][j], L["snr"][j], L["body"][j], L["cym"][j]
            is_bd = jb > 10 and lb > -12
            # caisse claire : corps ET timbre au niveau des coups les plus forts (la grosse caisse,
            # attaque claquante, a aussi du bruit aigu mais un corps 5-7 dB plus bas)
            is_sd = js > 5 and ls > -7 and jbody > 6 and lbody > -4
            # tom : corps médium-grave fort, sans timbre ni grave de grosse caisse
            is_tom = (not is_sd) and jbody > 7 and lbody > -7 and ls < -8 and lb < -10
            if is_bd:
                bar.setdefault("BD", {})[s] = round(float(lb), 1)
            if is_sd:
                bar.setdefault("SD", {})[s] = round(float(ls), 1)
            if is_tom:
                i = idx[j]
                spec = lowspec[:, i:i + 8].mean(1)
                f0 = float(lowfr[int(np.argmax(spec))])
                lane = "FT" if f0 < 110 else ("T2" if f0 < 170 else "T1")
                bar.setdefault(lane, {})[s] = round(float(lbody), 1)
            if j in CY:
                lc, jc, dec = CY[j]
                long_ = dec > -6
                if not (is_sd and not (long_ and lc > -4)):   # sinon : aigu de la caisse claire
                    if long_ and lc > -4 and jc > 6:
                        bar.setdefault("CR", {})[s] = round(float(lc), 1)
                    else:
                        bar.setdefault("CY", {})[s] = round(float(lc), 1)
                        bar.setdefault("_dec", {})[s] = round(float(dec), 1)
        out.append(bar)
    # crash du 1er temps : nappe aiguë tenue (300 ms) nettement au-dessus de la mesure précédente
    W3 = int(0.3 * SR / H)
    sus = np.array([cym[i:i + W3].mean() - ref["cym"] if i < n else -99 for i in idx]).reshape(nb, steps)
    q = max(1, steps // 4)
    for b in range(1, nb):
        bar = out[b]
        on = sorted(set(bar.get("CY", {})) | set(bar.get("CR", {})))
        first = [x for x in on if x < q]
        prev = np.median(sus[b - 1])
        if first and sus[b, :q].max() >= max(-10.0, prev + 4.0) and not any(x < q for x in bar.get("CR", {})):
            x = max(first, key=lambda k: bar.get("CY", {}).get(k, -99))
            bar.setdefault("CR", {})[x] = bar.get("CY", {}).pop(x, round(float(sus[b, x]), 1))
            bar.get("_dec", {}).pop(x, None)
    level = np.array([broad[idx[b * steps]:idx[min(len(idx) - 1, (b + 1) * steps - 1)] + 1].max()
                      if idx[b * steps] < n else -12 for b in range(nb)])
    return out, {"offset": off, "level": level}


def _cymbal_lanes(bars, steps=16, sections=None):
    """Flux de cymbale (charley / ride) : les coups cachés sous la caisse claire sont complétés si le
    flux est régulier (noires ou croches). Voie décidée par section (une voie stable pour le groove) :
    ride si le son tient (décroissance médiane lente), sinon charley. Le crash reste à part."""
    q = steps // 4
    lane_of = ["HH"] * len(bars)
    spans = [(s.start_bar, min(s.end_bar, len(bars))) for s in sections] if sections else [(0, len(bars))]
    for b0, b1 in spans:
        # médiane des médianes par mesure, sur les 3/4 de la section (la montée finale, pleine de
        # crashs, ne doit pas décider de la voie du groove)
        b2 = b0 + max(2, int(round(0.75 * (b1 - b0))))
        d = [np.median(list(bars[b]["_dec"].values())) for b in range(b0, min(b1, b2)) if bars[b].get("_dec")]
        lane = "RD" if (len(d) >= 2 and np.median(d) > -12) else "HH"
        for b in range(b0, b1):
            lane_of[b] = lane
    for k, bar in enumerate(bars):
        c = bar.pop("CY", {})
        bar.pop("_dec", None)
        if c:
            for p in (q, q // 2):
                if p < 1:
                    continue
                ph = min(c) % p
                on = [s for s in c if s % p == ph]
                slots = [s for s in range(ph, steps, p) if s not in bar.get("SD", {})]
                if len(on) >= 2 and len(on) >= 0.6 * max(1, len(slots)):
                    for s in range(ph, steps, p):
                        if s not in c and s in bar.get("SD", {}):
                            c[s] = float(np.median(list(c.values())))
                    break
            bar[lane_of[k]] = c
        if "CR" in bar:                           # crash et charley au même pas : on garde le crash
            for lane in ("HH", "RD"):
                for s in list(bar.get(lane, {})):
                    if s in bar["CR"]:
                        del bar[lane][s]
        for lane in list(bar):
            if not bar[lane]:
                del bar[lane]
    return bars


W = {"BD": 1.0, "SD": 1.0, "T1": 1.0, "T2": 1.0, "FT": 1.0, "HH": 0.5, "RD": 0.5, "CR": 0.0}


def _vec(bar):
    v = np.zeros((len(LANES), 16))
    for k, lane in enumerate(LANES):
        for s in bar.get(lane, {}):
            v[k, int(s)] = 1
    return v


_WV = np.array([W[l] for l in LANES])[:, None]
_CORE = np.array([1.0 if l in ("BD", "SD", "T1", "T2", "FT") else 0.0 for l in LANES])[:, None]


def _dist(u, v):
    """BD/SD/toms : 1 par écart ; cymbales : 0,5 (charley/ride confondus) + 0,4 si la voie diffère."""
    hh, rd = LANES.index("HH"), LANES.index("RD")
    d = (np.abs(u - v) * _WV).sum() - 0.5 * (np.abs(u[hh] - v[hh]).sum() + np.abs(u[rd] - v[rd]).sum())
    cu, cv = np.maximum(u[hh], u[rd]), np.maximum(v[hh], v[rd])
    return d + 0.5 * np.abs(cu - cv).sum() + 0.4 * (np.abs(u[hh] - v[hh]).sum() + np.abs(u[rd] - v[rd]).sum())


def _hits(bar):
    return {l: sorted(int(s) for s in bar[l]) for l in LANES if bar.get(l)}


def group(bars, sections, n_bars, rest, steps=16, near=2.5, fill_d=4.0):
    """Motifs, grooves de section, fills."""
    V = [_vec(b) for b in bars]
    patterns, pvec, order = {}, [], []
    sec_of = [None] * n_bars
    for si, s in enumerate(sections):
        for b in range(s.start_bar, min(s.end_bar, n_bars)):
            sec_of[b] = si
    sec_groove = {}
    for si, s in enumerate(sections):
        play = [b for b in range(s.start_bar, min(s.end_bar, n_bars)) if not rest[b]]
        if len(play) < 2:
            continue
        D = np.array([[_dist(V[i], V[j]) for j in play] for i in play])
        med = play[int(np.argmin(np.median(D, 1)))]
        close = [b for b in play if _dist(V[b], V[med]) <= near + 1]
        if len(close) < max(2, len(play) // 3):
            continue
        frac = np.mean([V[b] for b in close], 0)
        g = (frac > 0.5).astype(float)
        g[LANES.index("CR")] = 0
        # même groove qu'un motif déjà vu ?
        best = None
        if pvec:
            # même groove : mêmes grosse caisse / caisse claire (à 2 coups près) et même voie de cymbale
            def lane_(u):
                h, r = u[LANES.index("HH")].sum(), u[LANES.index("RD")].sum()
                return "RD" if r > h else ("HH" if h else None)
            dd = [float((np.abs(g - pv) * _CORE).sum()) if lane_(g) == lane_(pv) else 99 for pv in pvec]
            if min(dd) <= 2:
                best = int(np.argmin(dd))
        if best is None:
            name = chr(ord("A") + len(pvec))
            pvec.append(g)
            order.append(name)
            acc = {}
            for lane in ("HH", "RD", "SD", "BD"):
                li = LANES.index(lane)
                st = [int(x) for x in np.nonzero(g[li])[0]]
                if lane in ("HH", "RD") and len(st) >= 3:
                    lv = {x: np.median([bars[b][lane][x] for b in close if x in bars[b].get(lane, {})]) for x in st}
                    m = np.median(list(lv.values()))
                    a_ = [x for x in st if lv[x] > m + 3]
                    if a_:
                        acc[lane] = a_
            patterns[name] = {"name": f"Groove {name} — {s.name}", "sections": [s.name],
                              "hits": {l: [int(x) for x in np.nonzero(g[LANES.index(l)])[0]]
                                       for l in LANES if g[LANES.index(l)].any()},
                              "accents": acc}
            best = len(pvec) - 1
        else:
            patterns[order[best]]["sections"].append(s.name)
        sec_groove[si] = best
    # chaque groove est revoté sur toutes les mesures des sections qui l'utilisent (proches au cœur)
    for k, name in enumerate(order):
        mem = [b for b in range(n_bars) if not rest[b] and sec_of[b] is not None
               and sec_groove.get(sec_of[b]) == k and float((np.abs(V[b] - pvec[k]) * _CORE).sum()) <= 2]
        if len(mem) >= 4:
            g = (np.mean([V[b] for b in mem], 0) > 0.5).astype(float)
            g[LANES.index("CR")] = 0
            pvec[k] = g
            patterns[name]["hits"] = {l: [int(x) for x in np.nonzero(g[LANES.index(l)])[0]]
                                      for l in LANES if g[LANES.index(l)].any()}
            for lane in list(patterns[name]["accents"]):
                patterns[name]["accents"][lane] = [x for x in patterns[name]["accents"][lane]
                                                   if x in patterns[name]["hits"].get(lane, [])]
    out = []
    for b in range(n_bars):
        if rest[b]:
            out.append({"bar": b + 1, "pattern": None, "rest": True})
            continue
        bar = bars[b]
        ds = [_dist(V[b], pv) for pv in pvec]
        si = sec_of[b]
        own = sec_groove.get(si)
        toms = sum(len(bar.get(l, {})) for l in ("T1", "T2", "FT"))
        ref_d = ds[own] if own is not None else (min(ds) if ds else 99)
        # fill : des coups de caisse claire / toms en plus du groove, ou une mesure très différente
        # (une variation de grosse caisse ou de charley seule n'est pas un fill)
        extra = 0
        if own is not None:
            g = pvec[own]
            for lane in ("SD", "T1", "T2", "FT"):
                li = LANES.index(lane)
                extra += int(((V[b][li] > 0) & (g[li] == 0)).sum())
        core_d = float((np.abs(V[b] - pvec[own]) * _CORE).sum()) if own is not None else 0.0
        fill = bool(toms >= 2 or extra >= 2 or core_d >= fill_d)
        # groove de la section d'abord (variations tolérées), sinon le motif le plus proche
        pat = None
        if not fill:
            core = lambda u, v: float((np.abs(u - v) * _CORE).sum())
            if own is not None and (ref_d <= near + 0.5 or core(V[b], pvec[own]) <= 2):
                pat = order[own]
            elif ds and min(ds) <= near:
                pat = order[int(np.argmin(ds))]
            else:
                fill = True                   # passage nettement différent du groove de la section
        e = {"bar": b + 1, "pattern": pat, "fill": fill, "crash": any(x < steps // 4 for x in bar.get("CR", {})),
             "hits": _hits(bar)}
        out.append(e)
    return patterns, out


def detect_drums(a: Analysis, items=None) -> dict:
    """Transcription de la batterie (format du prompteur, cf. module) ; ValueError sans stem batterie."""
    import librosa
    src = _drum_source(a, items)
    if src is None:
        from .i18n import t as _t
        raise ValueError(_t("no_drum_stem"))
    f, shift = src
    y = librosa.load(f, sr=SR, mono=True)[0]
    n = max(len(y) + max(0, int(round(shift * SR))), int((a.downbeats[-1] + 1.0) * SR))
    y = _place(y, shift, SR, n)
    if a.beats_per_bar == 4 and a.denominator in (4, None):
        steps = 16
    else:
        steps = 4 * int(a.beats_per_bar) if a.denominator == 4 else 2 * int(a.beats_per_bar)
    n_bars = a.n_bars
    bars, diag = transcribe(y, a.downbeats[:n_bars + 1], steps)
    bars = _cymbal_lanes(bars, steps, a.sections)
    lvl = diag["level"]
    loud = np.percentile(lvl, 90)
    rest = [bool(lvl[b] < loud - 2.5 or not any(bars[b].values())) for b in range(n_bars)]
    # au moins 3 coups pour parler de batterie (repisse / baguettes isolées)
    rest = [r or sum(len(v) for v in bars[b].values()) < 3 for b, r in enumerate(rest)]
    patterns, out = group(bars, a.sections, n_bars, rest, steps)
    used = [l for l in LANES if any(l in e.get("hits", {}) for e in out)
            or any(l in p["hits"] for p in patterns.values())]
    for k, p in patterns.items():                 # nom lisible : les types de section qui l'utilisent
        ts = []
        for nm in p.pop("sections", []):
            t = re.sub(r"\s*\d+$", "", nm).strip().lower()
            if t not in ts:
                ts.append(t)
        p["name"] = f"Groove {k} — " + " / ".join(ts)
    return {"steps": steps, "lanes": used, "patterns": patterns, "bars": out,
            "offset_ms": round(diag["offset"] * 1000, 1), "version": VERSION}


def drums_cache_key(a: Analysis, items) -> str:
    import hashlib
    import json
    src = _drum_source(a, items)
    return hashlib.md5(json.dumps([src and src[0], src and round(src[1], 4),
                                   [round(float(x), 4) for x in a.downbeats], a.beats_per_bar,
                                   [(s.start_bar, s.end_bar, s.name) for s in a.sections],
                                   VERSION]).encode()).hexdigest()


def cached_drums(a: Analysis, items=None, cache=None) -> dict:
    """detect_drums avec cache disque (un seul morceau mémorisé, comme cached_chords)."""
    import json
    from pathlib import Path
    if cache is None:
        from .bridge import BRIDGE_DIR
        cache = BRIDGE_DIR / "prompter_drums.json"
    cache = Path(cache)
    ck = drums_cache_key(a, items)
    try:
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("key") == ck:
            return c["drums"]
    except Exception:
        pass
    res = detect_drums(a, items)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": ck, "drums": res}), encoding="utf-8")
    except OSError:
        pass
    return res


# --------------------------------------------------------------------------- #
# Export MIDI (fichier type 0, canal 10, notes GM), sans dépendance
# --------------------------------------------------------------------------- #
def _vlq(v: int) -> bytes:
    b = [v & 0x7F]
    v >>= 7
    while v:
        b.append((v & 0x7F) | 0x80)
        v >>= 7
    return bytes(reversed(b))


def drums_to_midi(d: dict, bpm: float, path, beats_per_bar: int = 4, ppq: int = 480) -> str:
    steps = int(d.get("steps", 16))
    tps = ppq * beats_per_bar // steps           # ticks par pas
    ev = []
    for e in d["bars"]:
        base = (int(e["bar"]) - 1) * steps * tps
        for lane, st in (e.get("hits") or {}).items():
            for s in st:
                t = base + int(s) * tps
                vel = 110 if (lane == "CR" or (lane in ("HH", "RD") and s % (steps // beats_per_bar) == 0)) else 90
                ev.append((t, 1, GM[lane], vel))
                ev.append((t + max(1, tps // 2), 0, GM[lane], 0))
    ev.sort(key=lambda x: (x[0], x[1]))
    tempo = int(round(60_000_000 / bpm))
    trk = bytearray(b"\x00\xff\x51\x03" + tempo.to_bytes(3, "big"))
    trk += b"\x00\xff\x58\x04" + bytes([beats_per_bar, 2, 24, 8])
    last = 0
    for t, on, note, vel in ev:
        trk += _vlq(t - last) + bytes([0x99 if on else 0x89, note, vel])
        last = t
    trk += b"\x00\xff\x2f\x00"
    data = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") \
        + ppq.to_bytes(2, "big") + b"MTrk" + len(trk).to_bytes(4, "big") + bytes(trk)
    with open(path, "wb") as fh:
        fh.write(data)
    return str(path)
