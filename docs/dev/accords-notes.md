# Accords : notes de développement (branche feat/accords-modele)

## Recherche (23/10/2026)
Accès réseau : GitHub (git clone) OK ; arXiv, Hugging Face, download.pytorch.org bloqués (lus via WebFetch).

| Candidat | Code | Poids | Vocabulaire | Installabilité Mac Intel | Verdict |
|---|---|---|---|---|---|
| **Jiang et al. ISMIR 2019** (music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition) | MIT (2023, Music X Lab) | dans le dépôt GitHub (5 × 5,7 Mo, ensemble), même licence | grand vocabulaire décomposé (triade, basse, 7e, 9e, 11e, 13e) : maj, min, dim, aug, sus2, sus4, 7, maj7, m7, hdim7, dim7, 9, maj9, m9, 11, 13, 7sus4, **renversements natifs** (/3, /5, /b3, /b7, /2) | torch + librosa + numpy (CRNN léger) ; HMM numpy avec **décodage calé sur les temps** | **retenu** |
| BTC (jayg996/BTC-ISMIR19) | MIT | dans le dépôt (12 Mo) | 170 classes, pas de basse | torch + librosa | 2e choix : pas de renversements, résultats ~équivalents (article BMACE : Root 0,805 / MIREX 0,749) |
| BMACE (arXiv 2601.02101, Yuan & Devaney, Mamba) | non publié | non publié | 170 | Mamba | écarté : rien de publié, perf ≈ BTC (« pas significativement différent ») |
| ChordFormer (arXiv 2502.11840) | pas de code/poids trouvés | — | structuré (comme Jiang) | — | écarté : non publié |
| madmom CRF / deep chroma | BSD (code) | **CC BY-NC-SA** | maj/min seulement | Cython à compiler, pas de roue Py 3.12 | écarté |
| Chordino / NNLS (vamp) | GPL | — | modéré | plugin vamp + hôte binaire | écarté (GPL, binaire) |
| autochord | MIT | TF bi-LSTM | maj/min | TensorFlow + vamp | écarté |

## Choix d'intégration (fait)
- Composant facultatif `.venv-chords` (Python 3.12, torch 2.2.2 x86_64 / 2.5.1 ailleurs = mêmes versions que
  Demucs, numpy<2, librosa<0.12, numba 0.62.1 sur Mac Intel) ; dépôt figé `481f4ce7` téléchargé dans `chords/model`.
- `reacue_chords.py` (sous-processus) : CQT hybride (288 cases, 36/oct, F#0, hop 512, 22050 Hz) -> 5 réseaux ->
  moyenne -> HMM XHMMDecoder du dépôt avec les temps de ReaCue (beat_arr : 2 = temps 1, 3 = milieu, 4 = autre
  temps, 0 = entre deux temps ; pénalités 15 / 45 / 100 du dépôt) -> segments Harte + confiance « famille ».
  Modules inutiles (h5py, pydub, pretty_midi, joblib) remplacés par des modules vides ; np.int rétabli.
- `reacue_mcp/chord_model.py` : mix harmonique (sans voix ni batterie), cache segments (audio + grille) et
  probabilités npz (audio) dans `.reacue/`, échec mémorisé 1 h, délai 10 min.
- `reacue_mcp/chords.py` : `chords_from_segments` (2 accords max, temps 1 et milieu), `speller` (tonalité),
  `spell_above` (basse des renversements = note de l'accord), simplification 9/11/13 -> 7 ;
  `cached_chords` : modèle si `chords_engine` = auto et installé, sinon / échec : detect_chords (clé inchangée).

## Validation ici (conteneur Linux, 2 vCPU, Python 3.11, torch 2.2.2)
- Vrai modèle, audio synthétique : C Am F G7 Dm7 G C/E F reconnus à 100 % (renversement et 7e compris).
- Vocabulaire étendu synthétique : maj7, m7, 7, dim, G/D, C/Bb OK ; sus2/sus4/aug/Em/G ratés (synthèse simple).
- Bout en bout (stems synthétiques keys/bass/drums/vocals) : Cmaj7 trouvé (ReaCue : C), reste identique.
- Morceau réel de 4 min 17 : 30 s (après chargement), 67 s en tout, 1,1 Go RAM max.
- Tests : tests/test_chords_model.py (40 tests, modèle simulé).

## Pistes
- Pastille « Accords » de la fenêtre : proposer l'installation (comme Structure) — non fait (Lua, hors axe).
- install_mac.sh / reacue_setup.py (désinstallation de .venv-chords) : non modifiés (conflits avec les autres axes).
- Afficher chord_model.LAST["message"] dans le résumé de publication (server.py non modifié).
