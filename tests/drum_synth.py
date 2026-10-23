"""Batterie synthétique pour les tests (aucun enregistrement réel) : sons de grosse caisse, caisse claire,
toms, charley fermé / ouvert, ride, crash, et partition par mesure.

score : liste de mesures, chacune {voie: [pas]} sur `steps` pas par mesure (voies de drums.LANES)."""
from __future__ import annotations

import numpy as np

SR = 44100


def sounds(sr: int = SR, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)

    def t(d):
        return np.arange(int(d * sr)) / sr

    def hp(x):                                   # aigu : double dérivée du bruit
        return np.diff(np.r_[0.0, np.diff(np.r_[0.0, x])])

    out = {}
    a = t(0.35)
    out["BD"] = np.sin(2 * np.pi * (50 + 90 * np.exp(-a * 30)) * a) * np.exp(-a * 9)
    a = t(0.25)
    out["SD"] = 0.5 * np.sin(2 * np.pi * 190 * a) * np.exp(-a * 25) + 0.6 * rng.standard_normal(len(a)) * np.exp(-a * 18)
    for lane, f in (("T1", 220.0), ("T2", 150.0), ("FT", 90.0)):
        a = t(0.45)
        out[lane] = (np.sin(2 * np.pi * f * (1 + 0.3 * np.exp(-a * 20)) * a) * np.exp(-a * 7)
                     + 0.15 * rng.standard_normal(len(a)) * np.exp(-a * 60))
    a = t(0.06)
    out["HH"] = hp(rng.standard_normal(len(a))) * 0.25 * np.exp(-a * 70)
    a = t(0.5)
    out["HO"] = hp(rng.standard_normal(len(a))) * 0.25 * np.exp(-a * 5)
    a = t(0.6)
    out["RD"] = (hp(rng.standard_normal(len(a))) * 0.12 * np.exp(-a * 6)
                 + 0.15 * np.sin(2 * np.pi * 3100 * a) * np.exp(-a * 8))
    a = t(2.0)
    out["CR"] = hp(rng.standard_normal(len(a))) * 0.35 * np.exp(-a * 1.8)
    return {k: v.astype(np.float32) for k, v in out.items()}


def render(score: list[dict], bpm: float = 120.0, beats_per_bar: int = 4, steps: int = 16, t0: float = 1.0,
           sr: int = SR, seed: int = 0):
    """Signal + grille (temps des mesures) d'une partition par mesure."""
    snd = sounds(sr, seed)
    bar = 60.0 / bpm * beats_per_bar
    n = int((t0 + bar * len(score) + 2.5) * sr)
    y = np.zeros(n, dtype=np.float32)
    for b, hits in enumerate(score):
        for lane, st in hits.items():
            for s in st:
                i = int((t0 + b * bar + s * bar / steps) * sr)
                seg = snd[lane][: n - i]
                y[i:i + len(seg)] += seg
    y = y / (np.abs(y).max() + 1e-9) * 0.8
    downbeats = [t0 + bar * k for k in range(len(score) + 1)]
    return y, downbeats


ROCK = {"HH": [0, 2, 4, 6, 8, 10, 12, 14], "BD": [0, 8, 10], "SD": [4, 12]}
RIDE = {"RD": [0, 2, 4, 6, 8, 10, 12, 14], "BD": [0, 6, 8], "SD": [4, 12]}
FILL = {"SD": [0, 2, 4, 6], "T1": [8, 9], "T2": [10, 11], "FT": [12, 13, 14, 15], "BD": [0]}


def demo_score() -> tuple[list[dict], list[tuple[int, int, str]]]:
    """Intro 4 (charley) / couplet 8 (charley, ouvert sur le « et » de 4) / refrain 8 (ride, crash au 1)
    avec un fill en fin de couplet et de refrain. Renvoie (partition, sections (début, fin, nom))."""
    sc = []
    sc += [dict(ROCK) for _ in range(4)]
    verse = [dict(ROCK) for _ in range(8)]
    for b in (1, 3, 5):
        verse[b] = {**ROCK, "HH": [0, 2, 4, 6, 8, 10, 12], "HO": [14]}
    verse[7] = dict(FILL)
    chorus = [dict(RIDE) for _ in range(8)]
    chorus[0] = {**RIDE, "RD": [2, 4, 6, 8, 10, 12, 14], "CR": [0]}
    chorus[7] = dict(FILL)
    sc += verse + chorus
    return sc, [(0, 4, "Intro"), (4, 12, "Couplet 1"), (12, 20, "Refrain 1")]
