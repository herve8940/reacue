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


def _with_words(song):
    """Paroles du morceau de démo avec des temps de mots fictifs (répartis sur la ligne)."""
    for ln in song["lyrics"]:
        ws = ln["text"].split()
        d = (ln["end"] - ln["t"]) / len(ws)
        ln["words"] = [{"w": w, "t": round(ln["t"] + k * d, 4), "end": round(ln["t"] + (k + 0.8) * d, 4)}
                       for k, w in enumerate(ws)]
    return song


@pytest.mark.parametrize("words", [True, False])
def test_vocals_word_highlight(words):
    """Calage mot par mot : le mot en cours est surligné (span .wd.now), les précédents estompés ;
    sans "words", la ligne reste du texte simple (comportement d'avant)."""
    import make_screenshots as M
    try:
        from playwright.sync_api import sync_playwright
        song = M.demo_song("fr")
        if words:
            _with_words(song)
        ln = next(x for x in song["lyrics"] if len(x["text"].split()) >= 3)
        pos = ln["t"] + 0.55 * (ln["end"] - ln["t"])
        M.FakeReaper.song, M.FakeReaper.pos = song, pos
        srv, base = M.serve()
        errors = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport=M.PHONE)
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(f"{base}/prompteur.html?role=vocals&lang=fr")
                page.wait_for_function("document.getElementById('nowName').textContent !== '—'", timeout=8000)
                page.wait_for_timeout(500)
                n_spans = page.locator("#lyLine .wd").count()
                now = page.locator("#lyLine .wd.now").all_text_contents()
                done = page.locator("#lyLine .wd.done").count()
                line = page.text_content("#lyLine")
                browser.close()
        finally:
            srv.shutdown()
    except Exception as e:                      # Chromium absent : non bloquant
        if "Executable doesn't exist" in str(e):
            pytest.skip("Chromium non installé")
        raise
    assert not errors, errors
    assert " ".join(line.split()) == " ".join(ln["text"].split())
    if not words:
        assert n_spans == 0
        return
    ws = ln["words"]
    k = max(j for j, w in enumerate(ws) if w["t"] <= pos + 0.03)
    assert n_spans == len(ws) and now == [ws[k]["w"]] and done == k
