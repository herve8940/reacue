# Accords : notes de développement (branche feat/accords-modele)

## Recherche (23/10/2026)
Accès réseau : GitHub (git clone) OK ; arXiv, Hugging Face, download.pytorch.org bloqués (lus via WebFetch).

| Candidat | Code | Poids | Vocabulaire | Installabilité Mac Intel | Verdict |
|---|---|---|---|---|---|
| **Jiang et al. ISMIR 2019** (music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition) | MIT (2023, Music X Lab) | dans le dépôt GitHub (5 × 5,7 Mo, ensemble), même licence | grand vocabulaire décomposé (triade, basse, 7e, 9e, 11e, 13e) : maj, min, dim, aug, sus2, sus4, 7, maj7, m7, hdim7, dim7, 9, maj9, m9, 11, 13, 7sus4, **renversements natifs** (/3, /5, /b3, /b7, /2) | torch + librosa + numpy (CRNN léger) ; HMM numpy avec **décodage calé sur les temps** | **retenu** |
| BTC (jayg996/BTC-ISMIR19) | MIT | dans le dépôt (12 Mo) | 170 classes, pas de basse | torch + librosa | 2e choix : pas de renversements, résultats ~équivalents (article BMACE : Root 0,805 / MIREX 0,749) |
| BMACE (arXiv 2601.02101, Yuan & Devaney, Mamba) | non publié | non publié | 170 | Mamba (noyaux CUDA souvent) | écarté : rien de publié, perf ≈ BTC |
| ChordFormer (arXiv 2502.11840) | pas de code/poids trouvés | — | structuré (comme Jiang) | — | écarté : non publié |
| madmom CRF / deep chroma | BSD (code) | **CC BY-NC-SA** | maj/min seulement | Cython à compiler, pas de roue Py 3.12 | écarté |
| Chordino / NNLS (vamp) | GPL | — | modéré | plugin vamp + hôte binaire | écarté (GPL, binaire) |
| autochord | MIT | TF bi-LSTM | maj/min | TensorFlow + vamp | écarté |

## Choix d'intégration
- Composant facultatif `.venv-chords` (torch 2.2.2 x86_64, numpy<2, librosa) ; sources figées téléchargées dans `chords/`.
- `reacue_chords.py` (sous-processus) : CQT hybride (288 cases, 36/oct, F#0, hop 512, 22050 Hz) de l'audio
  harmonique -> 5 modèles -> moyenne -> HMM XHMMDecoder du dépôt avec les temps de ReaCue (beat_arr) ->
  segments Harte (start, end, label).
- `reacue_mcp/chords.py` : calage des segments sur les mesures (2 accords max, temps 1 et 3), nommage
  dièses/bémols selon la tonalité, simplification lisible, renversements « A/C# » ; repli sur la méthode
  maison si absent / échec.
