# Notes de développement — paroles automatiques (branche feat/paroles-auto, depuis feat/modeles-1.1)

## Choix du modèle
- **openai-whisper 20250625** (PyPI, code MIT) + modèle **large-v3-turbo** (poids MIT : README d'openai/whisper
  « Whisper's code and model weights are released under the MIT License » ; carte HF openai/whisper-large-v3-turbo : MIT).
  809 M paramètres (encodeur large-v3 à 32 couches, décodeur réduit à 4 couches) : qualité proche de large-v3,
  décodage bien plus rapide ; fichier `large-v3-turbo.pt` ≈ 1,6 Go ; RAM ≈ 3 à 4 Go en float32 sur CPU.
- Écartés : faster-whisper / CTranslate2 (roues Mac Intel incertaines, autre runtime), whisper.cpp (compilation),
  transformers (refuse torch.load des .bin avec torch < 2.6, grosse dépendance), WhisperX (pyannote, torch récent),
  large-v3 complet (≈ 3 Go, décodage 8× plus lent pour un gain faible sur du chant), small/medium (moins bons).
- Même environnement que les paroles mot par mot : `.venv-words` (torch 2.2.2, numpy<2 sur Mac Intel).

## Installation
- `requirements-words.txt` reçoit les dépendances de Whisper, en roues : numba 0.62.1, llvmlite 0.45.1
  (roues macosx_10_15_x86_64 cp312 vérifiées sur PyPI ; numba accepte numpy 1.22–2.3), tiktoken 0.9.0
  (roue macosx_10_13_x86_64 cp312), more-itertools, tqdm.
- openai-whisper n'existe qu'en sdist (Python pur) : `requirements-whisper.txt` installé avec `--no-deps`
  (pas de --only-binary pour ce seul paquet ; aucune compilation ; triton inutile sur CPU).
- Poids dans `<ReaCue>/words/whisper/` (comme `words/hf`), téléchargés par `reacue_transcribe.py check --download`
  via `whisper._download` (serveur openaipublic.azureedge.net, contrôle SHA-256). Repli si ce serveur ne répond
  pas : dépôt HF officiel `openai/whisper-large-v3-turbo` (config.json + model.safetensors) converti localement en
  `large-v3-turbo-hf.pt` (format openai-whisper ; `hf_to_openai` vérifié contre transformers 4.46.3 sur un petit
  modèle aléatoire : logits identiques).
- Relancer `Install ReaCue Words` sur une installation existante : venv gardé, uv n'ajoute que les paquets manquants,
  modèles wav2vec2 déjà en cache (contrôle seulement), Whisper ajouté. `REACUE_WHISPER=0` = sans Whisper.

## Architecture
- `reacue_transcribe.py` (racine, tourne dans `.venv-words`) : détection d'activité vocale (RMS 20 ms, seuil
  p95 − 24 dB et ≥ −50 dBFS, trous < 0,5 s fusionnés, zones < 0,25 s ignorées, marge 0,2 s), signal mis à zéro hors
  zones, fenêtres ≤ 28 s (une passe d'encodeur chacune), langue = moyenne des probabilités sur les 3 plus longues
  fenêtres (une autre langue que fr/en seulement si ≥ 0,7), `whisper.transcribe` par fenêtre avec
  condition_on_previous_text=False, word_timestamps=True, hallucination_silence_threshold=2, seuils par défaut
  (no_speech 0,6, logprob −1, compression 2,4), beam 5. Sortie : segments + mots horodatés (jamais affichés).
- `reacue_mcp/lyrics_auto.py` (sans torch) : sous-processus, nettoyage (phrases parasites type sous-titres,
  [Musique], ♪, segments incertains, débit impossible, motifs répétés > 4 fois, même ligne > 4 fois de suite),
  découpe en lignes (silence ≥ 0,8 s, sinon > 9 mots ou > 6,5 s coupés au meilleur endroit : silence, ponctuation,
  milieu), ligne vide si silence > 2 mesures (2,5–6 s), en-tête « # » ; écriture avec open(..., "x") : jamais
  d'écrasement. Échec / morceau sans chant mémorisés dans `prompter_lyrics_auto.json` (clé : stem voix, réglages,
  date d'installation) : pas de nouvel essai à chaque publication.
- `lyrics.py` : `lyric_dirs` (extrait de find_lyrics_file), le brouillon est exclu de `find_lyrics_file`
  (fichier de l'utilisateur toujours prioritaire), `cached_lyrics` appelle `ensure_auto_lyrics` en dernier recours,
  lignes « # » = commentaires dans `read_lyrics`, entrées marquées "auto": True (prompteur -> grille PDF).
- Fenêtre REAPER : `read_lyrics` (tab_song) cherche d'abord le fichier de l'utilisateur, sinon le brouillon ;
  pastille `pill_lyrics_auto` « warn », clic = ouvrir le fichier, aide dans ReaCue_guide.lua.
- Progression : `lyrics_auto.PROGRESS` branché dans cli.py (fichier d'état lu par REAPER) ; message de résultat
  ajouté au résumé de la CLI. server.py non modifié.

## Conteneur de dev
- openaipublic.azureedge.net et Hugging Face bloqués (403 du proxy) : poids réels non testés ici.
- Chaîne complète testée dans un venv hors dépôt (Python 3.12, torch 2.2.2, openai-whisper 20250625, numba 0.62.1)
  avec des modèles Whisper aléatoires (tiny / minuscule) : VAD, fenêtres, langue, transcription, mots, sous-commande
  `transcribe` (fichier -> JSON), conversion HF.

## Pistes non faites
- Utiliser directement les horodatages de Whisper pour le calage (au lieu du calage par ligne sur le brouillon).
- Message « relance Install ReaCue Words pour ajouter Whisper » quand .venv-words existe sans Whisper (non fait :
  bruit à chaque publication pour ceux qui ont choisi REACUE_WHISPER=0).
- Réglage dans l'onglet Réglages de la fenêtre (clé `lyrics_auto` seulement dans reacue_settings.json).
