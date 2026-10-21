"""Chemins dépendant de l'OS (Windows simulé)."""
import sys
from pathlib import Path

from reacue_mcp import bridge, lyrics


def test_bridge_resource_dir_windows(monkeypatch):
    monkeypatch.delenv("REAPER_RESOURCE_PATH", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", "C:\\Users\\Zoé\\AppData\\Roaming")
    assert bridge.default_resource_dir() == Path("C:\\Users\\Zoé\\AppData\\Roaming") / "REAPER"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert bridge.default_resource_dir() == Path.home() / "Library" / "Application Support" / "REAPER"
    monkeypatch.setenv("REAPER_RESOURCE_PATH", "D:\\REAPER portable")
    assert bridge.default_resource_dir() == Path("D:\\REAPER portable")


def test_to_lua_windows_paths_and_accents():
    s = bridge.to_lua({"file": "C:\\Users\\Zoé\\Stems \"live\"\\drums.wav", "n": [1, 2.5, None, True]})
    assert '"C:\\\\Users\\\\Zoé\\\\Stems \\"live\\"\\\\drums.wav"' in s


def test_textutil_only_on_macos(tmp_path, monkeypatch):
    p = tmp_path / "paroles.rtf"
    p.write_bytes(b"{\\rtf1\\ansi\\ansicpg1252 Premi\\'e8re ligne\\par Deuxi\\'e8me\\par}")
    called = []
    monkeypatch.setattr(lyrics.shutil, "which", lambda n: "/usr/bin/textutil")
    monkeypatch.setattr(lyrics.subprocess, "run", lambda *a, **k: called.append(a) or (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(lyrics.sys, "platform", "win32")
    assert lyrics.read_lyrics(p)[0]["text"] == "Première ligne" and not called
    monkeypatch.setattr(lyrics.sys, "platform", "darwin")
    lyrics.read_lyrics(p)
    assert called                                       # macOS : textutil essayé d'abord


def test_lyrics_files_and_timing_names(tmp_path):
    (tmp_path / "Demo-drums.wav").write_bytes(b"")
    (tmp_path / "lyrics.txt").write_text("Line one\r\nLine two\r\n", encoding="utf-8")
    f = lyrics.find_lyrics_file([str(tmp_path / "Demo-drums.wav")])
    assert f.name == "lyrics.txt"
    assert [x["text"] for x in lyrics.read_lyrics(f)] == ["Line one", "Line two"]
    (tmp_path / "lyrics_timing.json").write_text('{"1": "3:1-4:1", "2": null}', encoding="utf-8")
    cal = lyrics.read_calage(f)
    assert cal["anchors"][(1, 1)]["start"] == (3, 0.0) and 2 in cal["off"]
    (tmp_path / "paroles_calage.json").write_text('{"1": "5"}', encoding="utf-8")
    assert lyrics.read_calage(f)["anchors"][(1, 1)]["start"] == (5, 0.0)      # nom français prioritaire


def test_missing_stems_give_localized_errors():
    import pytest
    from reacue_mcp import drums, i18n
    from reacue_mcp.analysis import Analysis
    a = Analysis(file="x.wav", duration=10, bpm=120, beats_per_bar=4, denominator=4, tempo_stable=True,
                 tempo_cv=0, beats=[], downbeats=[0, 2, 4])
    i18n.set_lang("en")
    try:
        with pytest.raises(ValueError, match="no vocal stem"):
            lyrics.align_lyrics(a, None, [{"i": 0, "line": 1, "text": "la la", "repeat": 1}])
        with pytest.raises(ValueError, match="no drum stem"):
            drums.detect_drums(a, None)
    finally:
        i18n.set_lang("fr")
