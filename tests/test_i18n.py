import pytest

from reacue_mcp import i18n
from reacue_mcp.i18n import localize_section, section_kind, section_color, cue_text, t


@pytest.mark.parametrize("fr,en", [
    ("Intro", "Intro"), ("Couplet 1", "Verse 1"), ("Pré-refrain 2", "Pre-chorus 2"), ("Refrain 3", "Chorus 3"),
    ("Pont", "Bridge"), ("Solo", "Solo"), ("Break", "Break"), ("Outro", "Outro"), ("Interlude", "Interlude"),
    ("Main Riff 2", "Main Riff 2"), ("Intro guitare", "Guitar intro"), ("Intro basse", "Bass intro"),
])
def test_section_names_fr_en(fr, en):
    assert localize_section(fr, "en") == en
    assert localize_section(en, "fr") == fr
    assert localize_section(fr, "fr") == fr


def test_unknown_names_kept():
    assert localize_section("Solo guitare Jimmy", "en") == "Solo guitare Jimmy"
    assert localize_section("Section E", "en") == "Section E"


@pytest.mark.parametrize("name,kind", [
    ("Refrain 2", "chorus"), ("Chorus 2", "chorus"), ("Pré-refrain", "prechorus"), ("Pre-chorus 1", "prechorus"),
    ("pre chorus", "prechorus"), ("Couplet 3", "verse"), ("Verse", "verse"), ("Pont", "bridge"),
    ("Bridge", "bridge"), ("Intro guitare", "intro"), ("Guitar intro", "intro"), ("Outro", "outro"),
    ("Main Riff", "riff"), ("Solo guitare", "solo"), ("Break 2", "break"), ("Interlude", "interlude"),
    ("Section E", "interlude"), ("Truc", "other"),
])
def test_section_kind_both_languages(name, kind):
    assert section_kind(name) == kind


def test_colors_same_in_both_languages():
    for fr in ("Intro", "Couplet", "Pré-refrain", "Refrain", "Pont", "Solo", "Break", "Outro", "Main Riff"):
        assert section_color(fr) == section_color(localize_section(fr, "en"))
    assert section_color("Refrain 1") == (220, 50, 60)


def test_cue_text():
    assert cue_text("Refrain 2") == "Refrain"
    assert cue_text("Chorus 12", "en") == "Chorus"
    assert cue_text("Pre-chorus 1", "en") == "Pre-chorus"
    assert cue_text("Section E", "fr") == "Interlude"
    assert cue_text("Section E", "en") == "Interlude"
    assert cue_text("Solo guitare") == "Solo guitare"


def test_messages_both_languages():
    for key, (fr, en) in i18n.MSG.items():
        assert fr and en and fr != "" and en != ""
    assert t("n_sections", "en", n=3) == "There are 3 sections."
    assert t("n_sections", "fr", n=3) == "Il y a 3 sections."
    i18n.set_lang("en")
    try:
        assert t("song") == "Song"
    finally:
        i18n.set_lang("fr")
    assert t("song") == "Morceau"


def test_bpm_from_name_warning_detected():
    for lg in ("fr", "en"):
        assert i18n.is_bpm_from_name_warning(t("bpm_from_name", lg, bpm=188))
    assert not i18n.is_bpm_from_name_warning(t("irregular_pulse", "en"))


def test_localize_analysis():
    from reacue_mcp.analysis import Analysis, Section
    a = Analysis(file="x", duration=10, bpm=120, beats_per_bar=4, denominator=4, tempo_stable=True,
                 tempo_cv=0, beats=[], downbeats=[0, 2, 4],
                 sections=[Section(0, 1, "A", "Intro"), Section(1, 2, "B", "Refrain")])
    i18n.localize_analysis(a, "en")
    assert [s.name for s in a.sections] == ["Intro", "Chorus"]


def test_prompter_section_type_and_lyrics_repeat_types():
    from reacue_mcp.prompter import section_type
    from reacue_mcp.lyrics import REPEAT_TYPES
    assert section_type("Refrain 1") in REPEAT_TYPES and section_type("Chorus 1") in REPEAT_TYPES
    assert section_type("Pre-chorus") in REPEAT_TYPES and section_type("Pré-refrain") in REPEAT_TYPES
    assert section_type("Break") == "break" and section_type("Solo 2") == "solo"   # utilisés par la page


def test_key_from_names_both_languages():
    from reacue_mcp.prompter import key_from_names
    k = key_from_names(["Demo-F# minor-120bpm.wav"])
    assert k == {"chord": "F#m", "fr": "Fa dièse mineur", "en": "F♯ minor"}
