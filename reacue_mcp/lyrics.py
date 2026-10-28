"""Calage des paroles sur le stem voix pour le prompteur des musiciens.

Fichier de paroles cherché à côté des stems : paroles*.txt|rtf, parole*.txt|rtf, lyrics*.txt|rtf.
ReaCue ne télécharge jamais de paroles : c'est l'utilisateur qui fournit le fichier. S'il n'y en a pas et que
Whisper est installé (composant facultatif, lyrics_auto.py), ReaCue transcrit le stem voix et écrit un brouillon
« paroles (auto).txt » dans le dossier du morceau, utilisé ensuite comme un fichier de paroles normal
(le fichier de l'utilisateur reste toujours prioritaire ; le brouillon n'est jamais écrasé).
Une ligne = une phrase chantée ; ligne vide = séparation de blocs (couplet, refrain…) ; « # » = commentaire.

Méthode (librosa / numpy uniquement, quelques secondes) — détaillée dans align_lyrics :
  1. phrases chantées : niveau du stem voix (seuil relatif p90 − 20 dB, comme _vocal_activity),
     découpées aux respirations (≥ 0,2 s) ; attaques (onsets) = estimation du nombre de syllabes ;
  2. syllabes de chaque ligne estimées (groupes de voyelles, « e » muets de fin retirés) ;
  3. programmation dynamique monotone lignes ↔ phrases : une ligne peut couvrir 1 à 3 phrases,
     une phrase peut contenir 2 lignes courtes ; coût = écart de durée (syllabes × durée apprise
     par syllabe) + écart du nombre d'attaques ; phrases sans ligne et lignes sautées pénalisées ;
     à la fin d'un bloc, on peut rejouer un bloc précédent (refrain écrit une seule fois) ;
  4. rejouer un bloc n'est accepté que si l'audio (chroma + MFCC du stem voix) ressemble à celui de
     sa première occurrence ; sinon le passage reste sans ligne (la suite ne se décale pas) ;
  5. corrections manuelles / ancres exactes : paroles_calage.json (ou lyrics_timing.json) à côté des
     paroles (voir ci-dessous) ;
  6. si le composant facultatif « paroles mot par mot » est installé (.venv-words, voir words.py) : chaque
     ligne calée reçoit "words": [{"w", "t", "end"}] par alignement forcé du texte sur le stem voix.

paroles_calage.json / lyrics_timing.json — aucun texte, seulement des numéros de ligne et des positions sur la grille :
  clé   "12"   = ligne 12 (1-based, lignes non vides du fichier, étiquettes exclues), 1re occurrence ;
        "12#2" = 2e occurrence chantée de la ligne 12 (refrain chanté de nouveau sans être réécrit) ;
        clés commençant par « _ » ignorées (commentaires, "_format", "_grille").
  valeur 45 | "45"   = mesure 45, 1er temps (ancien format) ;
         "45.3"      = mesure 45, temps 3 (ancien format : temps entier 1-based) ;
         "45:2.75"   = mesure 45, temps 2,75 (temps 1-based décimal : 2,75 = 3e double-croche du temps 2) ;
         "45:2.75-49:1.5" = début et fin (fin = fin du dernier mot chanté) ;
         {"debut": "45:2.75", "fin": "49:1.5"} = idem ;
         null        = ligne non chantée : jamais affichée.
  Si CHAQUE ligne du fichier a son ancre "N" (ou null), le calage automatique n'est pas utilisé : les
  occurrences publiées sont exactement celles du fichier (fin absente = début de la suivante, au plus
  0,3 s par syllabe). Sinon les débuts des 1res occurrences guident le calage automatique et les
  autres ancres (fins, occurrences #k) remplacent ensuite les lignes calées correspondantes.

Produire des ancres exactes pour un nouveau morceau (reconnaissance vocale, outil de développement) :
  python3 tools/asr_anchor.py --voice <stem voix> --lyrics <paroles> --bpm <tempo> --bar1 <s> --out paroles_calage.json
  (--bar1 = temps de la mesure 1 dans le fichier voix ; modèles Parakeet TDT v3 + Omnilingual CTC 1B via
  sherpa-onnx ; voir son en-tête), puis copier le JSON à côté du fichier de paroles. Les lignes signalées
  « devinée » sont à vérifier à l'oreille.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

from .analysis import Analysis, SR, HOP, _place, _frame_db, assign_roles
from .i18n import t as _t

VERSION = "lyrics-3"          # à changer quand l'algorithme change (invalide le cache)
CALAGE_NAME = "paroles_calage.json"
CALAGE_NAMES = (CALAGE_NAME, "lyrics_timing.json")   # même format ; le premier trouvé est utilisé


def calage_file(lyrics_path) -> Path | None:
    """Fichier d'ancres à côté des paroles (paroles_calage.json, sinon lyrics_timing.json)."""
    if not lyrics_path:
        return None
    for name in CALAGE_NAMES:
        p = Path(lyrics_path).parent / name
        if p.exists():
            return p
    return None
_PATTERNS = ("paroles", "parole", "lyrics")
AUTO_NAME = "paroles (auto).txt"   # brouillon écrit par lyrics_auto.py (Whisper) si l'utilisateur n'a rien fourni
_EXTS = (".txt", ".rtf")


# --------------------------------------------------------------------------- #
# Fichier de paroles
# --------------------------------------------------------------------------- #
def lyric_dirs(paths: list[str]) -> list[Path]:
    """Dossiers où chercher les paroles : ceux des fichiers donnés (ou les dossiers donnés) ; pour des stems
    séparés par ReaCue (<morceau>-stems/<modèle>/), aussi le dossier du morceau d'origine."""
    dirs = []
    for p in paths or []:
        p = Path(str(p)).expanduser()
        d = p if p.is_dir() else p.parent
        if d not in dirs:
            dirs.append(d)
    for d in list(dirs):       # stems séparés par ReaCue : <morceau>-stems/<modèle>/ -> dossier du morceau
        if d.parent.name.endswith("-stems") and d.parent.parent not in dirs:
            dirs.append(d.parent.parent)
    return dirs


def find_lyrics_file(paths: list[str]) -> Path | None:
    """Premier fichier paroles*/parole*/lyrics* (.txt, .rtf) de l'utilisateur dans lyric_dirs(paths).
    Insensible à la casse ; .txt préféré à .rtf à préfixe égal. Le brouillon automatique « paroles (auto).txt »
    (lyrics_auto.py) n'est jamais renvoyé ici : le fichier de l'utilisateur est toujours prioritaire."""
    for d in lyric_dirs(paths):
        try:
            files = sorted(f for f in d.iterdir() if f.is_file())
        except OSError:
            continue
        best = None
        for f in files:
            n = f.name.lower()
            if n.startswith(".") or f.suffix.lower() not in _EXTS or n == AUTO_NAME.lower():
                continue
            for rank, pre in enumerate(_PATTERNS):
                if n.startswith(pre):
                    r = (rank, _EXTS.index(f.suffix.lower()), n)
                    if best is None or r < best[0]:
                        best = (r, f)
                    break
        if best:
            return best[1]
    return None


_SKIP_DEST = {"fonttbl", "colortbl", "expandedcolortbl", "stylesheet", "info", "pict", "header",
              "footer", "headerl", "headerr", "footerl", "footerr", "listtable", "listoverridetable",
              "revtbl", "rsidtbl", "generator", "xmlnstbl", "themedata", "colorschememapping",
              "latentstyles", "datastore", "object", "fldinst", "filetbl", "mmathPr"}
_SPECIAL = {"par": "\n", "line": "\n", "sect": "\n", "page": "\n", "tab": "\t", "emdash": "—",
            "endash": "–", "lquote": "‘", "rquote": "’", "ldblquote": "“", "rdblquote": "”",
            "bullet": "•", "emspace": " ", "enspace": " ", "qmspace": " "}


def rtf_to_text(data: bytes | str) -> str:
    """Décodeur RTF minimal : texte brut, paragraphes -> lignes (sans dépendance)."""
    s = data.decode("latin-1") if isinstance(data, bytes) else data
    m = re.search(r"\\ansicpg(\d+)", s)
    codepage = f"cp{m.group(1)}" if m else "cp1252"
    try:
        b"".decode(codepage)
    except LookupError:
        codepage = "cp1252"
    out: list[str] = []
    pend = bytearray()                 # octets \'hh en attente (caractères multi-octets)

    def flush():
        if pend:
            out.append(pend.decode(codepage, errors="replace"))
            pend.clear()

    stack = []
    skip, uc, ucskip = False, 1, 0
    i, n = 0, len(s)
    tok = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|([^\\{}\r\n]+)|[\r\n]",
                     re.S)
    first_in_group = False
    while i < n:
        mt = tok.match(s, i)
        if not mt:
            i += 1
            continue
        i = mt.end()
        word, arg, hexb, sym, brace, text = mt.groups()
        if ucskip and (text or hexb or sym):           # caractères de repli après \uN
            if text:
                k = min(ucskip, len(text))
                ucskip -= k
                text = text[k:]
                if not text:
                    continue
            else:
                ucskip -= 1
                continue
        if brace == "{":
            flush()
            stack.append((skip, uc))
            first_in_group = True
            continue
        if brace == "}":
            flush()
            skip, uc = stack.pop() if stack else (False, 1)
            first_in_group = False
            continue
        fig = first_in_group
        first_in_group = False
        if word:
            if word in _SKIP_DEST and fig:
                skip = True
            if skip:
                continue
            if word == "uc":
                uc = int(arg or 1)
            elif word == "u":
                flush()
                v = int(arg or 0)
                out.append(chr(v + 65536 if v < 0 else v))
                ucskip = uc
            elif word in _SPECIAL:
                flush()
                out.append(_SPECIAL[word])
            continue
        if hexb:
            if not skip:
                pend.append(int(hexb, 16))
            continue
        if sym:
            if sym == "*" and fig:
                skip = True
                continue
            if skip:
                continue
            flush()
            if sym in "\n\r":
                out.append("\n")                    # « \ » + retour ligne (TextEdit) = \par
            elif sym in "\\{}":
                out.append(sym)
            elif sym == "~":
                out.append(" ")
            elif sym == "_":
                out.append("-")
            # \- (césure facultative), \: … ignorés
            continue
        if text and not skip:
            flush()
            out.append(text)
    flush()
    return "".join(out)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    if path.suffix.lower() == ".rtf" or raw.lstrip().startswith(b"{\\rtf"):
        if sys.platform == "darwin" and shutil.which("textutil"):   # macOS : le convertisseur du système
            try:
                r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)],
                                   capture_output=True, timeout=10)
                if r.returncode == 0 and r.stdout:
                    return r.stdout.decode("utf-8", errors="replace")
            except (OSError, subprocess.SubprocessError):
                pass
        return rtf_to_text(raw)
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


_LABEL = re.compile(r"^\s*[\[(]?\s*(refrain|couplet|pr[ée][- ]?refrain|pont|bridge|chorus|verse|"
                    r"intro|outro|break|solo|pre[- ]?chorus)\b[^\]\)]*[\])]?\s*:?\s*$", re.I)
_REPEAT = re.compile(r"\s*[\[(]?\s*(?:x\s*(\d)|(\d)\s*x|(bis))\s*[\])]?\s*$", re.I)


def read_lyrics(path) -> list[dict]:
    """Lignes non vides : [{"i": index 0-based, "line": n° 1-based, "block": n° de bloc 0-based,
    "text": …, "repeat": répétitions demandées (« x2 », « bis »), "label": étiquette du bloc}].
    Les lignes-étiquettes (« [Refrain] », « Couplet 2 : ») ne sont pas des lignes chantées ; les lignes qui
    commencent par « # » sont des commentaires (ignorés, ne séparent pas les blocs)."""
    text = _read_text(Path(path))
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    out, block, label, gap = [], 0, None, False
    for raw in text.split("\n"):
        t = raw.replace("\u00a0", " ").replace("\u2028", " ").strip()
        if not t:
            gap = True
            continue
        if t.startswith("#"):              # commentaire (en-tête du brouillon automatique…)
            continue
        if gap and out:
            block += 1
            label = None
        gap = False
        if _LABEL.match(t):
            if out and out[-1]["block"] == block:
                block += 1
            label = re.sub(r"[\[\]():]", "", t).strip()
            continue
        rep = 1
        mr = _REPEAT.search(t)
        if mr and mr.start() > 0:
            rep = 2 if mr.group(3) else int(mr.group(1) or mr.group(2))
            t = t[:mr.start()].rstrip()
        elif mr:                           # « (x2) » seul sur sa ligne : répète la ligne précédente
            if out:
                out[-1]["repeat"] = 2 if mr.group(3) else int(mr.group(1) or mr.group(2))
            continue
        out.append({"i": len(out), "line": len(out) + 1, "block": block, "text": t,
                    "repeat": max(1, rep), "label": label})
    return out


# --------------------------------------------------------------------------- #
# Syllabes (français, estimation)
# --------------------------------------------------------------------------- #
_VOW = "aeiouyàâäéèêëîïôöûùüœæ"


def syllables(text: str) -> int:
    """Nombre de syllabes chantées estimé : groupes de voyelles par mot, « e » muet final retiré
    (-e, -es), sauf mots d'une syllabe."""
    n = 0
    for w in re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", text.lower()):
        for part in re.split(r"['’-]", w):
            if not part:
                continue
            g = re.findall(f"[{_VOW}]+", part)
            k = len(g)
            if k == 0:
                continue
            if k > 1 and re.search(f"([^{_VOW}]|gu|qu)es?$", part):
                k -= 1
            n += k
    return max(1, n)


# --------------------------------------------------------------------------- #
# Phrases chantées (stem voix)
# --------------------------------------------------------------------------- #
FR = HOP / SR                  # durée d'une trame (≈ 23 ms)


def _voice_source(a: Analysis, items: list[dict] | None) -> tuple[str, float] | None:
    """(fichier du stem voix, décalage s dans le temps de référence) ou None."""
    if items:
        from .prompter import _shifts
        files = [d["file"] for d in items]
        sh = _shifts(items)
        for r, f in zip(assign_roles(files), files):
            if r == "vocals":
                return f, sh[f]
        return None
    if a.stems and "vocals" in a.stems:
        return a.stems["vocals"], 0.0
    return None


def vocal_features(y: np.ndarray) -> dict:
    """Niveau (dB), activité, attaques, chroma et MFCC du stem voix (trames HOP)."""
    import librosa
    from scipy.ndimage import gaussian_filter1d
    d = _frame_db(y)
    top = float(np.percentile(d, 90))
    ds = gaussian_filter1d(d, 1.5)
    o_env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    on = librosa.onset.onset_detect(onset_envelope=o_env, sr=SR, hop_length=HOP, units="frames",
                                    backtrack=False, delta=0.05)
    on = on[d[np.minimum(on + 2, len(d) - 1)] > top - 20]           # attaques dans du chant
    chroma = librosa.feature.chroma_stft(y=y, sr=SR, hop_length=HOP, n_fft=4096)
    mfcc = librosa.feature.mfcc(y=y, sr=SR, hop_length=HOP, n_mfcc=14)[1:]
    n = min(len(d), chroma.shape[1], mfcc.shape[1])
    return {"db": d[:n], "dbs": ds[:n], "top": top, "thr": top - 20.0, "onsets": on[on < n],
            "chroma": chroma[:, :n], "mfcc": mfcc[:, :n]}


def detect_units(F: dict, min_gap: float = 0.15, dip_db: float = 9.0) -> list[dict]:
    """Phrases chantées découpées en unités aux respirations et aux creux marqués du niveau.
    Chaque unité : {"s", "e" (trames), "strength" (0..1 : netteté de la frontière de début)}."""
    ds, thr = F["dbs"], F["thr"]
    act = ds > thr
    n = len(act)
    runs, i = [], 0
    while i < n:
        if act[i]:
            j = i
            while j < n and act[j]:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    g = max(1, int(round(min_gap / FR)))
    ph = []
    for s, e in runs:
        if ph and s - ph[-1][1] < g:
            ph[-1][1] = e
        else:
            ph.append([s, e])
    ph = [p for p in ph if (p[1] - p[0]) * FR >= 0.12 and ds[p[0]:p[1]].max() > thr + 6]
    units = []
    w = int(round(0.35 / FR))
    for pi, (s, e) in enumerate(ph):
        gap = (s - ph[pi - 1][1]) * FR if pi else 10.0
        cuts = []
        seg = ds[s:e]
        # creux : minimum local nettement sous les maxima voisins (± 0,35 s)
        for k in range(3, len(seg) - 3):
            if seg[k] <= seg[k - 1] and seg[k] < seg[k + 1] and seg[k] == seg[max(0, k - 4):k + 5].min():
                left = seg[max(0, k - w):k].max()
                right = seg[k + 1:k + 1 + w].max()
                depth = min(left, right) - seg[k]
                if depth >= dip_db:
                    cuts.append((k, depth))
        bounds = [(0, min(1.0, 0.5 + gap / 0.6))] + [(k, min(0.9, 0.15 + (dp - dip_db) / 15 + 0.2))
                                                     for k, dp in cuts]
        for (k0, st), nxt in zip(bounds, bounds[1:] + [(len(seg), 0)]):
            if (nxt[0] - k0) * FR < 0.1 and units:       # miette : rattachée à l'unité précédente
                continue
            units.append({"s": s + k0, "e": s + nxt[0], "strength": float(st)})
    for u, v in zip(units, units[1:]):                 # fin d'unité = début de la suivante si collées
        if v["s"] < u["e"]:
            u["e"] = v["s"]
    on = F["onsets"]
    for u in units:
        u["n_on"] = int(((on >= u["s"] - 2) & (on < u["e"])).sum())
    return units


# --------------------------------------------------------------------------- #
# Blocs répétés (refrains) : similarité du stem voix entre occurrences d'une même section
# --------------------------------------------------------------------------- #
REPEAT_TYPES = ("chorus", "prechorus")      # types de section (i18n.section_kind)
REPEAT_MIN_SIM = 0.5           # similarité (chroma et MFCC) minimale pour réutiliser les lignes


def _beat_grid(a: Analysis) -> np.ndarray:
    m = max(1, int(a.beats_per_bar))
    db = np.asarray(a.downbeats, dtype=float)
    t = [db[k] + (db[k + 1] - db[k]) * j / m for k in range(len(db) - 1) for j in range(m)]
    t.append(db[-1])
    return np.array(t)


def _beat_feats(F: dict, tb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import librosa
    n = len(F["db"])
    fr = np.clip(librosa.time_to_frames(tb, sr=SR, hop_length=HOP), 0, n)
    act = (F["dbs"] > F["thr"]).astype(float)
    C, M = F["chroma"], F["mfcc"]
    M = (M - M.mean(1, keepdims=True)) / (M.std(1, keepdims=True) + 1e-9)
    nb = len(tb) - 1
    Cb, Mb, Ab = np.zeros((nb, 12)), np.zeros((nb, M.shape[0])), np.zeros(nb)
    for k in range(nb):
        a0, b0 = fr[k], max(fr[k + 1], fr[k] + 1)
        if a0 >= n:
            break
        Cb[k], Mb[k], Ab[k] = C[:, a0:b0].mean(1), M[:, a0:b0].mean(1), act[a0:b0].mean()
    Cb = Cb - Cb.mean(1, keepdims=True)
    Cb /= np.linalg.norm(Cb, axis=1, keepdims=True) + 1e-9
    Mb /= np.linalg.norm(Mb, axis=1, keepdims=True) + 1e-9
    return Cb, Mb, Ab


def _occurrence_sim(B, i0: int, j0: int, n: int, max_lag: int = 2) -> tuple[float, int]:
    """Similarité (0..1) entre les n temps à partir de i0 et de j0 (meilleur décalage ± max_lag)."""
    Cb, Mb, Ab = B
    best = (0.0, 0)
    for lag in range(-max_lag, max_lag + 1):
        i = np.arange(i0, i0 + n)
        j = i - i0 + j0 + lag
        ok = (j >= 0) & (j < len(Ab)) & (i < len(Ab))
        i, j = i[ok], j[ok]
        w = np.maximum(Ab[i], Ab[j])
        if w.sum() < 2:
            continue
        w2 = np.minimum(Ab[i], Ab[j])
        c = float((w2 * (Cb[i] * Cb[j]).sum(1)).sum() / w.sum())
        m = float((w2 * (Mb[i] * Mb[j]).sum(1)).sum() / w.sum())
        s = min(c, m)
        if s > best[0]:
            best = (s, lag)
    return best


def repeated_sections(a: Analysis, F: dict, B=None) -> list[dict]:
    """Occurrences de refrain / pré-refrain dont le chant ressemble à la 1re occurrence :
    [{"ref": index section, "occ": index section, "sim": 0..1, "shift_bars": …}]."""
    from .prompter import section_type
    m = max(1, int(a.beats_per_bar))
    if B is None:
        B = _beat_feats(F, _beat_grid(a))
    first, out = {}, []
    for si, s in enumerate(a.sections):
        t = section_type(s.name)
        if t not in REPEAT_TYPES:
            continue
        if t not in first:
            first[t] = si
            continue
        r = a.sections[first[t]]
        n = min(r.end_bar - r.start_bar, s.end_bar - s.start_bar) * m
        sim, lag = _occurrence_sim(B, r.start_bar * m, s.start_bar * m, n)
        out.append({"ref": first[t], "occ": si, "sim": round(sim, 3),
                    "shift_bars": s.start_bar - r.start_bar, "lag_beats": lag})
    return out


# --------------------------------------------------------------------------- #
# Alignement lignes ↔ unités chantées
# --------------------------------------------------------------------------- #
# paramètres du coût (réglés sur un morceau de test ; variantes = estimation de la confiance)
PARAMS = {
    "sig_dur": 0.30, "sig_on": 0.45,    # tolérances (log) sur la durée et le nombre d'attaques
    "p_line": 3.0,                      # ligne du fichier non chantée (sautée)
    "p_unit_s": 0.9, "p_unit": 0.4,     # unité chantée sans ligne : par seconde + fixe
    "p_split": 0.6,                     # deux lignes dans une seule unité
    "w_start": 1.5, "w_end": 1.0,       # début / fin de ligne sur une frontière de phrase nette
    "w_gap": 2.0, "gap_ok": 0.6,        # pause (s) tolérée dans une ligne, au-delà pénalisée
}
VARIANTS = ({"w_start": 3.0}, {"sig_dur": 0.25}, {"p_unit_s": 1.2}, {"w_gap": 3.5, "gap_ok": 0.45},
            {"_dsyl": 0.9}, {"_dsyl": 1.1})
K_MAX = 6                               # unités max par ligne


def _line_cost(syl, dur, n_on, st_start, st_next, gaps, dsyl, ratio, P):
    c = (math.log(max(dur, 0.05) / (syl * dsyl))) ** 2 / (2 * P["sig_dur"] ** 2)
    c += (math.log((n_on + 1) / (syl * ratio + 1))) ** 2 / (2 * P["sig_on"] ** 2)
    c += P["w_start"] * (1 - st_start) + P["w_end"] * (1 - st_next)
    c += sum(P["w_gap"] * (g - P["gap_ok"]) for g in gaps if g > P["gap_ok"])
    return float(c)


def _dp(U, syl, dsyl, ratio, skips, anchors, P=None):
    """U : unités (secondes) ; syl : syllabes de la séquence de lignes ; skips : {u0: (u1, coût)}
    (bloc répété sautable) ; anchors : {j: u} (la ligne j doit commencer à l'unité u).
    Renvoie (coût, chemin [(type, u0, u1, j0, j1, coût)])."""
    P = P or PARAMS
    M, N = len(U), len(syl)
    INF = 1e18
    D = np.full((M + 1, N + 1), INF)
    back = {}
    D[0, 0] = 0.0
    st = [u["strength"] for u in U] + [1.0]
    for u in range(M + 1):
        for j in range(N + 1):
            c0 = D[u, j]
            if c0 >= INF:
                continue

            def relax(u2, j2, c, info):
                if c0 + c < D[u2, j2]:
                    D[u2, j2] = c0 + c
                    back[(u2, j2)] = (u, j, info)
            if u < M:                                              # unité sans ligne
                dur = U[u]["t1"] - U[u]["t0"]
                relax(u + 1, j, P["p_unit_s"] * dur + P["p_unit"], ("unit", u, u + 1, j, j, 0.0))
                if u in skips:                                     # bloc répété : lignes recopiées
                    u1, cs = skips[u]
                    relax(u1, j, cs, ("repeat", u, u1, j, j, cs))
            if j < N and j not in anchors:                        # ligne non chantée
                relax(u, j + 1, P["p_line"], ("skip", u, u, j, j + 1, P["p_line"]))
            if j >= N or u >= M:
                continue
            if j in anchors and anchors[j] != u:
                continue
            gaps, n_on = [], 0
            for v in range(u, min(M, u + K_MAX)):
                if v > u:
                    gaps.append(U[v]["t0"] - U[v - 1]["t1"])
                n_on += U[v]["n_on"]
                dur = U[v]["t1"] - U[u]["t0"]
                if dur > 3.5 * syl[j] * dsyl + 1.0:
                    break
                c = _line_cost(syl[j], dur, n_on, st[u], st[v + 1], gaps, dsyl, ratio, P)
                relax(v + 1, j + 1, c, ("line", u, v + 1, j, j + 1, c))
            if j + 1 < N and (j + 1) not in anchors:              # deux lignes dans une unité
                dur = U[u]["t1"] - U[u]["t0"]
                c = _line_cost(syl[j] + syl[j + 1], dur, U[u]["n_on"], st[u], st[u + 1], [],
                               dsyl, ratio, P) + P["p_split"]
                relax(u + 1, j + 2, c, ("pair", u, u + 1, j, j + 2, c))
    path, key = [], (M, N)
    if D[M, N] >= INF:
        return INF, []
    while key != (0, 0):
        u, j, info = back[key]
        path.append(info)
        key = (u, j)
    return float(D[M, N]), path[::-1]


W_CONS = 3.0                            # poids de la cohérence des lignes de même texte


def _elem_cost(x, U, syl, dsyl, ratio, P):
    kind, u0, u1, j0, j1, c = x
    if kind == "unit":
        return P["p_unit_s"] * (U[u0]["t1"] - U[u0]["t0"]) + P["p_unit"]
    if kind == "skip":
        return P["p_line"]
    if kind == "repeat":
        return c
    st = [u["strength"] for u in U] + [1.0]
    if kind == "pair":
        return _line_cost(syl[j0] + syl[j0 + 1], U[u0]["t1"] - U[u0]["t0"], U[u0]["n_on"], st[u0],
                          st[u0 + 1], [], dsyl, ratio, P) + P["p_split"]
    gaps = [U[v]["t0"] - U[v - 1]["t1"] for v in range(u0 + 1, u1)]
    return _line_cost(syl[j0], U[u1 - 1]["t1"] - U[u0]["t0"], sum(U[v]["n_on"] for v in range(u0, u1)),
                      st[u0], st[u1], gaps, dsyl, ratio, P)


def _path_cost(path, U, syl, dsyl, ratio, P=None):
    return float(sum(_elem_cost(x, U, syl, dsyl, ratio, P or PARAMS) for x in path))


def _norm_text(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", t))


def _same_text_pairs(lines, seq) -> list[tuple[int, int]]:
    """Paires (j, j') de la séquence chantée dont le texte est (presque) identique."""
    from difflib import SequenceMatcher
    norm = [_norm_text(lines[i]["text"]) for i in seq]
    out = []
    for j in range(len(seq)):
        for k in range(j + 1, len(seq)):
            if norm[j] and (norm[j] == norm[k] or
                            SequenceMatcher(None, norm[j], norm[k]).ratio() >= 0.8):
                out.append((j, k))
    return out


def _consistency(path, U, pairs, B, a, beat_s, detail: dict | None = None) -> float:
    """Somme des max(0, similarité du chant − 0,4) sur les paires de lignes de même texte placées
    (detail : {j: meilleure similarité avec une ligne de même texte})."""
    if not pairs:
        return 0.0
    span = {}
    for x in path:
        if x[0] == "line":
            span[x[3]] = (U[x[1]]["t0"], U[x[2] - 1]["t1"])
        elif x[0] == "pair":
            span[x[3]] = span[x[3] + 1] = (U[x[1]]["t0"], U[x[1]]["t1"])
    tb0 = a.downbeats[0]
    tot = 0.0
    for j, k in pairs:
        if j not in span or k not in span:
            continue
        bj = int(round((span[j][0] - tb0) / beat_s))
        bk = int(round((span[k][0] - tb0) / beat_s))
        n = max(2, int(round((span[j][1] - span[j][0]) / beat_s)))
        if bj < 0 or bk < 0:
            continue
        sim = _occurrence_sim(B, bj, bk, n, max_lag=1)[0]
        if detail is not None:
            detail[j] = max(detail.get(j, 0.0), sim)
            detail[k] = max(detail.get(k, 0.0), sim)
        tot += max(0.0, sim - 0.4)          # même texte sur une autre mélodie (pont) : pas de malus
    return tot


def _bar_pos(a: Analysis, t: float) -> tuple[int, int, float]:
    """Temps (fichier de référence) -> (mesure 1-based, temps 0-based, position en temps dans la mesure)."""
    db = np.asarray(a.downbeats, dtype=float)
    m = max(1, int(a.beats_per_bar))
    if t < db[0]:
        L = db[1] - db[0]
        k = int(np.floor((t - db[0]) / L))
        pos = (t - (db[0] + k * L)) / L * m
    else:
        k = int(min(len(db) - 2, np.searchsorted(db, t, "right") - 1))
        pos = (t - db[k]) / (db[k + 1] - db[k]) * m
    pos = max(0.0, pos)
    return k + 1, int(min(m - 1, np.floor(pos + 1e-6))), round(float(pos), 3)


def _bar_time(a: Analysis, bar: int, pos: float) -> float:
    db = np.asarray(a.downbeats, dtype=float)
    m = max(1, int(a.beats_per_bar))
    k = bar - 1
    if 0 <= k < len(db) - 1:
        return float(db[k] + (db[k + 1] - db[k]) * pos / m)
    L = db[1] - db[0] if k < 0 else db[-1] - db[-2]
    base = db[0] + k * L if k < 0 else db[-1] + (k - len(db) + 1) * L
    return float(base + L * pos / m)


def _parse_pos(v) -> tuple[int, float] | None:
    """Une position -> (mesure 1-based, position en temps 0-based dans la mesure).
    45 -> (45, 0) ; "45.3" -> (45, 2.0) (ancien format, temps entier) ; "45:2.75" -> (45, 1.75)."""
    try:
        if isinstance(v, bool) or v is None:
            return None
        if isinstance(v, (int, float)) and float(v).is_integer():
            return int(v), 0.0
        s = str(v).strip().replace(",", ".")
        if ":" in s:
            b, beat = s.split(":", 1)
            return int(b), max(0.0, float(beat) - 1.0)
        if "." in s:
            b, beat = s.split(".", 1)
            return int(b), max(0.0, float(beat) - 1.0)
        return int(s), 0.0
    except (TypeError, ValueError):
        return None


def _parse_anchor(v) -> tuple[int, float] | None:
    """Début d'une ancre (compatibilité) : voir _parse_value."""
    pv = _parse_value(v)
    return pv["start"] if pv else None


def _parse_value(v) -> dict | None:
    """Valeur d'ancre -> {"start": (mesure, pos), "end": (mesure, pos) | None} ; None si invalide."""
    if isinstance(v, dict):
        st = _parse_pos(v.get("debut", v.get("start")))
        en = v.get("fin", v.get("end"))
        return {"start": st, "end": _parse_pos(en) if en is not None else None} if st else None
    if isinstance(v, str) and "-" in v.strip()[1:]:
        a, b = v.strip().split("-", 1)
        st, en = _parse_pos(a), _parse_pos(b)
        return {"start": st, "end": en} if st else None
    st = _parse_pos(v)
    return {"start": st, "end": None} if st else None


_KEY = re.compile(r"^\s*(\d+)\s*(?:#\s*(\d+))?\s*$")


def read_calage(lyrics_path) -> dict:
    """paroles_calage.json à côté des paroles -> {"anchors": {(ligne 1-based, occurrence 1-based):
    {"start": (mesure, pos), "end": … | None}}, "off": {lignes non chantées}}."""
    out = {"anchors": {}, "off": set()}
    p = calage_file(lyrics_path)
    if p is None:
        return out
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return out
    for k, v in (raw.items() if isinstance(raw, dict) else []):
        m = _KEY.match(str(k))
        if not m:
            continue
        line, occ = int(m.group(1)), int(m.group(2) or 1)
        if v is None:
            if occ == 1:
                out["off"].add(line)
            continue
        pv = _parse_value(v)
        if pv:
            out["anchors"][(line, occ)] = pv
    return out


def read_anchors(lyrics_path) -> dict[int, tuple[int, float]]:
    """Débuts des 1res occurrences : {n° de ligne 1-based: (mesure, position en temps)}."""
    return {ln: a["start"] for (ln, occ), a in read_calage(lyrics_path)["anchors"].items() if occ == 1}


def calage_complete(lines: list[dict], calage: dict | None) -> bool:
    """Chaque ligne a une ancre de 1re occurrence ou est déclarée non chantée."""
    if not calage or not lines:
        return False
    have = {ln for (ln, occ) in calage["anchors"] if occ == 1} | set(calage["off"])
    return all(x["line"] in have for x in lines)


def _entry(a, line: dict, t0: float, t1: float, occ: int, conf: float = 1.0, start=None, end=None) -> dict:
    """Ligne calée ; start/end = (mesure, pos) exacts de l'ancre si connus (sinon depuis le temps)."""
    bar, beat, pos = _bar_pos(a, t0)
    if start:
        bar, pos = start[0], round(float(start[1]), 3)
        beat = int(min(max(1, int(a.beats_per_bar)) - 1, math.floor(pos + 1e-6)))
    eb, _, ep = _bar_pos(a, t1)
    if end:
        eb, ep = end[0], round(float(end[1]), 3)
    return {"i": line["i"], "line": line["line"], "t": round(t0, 3), "end": round(t1, 3), "bar": bar,
            "beat": beat, "pos": pos, "end_bar": eb, "end_pos": ep, "text": line["text"],
            "confidence": round(conf, 2), "copy": occ > 1, "occ": occ, "anchored": True}


def lyrics_from_calage(a: Analysis, lines: list[dict], calage: dict) -> list[dict]:
    """Calage entièrement donné par les ancres (calage_complete) : aucune analyse audio."""
    by_line = {x["line"]: x for x in lines}
    occ = []
    for (ln, k), an in calage["anchors"].items():
        if ln in by_line and ln not in calage["off"]:
            occ.append((_bar_time(a, *an["start"]), ln, k, an))
    occ.sort()
    out = []
    for n, (t0, ln, k, an) in enumerate(occ):
        if an["end"]:
            t1 = _bar_time(a, *an["end"])
        else:
            nxt = occ[n + 1][0] - 0.05 if n + 1 < len(occ) else t0 + 8.0
            t1 = min(nxt, t0 + 0.3 * syllables(by_line[ln]["text"]))
        t1 = max(t1, t0 + 0.2)
        out.append(_entry(a, by_line[ln], t0, t1, k, start=an["start"], end=an["end"]))
    return out


def apply_calage(a: Analysis, lines: list[dict], out: list[dict], calage: dict) -> list[dict]:
    """Calage partiel : fins et occurrences #k ancrées remplacent les lignes calées correspondantes
    (même ligne, à moins de 4 mesures) ou s'ajoutent ; lignes non chantées retirées."""
    by_line = {x["line"]: x for x in lines}
    out = [o for o in out if o["line"] not in calage["off"]]
    bar_s = (a.downbeats[-1] - a.downbeats[0]) / max(1, len(a.downbeats) - 1)
    for (ln, k), an in sorted(calage["anchors"].items()):
        if ln not in by_line or ln in calage["off"]:
            continue
        t0 = _bar_time(a, *an["start"])
        same = [o for o in out if o["line"] == ln and abs(o["t"] - t0) <= 4 * bar_s]
        old = min(same, key=lambda o: abs(o["t"] - t0)) if same else None
        if old is None and k == 1 and not an["end"]:
            continue
        if an["end"]:
            t1 = _bar_time(a, *an["end"])
        elif old is not None:
            t1 = old["end"] + (t0 - old["t"])
        else:
            t1 = t0 + 0.3 * syllables(by_line[ln]["text"])
        if old is not None:
            out.remove(old)
        out.append(_entry(a, by_line[ln], t0, max(t1, t0 + 0.2), k, start=an["start"], end=an["end"]))
    out.sort(key=lambda o: o["t"])
    return out


def _split_unit(U, t, F):
    """Coupe l'unité qui contient t (secondes) ; renvoie l'index de l'unité qui commence à t."""
    for i, u in enumerate(U):
        if u["t0"] - 1e-6 <= t < u["t1"]:
            if t - u["t0"] < 0.05:
                return i
            v = dict(u, t0=t, strength=1.0)
            u2 = dict(u, t1=t)
            on = F["onsets"] * FR
            u2["n_on"] = int(((on >= u2["t0"] - 0.05) & (on < t)).sum())
            v["n_on"] = max(0, u["n_on"] - u2["n_on"])
            U[i:i + 1] = [u2, v]
            return i + 1
    return None


def align_lyrics(a: Analysis, items: list[dict] | None, lines: list[dict],
                 anchors: dict[int, tuple[int, float]] | None = None, y_voice: np.ndarray | None = None,
                 stats: dict | None = None) -> list[dict]:
    """Cale les lignes (read_lyrics) sur le chant. Temps dans le fichier de référence.
    Sortie triée : [{"i", "line", "t", "end", "bar", "beat", "pos", "end_bar", "end_pos", "text",
    "confidence", "copy"}] ; bar 1-based, beat 0-based, pos = position en temps dans la mesure (float),
    copy = ligne recopiée d'une occurrence précédente (refrain non réécrit dans le fichier)."""
    if not lines:
        return []
    if y_voice is None:
        src = _voice_source(a, items)
        if not src:
            raise ValueError(_t("no_voice_stem"))
        import librosa
        y = librosa.load(src[0], sr=SR, mono=True)[0]
        n = int((a.downbeats[-1] + 2.0) * SR)
        y_voice = _place(y, src[1], SR, max(n, len(y) + max(0, int(round(src[1] * SR)))))
    F = vocal_features(y_voice)
    U = detect_units(F)
    for u in U:
        u["t0"], u["t1"] = u["s"] * FR, u["e"] * FR
    # séquence chantée attendue : lignes répétées (« x2 ») dépliées
    seq = [ln["i"] for ln in lines for _ in range(int(ln.get("repeat", 1)))]
    syl = [float(syllables(lines[i]["text"])) for i in seq]
    # ancres manuelles -> (index dans la séquence, unité)
    anc_t = {}
    for num, (bar, pos) in (anchors or {}).items():
        js = [j for j, i in enumerate(seq) if lines[i]["line"] == num]
        if js:
            anc_t[js[0]] = _bar_time(a, bar, pos)
    for j, t in sorted(anc_t.items(), key=lambda x: x[1]):
        near = [k for k, u in enumerate(U) if abs(u["t0"] - t) <= 0.5 * 60 / max(a.bpm, 1)]
        if not near and _split_unit(U, t, F) is None:
            later = [k for k, u in enumerate(U) if 0 <= u["t0"] - t <= 4 * 60 / max(a.bpm, 1)]
            if not later:
                U.append({"t0": t, "t1": t + 0.5, "strength": 1.0, "n_on": 1})
                U.sort(key=lambda u: u["t0"])
    anc = {}
    for j, t in anc_t.items():
        k = int(np.argmin([abs(u["t0"] - t) if u["t0"] >= t - 0.4 else 1e9 for u in U]))
        anc[j] = k
    # blocs répétés sautables
    B = _beat_feats(F, _beat_grid(a))
    reps = repeated_sections(a, F, B)
    skips, rep_info = {}, {}
    for r in reps:
        if r["sim"] < REPEAT_MIN_SIM:
            continue
        s = a.sections[r["occ"]]
        t0 = a.downbeats[s.start_bar] - 0.25 * 60 / max(a.bpm, 1)
        t1 = a.downbeats[min(s.end_bar, len(a.downbeats) - 1)] - 0.25 * 60 / max(a.bpm, 1)
        us = [k for k, u in enumerate(U) if t0 <= u["t0"] < t1]
        if not us or any(k in anc.values() for k in us):
            continue
        skips[us[0]] = (us[-1] + 1, 0.3 + 2.0 * (1 - r["sim"]))
        rep_info[us[0]] = r
    # recherche de la durée par syllabe, puis réestimation sur les lignes calées
    ratio = 0.7
    best = None
    for dsyl in np.geomspace(0.10, 0.36, 12):
        c, p = _dp(U, syl, dsyl, ratio, skips, anc)
        if best is None or c < best[0]:
            best = (c, p, dsyl)
    for _ in range(2):
        _, p, dsyl = best
        ls = [x for x in p if x[0] == "line"]
        if len(ls) >= 4:
            dsyl = float(np.median([(U[x[2] - 1]["t1"] - U[x[1]]["t0"]) / syl[x[3]] for x in ls]))
            ratio = float(np.clip(np.median([sum(U[k]["n_on"] for k in range(x[1], x[2])) / syl[x[3]]
                                             for x in ls]), 0.3, 1.5))
        c, p = _dp(U, syl, dsyl, ratio, skips, anc)
        best = (c, p, dsyl)
    _, path0, dsyl = best
    # variantes de réglage : candidats, puis choix global avec la cohérence des lignes répétées
    # dans le fichier (même texte -> chant semblable), et confiance = accord entre candidats
    cands = [path0]
    for v in VARIANTS:
        P = dict(PARAMS, **{k: w for k, w in v.items() if not k.startswith("_")})
        cands.append(_dp(U, syl, dsyl * v.get("_dsyl", 1.0), ratio, skips, anc, P)[1])
    pairs = _same_text_pairs(lines, seq)
    beat_s = 60.0 / max(a.bpm, 1)

    def score(p):
        c = _path_cost(p, U, syl, dsyl, ratio)
        return c - W_CONS * _consistency(p, U, pairs, B, a, beat_s), c
    scored = [score(p) for p in cands]
    k_best = int(np.argmin([x[0] for x in scored]))
    path, cost = cands[k_best], scored[k_best][1]

    def starts_of(p):
        st = {}
        for x in p:
            if x[0] == "line":
                st[x[3]] = x[1]
            elif x[0] == "pair":
                st[x[3]] = x[1]
                st[x[3] + 1] = (x[1], "pair")
        return st
    starts = starts_of(path)
    close = [k for k, x in enumerate(scored) if k != k_best and x[0] <= scored[k_best][0] + 2.5]
    agree = {j: 1.0 for j in starts}
    for j in agree:
        if close:
            agree[j] = sum(starts_of(cands[k]).get(j) == starts[j] for k in close) / len(close)
    rep_sim = {}
    _consistency(path, U, pairs, B, a, beat_s, rep_sim)
    on_t = F["onsets"] * FR
    placed = []
    for kind, u0, u1, j0, j1, c in path:
        if kind == "line":
            conf = float(np.exp(-c / 3.0)) * (0.4 + 0.6 * agree[j0])
            if rep_sim.get(j0, 0) >= 0.6:            # même texte chanté pareil ailleurs : confirmé
                conf = max(conf, 0.9 * rep_sim[j0])
            placed.append((seq[j0], U[u0]["t0"], U[u1 - 1]["t1"], conf, j0))
        elif kind == "pair":
            t0, t1 = U[u0]["t0"], U[u0]["t1"]
            tm = t0 + (t1 - t0) * syl[j0] / (syl[j0] + syl[j0 + 1])
            cand = on_t[(on_t > t0 + 0.2) & (on_t < t1 - 0.2)]
            if len(cand):
                tm = float(cand[np.argmin(np.abs(cand - tm))])
            conf = float(np.exp(-c / 3.0)) * 0.8 * (0.4 + 0.6 * agree[j0 + 1])
            placed.append((seq[j0], t0, tm, conf, j0))
            placed.append((seq[j0 + 1], tm, t1, conf, j0 + 1))
    for j, t in anc_t.items():                     # une ancre fixe le début (recalé sur l'attaque
        for k, x in enumerate(placed):             # chantée si elle est à moins d'un demi-temps)
            if x[4] == j:
                if abs(x[1] - t) <= 0.5 * 60.0 / max(a.bpm, 1):
                    t = x[1]
                placed[k] = (x[0], t, max(x[2], t + 0.3), 1.0, j)
    out = []
    for i, t0, t1, conf, _ in placed:
        bar, beat, pos = _bar_pos(a, t0)
        out.append({"i": i, "line": lines[i]["line"], "t": round(t0, 3), "end": round(t1, 3), "bar": bar,
                    "beat": beat, "pos": pos, "text": lines[i]["text"], "confidence": round(conf, 2),
                    "copy": False})
    # recopie des lignes des blocs répétés depuis leur 1re occurrence
    n_copy = 0
    act = F["dbs"] > F["thr"]
    for kind, u0, u1, *_ in path:
        if kind != "repeat":
            continue
        r = rep_info[u0]
        ref, occ = a.sections[r["ref"]], a.sections[r["occ"]]
        L = max(1, min(ref.end_bar - ref.start_bar, occ.end_bar - occ.start_bar))
        t_ref0 = a.downbeats[ref.start_bar] - 0.25 * 60 / max(a.bpm, 1)
        t_ref1 = a.downbeats[min(ref.start_bar + L, len(a.downbeats) - 1)] - 0.25 * 60 / max(a.bpm, 1)
        for x in [o for o in out if not o["copy"] and t_ref0 <= o["t"] < t_ref1]:
            bar = x["bar"] + r["shift_bars"]
            t0 = _bar_time(a, bar, x["pos"])
            eb, _, epos = _bar_pos(a, x["end"])
            t1 = _bar_time(a, eb + r["shift_bars"], epos)
            f0 = int(t0 / FR)
            live = act[max(0, f0 - 8): f0 + 12].any() if f0 < len(act) else False
            conf = x["confidence"] * r["sim"] * (1.0 if live else 0.3)
            beat_s = 60.0 / max(a.bpm, 1)
            near = [u for u in U if abs(u["t0"] - t0) <= 0.75 * beat_s]
            if near:                                   # recalé sur l'attaque réelle de la phrase
                u = min(near, key=lambda u: abs(u["t0"] - t0))
                t1 += u["t0"] - t0
                t0 = u["t0"]
                live = True
            b2, beat2, pos2 = _bar_pos(a, t0)
            out.append(dict(x, t=round(t0, 3), end=round(t1, 3), bar=b2, beat=beat2, pos=pos2,
                            confidence=round(float(conf), 2), copy=True))
            n_copy += 1
    out.sort(key=lambda o: o["t"])
    for o in out:
        o["end_bar"], _, o["end_pos"] = _bar_pos(a, o["end"])
    if stats is not None:
        stats.update({
            "units": len(U), "dsyl": round(dsyl, 3), "onset_ratio": round(ratio, 2), "cost": round(cost, 2),
            "lines_placed": len({o["i"] for o in out}), "lines_total": len(lines),
            "lines_skipped": sorted({seq[x[3]] for x in path if x[0] == "skip"}),
            "units_without_line": [(round(U[x[1]]["t0"], 2), round(U[x[1]]["t1"] - U[x[1]]["t0"], 2))
                                   for x in path if x[0] == "unit"],
            "repeats": reps, "copies": n_copy,
        })
    return out


# --------------------------------------------------------------------------- #
# Cache disque
# --------------------------------------------------------------------------- #
def lyrics_cache_key(a: Analysis, items: list[dict] | None, path: Path) -> str:
    """Clé : contenu des paroles + corrections + fichiers + décalages + grille + sections + version."""
    src = _voice_source(a, items)
    try:
        h = hashlib.md5(Path(path).read_bytes()).hexdigest()
    except OSError:
        h = None
    try:
        cf = calage_file(path)
        hc = hashlib.md5(cf.read_bytes()).hexdigest() if cf else None
    except OSError:
        hc = None
    voice_stamp = None
    if src:
        try:
            stat = Path(src[0]).stat()
            voice_stamp = [stat.st_size, stat.st_mtime_ns]
        except OSError:
            pass
    timing_hash = None
    if path.name.lower() == AUTO_NAME.lower():
        from .lyrics_auto import timing_path
        try:
            timing_hash = hashlib.md5(timing_path(path).read_bytes()).hexdigest()
        except OSError:
            pass
    files = [d["file"] for d in items] if items else [a.file]
    return hashlib.md5(json.dumps([h, hc, files, [src[0], round(src[1], 4)] if src else None,
                                   [round(float(x), 4) for x in a.downbeats], a.beats_per_bar,
                                   [(s.start_bar, s.end_bar, s.name) for s in a.sections],
                                   VERSION, timing_hash, voice_stamp]).encode()).hexdigest()


def cached_lyrics(a: Analysis, items: list[dict] | None, cache=None, path=None) -> list[dict] | None:
    """Paroles calées (align_lyrics) avec cache disque ; None s'il n'y a pas de fichier de paroles.
    path : fichier de paroles (sinon cherché à côté des stems / du fichier audio)."""
    if path is None:
        files = [d["file"] for d in items] if items else [a.file] + list((a.stems or {}).values())
        path = find_lyrics_file(files)
        if not path:                    # pas de paroles de l'utilisateur : brouillon automatique (Whisper)
            try:
                from . import lyrics_auto
                path = lyrics_auto.ensure_auto_lyrics(a, items, files)
            except Exception:           # noqa: BLE001 - jamais bloquant : pas de paroles, comme avant
                path = None
    if not path:
        return None
    path = Path(path)
    auto = path.name.lower() == AUTO_NAME.lower()
    if cache is None:
        from .bridge import BRIDGE_DIR
        cache = BRIDGE_DIR / "prompter_lyrics.json"
    cache = Path(cache)
    ck = lyrics_cache_key(a, items, path)
    try:
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("key") == ck:
            return _mark_auto(_with_words(a, items, c["lyrics"], cache), auto)
    except Exception:
        pass
    lines = read_lyrics(path)
    cal = read_calage(path)
    preserved = None
    if auto:
        from . import lyrics_auto
        preserved = lyrics_auto.timed_draft(a, items, path, lines)
    if preserved is not None:
        res = apply_calage(a, lines, preserved, cal) if cal["anchors"] or cal["off"] else preserved
    elif calage_complete(lines, cal):
        res = lyrics_from_calage(a, lines, cal)          # ancres exactes : pas d'analyse audio
    else:
        res = align_lyrics(a, items, lines, anchors=read_anchors(path))
        if cal["anchors"] or cal["off"]:
            res = apply_calage(a, lines, res, cal)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": ck, "lyrics": res}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return _mark_auto(_with_words(a, items, res, cache), auto)


def _mark_auto(res: list[dict] | None, auto: bool) -> list[dict] | None:
    """Lignes venues du brouillon automatique : "auto": True (mention sur la grille PDF)."""
    if auto and res:
        for o in res:
            o["auto"] = True
    return res


def _with_words(a: Analysis, items: list[dict] | None, res: list[dict], cache: Path) -> list[dict]:
    """Calage mot par mot (words.py, composant optionnel) à l'intérieur des lignes calées ; son propre cache
    (<cache>_words.json) : le cache des lignes ne dépend pas du composant. Jamais bloquant."""
    try:
        from . import words
        return words.add_words(a, items, res, cache=cache.with_name(cache.stem + "_words.json"))
    except Exception:                                   # noqa: BLE001 - lignes seules
        return res
