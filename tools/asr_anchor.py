#!/usr/bin/env python3
"""Ancres exactes des paroles (paroles_calage.json) par reconnaissance vocale.

OUTIL DE DÉVELOPPEMENT (facultatif, non utilisé par ReaCue) : lourd (modèles de ~1,3 Go), prévu pour
une machine Linux ; le JSON produit est ensuite copié à côté du fichier de paroles. ReaCue ne télécharge
jamais de paroles : l'utilisateur fournit son propre fichier.

Produit, pour un morceau, le fichier d'ancres lu par reacue_mcp/lyrics.py : début et fin de CHAQUE
occurrence chantée de chaque ligne (refrains répétés compris), en mesure:temps. Le fichier ne
contient aucun texte. Le script n'imprime jamais de paroles ni de mots reconnus (index, temps, scores).

Prérequis (Linux) :
  pip install --break-system-packages sherpa-onnx librosa soundfile
  pip install --break-system-packages onnxruntime
  modèles (GitHub releases de sherpa-onnx, ~490 Mo + ~850 Mo) :
    R=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
    curl -L $R/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2 | tar xj
    curl -L $R/sherpa-onnx-omnilingual-asr-1600-languages-1B-ctc-int8-2025-11-12.tar.bz2 | tar xj
  (Parakeet TDT 0.6B v3 : reconnaissance multilingue horodatée ; Omnilingual ASR CTC 1B : alignement
   forcé caractère par caractère.) Dossier des modèles : --model-dir / --ctc-model-dir, ou variable
   REACUE_ASR_MODELS (défaut : ./models).
  Durée : ~3 min de reconnaissance + ~2,5 min de log-probas CTC (2 cœurs), puis quelques secondes.

Usage :
  python3 asr_anchor.py --voice stem_voix.wav --lyrics parole.rtf --bpm 187.9885 --bar1 0.4117 \
      --out paroles_calage.json [--bpb 4] [--model-dir …] [--ctc-model-dir …] [--cache préfixe]
      [--report rapport.json]
  --bar1 : temps (s) de la mesure 1 DANS le fichier voix (= position du marqueur de la mesure 1 sur
           la timeline − position de l'item voix). Tempo constant supposé.

Méthode :
  1. Parakeet TDT v3 (sherpa-onnx), 9 passes (découpages 4 à 20 s, fenêtres glissantes) : mots
     reconnus horodatés (trames de 80 ms) ;
  2. par passe, programmation dynamique mots reconnus ↔ mots des lignes (normalisés, phonétique
     grossière) ; après une ligne : la suivante (gratuit), une ligne antérieure (refrain rejoué) ou
     plus loin (pénalités) ; mots hors paroles = déchets ;
  3. vote entre passes -> occurrences (ligne, placement grossier) ; mots isolés après > 2 s exclus ;
  4. chant resté libre : la ligne dont l'alignement forcé CTC est le meilleur (refrain manqué) ;
     lignes jamais trouvées : posées sur le chant libre entre leurs voisines (« devinées ») ;
  5. alignement forcé CTC conjoint (Omnilingual ASR 1B, trames de 20 ms) de toutes les occurrences
     dans l'ordre, chacune confinée à ± 1,5 s de son placement grossier ;
  6. affinage sur le stem voix : début = dernière montée de niveau / respiration dans
     [CTC − 0,4 s, CTC + 0,05 s] (le CTC émet le 1er caractère en retard), fin = chute du niveau ;
  7. occurrences d'un même texte sur la même mélodie (refrains) : un début ou une fin aberrant(e)
     (> 0,15 s de la médiane, les autres concordant) est remplacé(e) par la médiane.
  Précision constatée sur un morceau de test : refrains répétés concordants à ± 0,05–0,1 s.

Format écrit (voir lyrics.read_anchors) : {"_format": "reacue-calage-2", "1": "18:4.37-22:2.10",
"7#2": "80:1.37-84:1.55", …} : clé = ligne 1-based [#occurrence], valeur = début[-fin] en
mesure:temps (temps 1-based, décimal).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reacue_mcp import lyrics as ly                     # noqa: E402

MODELS = Path(os.environ.get("REACUE_ASR_MODELS", "models"))
DEFAULT_MODEL = str(MODELS / "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")
PASSES = (("seg", 4), ("seg", 6), ("seg", 8), ("seg", 12), ("seg", 20),
          ("slide", 6, 0.0), ("slide", 6, 1.5), ("slide", 10, 0.0), ("slide", 10, 2.5))


# --------------------------------------------------------------------------- #
# Reconnaissance
# --------------------------------------------------------------------------- #
def _recognizer(md):
    import sherpa_onnx
    md = Path(md)
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(md / "encoder.int8.onnx"), decoder=str(md / "decoder.int8.onnx"),
        joiner=str(md / "joiner.int8.onnx"), tokens=str(md / "tokens.txt"),
        model_type="nemo_transducer", num_threads=os.cpu_count() or 2)


def _decode(rec, y, sr, a, b):
    st = rec.create_stream()
    st.accept_waveform(sr, y[a:b])
    rec.decode_stream(st)
    r = st.result
    du = list(r.durations) if len(getattr(r, "durations", []) or []) else [0.08] * len(r.tokens)
    return list(r.tokens), [a / sr + t for t in r.timestamps], du


def run_pass(rec, y, sr, spec):
    """Une passe -> liste de jetons [(jeton, début s, durée s)]."""
    toks = []
    if spec[0] == "seg":
        maxf = int(spec[1] * 100)
        import librosa
        hop = sr // 100
        rms = librosa.feature.rms(y=y, frame_length=4 * hop, hop_length=hop)[0]
        db = 20 * np.log10(rms + 1e-9)
        act = db > np.percentile(db, 90) - 25
        segs, i, n = [], 0, len(act)
        while i < n:
            if act[i]:
                j = i
                while j < n and act[j]:
                    j += 1
                if segs and i - segs[-1][1] < 120:
                    segs[-1][1] = j
                else:
                    segs.append([i, j])
                i = j
            else:
                i += 1
        fin = []

        def split(s, e):
            if e - s <= maxf:
                fin.append((s, e))
                return
            m = s + maxf // 3 + int(np.argmin(db[s + maxf // 3:e - maxf // 3]))
            split(s, m)
            split(m, e)
        for s, e in segs:
            if e - s > 15:
                split(s, e)
        for s, e in fin:
            a, b = max(0, s * hop - int(0.4 * sr)), min(len(y), e * hop + int(0.4 * sr))
            tk, ts, du = _decode(rec, y, sr, a, b)
            toks += list(zip(tk, ts, du))
    else:
        win, off = spec[1], spec[2]
        hop = win / 2
        t = off
        while t < len(y) / sr:
            a, b = int(max(0, t - hop / 2) * sr), int(min(len(y) / sr, t + win) * sr)
            if b - a > sr // 2 and np.sqrt(np.mean(y[a:b] ** 2)) > 1e-3:
                tk, ts, du = _decode(rec, y, sr, a, b)
                words = []
                for x in zip(tk, ts, du):
                    if x[0].startswith(" ") or not words:
                        words.append([x])
                    else:
                        words[-1].append(x)
                for w in words:
                    if t <= w[0][1] < t + hop:
                        w[0] = (" " + w[0][0].lstrip(),) + w[0][1:]
                        toks += w
            t += hop
    return toks


def transcribe(voice, model_dir, cache=None):
    """Passes de reconnaissance (mises en cache : contient des mots, ne jamais l'afficher)."""
    if cache and Path(cache).exists():
        c = json.loads(Path(cache).read_text(encoding="utf-8"))
        if c.get("voice") == str(voice) and len(c.get("passes", [])) == len(PASSES):
            return c["passes"]
    import librosa
    sr = 16000
    y = librosa.load(str(voice), sr=sr, mono=True)[0]
    rec = _recognizer(model_dir)
    passes = [run_pass(rec, y, sr, spec) for spec in PASSES]
    if cache:
        Path(cache).write_text(json.dumps({"voice": str(voice), "passes": passes}, ensure_ascii=False),
                               encoding="utf-8")
    return passes


# --------------------------------------------------------------------------- #
# Mots
# --------------------------------------------------------------------------- #
_PHON = (("eaux", "o"), ("eau", "o"), ("aux", "o"), ("au", "o"), ("ph", "f"), ("qu", "k"),
         ("c(?=[eiy])", "s"), ("c", "k"), ("ai", "e"), ("ei", "e"), ("er$", "e"), ("ez$", "e"),
         ("et$", "e"), ("h", ""), ("y", "i"), (r"(.)\1", r"\1"))


def simp(w: str) -> str:
    """Forme simplifiée (minuscules, sans accents, phonétique grossière, finales muettes)."""
    w = unicodedata.normalize("NFD", w.lower())
    w = re.sub(r"[^a-z]", "", "".join(c for c in w if not unicodedata.combining(c)))
    for a, b in _PHON:
        w = re.sub(a, b, w)
    w = re.sub(r"(?<=.)[stxdp]+$", "", w)
    if len(w) > 2:
        w = re.sub(r"e$", "", w)
    return w or "_"


def line_words(text: str) -> list[str]:
    return [simp(p) for w in re.findall(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", text.lower())
            for p in re.split(r"['’\-]", w) if p]


def asr_words(toks) -> list[dict]:
    W, cur = [], None
    for t, s, d in toks:
        if t.startswith(" ") or cur is None:
            if cur:
                W.append(cur)
            cur = {"w": t.strip(), "t": s, "e": s + max(d, 0.04)}
        else:
            cur["w"] += t
            cur["e"] = s + max(d, 0.04)
    if cur:
        W.append(cur)
    out = []
    for x in sorted(W, key=lambda x: x["t"]):
        parts = [p for p in re.split(r"['’\-]", x["w"]) if re.search(r"[^\W\d_]", p)]
        L = x["e"] - x["t"]
        for k, p in enumerate(parts):
            out.append({"s": simp(p), "t": x["t"] + L * k / len(parts), "e": x["t"] + L * (k + 1) / len(parts)})
    return out


def sim(a, b):
    return 1.0 if a == b else SequenceMatcher(None, a, b).ratio()


# --------------------------------------------------------------------------- #
# Programmation dynamique mots reconnus ↔ lignes
# --------------------------------------------------------------------------- #
P = {"garb": -0.35, "ins": -0.5, "del": -0.55, "thr": 0.55, "back": -1.0, "fwd": -2.5}


def align_pass(A, L):
    """A : mots reconnus ; L : mots (simplifiés) de chaque ligne. Renvoie les occurrences
    [{"line": j, "m": [(index mot reconnu, index mot de ligne, similarité)]}]."""
    J, N = len(L), len(A)
    idx, st = {}, []
    for j in range(J):
        for k in range(len(L[j]) + 1):
            idx[(j, k)] = len(st)
            st.append((j, k))
    S = len(st)
    NEG = -1e9
    ends = [(idx[(j, len(L[j]))], j) for j in range(J)] + [(S, -1)]

    def closure(V, B):
        for j in range(J):
            t = idx[(j, 0)]
            for e, jp in ends:
                if V[e] <= NEG / 2:
                    continue
                if jp == -1:
                    pen = -0.3 * j
                elif j == jp + 1:
                    pen = 0.0
                elif j <= jp:
                    pen = P["back"]
                else:
                    pen = P["fwd"] - 0.5 * (j - jp - 1)
                if V[e] + pen > V[t]:
                    V[t] = V[e] + pen
                    B[t] = (e, "start")
        for j in range(J):
            for k in range(len(L[j])):
                a, b = idx[(j, k)], idx[(j, k + 1)]
                if V[a] + P["del"] > V[b]:
                    V[b] = V[a] + P["del"]
                    B[b] = (a, "del")

    V = np.full(S + 1, NEG)
    V[S] = 0.0
    B0 = {}
    closure(V, B0)
    bps = [B0]
    for i in range(N):
        W, B = np.full(S + 1, NEG), {}
        w = A[i]["s"]
        for s in np.nonzero(V > NEG / 2)[0]:
            if s == S or st[s][1] == len(L[st[s][0]]):
                if V[s] + P["garb"] > W[s]:
                    W[s] = V[s] + P["garb"]
                    B[s] = (s, "garb")
                continue
            j, k = st[s]
            sc = sim(w, L[j][k])
            v, t = V[s] + (sc - P["thr"]) * 2.0, idx[(j, k + 1)]
            if v > W[t]:
                W[t], B[t] = v, (s, "match", sc, 1)
            if k + 1 < len(L[j]):
                sc2 = sim(w, L[j][k] + L[j][k + 1])
                v, t = V[s] + (sc2 - P["thr"]) * 2.0 + 0.2, idx[(j, k + 2)]
                if v > W[t]:
                    W[t], B[t] = v, (s, "match", sc2, 2)
            if k > 0 and V[s] + P["ins"] > W[s]:
                W[s], B[s] = V[s] + P["ins"], (s, "ins")
        closure(W, B)
        bps.append(B)
        V = W
    s = max([e for e, _ in ends], key=lambda e: V[e])
    path = []
    for i in range(N, -1, -1):
        B = bps[i]
        while s in B and B[s][1] in ("start", "del"):
            path.append((i, s) + B[s][1:])
            s = B[s][0]
        if i == 0:
            break
        path.append((i - 1, s) + B[s][1:])
        s = B[s][0]
    path.reverse()
    occ, cur = [], None
    for p in path:
        i, s, kind = p[0], p[1], p[2]
        if kind == "start":
            cur = {"line": st[s][0], "m": []}
            occ.append(cur)
        elif kind == "match" and cur is not None:
            j, k = st[s]
            for q in range(p[4]):                       # un mot reconnu = 1 ou 2 mots de ligne
                cur["m"].append((i, k - p[4] + q, p[3]))
    return [o for o in occ if o["m"]]


# --------------------------------------------------------------------------- #
# Vote entre passes, extrapolation, affinage
# --------------------------------------------------------------------------- #
def text_groups(lines):
    norm = [ly._norm_text(x["text"]) for x in lines]
    g = list(range(len(lines)))
    for j in range(len(lines)):
        for i in range(j):
            if norm[i] and SequenceMatcher(None, norm[i], norm[j]).ratio() >= 0.95:
                g[j] = g[i]
                break
    return g


def vote(passes_occ, lines, L, n_pass):
    grp = text_groups(lines)
    items = []                      # une occurrence d'une passe
    for p, occs in enumerate(passes_occ):
        for o in occs:
            n = len(L[o["line"]])
            t = {}
            for i, k, sc in o["m"]:
                if sc >= 0.5:
                    t.setdefault(k, (i, sc))
            if len(t) < max(2, 0.3 * n):
                continue
            items.append({"p": p, "line": o["line"], "g": grp[o["line"]], "w": t, "A": o["A"], "n": n})
    for it in items:                # estimation grossière du début (pour regrouper)
        k0 = min(it["w"])
        it["est"] = it["A"][it["w"][k0][0]]["t"] - 0.3 * k0
    clusters = []
    for it in sorted(items, key=lambda x: x["est"]):
        for c in clusters:
            if c["g"] == it["g"] and abs(c["est"] - it["est"]) < 2.0 and it["p"] not in c["ps"]:
                c["its"].append(it)
                c["ps"].add(it["p"])
                c["est"] = float(np.median([x["est"] for x in c["its"]]))
                break
        else:
            clusters.append({"g": it["g"], "est": it["est"], "its": [it], "ps": {it["p"]}})
    out = []
    for c in clusters:
        n = c["its"][0]["n"]
        wt, we = {}, {}
        for it in c["its"]:
            for k, (i, sc) in it["w"].items():
                wt.setdefault(k, []).append(it["A"][i]["t"])
                we.setdefault(k, []).append(it["A"][i]["e"])
        words = {k: (float(np.median(v)), float(np.median(we[k])), len(v)) for k, v in wt.items()}
        support = len(c["ps"]) / n_pass
        strength = sum(len(it["w"]) for it in c["its"]) / (n_pass * n)
        lines_v = [it["line"] for it in c["its"]]
        line = max(set(lines_v), key=lambda j: (lines_v.count(j), -j))
        out.append({"line": line, "g": c["g"], "words": words, "n": n, "support": round(support, 2),
                    "strength": round(strength, 2)})
    # garder les occurrences soutenues ; conflits (chevauchement) : la plus forte gagne
    out = [o for o in out if o["support"] >= 0.3 and o["strength"] >= 0.2]
    for o in out:
        ks = [k for k, v in o["words"].items() if v[2] >= 2] or list(o["words"])
        o["span"] = (min(o["words"][k][0] for k in ks), max(o["words"][k][1] for k in ks))
    out.sort(key=lambda o: -o["strength"])
    kept = []
    for o in out:
        if all(min(o["span"][1], k["span"][1]) - max(o["span"][0], k["span"][0]) < 0.5 for k in kept):
            kept.append(o)
    return sorted(kept, key=lambda o: o["span"][0])


def _reliable(o, k):
    v = o["words"].get(k)
    return v if v and v[2] >= 2 else None


def estimate_bounds(occ):
    """Début (mot 0) et fin (dernier mot) ; extrapolés d'une autre occurrence du même texte."""
    for o in occ:
        n = o["n"]
        refs = [r for r in occ if r is not o and r["g"] == o["g"]]
        k0 = min((k for k in o["words"] if _reliable(o, k)), default=min(o["words"]))
        rel = sorted((k for k in o["words"] if _reliable(o, k)), key=lambda k: o["words"][k][0]) or \
            sorted(o["words"], key=lambda k: o["words"][k][0])
        keep = rel[:1]
        for k in rel[1:]:                       # mots isolés après un long silence : pas cette ligne
            if o["words"][k][0] - o["words"][keep[-1]][1] > 2.0:
                break
            keep.append(k)
        k1 = max(keep)
        o["t0"], o["start_extrap"] = o["words"][k0][0], k0 > 0
        if k0 > 0:
            for r in refs:
                if _reliable(r, 0) and _reliable(r, k0):
                    o["t0"] = o["words"][k0][0] - (r["words"][k0][0] - r["words"][0][0])
                    break
            else:
                o["t0"] -= 0.3 * k0
        o["t1"], o["end_extrap"] = o["words"][k1][1], k1 < n - 1
        if k1 < n - 1:
            for r in refs:
                if _reliable(r, n - 1) and _reliable(r, k1):
                    o["t1"] = o["words"][k1][1] + (r["words"][n - 1][1] - r["words"][k1][1])
                    break
            else:
                o["t1"] += 0.3 * (n - 1 - k1)


def active_intervals(F, gap=0.35):
    act = F["dbs"] > F["thr"]
    out, i, n = [], 0, len(act)
    while i < n:
        if act[i]:
            j = i
            while j < n and act[j]:
                j += 1
            if out and (i - out[-1][1]) * ly.FR < gap:
                out[-1][1] = j
            else:
                out.append([i, j])
            i = j
        else:
            i += 1
    return [(s * ly.FR, e * ly.FR) for s, e in out]


def free_intervals(F, occ, min_len=1.0, margin=0.15, gap=0.35):
    """Chant non couvert par les occurrences placées (intervalles ≥ min_len s)."""
    out = []
    for a, b in active_intervals(F, gap):
        segs = [(a, b)]
        for o in occ:
            lo, hi = o["t0"] - margin, o["t1"] + margin
            nxt = []
            for x, y in segs:
                if hi <= x or lo >= y:
                    nxt.append((x, y))
                else:
                    if lo > x:
                        nxt.append((x, lo))
                    if hi < y:
                        nxt.append((hi, y))
            segs = nxt
        out += [(x, y) for x, y in segs if y - x >= min_len]
    return out


CONF_MIN = -2.0                 # log-proba moyenne minimale des caractères (alignement CTC)


def ctc_fill(occ, lines, F, LP, tok):
    """Chant libre (occurrence manquée par le vote) : la ligne dont l'alignement forcé CTC est le
    meilleur, si assez bon. La ligne choisie dans un groupe de même texte suit l'ordre du fichier."""
    grp = text_groups(lines)
    reps = sorted(set(grp))
    W = {j: norm_words(lines[j]["text"], tok) for j in reps}
    for lo, hi in free_intervals(F, occ, min_len=1.5, gap=1.2):
        f0, f1 = int(max(0, lo - 0.4) / CFR), int(min(len(LP) * CFR, hi + 0.4) / CFR)
        best = None
        for j in reps:
            if not W[j]:
                continue
            r = align(LP, W[j], tok, f0, f1, partial=False, wild_pen=1.0)
            if best is None or r["conf"] > best[1]["conf"]:
                best = (j, r)
        if not best or best[1]["conf"] < CONF_MIN or best[1]["t1"] - best[1]["t0"] < 0.6 * (hi - lo):
            continue
        g, r = best
        prev = [o for o in occ if o["t0"] < lo]
        nxt = [o for o in occ if o["t0"] > lo]
        if prev and nxt and min(nxt, key=lambda o: o["t0"])["line"] == max(prev, key=lambda o: o["t0"])["line"] + 1 \
                and r["conf"] < -1.0:
            continue                    # rien n'est attendu entre deux lignes consécutives du fichier
        members = [j for j in range(len(lines)) if grp[j] == g]
        pl = max(prev, key=lambda o: o["t0"])["line"] if prev else -1
        nl = min(nxt, key=lambda o: o["t0"])["line"] if nxt else len(lines)
        line = min(members, key=lambda m: (not (m == pl + 1 or m + 1 == nl), abs(m - pl)))
        occ.append({"line": line, "g": g, "t0": r["t0"], "t1": r["t1"], "support": 0.0, "strength": 0.0,
                    "n": len(W[g]), "words": {}, "ctc_found": True, "start_extrap": False, "end_extrap": False})
    occ.sort(key=lambda o: o["t0"])


def fill_missing(occ, lines, F):
    """Lignes jamais trouvées : posées, dans l'ordre, sur le chant libre entre leurs voisines (devinées)."""
    placed = {o["line"] for o in occ}
    missing = [j for j in range(len(lines)) if j not in placed]
    ph = free_intervals(F, occ)
    used, run = set(), []
    for j in missing + [None]:
        if run and (j is None or j != run[-1] + 1):
            prev = [o for o in occ if o["line"] < run[0]]
            nxt = [o for o in occ if o["line"] > run[-1]]
            lo = max((o["t1"] for o in prev if o["line"] == max(p["line"] for p in prev)), default=0.0)
            hi = min((o["t0"] for o in nxt if o["line"] == min(p["line"] for p in nxt)), default=1e9)
            cand = [p for p in ph if lo - 0.1 <= p[0] and p[1] <= hi + 0.1 and p not in used]
            for jj, p in zip(run, cand):
                used.add(p)
                occ.append({"line": jj, "g": jj, "t0": p[0], "t1": p[1], "support": 0.0, "strength": 0.0,
                            "n": 0, "words": {}, "guess": True, "start_extrap": False, "end_extrap": False})
            run = []
        if j is not None:
            run.append(j)
    occ.sort(key=lambda o: o["t0"])
    return [j for j in missing if j not in {o["line"] for o in occ}], [p for p in ph if p not in used]


def fine_align(occ, lines, LP, tok, margin=1.5):
    """Alignement forcé CTC conjoint de toutes les occurrences (ordre imposé, fenêtre ± margin
    autour du placement grossier)."""
    todo = [o for o in occ if not o.get("guess")]
    words = [norm_words(lines[o["line"]]["text"], tok) for o in todo]
    win = [(o["t0"] - margin, o["t1"] + margin) for o in todo]
    res = joint_align(LP, words, tok, windows=win)
    for o, r in zip(todo, res):
        o["coarse_t0"], o["coarse_t1"] = o["t0"], o["t1"]
        if r:
            o["t0"], o["t1"], o["ctc_conf"] = r["t0"], r["t1"], r["conf"]


def refine(occ, F, back=0.4, fwd=0.05):
    """Début : le CTC émet le 1er caractère en retard (0,05–0,15 s après un silence, jusqu'à 0,3 s en
    legato) ; on prend le dernier événement du stem voix dans [CTC − 0,4 s, CTC + 0,05 s] :
    montée du niveau au-dessus du seuil (après un silence) ou début d'unité chantée (respiration /
    creux marqué, ly.detect_units) ; sinon l'attaque (onset) la plus proche du temps Parakeet ;
    sinon CTC − 0,1 s. Jamais avant la fin CTC de la ligne précédente.
    Fin : chute du niveau après le dernier caractère, sans dépasser le début de la ligne suivante."""
    dbs, thr = F["dbs"], F["thr"]
    on = F["onsets"] * ly.FR
    us = np.array([u["s"] * ly.FR for u in ly.detect_units(F) if u["strength"] >= 0.45])
    fr = lambda t: int(round(t / ly.FR))                         # noqa: E731
    prev_end = -1.0
    for o in sorted(occ, key=lambda o: o["t0"]):
        if o.get("guess"):
            prev_end = o["t1"]
            continue
        t = o["t0"]
        lo, hi = max(t - back, prev_end), t + fwd
        a, b = max(1, fr(lo)), fr(hi)
        ev = [k * ly.FR for k in range(a, b + 1) if dbs[k - 1] < thr <= dbs[k]]
        ev += [float(x) for x in us if lo <= x <= hi]
        if ev:
            t = max(ev)
        else:
            ref = o.get("asr_t0") or t - 0.1
            c = on[(on >= lo) & (on <= hi)]
            t = float(c[np.argmin(np.abs(c - ref))]) if len(c) else max(lo, t - 0.1)
        prev_end = o["t1"]
        o["t0"] = t
        e = o["t1"]
        a, b = fr(e), min(len(dbs), fr(e + 0.8))
        below = np.nonzero(dbs[a:b] < thr)[0]
        o["t1"] = (a + int(below[0])) * ly.FR if len(below) else e
    occ.sort(key=lambda o: o["t0"])
    for o, nx in zip(occ, occ[1:]):
        o["t1"] = min(max(o["t1"], o["t0"] + 0.3), nx["t0"] - 0.02)
    occ[-1]["t1"] = max(occ[-1]["t1"], occ[-1]["t0"] + 0.3)


def parallel_consensus(occ, bar_s, tol=0.15, agree=0.1):
    """Occurrences d'un même texte (≥ 3, ex. refrains) chantées sur la même mélodie, décalées d'un
    nombre entier de mesures : un début (ou une fin) qui s'écarte de plus de tol s de la médiane,
    alors que les autres concordent à agree s près, est remplacé par la médiane (marqué)."""
    groups = {}
    for o in occ:
        if not o.get("guess"):
            groups.setdefault(o["g"], []).append(o)
    for G in groups.values():
        if len(G) < 3:
            continue
        for key in ("t0", "t1"):
            ref = G[0][key]
            ks = [round((o[key] - ref) / bar_s) for o in G]
            p = np.array([o[key] - k * bar_s for o, k in zip(G, ks)])
            m = float(np.median(p))
            for i, o in enumerate(G):
                others = np.delete(p, i)
                if abs(p[i] - m) > tol and np.all(np.abs(others - np.median(others)) <= agree):
                    o[key] = float(np.median(others)) + ks[i] * bar_s
                    o.setdefault("consensus", []).append(key)
    occ.sort(key=lambda o: o["t0"])
    for o, nx in zip(occ, occ[1:]):
        o["t1"] = min(o["t1"], nx["t0"] - 0.02)


# --------------------------------------------------------------------------- #
# Alignement forcé CTC (Omnilingual ASR, trames de 20 ms) : précision fine
# --------------------------------------------------------------------------- #
CFR=0.02
DEFAULT_CTC = str(MODELS / "sherpa-onnx-omnilingual-asr-1600-languages-1B-ctc-int8-2025-11-12")


def ctc_logprobs(voice, model_dir, cache=None, chunk=20.0, ov=3.0):
    """Log-probabilités CTC (trames de 20 ms × vocabulaire) du stem voix, par morceaux de 20 s."""
    if cache and Path(cache).exists():
        return np.load(cache, mmap_mode="r")
    import librosa
    import onnxruntime as ort
    opt = ort.SessionOptions()
    opt.intra_op_num_threads = os.cpu_count() or 2
    s = ort.InferenceSession(str(Path(model_dir) / "model.int8.onnx"), opt)
    sr, hop = 16000, 320
    y = librosa.load(str(voice), sr=sr, mono=True)[0]
    nfr = len(y) // hop
    LP = None
    start = 0.0
    while start * sr < len(y):
        a, b = int(max(0, start - ov) * sr), int(min(len(y), (start + chunk + ov) * sr))
        lg = s.run(None, {"x": y[a:b].astype(np.float32)[None]})[0][0]
        lg = lg - np.logaddexp.reduce(lg, axis=1, keepdims=True)
        if LP is None:
            LP = np.full((nfr, lg.shape[1]), -30.0, np.float16)
        for f in range(int(start * sr) // hop, min(nfr, int(min(len(y), (start + chunk) * sr)) // hop)):
            if 0 <= f - a // hop < len(lg):
                LP[f] = lg[f - a // hop]
        start += chunk
    if cache:
        np.save(cache, LP)
    return LP


def load_vocab(path):
    tok={}
    for l in open(path,encoding='utf-8'):
        l=l.rstrip('\n'); p=l.rfind(' '); tok[l[:p]]=int(l[p+1:])
    return tok
def norm_words(text,tok):
    t=unicodedata.normalize("NFC",text.lower()).replace("’","'").replace("-"," ")
    words=[]
    for w in t.split():
        cs=[c for c in w if c in tok and c!=" "]
        if not cs: cs=[c for c in unicodedata.normalize("NFD",w) if c in tok and c!=" "]
        if cs: words.append(cs)
    return words
def build(words,tok):
    lab=[];wi=[];opt=[]
    for k,w in enumerate(words):
        if k>0: lab.append(tok[" "]); wi.append(k); opt.append(True)
        for c in w: lab.append(tok[c]); wi.append(k); opt.append(False)
    return lab,wi,opt
def align(LP, words, tok, f0, f1, skip_pen=2.0, wild_pen=1.0, partial=True):
    lab,wi,opt=build(words,tok)
    X=LP[f0:f1].astype(np.float32); T=len(X); U=len(lab); S=2*U+1
    ids=np.zeros(S,int); ids[1::2]=lab
    E=X[:,ids]; wild=X.max(1)-wild_pen
    NEG=-1e9
    p2=np.zeros(S,bool); p3=np.zeros(S,bool); p4=np.zeros(S,bool)
    for s in range(3,S,2):
        u=(s-1)//2
        if lab[u]!=lab[u-1]: p2[s]=True
        if u>=2 and opt[u-1]:
            p3[s]=True
            if lab[u]!=lab[u-2]: p4[s]=True
    nW=len(words)
    entry=np.full(S,NEG); exitp=np.full(S,NEG)
    first={};last={}
    for u in range(U):
        if not opt[u]: first.setdefault(wi[u],u); last[wi[u]]=u
    for k in range(nW):
        pen=-skip_pen*k if (partial or k==0) else NEG
        if k==0 or partial:
            s=2*first[k]+1; entry[s]=max(entry[s],pen); entry[s-1]=max(entry[s-1],pen)
        pen=-skip_pen*(nW-1-k) if (partial or k==nW-1) else NEG
        if k==nW-1 or partial:
            s=2*last[k]+1; exitp[s]=max(exitp[s],pen); exitp[s+1]=max(exitp[s+1],pen)
    Wsuf=np.r_[np.cumsum(wild[::-1])[::-1][1:],0.0]
    D=np.full(S,NEG); G0=0.0
    BP=np.zeros((T,S),np.int8)
    best=(NEG,None,None)
    sh=lambda a,k: np.r_[np.full(k,NEG),a[:-k]]
    for t in range(T):
        cand=np.stack([D,sh(D,1),np.where(p2,sh(D,2),NEG),np.where(p3,sh(D,3),NEG),np.where(p4,sh(D,4),NEG),G0+entry])
        b=cand.argmax(0); D=cand[b,np.arange(S)]+E[t]; BP[t]=b
        sc=D+exitp; s=int(sc.argmax())
        if sc[s]+Wsuf[t]>best[0]: best=(sc[s]+Wsuf[t],t,s)
        G0+=wild[t]
    _,t,s=best
    path=[]
    while t>=0:
        path.append((t,s)); b=BP[t,s]
        if b==5: break
        s-= int(b); t-=1
    path.reverse()
    # first/last frame of each label emitted
    fl={}
    for t,s in path:
        if s%2==1:
            u=(s-1)//2
            if u not in fl: fl[u]=[t,t]
            fl[u][1]=t
    us=[u for u in fl if not opt[u]]
    u0,u1=min(us),max(us)
    wf={}
    for u,(a,b) in fl.items():
        if opt[u]: continue
        k=wi[u]; wf.setdefault(k,[a,b]); wf[k][0]=min(wf[k][0],a); wf[k][1]=max(wf[k][1],b)
    # confidence: mean emission logprob of label frames
    conf=float(np.mean([X[t,ids[s]] for t,s in path if s%2==1]))
    return {"t0":(f0+fl[u0][0])*CFR,"t1":(f0+fl[u1][1]+1)*CFR,"k0":wi[u0],"k1":wi[u1],"nW":nW,
            "words":{k:((f0+a)*CFR,(f0+b+1)*CFR) for k,(a,b) in wf.items()},"conf":conf,"score":best[0]}


def joint_align(LP, seqwords, tok, f0=0, f1=None, wild_pen=0.1, blank_pen=0.05, windows=None):
    """Alignement forcé de lignes successives (ordre imposé), avec « joker » entre lignes.
    seqwords : [mots (listes de caractères)] par occurrence. Renvoie [(t0, t1, mots {k: (a, b)}, conf)]."""
    f1 = f1 or len(LP)
    X = LP[f0:f1].astype(np.float32); T = len(X)
    ids, kind, mask = [], [], {k: [] for k in (1, 2, 3, 4)}
    owner = []                      # (occurrence, word index, optionnel) des états-labels
    NEG = -1e9

    def add(i, kd, own=None):
        ids.append(i); kind.append(kd); owner.append(own)
        for k in mask: mask[k].append(False)
        return len(ids) - 1
    W = [add(0, "W")]
    for n, words in enumerate(seqwords):
        lab, wi, opt = build(words, tok)
        base = len(ids)
        for u in range(len(lab)):
            add(0, "b")
            add(lab[u], "l", (n, wi[u], opt[u]))
        add(0, "b")
        U = len(lab)
        for u in range(U):
            s = base + 2 * u + 1
            mask[1][s] = True                                 # from blank before
            if u > 0 and lab[u] != lab[u - 1]:
                mask[2][s] = True
            if u >= 2 and opt[u - 1]:
                mask[3][s] = True
                if lab[u] != lab[u - 2]:
                    mask[4][s] = True
            mask[1][s + 1] = True                             # blank after label
        # line start: b0 = base, l1 = base+1 ; W before at base-1
        mask[1][base] = True                                  # W -> b0
        mask[2][base + 1] = True                              # W -> l1
        if n > 0:
            mask[2][base] = True; mask[3][base] = True        # prev final blank/label -> b0
            mask[3][base + 1] = True; mask[4][base + 1] = True
        w = add(0, "W")
        mask[1][w] = True; mask[2][w] = True                  # final blank / label -> W
        W.append(w)
    S = len(ids)
    ids = np.array(ids); M = {k: np.array(v) for k, v in mask.items()}
    isW = np.array([k == "W" for k in kind])
    E = X[:, ids]
    wild = X.max(1) - wild_pen
    E[:, isW] = wild[:, None]
    isB = np.array([k == 'b' for k in kind])
    E[:, isB] -= blank_pen
    if windows:                                   # chaque occurrence confinée à sa fenêtre (s)
        st_occ = np.full(S, -1)
        cur = -1
        for s_ in range(S):
            if kind[s_] == "W":
                continue
            if owner[s_] is not None:
                cur = owner[s_][0]
            st_occ[s_] = cur if owner[s_] is not None else st_occ[s_]
        # blanks: occurrence of the next label (or previous for the final blank)
        last = -1
        for s_ in range(S):
            if kind[s_] == "l":
                last = owner[s_][0]
            elif kind[s_] == "b":
                nxt = s_ + 1 if s_ + 1 < S and kind[s_ + 1] == "l" else None
                st_occ[s_] = owner[nxt][0] if nxt is not None else last
        tt = (f0 + np.arange(T)) * CFR
        for n, (lo, hi) in enumerate(windows):
            if lo is None:
                continue
            cols = np.nonzero(st_occ == n)[0]
            out_ = (tt < lo) | (tt > hi)
            E[np.ix_(out_, cols)] = NEG / 10
    D = np.full(S, NEG); D[0] = 0.0 + E[0, 0]
    D[1] = E[0, 1]; D[2] = E[0, 2]
    BP = np.zeros((T, S), np.int8)
    for t in range(1, T):
        best = D.copy(); arg = np.zeros(S, np.int8)
        for k in (1, 2, 3, 4):
            c = np.r_[np.full(k, NEG), D[:-k]]
            c = np.where(M[k], c, NEG)
            upd = c > best
            best = np.where(upd, c, best); arg = np.where(upd, k, arg)
        D = best + E[t]; BP[t] = arg
    s = S - 1
    for c in (S - 2, S - 3):
        if D[c] > D[s]:
            s = c
    t = T - 1
    path = []
    while t >= 0:
        path.append((t, s))
        s -= int(BP[t, s]); t -= 1
    path.reverse()
    out = {}
    for t, s in path:
        o = owner[s]
        if kind[s] == "l" and not o[2]:
            n, k = o[0], o[1]
            d = out.setdefault(n, {"words": {}, "lp": []})
            a = d["words"].setdefault(k, [t, t]); a[1] = t
            d["lp"].append(float(X[t, ids[s]]))
    res = []
    for n in range(len(seqwords)):
        d = out.get(n)
        if not d:
            res.append(None); continue
        ks = sorted(d["words"])
        res.append({"t0": (f0 + d["words"][ks[0]][0]) * CFR, "t1": (f0 + d["words"][ks[-1]][1] + 1) * CFR,
                    "words": {k: ((f0 + a) * CFR, (f0 + b + 1) * CFR) for k, (a, b) in d["words"].items()},
                    "conf": float(np.mean(d["lp"]))})
    return res


# --------------------------------------------------------------------------- #
# Grille
# --------------------------------------------------------------------------- #
def to_bar(t, bar1, bpm, bpb):
    beat = 60.0 / bpm
    x = (t - bar1) / beat
    bar = int(np.floor(x / bpb + 1e-9))
    pos = x - bar * bpb
    if pos > bpb - 0.005:
        bar, pos = bar + 1, 0.0
    return bar + 1, round(pos + 1.0, 2)            # mesure 1-based, temps 1-based décimal


def fmt(t, g):
    b, p = to_bar(t, *g)
    return f"{b}:{p:.2f}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--voice", required=True)
    ap.add_argument("--lyrics", required=True)
    ap.add_argument("--bpm", type=float, required=True)
    ap.add_argument("--bar1", type=float, required=True, help="temps de la mesure 1 dans le fichier voix (s)")
    ap.add_argument("--bpb", type=int, default=4)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model-dir", default=DEFAULT_MODEL)
    ap.add_argument("--ctc-model-dir", default=DEFAULT_CTC)
    ap.add_argument("--cache", default=None, help="préfixe des caches (passes : contient des mots, ne pas "
                                                  "afficher ; log-probas CTC .npy)")
    ap.add_argument("--report", default=None, help="rapport JSON (chiffres seuls)")
    args = ap.parse_args(argv)
    g = (args.bar1, args.bpm, args.bpb)
    lines = ly.read_lyrics(args.lyrics)
    L = [line_words(x["text"]) for x in lines]
    passes = transcribe(args.voice, args.model_dir, args.cache and args.cache + "_passes.json")
    occs = []
    for toks in passes:
        A = asr_words(toks)
        po = align_pass(A, L)
        for o in po:
            o["A"] = A
        occs.append(po)
    occ = vote(occs, lines, L, len(passes))
    estimate_bounds(occ)
    import librosa
    y = librosa.load(args.voice, sr=ly.SR, mono=True)[0]
    F = ly.vocal_features(y)
    for o in occ:
        o["asr_t0"] = o["t0"]
    LP = ctc_logprobs(args.voice, args.ctc_model_dir, args.cache and args.cache + "_ctc.npy")
    tok = load_vocab(Path(args.ctc_model_dir) / "tokens.txt")
    ctc_fill(occ, lines, F, LP, tok)
    still_missing, free = fill_missing(occ, lines, F)
    fine_align(occ, lines, LP, tok)
    refine(occ, F)
    parallel_consensus(occ, 60.0 * args.bpb / args.bpm)
    # numérotation des occurrences
    cnt, anchors, rep = {}, {"_format": "reacue-calage-2",
                             "_grille": {"bpm": args.bpm, "temps_par_mesure": args.bpb}}, []
    for o in occ:
        j = o["line"]
        cnt[j] = cnt.get(j, 0) + 1
        key = str(j + 1) if cnt[j] == 1 else f"{j + 1}#{cnt[j]}"
        anchors[key] = f"{fmt(o['t0'], g)}-{fmt(o['t1'], g)}"
        rep.append({"key": key, "t0": round(o["t0"], 3), "t1": round(o["t1"], 3),
                    "asr_t0": None if o.get("asr_t0") is None else round(o["asr_t0"], 3),
                    "support": o["support"], "strength": o["strength"],
                    "start_extrap": o["start_extrap"], "end_extrap": o["end_extrap"],
                    "guess": bool(o.get("guess")), "ctc_found": bool(o.get("ctc_found")),
                    "consensus": o.get("consensus", []),
                    "ctc_conf": None if o.get("ctc_conf") is None else round(o["ctc_conf"], 2)})
    for j in still_missing:
        anchors[str(j + 1)] = None                     # ligne non chantée : non affichée
    Path(args.out).write_text(json.dumps(anchors, indent=1), encoding="utf-8")
    if args.report:
        Path(args.report).write_text(json.dumps({"occurrences": rep, "missing": [j + 1 for j in still_missing],
                                                 "free_phrases": [[round(a, 2), round(b, 2)] for a, b in free]},
                                                indent=1), encoding="utf-8")
    print(f"{len(rep)} occurrences, {len(lines)} lignes, non chantées : {[j + 1 for j in still_missing]}")
    for r in rep:
        flag = (" devinée" if r["guess"] else "") + (" trouvée par CTC" if r["ctc_found"] else "") + \
               ("".join(f" {k}=médiane des répétitions" for k in r["consensus"])) + (" début extrapolé" if r["start_extrap"] else "") + \
               (" fin extrapolée" if r["end_extrap"] else "") + (" soutien faible" if 0 < r["support"] < 0.6 else "")
        print(f"{r['key']:>5} {anchors[r['key']]:>17}  t {r['t0']:7.2f}-{r['t1']:7.2f}  "
              f"asr {r['asr_t0'] if r['asr_t0'] is not None else '-':>7}  ctc {r['ctc_conf']}  soutien {r['support']:.2f}{flag}")
    free = free_intervals(F, occ)
    print(f"chant sans ligne (début s, durée s) : {[(round(a, 2), round(b - a, 2)) for a, b in free]}")


if __name__ == "__main__":
    main()
