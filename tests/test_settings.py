import json

from reacue_mcp import settings
from reacue_mcp.planner import Options


def test_defaults_are_authors(tmp_path):
    s = settings.load_settings(tmp_path / "absent.json")
    assert s["language"] == "fr" and s["count_in_bars"] == 2 and s["cue_lead_bars"] == 2
    assert s["count_lang"] == "en" and s["voice_count_each"] is True
    o = Options(**settings.option_defaults(s))
    assert o.count_in_bars == 2 and o.count_lang == "en" and o.voice_name is None


def test_partial_and_bad_values(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"language": "EN", "count_in_bars": 1, "unknown": 5, "count_lang": "xx"}))
    s = settings.load_settings(p)
    assert s["language"] == "en" and s["count_in_bars"] == 1 and s["count_lang"] == "en"
    assert "unknown" not in s
    p.write_text("{not json")
    assert settings.load_settings(p)["language"] == "fr"


def test_bom_tolerated(tmp_path):
    p = tmp_path / "s.json"
    p.write_bytes("﻿".encode("utf-8") + b'{"language": "en"}')    # Bloc-notes Windows
    assert settings.load_settings(p)["language"] == "en"


def test_server_new_options_uses_settings(lang):
    lang("en", count_in_bars=4, announce_voice="Microsoft Zira Desktop")
    from reacue_mcp import server
    o = server._new_options(count_in_bars=None, cue_lead_bars=3)
    assert o.count_in_bars == 4 and o.cue_lead_bars == 3 and o.voice_name == "Microsoft Zira Desktop"
