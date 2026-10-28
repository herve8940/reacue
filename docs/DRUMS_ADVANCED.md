# Batterie : transcription avancée / Advanced drum transcription

## Français

ADT_STR est un moteur optionnel de transcription audio vers MIDI, distinct d'un
générateur de patterns. Il analyse le stem batterie existant. Les poids et le code
sont figés et installés dans `.venv-drums-advanced`, sans changer ADTOF ni Whisper.

1. Mettre ReaCue à jour et fermer sa fenêtre dans REAPER.
2. Sur Mac, lancer **Install ReaCue Advanced Drums.command**. Sur Windows,
   **Install ReaCue Advanced Drums.bat**. Internet est nécessaire pour les dépendances
   et les poids. Le téléchargement ne concerne qu'une variante du modèle.
3. Attendre **ADT_STR_READY** : ce message exige un chargement et une inférence
   réels réussis. Une installation échouée n'active pas le moteur.
4. Rouvrir ReaCue et relancer « Analyser et préparer ». Le mode batterie Auto utilise
   alors ADT_STR, puis ADTOF ou les règles si le moteur avancé échoue. L'avertissement
   de repli est conservé dans le résultat.

L'affichage conserve les neuf voies existantes : les catégories supplémentaires
restent dans les événements bruts et l'export MIDI, avec les temps et vélocités
mesurés. La grille et les grooves affichés sont une simplification de lecture.
Le MIDI avancé n'est pas quantifié. Son export utilise le tempo constant fourni
à l'exporteur actuel ; les cartes de tempo variables demandent un traitement distinct.

Le cache est séparé de celui d'ADTOF. Changer la grille ne relance pas le modèle.
`drums_engine` accepte `auto`, `adt-str`, `adtof` et `reacue` dans les réglages JSON ;
`REACUE_DRUMS_ENGINE` est prioritaire. Choisir `adtof` désactive le moteur avancé.

Mac Intel : PyTorch/TorchAudio 2.2.2 et Transformers 4.44.2, chargement audio avec
SoundFile sans TorchCodec. Apple Silicon et Windows : PyTorch/TorchAudio 2.8.0.
Cette adaptation doit être vérifiée sur les machines réelles. Apple MPS est essayé
si disponible avec reprise CPU sur erreur d'exécution. Un modèle plus détaillé ne
garantit pas une meilleure précision sur chaque morceau, notamment après séparation.

## English

Run **Install ReaCue Advanced Drums.command** (macOS) or
**Install ReaCue Advanced Drums.bat** (Windows). The isolated installer downloads
pinned ADT_STR code and one pretrained checkpoint, then loads it and runs a real
inference check before enabling Auto mode (`ADT_STR_READY`). Prepare the song again.

Auto prefers ADT_STR, with the existing ADTOF/rules fallback. Raw GM pitches,
velocities and timing survive MIDI export; the nine-lane pattern display is a
simplified projection. Advanced MIDI is not quantized and uses the exporter's
constant BPM. Variable tempo maps need separate handling. Set `drums_engine` to
`adtof` to use the old engine. Hardware compatibility and transcription accuracy
must be checked on real Mac/Windows machines; no quality or speed gain is guaranteed.

Attribution and CC BY-SA 4.0 details: [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md).
