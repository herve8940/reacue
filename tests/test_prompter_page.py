"""La page du prompteur s'affiche sans erreur console, en français et en anglais (Chromium headless)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip("playwright")
sys.path.insert(0, str(ROOT / "tools"))


def test_page_no_console_errors_fr_en():
    import make_screenshots as M
    try:
        M.run(None, check_only=True)
    except SystemExit as e:
        pytest.fail(str(e))
    except Exception as e:                      # Chromium absent : non bloquant
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium non installé")
        raise


def test_demo_song_is_fictional_and_complete():
    import make_screenshots as M
    for lang in ("fr", "en"):
        s = M.demo_song(lang)
        assert s["title"] == "Demo Song" and s["language"] == lang
        assert len(s["bar_times"]) == s["n_bars"] + s["count_in_bars"] + 1
        assert s["lyrics"] and s["chords"] and s["drums"]["bars"]
    assert M.demo_song("en")["sections"][3]["name"] == "Chorus 1"
