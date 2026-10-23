# Notes de développement — paroles calées mot par mot (branche feat/paroles-mots)

## Choix du modèle
- Alignement forcé CTC : `torchaudio.functional.forced_align` (torchaudio 2.2.2, présent depuis 2.1).
- Modèles : wav2vec2 XLSR-53 large affinés sur Common Voice par J. Grosman
  - fr : `jonatasgrosman/wav2vec2-large-xlsr-53-french` (Apache-2.0), modèle d'alignement par défaut de WhisperX
    pour le français ;
  - en : `jonatasgrosman/wav2vec2-large-xlsr-53-english` (Apache-2.0) ;
  - base `facebook/wav2vec2-large-xlsr-53` : Apache-2.0 ; données Common Voice : CC0 ;
  - ~1,26 Go chacun (315 M paramètres, float32), téléchargés depuis Hugging Face par l'installateur.
- Pas de `transformers` : poids HF convertis vers `torchaudio.models.wav2vec2_model` (même correspondance que
  `torchaudio.models.wav2vec2.utils.import_huggingface_model`), vérifiée contre transformers sur un modèle
  aléatoire. Raison : transformers >= 4.50 refuse `torch.load` des `.bin` avec torch < 2.6 (Mac Intel bloqué
  à torch 2.2.2) et c'est une grosse dépendance inutile ici.
- Écartés : MMS_FA (poids CC BY-NC 4.0), VoxPopuli FR de torchaudio (CC BY-NC 4.0), WhisperX (ASR + pyannote,
  torch récent, inutile puisque le texte est connu), modèles phonèmes espeak (installation d'espeak-ng).

## Architecture (même modèle que SongFormer)
- `reacue_words.py` (racine) : tourne dans `.venv-words` (torch/torchaudio aux mêmes versions que Demucs).
- `reacue_mcp/words.py` : côté ReaCue, sans torch : langue, fenêtres par ligne, sous-processus, cache, fusion.
- Appelé depuis `lyrics.cached_lyrics` après le calage par ligne (cache des lignes inchangé) ; repli = lignes
  seules.
- Champ `words: [{"w","t","end"}]` (temps fichier) ; `prompter.lyrics_on_timeline` les convertit.

## Fichiers
- `reacue_words.py`, `reacue_mcp/words.py`, `requirements-words.txt`, `install/install_words_{mac.sh,windows.ps1}`,
  `Install ReaCue Words.{command,bat}`, `tools/compare_words.py`, `tests/test_words.py`.
- Modifiés : `lyrics.py` (`_with_words` dans `cached_lyrics`), `prompter.py` (`lyrics_on_timeline` + `downbeats`),
  `sheet.py` (`bar_lyrics`), `web/prompteur.html` (`lineWords`, `.wd.now/.done`), `i18n.py` (bloc `words_*`),
  `settings.py` (`words_engine`, `words_language`), `tests/conftest.py` (`REACUE_WORDS_ENGINE=off`), docs.

## Réglages fins (à ajuster avec tools/compare_words.py sur de vrais morceaux)
- `MIN_LINE_SCORE = 0.12` (probabilité moyenne des lettres sous laquelle une ligne garde le calage par ligne).
- Marges `PAD_MIN/PAD_MAX = 0.15/0.8 s`, `MAX_SHIFT_S = 1.0` (resserrement de la ligne sur ses mots).
- Le séparateur de mots `|` du vocabulaire est inclus entre les mots (comme à l'entraînement).

## Pistes non faites
- Progression dans la fenêtre REAPER (`words.PROGRESS` n'est pas branché : server.py non modifié).
- Révision HF figée (inconnue ici : `REVISION = "main"`, variable REACUE_WORDS_REVISION).
- Proposition dans l'installateur principal (install_mac.sh) non ajoutée pour éviter les conflits.

## Conteneur de dev
- Pas d'accès Hugging Face ici : tests avec sous-processus simulé ; le code torch est testé avec un petit
  modèle wav2vec2 aléatoire (venv de test avec torch 2.2.2 depuis PyPI, hors dépôt).
