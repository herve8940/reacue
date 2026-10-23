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

## Conteneur de dev
- Pas d'accès Hugging Face ici : tests avec sous-processus simulé ; le code torch est testé avec un petit
  modèle wav2vec2 aléatoire (venv de test avec torch 2.2.2 depuis PyPI, hors dépôt).
