"""Langue de ReaCue (français / anglais) : noms de sections, annonces, messages.

L'analyse produit des noms de sections en français (clés internes). Ils sont traduits en sortie
(régions, annonces, prompteur) selon le réglage `language`. Les noms saisis par l'utilisateur
(set_sections, rename_section) sont gardés tels quels : section_kind / section_color / cue_text
reconnaissent les deux langues.
"""
from __future__ import annotations

import re

LANGS = ("fr", "en")
_lang = "fr"


def set_lang(lang: str | None) -> str:
    global _lang
    lang = str(lang or "fr").lower()[:2]
    _lang = lang if lang in LANGS else "fr"
    return _lang


def get_lang() -> str:
    return _lang


def use_settings_lang() -> str:
    """Langue lue dans reacue_settings.json (appelé au début de chaque commande)."""
    from .settings import load_settings
    return set_lang(load_settings()["language"])


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
# nom de base produit par l'analyse (FR) -> EN
SECTION_EN = {
    "Intro": "Intro", "Couplet": "Verse", "Pré-refrain": "Pre-chorus", "Refrain": "Chorus",
    "Pont": "Bridge", "Solo": "Solo", "Break": "Break", "Outro": "Outro", "Interlude": "Interlude",
    "Main Riff": "Main Riff", "Riff": "Riff", "Section": "Section",
    "Intro guitare": "Guitar intro", "Intro basse": "Bass intro", "Intro claviers": "Keys intro",
    "Intro voix": "Vocal intro", "Bridge": "Bridge", "Instrumental": "Instrumental",
}
SECTION_FR = {v: k for k, v in SECTION_EN.items() if k != "Bridge"}
SECTION_FR["Bridge"] = "Pont"

# type canonique (indépendant de la langue) : ordre = priorité de reconnaissance
_KINDS = (
    ("prechorus", r"pr[ée][- ]?refrain|pre[- ]?chorus|pr[ée][- ]?chorus|build[- ]?up"),
    ("chorus", r"refrain|chorus|hook"),
    ("verse", r"couplet|verse|strophe"),
    ("intro", r"intro"),
    ("outro", r"outro|coda|fin|ending|end"),
    ("bridge", r"pont|bridge|middle[- ]?(?:8|eight)"),
    ("solo", r"solo"),
    ("break", r"break|breakdown|stop"),
    ("riff", r"main[- ]?riff|riff|instrus?|instrumental"),
    ("interlude", r"interlude|section"),
)
_KIND_RE = [(k, re.compile(rf"(?:^|\b)(?:{p})(?:\b|$)", re.I)) for k, p in _KINDS]

KIND_COLORS = {
    "intro": (120, 120, 120), "verse": (60, 120, 220), "prechorus": (240, 160, 40),
    "chorus": (220, 50, 60), "bridge": (150, 80, 200), "solo": (40, 170, 90),
    "outro": (120, 120, 120), "break": (200, 200, 90), "interlude": (90, 160, 160),
    "riff": (230, 120, 50), "other": (90, 160, 160),
}


def _split_num(name: str) -> tuple[str, str]:
    m = re.match(r"^(.*?)(\s+\d+)?\s*$", str(name))
    return (m.group(1) if m else str(name)), ((m.group(2) or "") if m else "")


def section_kind(name: str) -> str:
    """Type canonique d'une section, en français ou en anglais : intro, verse, prechorus, chorus,
    bridge, solo, break, outro, interlude, riff, other."""
    base = _split_num(name)[0].strip().lower()
    # « Intro guitare », « Guitar intro » -> intro (le mot le plus significatif d'abord)
    for kind, rx in _KIND_RE:
        if rx.search(base):
            return kind
    return "other"


def section_color(name: str) -> tuple[int, int, int]:
    return KIND_COLORS[section_kind(name)]


def localize_section(name: str, lang: str | None = None) -> str:
    """Nom produit par l'analyse -> langue voulue (« Refrain 2 » -> « Chorus 2 »).
    Un nom inconnu (saisi par l'utilisateur) est rendu tel quel."""
    lang = lang or _lang
    base, num = _split_num(name)
    table = SECTION_EN if lang == "en" else SECTION_FR
    for k, v in table.items():
        if base.strip().lower() == k.lower():
            return v + num
    return str(name)


def localize_analysis(a, lang: str | None = None):
    """Traduit les noms de sections d'une Analysis (sur place) ; renvoie l'Analysis."""
    for s in a.sections:
        s.name = localize_section(s.name, lang)
    return a


CUE_FALLBACK = {"fr": "Interlude", "en": "Interlude"}


def cue_text(section_name: str, lang: str | None = None) -> str:
    """« Refrain 2 » -> « Refrain », « Chorus 2 » -> « Chorus » : l'annonce dit le type de section.
    « Section E » (groupe sans nom) n'est pas une annonce utile sur scène : « Interlude »."""
    lang = lang or _lang
    t = re.sub(r"\s+\d+$", "", str(section_name)).strip() or str(section_name)
    if re.fullmatch(r"Section\s+\w", t):
        return CUE_FALLBACK.get(lang, "Interlude")
    return t


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #
MSG = {
    # pont / REAPER
    "bridge_dir_missing": ("Dossier du pont absent ({dir}). Lance ReaCue_Bridge.lua dans REAPER.",
                           "Bridge folder missing ({dir}). Run ReaCue_Bridge.lua in REAPER."),
    "bridge_no_heartbeat": ("REAPER ne répond pas : lance l'action « ReaCue_Bridge.lua » dans REAPER.",
                            "REAPER is not responding: run the “ReaCue_Bridge.lua” action in REAPER."),
    "bridge_silent": ("Pont silencieux depuis {age:.0f} s : REAPER est fermé ou le script a été arrêté.",
                      "Bridge silent for {age:.0f} s: REAPER is closed or the script was stopped."),
    "bridge_timeout": ("Pas de réponse de REAPER en {timeout:.0f} s (une fenêtre modale est-elle ouverte ?).",
                       "No answer from REAPER within {timeout:.0f} s (is a modal window open?)."),
    "bridge_unknown_error": ("erreur inconnue côté REAPER", "unknown error on the REAPER side"),
    "old_bridge_stems": (
        "Ce projet contient plusieurs pistes audio (stems) mais le pont REAPER est trop ancien (< 1.2). "
        "Relance l'installation de ReaCue (ou recopie ReaCue_Bridge.lua dans REAPER/Scripts/ReaCue) puis "
        "redémarre REAPER. Rien n'a été modifié.",
        "This project has several audio tracks (stems) but the REAPER bridge is too old (< 1.2). "
        "Run the ReaCue installer again (or copy ReaCue_Bridge.lua to REAPER/Scripts/ReaCue) and restart "
        "REAPER. Nothing was changed."),
    "old_bridge_voice": (
        "Pont REAPER trop ancien pour les appels vocaux : relance l'installation de ReaCue puis redémarre REAPER.",
        "REAPER bridge too old for voice cues: run the ReaCue installer again and restart REAPER."),
    "wrong_project": (
        "Le projet ouvert dans REAPER ne contient plus les pistes du dernier morceau préparé "
        "(projet consolidé, rendu ou autre morceau ?) : rien n'a été modifié. Relance la préparation "
        "sur ce projet, ou republie seulement le prompteur.",
        "The project open in REAPER no longer contains the tracks of the last prepared song "
        "(consolidated, rendered or another song?): nothing was changed. Prepare this project again, "
        "or only republish the prompter."),
    "no_session": ("Aucun morceau préparé pour l'instant : lance d'abord la préparation.",
                   "No song prepared yet: run the preparation first."),
    "no_audio_item": ("Aucun item audio dans le projet. Importe d'abord le morceau (stems ou MP3).",
                      "No audio item in the project. Import the song first (stems or MP3)."),
    "file_not_found": ("Fichier introuvable : {path}", "File not found: {path}"),
    "stem_rates": ("Les stems n'ont pas tous la même vitesse de lecture : l'alignement et la grille ne sont "
                   "fiables que si elle est identique.",
                   "The stems do not all have the same playback rate: alignment and grid are only "
                   "reliable when it is identical."),
    "n_sections": ("Il y a {n} sections.", "There are {n} sections."),
    "prompter_not_updated": ("Prompteur non mis à jour : {e}", "Prompter not updated: {e}"),
    "chords_failed": ("Accords non détectés : {e}", "Chords not detected: {e}"),
    "lyrics_failed": ("Paroles non calées : {e}", "Lyrics not aligned: {e}"),
    "drums_failed": ("Batterie non transcrite : {e}", "Drums not transcribed: {e}"),
    "prompter_url": ("http://<IP de cet ordinateur>:<port de l'interface web REAPER>/{page}",
                     "http://<this computer's IP>:<REAPER web interface port>/{page}"),
    "unchanged": ("inchangé", "unchanged"),
    # planificateur
    "item_rate": ("L'item est lu à x{rate:.3f} : les positions en tiennent compte.",
                  "The item plays at x{rate:.3f}: positions take it into account."),
    "no_room_cue": ("Pas la place d'annoncer « {name} » avant le début : augmente count_in_bars.",
                    "No room to announce “{name}” before the start: increase count_in_bars."),
    "song": ("Morceau", "Song"),
    # analyse
    "intro_off_tempo": ("Intro hors tempo avant l'entrée de la pulsation : la mesure 1 est placée à "
                        "l'entrée de la batterie/pulsation.",
                        "Intro out of tempo before the beat comes in: bar 1 is placed where the "
                        "drums/beat start."),
    "irregular_pulse": ("Pulsation irrégulière par endroits : vérifie la grille (rubato, break, changement "
                        "de mesure ?).",
                        "Irregular pulse in places: check the grid (rubato, break, time signature change?)."),
    "bpm_from_name": ("Tempo {bpm:g} bpm lu dans le nom des fichiers.", "Tempo {bpm:g} bpm read from the file names."),
    "tempo_octave": ("Octave de tempo ambigu : {bpm:.1f} ou {alt:.1f} bpm. Passe bpm_hint si la grille n'est "
                     "pas dans le bon sens.",
                     "Ambiguous tempo octave: {bpm:.1f} or {alt:.1f} bpm. Pass bpm_hint if the grid is "
                     "the wrong way round."),
    "too_few_beats": ("Pas assez de temps détectés : morceau trop court ou sans pulsation.",
                      "Not enough beats detected: song too short or without a pulse."),
    "too_short": ("Morceau trop court pour construire des mesures.", "Song too short to build bars."),
    "no_stem": ("Aucun stem fourni.", "No stem given."),
    "empty_sections": ("Liste de sections vide.", "Empty section list."),
    "bad_section": ("Section « {name} » vide ou mal ordonnée.", "Section “{name}” is empty or out of order."),
    "no_voice_stem": ("pas de stem voix : calage des paroles impossible",
                      "no vocal stem: lyrics cannot be aligned"),
    "no_drum_stem": ("pas de stem batterie", "no drum stem"),
    # synthèse vocale
    "tts_none": ("Aucune synthèse vocale disponible sur cet ordinateur : pas d'annonces ni de décompte "
                 "parlés (le reste fonctionne).",
                 "No speech synthesis available on this computer: no spoken cues or count-in "
                 "(everything else works)."),
    "tts_voice_missing": ("Voix « {voice} » absente, choix automatique.",
                          "Voice “{voice}” not found, picking one automatically."),
    "tts_no_lang_voice": ("Aucune voix « {code} » installée : voix système par défaut.",
                          "No “{code}” voice installed: using the system default voice."),
    "tts_failed": ("Synthèse impossible pour « {text} » : {err}", "Speech synthesis failed for “{text}”: {err}"),
    "tts_tighten": ("Recalage impossible pour « {text} » ({e}) : fichier brut utilisé.",
                    "Could not trim “{text}” ({e}): raw file used."),
    # CLI (fenêtre de fin dans REAPER)
    "cli_error": ("Erreur : {e}", "Error: {e}"),
    "cli_error_log": ("Erreur : {e}\n\n(détails dans {log})", "Error: {e}\n\n(details in {log})"),
    "cli_tempo": ("Tempo {bpm} BPM · {sig} · {bars} mesures", "Tempo {bpm} BPM · {sig} · {bars} bars"),
    "cli_alt": (" (ou {alt} ?)", " (or {alt}?)"),
    "cli_structure": ("Structure :", "Structure:"),
    "cli_published": ("Prompteur publié", "Prompter published"),
    "cli_chords": ("accords", "chords"),
    "cli_drums": ("batterie", "drums"),
    "cli_lyrics": ("{n} lignes de paroles", "{n} lyric lines"),
    "cli_prepared": ("Morceau préparé", "Song prepared"),
    "cli_published_title": ("Prompteur republié", "Prompter republished"),
    "cli_rebuilt": ("Morceau reconstruit (structure conservée)", "Song rebuilt (structure kept)"),
    "cli_from_regions": ("Structure reprise de tes régions REAPER", "Structure taken from your REAPER regions"),
    # régions modifiées à la main dans REAPER
    "region_before": ("Région « {name} » avant la mesure 1 : ignorée.", "Region “{name}” before bar 1: ignored."),
    "region_after": ("Région « {name} » après la fin du morceau : ignorée.",
                     "Region “{name}” after the end of the song: ignored."),
    "region_rounded": ("Région « {name} » entre deux mesures : placée au début de la mesure {bar}.",
                       "Region “{name}” between two bars: moved to the start of bar {bar}."),
    "region_duplicate": ("Région « {name} » à la même mesure ({bar}) qu'une autre : ignorée.",
                         "Region “{name}” on the same bar ({bar}) as another one: ignored."),
    "region_first": ("Aucune région sur la mesure 1 : les mesures 1 à {last} sont rattachées à « {name} ».",
                     "No region on bar 1: bars 1 to {last} are joined to “{name}”."),
    "region_unnamed": ("Section {n}", "Section {n}"),
    "regions_none": ("Aucune région utilisable dans le projet : la structure enregistrée est gardée.",
                     "No usable region in the project: the saved structure is kept."),
    "regions_changed_publish": (
        "Tes régions REAPER ont changé depuis la dernière préparation : le prompteur garde la structure "
        "enregistrée (pour rester d'accord avec les annonces et le click). Clique « Appliquer » (fenêtre "
        "ReaCue, onglet Morceau) pour reprendre tes régions partout.",
        "Your REAPER regions changed since the last preparation: the prompter keeps the saved structure "
        "(to stay in line with the cues and the click). Click “Apply” (ReaCue window, Song "
        "tab) to take your regions everywhere."),
    # mode concert
    "concert_rpp_unreadable": ("Fichier RPP illisible.", "Unreadable RPP file."),
    "concert_project_missing": ("Projet introuvable pour « {name} » (cherché dans {dirs}).",
                                "Project not found for “{name}” (searched in {dirs})."),
    "concert_no_audio": ("{title} : aucun item audio trouvé dans le projet.",
                         "{title}: no audio item found in the project."),
    "concert_region_off_grid": ("{title} : la 1re région n'est pas sur une barre de mesure.",
                                "{title}: the first region is not on a bar line."),
    "concert_no_regions": ("{title} : aucune région (structure) : morceau entier sans sections. Prépare ce "
                           "morceau et enregistre son projet, puis reconstruis le concert.",
                           "{title}: no regions (structure): whole song without sections. Prepare this song "
                           "and save its project, then rebuild the concert."),
    "concert_live_role": ("Instrument inconnu : « {r} » (possibles : {roles}).",
                          "Unknown instrument: “{r}” (possible: {roles})."),
    "concert_live_mode": ("Valeur inconnue : « {v} » (live ou stem).", "Unknown value: “{v}” (live or stem)."),
    "concert_live_song": ("Morceau introuvable dans la setlist : « {s} » ({songs}).",
                          "Song not found in the setlist: “{s}” ({songs})."),
    "concert_not_found": ("Concert introuvable : « {name} » (dossier {d}).", "Concert not found: “{name}” (folder {d})."),
    "concert_live_applied": ("Profil enregistré : la fenêtre ReaCue l'applique tout de suite (pas besoin de reconstruire).",
                             "Profile saved: the ReaCue window applies it right away (no rebuild needed)."),
    "concert_empty": ("Setlist vide.", "Empty setlist."),
    "concert_lane_songs": ("Morceaux", "Songs"),
    "concert_prompter_failed": ("Prompteur du concert non publié : {e}", "Concert prompter not published: {e}"),
    "concert_extra_failed": ("{title} : {what} non disponible ({e})", "{title}: {what} not available ({e})"),
    "concert_built": ("Concert « {name} » construit", "Concert “{name}” built"),
    "concert_line": ("  {n}. {title}  ·  {bpm:g} BPM  ·  {bars} mesures", "  {n}. {title}  ·  {bpm:g} BPM  ·  {bars} bars"),
    "concert_duration": ("Durée : {m} min {s:02d} s", "Length: {m} min {s:02d} s"),
    "concert_extras_running": ("Accords, paroles et batterie : calcul en cours pour le prompteur.",
                               "Chords, lyrics and drums: being computed for the prompter."),
    "concert_args": ("concert : donne --setlist, ou --name et --songs", "concert: give --setlist, or --name and --songs"),
    "cli_concert_running": ("Construction du concert…", "Building the concert…"),
    "concert_extras_spawned": ("structure publiée ; accords, paroles et batterie en cours de calcul (arrière-plan)",
                               "structure published; chords, lyrics and drums being computed (background)"),
    "concert_extras_not_spawned": ("Calcul des accords/paroles/batterie non lancé : {e}",
                                   "Chords/lyrics/drums computation not started: {e}"),
    "new_song_open_hint": ("Dans REAPER : fenêtre ReaCue, onglet Concert → clic sur le nom du morceau (nouvel onglet), "
                           "puis « Tout faire » (stems, structure, click, téléphones).",
                           "In REAPER: ReaCue window, Concert tab → click the song's name (new tab), then "
                           "“Do everything” (stems, structure, click, phones)."),
    "concert_open_hint": ("Dans REAPER : action « ReaCue - Concert » → choisir le concert (nouvel onglet).",
                          "In REAPER: “ReaCue - Concert” action → choose the concert (new tab)."),
    "cli_running": ("Analyse et préparation en cours…", "Analysis and preparation in progress…"),
    "cli_unknown": ("commande inconnue : {cmd}", "unknown command: {cmd}"),
    # analyse de structure (SongFormer, composant optionnel)
    "structure_running": ("Analyse de structure (SongFormer)… {s} s",
                          "Structure analysis (SongFormer)… {s} s"),
    "structure_timeout": ("SongFormer n'a pas répondu en {min} min", "SongFormer did not answer within {min} min"),
    "structure_empty": ("SongFormer n'a trouvé aucune section", "SongFormer found no section"),
    "structure_used": ("Sections détectées par SongFormer ({s} s), calées sur la grille de ReaCue.",
                       "Sections detected by SongFormer ({s} s), aligned on ReaCue's grid."),
    "structure_used_cached": ("Sections détectées par SongFormer (résultat mémorisé), calées sur la grille de ReaCue.",
                              "Sections detected by SongFormer (cached result), aligned on ReaCue's grid."),
    "cli_pdf": ("Grille PDF : {name} (dossier du morceau)", "PDF chart: {name} (song folder)"),
    "sheet_file": ("Grille - {title}.pdf", "Chart - {title}.pdf"),
    "sheet_tempo": ("Tempo : {bpm} BPM", "Tempo: {bpm} BPM"),
    "sheet_count_in": ("décompte {n} mes.", "count-in {n} bars"),
    "sheet_key": ("Tonalité : {k}", "Key: {k}"),
    "sheet_key_est": ("Tonalité : {k} (estimée)", "Key: {k} (estimated)"),
    "sheet_bars": ("{n} mes.", "{n} bars"),
    "sheet_cont": ("{name} (suite)", "{name} (continued)"),
    "sheet_footer": ("Grille ReaCue : accords et paroles détectés automatiquement, à vérifier.",
                     "ReaCue chart: chords and lyrics detected automatically, please check."),
    "sheet_failed": ("Grille PDF non créée : {e}", "PDF chart not created: {e}"),
    # paroles mot par mot (alignement forcé wav2vec2, composant optionnel)
    "words_running": ("Paroles mot par mot… {s} s", "Word-by-word lyrics… {s} s"),
    "words_timeout": ("le calage mot par mot n'a pas répondu en {min} min",
                      "word-by-word timing did not answer within {min} min"),
    "words_used": ("Paroles calées mot par mot ({n}/{total} lignes, modèle {model}).",
                   "Lyrics timed word by word ({n}/{total} lines, {model} model)."),
    "words_failed": ("Calage mot par mot impossible : {e} → paroles calées par ligne.",
                     "Word-by-word timing failed: {e} → lyrics timed by line."),
    # accords : modèle entraîné (Jiang et al. 2019, composant optionnel)
    "chords_model_running": ("Accords (modèle)… {s} s", "Chords (model)… {s} s"),
    "chords_model_timeout": ("le modèle d'accords n'a pas répondu en {min} min",
                             "the chord model did not answer within {min} min"),
    "chords_model_failed": ("Modèle d'accords indisponible : {e} → détection d'accords de ReaCue utilisée.",
                            "Chord model unavailable: {e} → ReaCue's chord detection used."),
    "chords_model_used": ("Accords reconnus par le modèle (Jiang et al. 2019), calés sur la grille de ReaCue.",
                          "Chords recognised by the model (Jiang et al. 2019), aligned on ReaCue's grid."),
    # batterie : transcription par modèle (ADTOF, composant optionnel)
    "drums_model_failed": ("Transcription de batterie par modèle (ADTOF) impossible : {e} → méthode ReaCue utilisée.",
                           "Drum transcription by model (ADTOF) failed: {e} → ReaCue method used."),
    "drums_model_timeout": ("ADTOF n'a pas répondu en {min} min", "ADTOF did not answer within {min} min"),
    "structure_failed": ("Analyse SongFormer impossible : {e} → structure ReaCue utilisée.",
                         "SongFormer analysis failed: {e} → ReaCue structure used."),
}


def t(key: str, lang: str | None = None, **kw) -> str:
    fr, en = MSG[key]
    s = en if (lang or _lang) == "en" else fr
    return s.format(**kw) if kw else s


def is_bpm_from_name_warning(w: str) -> bool:
    """Avertissement purement informatif (tempo lu dans le nom des fichiers), masqué dans REAPER."""
    return bool(re.search(r"bpm (lu dans le nom des fichiers|read from the file names)", str(w)))
