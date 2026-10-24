"""Grille du morceau en PDF (reacue_mcp/sheet.py) : contenu, mise en page, intégration à la publication."""
import json
import subprocess
import shutil
from pathlib import Path

import pytest

from reacue_mcp import cli, sheet

from test_cli import FakeBridge, env, status  # noqa: F401  (fixture)

BT = [2.0 * k for k in range(60)]          # mesure k du morceau (1-based) = BT[k + 1] (count-in 2)


def song(**kw):
    s = {"title": "Chanson d'essai – démo", "bpm": 120, "beats_per_bar": 4, "count_in_bars": 2, "n_bars": 24,
         "bar_times": BT, "key": {"chord": "Am"},
         "sections": [{"name": "Intro", "start_bar": 1, "end_bar": 4, "color": "#5a7fa8"},
                      {"name": "Couplet 1", "start_bar": 5, "end_bar": 14, "color": "#3e9e7a"},
                      {"name": "Refrain 1", "start_bar": 15, "end_bar": 24, "color": "#c2554f"}],
         "chords": [{"bar": b, "chords": [{"beat": 0, "chord": "Am"}] + ([{"beat": 2, "chord": "E7"}] if b % 4 == 0 else [])}
                    for b in range(1, 25)],
         # ligne chantée sur les mesures 5 et 6 : 4 mots -> 2 + 2
         "lyrics": [{"t": BT[6], "end": BT[8], "text": "un deux trois quatre", "bar": 5}],
         "activity": {"vocals": [0] * 4 + [1] * 20}}
    s.update(kw)
    return s


def pdf_text(data: bytes, tmp_path) -> str:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext absent")
    f = tmp_path / "x.pdf"
    f.write_bytes(data)
    return subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True, check=True).stdout


def test_bar_chords_and_lyrics():
    s = song()
    ch = sheet.bar_chords(s)
    assert ch[1] == ["Am"] and ch[4] == ["Am", "E7"]
    # deux temps du même accord : une seule case
    s2 = song(chords=[{"bar": 1, "chords": [{"beat": 0, "chord": "C"}, {"beat": 2, "chord": "C"}]}])
    assert sheet.bar_chords(s2) == {1: ["C"]}
    assert sheet.bar_lyrics(s) == {5: "un deux", 6: "trois quatre"}


def test_bar_lyrics_uses_word_times():
    # mesure 5 = 12-14 s, mesure 6 = 14-16 s : « un » seul en mesure 5, le reste en mesure 6 (dont « deux »,
    # attaqué 20 ms avant la barre : reste dans la mesure 6) ; la répartition régulière aurait donné 2 + 2
    words = [{"w": "un", "t": 12.1, "end": 12.8}, {"w": "deux", "t": 13.98, "end": 14.4},
             {"w": "trois", "t": 14.5, "end": 15.0}, {"w": "quatre", "t": 15.2, "end": 15.9}]
    s = song(lyrics=[{"t": 12.1, "end": 15.9, "text": "un deux trois quatre", "bar": 5, "words": words}])
    assert sheet.bar_lyrics(s) == {5: "un", 6: "deux trois quatre"}
    # mots vides ou mal formés : ignorés ; aucun mot exploitable -> répartition régulière (comportement d'avant)
    s = song(lyrics=[{"t": BT[6], "end": BT[8], "text": "un deux trois quatre", "bar": 5,
                      "words": [{"w": "", "t": 12.0}, {"w": "x"}]}])
    assert sheet.bar_lyrics(s) == {5: "un deux", 6: "trois quatre"}


def test_key_from_name_or_estimated():
    assert sheet.song_key(song()) == ("Am", False)
    assert sheet.song_key(song(key=None)) == ("Am", True)
    assert sheet.song_key(song(key=None, chords=[])) == (None, False)


def test_song_folder_stems():
    assert sheet.song_folder(["/x/Song/Song-stems/htdemucs/Song-vocals.wav"]) == Path("/x/Song")
    assert sheet.song_folder(["/x/Song/Song-stems/Song-vocals.wav"]) == Path("/x/Song")
    assert sheet.song_folder(["/x/Song/Song.mp3"]) == Path("/x/Song")
    assert sheet.song_folder([]) is None


def test_pdf_content_fr_en(tmp_path, monkeypatch):
    data = sheet.build_pdf(song(), lang="fr")
    assert data.startswith(b"%PDF-1.4") and data.rstrip().endswith(b"%%EOF")
    txt = pdf_text(data, tmp_path)
    for s in ("Chanson d'essai – démo", "Tempo : 120 BPM", "Tonalité : Am", "Intro", "Couplet 1", "10 mes.",
              "Refrain 1", "E7", "un deux", "trois quatre", "1/1"):
        assert s in txt, (s, txt)
    txt = pdf_text(sheet.build_pdf(song(key=None), lang="en"), tmp_path)
    assert "Key: Am (estimated)" in txt and "10 bars" in txt and "Tempo: 120 BPM" in txt


def test_long_song_paginates_and_long_lyrics_fit(tmp_path):
    secs = [{"name": f"Couplet {i}", "start_bar": 1 + 16 * (i - 1), "end_bar": 16 * i} for i in range(1, 9)]
    long = "mot " * 40
    s = song(n_bars=128, sections=secs, bar_times=[2.0 * k for k in range(140)],
             lyrics=[{"t": 2.0 * (b + 1), "end": 2.0 * (b + 2), "text": long, "bar": b} for b in range(1, 128, 2)],
             chords=[], key=None)
    txt = pdf_text(sheet.build_pdf(s), tmp_path)
    assert "1/2" in txt and "2/2" in txt and "…" in txt
    assert txt.count("Couplet 8") >= 1


def test_publish_writes_sheet_in_song_folder(env, lang, bridge_dir, resdir, tmp_path):
    lang("fr")
    assert cli.main(["prepare", "--resource-dir", str(resdir)]) == 0
    pdfs = list((tmp_path / "song").glob("Grille - *.pdf"))
    assert len(pdfs) == 1 and pdfs[0].read_bytes().startswith(b"%PDF")
    assert "Grille PDF : Grille - " in status(bridge_dir)["message"]
    # publication seule : la grille est réécrite
    pdfs[0].unlink()
    assert cli.main(["publish", "--resource-dir", str(resdir)]) == 0
    assert list((tmp_path / "song").glob("Grille - *.pdf"))
    # échec de la grille : jamais bloquant, simple avertissement
    import reacue_mcp.server as server
    def boom(*a, **k):
        raise OSError("disque plein")
    server.sheet.write_sheet, old = boom, server.sheet.write_sheet
    try:
        assert cli.main(["publish", "--resource-dir", str(resdir)]) == 0
        assert "Grille PDF non créée : disque plein" in status(bridge_dir)["message"]
    finally:
        server.sheet.write_sheet = old
