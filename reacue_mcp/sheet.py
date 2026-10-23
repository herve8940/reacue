"""Grille du morceau en PDF (A4), à imprimer : titre, tempo, tonalité, puis chaque section en grille
de 4 mesures par ligne avec l'accord de chaque mesure (case coupée s'il y en a deux) et, s'il y a des
paroles, le bout de texte chanté dans la mesure (case colorée).

Construite à partir des données du prompteur (prompter.build_song) : ce que montre le PDF est ce que
voient les téléphones. Écriture PDF autonome (polices standard Helvetica, encodage WinAnsi) : aucune
dépendance supplémentaire."""
from __future__ import annotations

import re
import zlib
from collections import Counter
from pathlib import Path

from .i18n import t

# largeurs des glyphes (1/1000 em), octets cp1252 32..255 : polices standard PDF (métriques AFM d'Adobe)
_W_REG = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 761,
    556, 556, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 556, 611, 556,
    556, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 556, 500, 667,
    278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
]
_W_BOLD = [
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 761,
    556, 556, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 556, 611, 556,
    556, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 556, 500, 667,
    278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278,
    611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556,
]

PAGE_W, PAGE_H = 595.28, 841.89          # A4 en points
MARGIN = 48
COLS = 4                                  # mesures par ligne
SUNG = (0.984, 0.894, 0.835)              # case chantée (saumon clair)
LYRIC = (0.75, 0.0, 0.0)                  # paroles (rouge)
GRID = (0.0, 0.0, 0.0)
GREY = (0.45, 0.45, 0.45)


# --------------------------------------------------------------------------- #
# Texte : encodage WinAnsi et largeurs
# --------------------------------------------------------------------------- #
_SUBST = {"♯": "#", "♭": "b", "\u00a0": " "}


def _enc(s: str) -> bytes:
    s = "".join(_SUBST.get(c, c) for c in str(s))
    return s.encode("cp1252", errors="replace")


def text_width(s: str, size: float, bold: bool = False) -> float:
    w = _W_BOLD if bold else _W_REG
    return sum(w[b - 32] if 32 <= b <= 255 else 556 for b in _enc(s)) * size / 1000.0


def _esc(b: bytes) -> bytes:
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def fit(s: str, width: float, size: float, min_size: float, bold: bool = False) -> tuple[str, float]:
    """Réduit la taille jusqu'à min_size, puis coupe avec « … » ; renvoie (texte, taille)."""
    while size > min_size and text_width(s, size, bold) > width:
        size = round(size - 0.25, 2)
    if text_width(s, size, bold) <= width:
        return s, size
    while s and text_width(s + "…", size, bold) > width:
        s = s[:-1]
    return (s.rstrip() + "…") if s else "", size


class _Page:
    def __init__(self):
        self.ops: list[bytes] = []

    def rect(self, x, y, w, h, fill=None, stroke=GRID, lw=0.6):
        o = b""
        if fill:
            o += b"%.3f %.3f %.3f rg " % fill
        if stroke:
            o += b"%.3f %.3f %.3f RG %.2f w " % (*stroke, lw)
        op = b"B" if fill and stroke else (b"f" if fill else b"S")
        self.ops.append(o + b"%.2f %.2f %.2f %.2f re %s" % (x, y, w, h, op))

    def line(self, x1, y1, x2, y2, color=GRID, lw=0.6):
        self.ops.append(b"%.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S" % (*color, lw, x1, y1, x2, y2))

    def text(self, x, y, s, size=10, bold=False, color=(0, 0, 0), align="left"):
        if not s:
            return
        if align != "left":
            w = text_width(s, size, bold)
            x -= w / 2 if align == "center" else w
        self.ops.append(b"BT /%s %.2f Tf %.3f %.3f %.3f rg %.2f %.2f Td (%s) Tj ET"
                        % (b"F2" if bold else b"F1", size, *color, x, y, _esc(_enc(s))))


def _pdf_bytes(pages: list[_Page], title: str) -> bytes:
    objs: list[bytes] = []

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    cat = add(b"")                                   # rempli plus bas
    pages_id = add(b"")
    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    kids = []
    for p in pages:
        data = zlib.compress(b"\n".join(p.ops))
        c = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                        b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
                        % (pages_id, PAGE_W, PAGE_H, f1, f2, c)))
    objs[cat - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id
    objs[pages_id - 1] = (b"<< /Type /Pages /Kids [%s] /Count %d >>"
                          % (b" ".join(b"%d 0 R" % k for k in kids), len(kids)))
    info = add(b"<< /Title (%s) /Producer (ReaCue) /Creator (ReaCue) >>" % _esc(_enc(title)))
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1, cat, info, xref)
    return bytes(out)


# --------------------------------------------------------------------------- #
# Contenu de la grille
# --------------------------------------------------------------------------- #
def bar_chords(song: dict) -> dict[int, list[str]]:
    """{mesure 1-based: [accord] ou [accord1, accord2]} (deux seulement s'ils diffèrent)."""
    out = {}
    for e in song.get("chords") or []:
        names = []
        for c in sorted(e.get("chords") or [], key=lambda c: c.get("beat", 0)):
            n = str(c.get("chord") or "").strip()
            if n and (not names or names[-1] != n):
                names.append(n)
        if names:
            out[int(e["bar"])] = names[:2]
    return out


def _bar_index(song: dict, time: float) -> float:
    """Temps de la timeline -> mesure du morceau (1-based) + fraction."""
    bt = song.get("bar_times") or []
    ci = int(song.get("count_in_bars") or 0)
    if len(bt) < 2:
        return 1.0
    k = 0
    while k + 2 < len(bt) and bt[k + 1] <= time:
        k += 1
    L = (bt[k + 1] - bt[k]) or 1.0
    frac = min(max((time - bt[k]) / L, 0.0), 0.999)
    return k - ci + 1 + frac


def bar_lyrics(song: dict) -> dict[int, str]:
    """Bouts de paroles par mesure. Avec le calage mot par mot ("words" : temps réel de chaque mot), chaque
    mot va dans la mesure où il commence (à quelques centisecondes près : une attaque un rien en avance
    reste dans la mesure suivante) ; sinon les mots de la ligne sont répartis régulièrement entre son début
    et sa fin."""
    parts: dict[int, list[str]] = {}
    for ln in song.get("lyrics") or []:
        words = str(ln.get("text") or "").split()
        if not words:
            continue
        t0 = float(ln.get("t", 0.0))
        t1 = max(float(ln.get("end", t0)), t0 + 0.01)
        if not song.get("bar_times"):
            parts.setdefault(int(ln.get("bar", 1)), []).extend(words)
            continue
        timed = [w for w in (ln.get("words") or []) if isinstance(w, dict) and str(w.get("w") or "").strip()
                 and isinstance(w.get("t"), (int, float))]
        if timed:
            for w in timed:
                d = max(0.0, float(w.get("end", w["t"])) - float(w["t"]))
                tw = float(w["t"]) + min(0.05, 0.25 * d)
                parts.setdefault(int(_bar_index(song, tw)), []).extend(str(w["w"]).split())
            continue
        for k, w in enumerate(words):
            tw = t0 + (k + 0.5) / len(words) * (t1 - t0)
            parts.setdefault(int(_bar_index(song, tw)), []).append(w)
    return {b: " ".join(ws) for b, ws in parts.items()}


def song_key(song: dict) -> tuple[str | None, bool]:
    """(tonalité, estimée ?) : celle du nom de fichier, sinon l'accord le plus fréquent."""
    k = song.get("key")
    if isinstance(k, dict) and k.get("chord"):
        return k["chord"], False
    if isinstance(k, str) and k:
        return k, False
    cnt = Counter()
    for names in bar_chords(song).values():
        for n in names:
            if n != "N.C.":
                cnt[n.split("/")[0]] += 1
    return (cnt.most_common(1)[0][0], True) if cnt else (None, False)


def sheet_name(title: str, lang: str | None = None) -> str:
    safe = re.sub(r'[\\/:*?"<>|]+', " ", str(title or "Song")).strip() or "Song"
    return t("sheet_file", lang=lang, title=safe)


def song_folder(files: list[str]) -> Path | None:
    """Dossier du morceau : celui des fichiers, ou le parent d'un dossier « …-stems »."""
    if not files:
        return None
    p = Path(files[0]).parent
    for d in (p, p.parent):
        if d.name.endswith("-stems"):
            return d.parent
    return p


def build_pdf(song: dict, lang: str | None = None) -> bytes:
    title = str(song.get("title") or "Song")
    chords = bar_chords(song)
    words = bar_lyrics(song)
    vocals = (song.get("activity") or {}).get("vocals") or []
    has_lyrics = bool(words)
    bpb = int(song.get("beats_per_bar") or 4)
    W = PAGE_W - 2 * MARGIN
    cw = W / COLS
    row_h = 30.0 if has_lyrics else 22.0
    pages = [_Page()]
    pg = pages[0]

    # en-tête
    y = PAGE_H - MARGIN
    tt, ts = fit(title, W, 18, 11, bold=True)
    pg.text(PAGE_W / 2, y - 14, tt, ts, bold=True, align="center")
    y -= 34
    bpm = song.get("bpm")
    info = [t("sheet_tempo", lang=lang, bpm=f"{float(bpm):.0f}") if bpm else None, f"{bpb}/4"]
    if song.get("count_in_bars"):
        info.append(t("sheet_count_in", lang=lang, n=int(song["count_in_bars"])))
    pg.text(MARGIN, y, "   ·   ".join(i for i in info if i), 10)
    key, est = song_key(song)
    if key:
        pg.text(PAGE_W - MARGIN, y, t("sheet_key_est" if est else "sheet_key", lang=lang, k=key), 13,
                bold=True, align="right")
    y -= 26

    def new_page():
        nonlocal pg, y
        pg = _Page()
        pages.append(pg)
        y = PAGE_H - MARGIN

    def draw_row(bars, y_top):
        for c, b in enumerate(bars):
            x = MARGIN + c * cw
            lyr = words.get(b, "")
            sung = bool(lyr) if has_lyrics else (b - 1 < len(vocals) and vocals[b - 1] == 1)
            pg.rect(x, y_top - row_h, cw, row_h, fill=SUNG if sung else None)
            names = chords.get(b, [])
            cy = y_top - (12.5 if has_lyrics else 14.5)
            if len(names) == 2:
                # avec des paroles, le trait s'arrête au-dessus du texte (comme une grille écrite à la main)
                pg.line(x + cw / 2, y_top - row_h + (13 if lyr else 0), x + cw / 2, y_top)
                for j, n in enumerate(names):
                    s, sz = fit(n, cw / 2 - 6, 10, 7)
                    pg.text(x + cw / 4 + j * cw / 2, cy, s, sz, align="center")
            elif names:
                s, sz = fit(names[0], cw - 8, 10, 7)
                pg.text(x + cw / 2, cy, s, sz, align="center")
            if lyr:
                s, sz = fit(lyr, cw - 6, 8, 6)
                pg.text(x + cw / 2, y_top - row_h + 6, s, sz, color=LYRIC, align="center")

    sections = song.get("sections") or [{"name": "", "start_bar": 1, "end_bar": int(song.get("n_bars") or 0)}]
    usable = PAGE_H - 2 * MARGIN - 20
    for sec in sections:
        bars = list(range(int(sec["start_bar"]), int(sec["end_bar"]) + 1))
        rows = [bars[i:i + COLS] for i in range(0, len(bars), COLS)] or [[]]
        block = 16 + len(rows) * row_h
        room = y - MARGIN - 20
        if block > room and (block <= usable or room < 16 + 2 * row_h):
            new_page()
        label = str(sec.get("name") or "")
        col = sec.get("color")
        if isinstance(col, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", col):
            rgb = tuple(int(col[i:i + 2], 16) / 255 for i in (1, 3, 5))
            pg.rect(MARGIN, y - 9, 6, 9, fill=rgb, stroke=None)
        n = len(bars)
        pg.text(MARGIN + 10, y - 8, label, 10, bold=True)
        pg.text(MARGIN + 14 + text_width(label, 10, True), y - 8,
                t("sheet_bars", lang=lang, n=n), 8, color=GREY)
        y -= 13
        for r in rows:
            if y - row_h < MARGIN + 20:
                new_page()
                pg.text(MARGIN, y - 8, t("sheet_cont", lang=lang, name=label), 9, color=GREY)
                y -= 13
            draw_row(r, y)
            y -= row_h
        y -= 16

    total = len(pages)
    for i, p in enumerate(pages, 1):
        p.text(MARGIN, MARGIN - 16, t("sheet_footer", lang=lang), 7, color=GREY)
        p.text(PAGE_W - MARGIN, MARGIN - 16, f"{i}/{total}", 7, color=GREY, align="right")
    return _pdf_bytes(pages, title)


def write_sheet(song: dict, folder: Path, lang: str | None = None) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / sheet_name(song.get("title") or "Song", lang)
    tmp = out.with_suffix(".pdf.tmp")
    tmp.write_bytes(build_pdf(song, lang))
    tmp.replace(out)
    return out
