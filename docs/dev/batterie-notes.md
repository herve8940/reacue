# Batterie par modèle — notes de travail (branche feat/batterie-modele)

## Choix du modèle (23/10/2026)
| Candidat | Classes | Code / poids | Installabilité Mac Intel | Verdict |
|---|---|---|---|---|
| ADTOF (MZehren, Frame_RNN, TF/Keras + madmom) | 5 : BD, SD, toms, HH, cymbales (crash+ride) | CC BY-NC-SA 4.0 (code + poids dans le dépôt GitHub) | TF + madmom (Cython) : pénible | modèle retenu, via le portage PyTorch |
| ADTOF-pytorch (xavriley, rév. 85c192e) | idem, F -0,2 pt vs original (MDB++ : 88,5) | pas de fichier de licence (code) ; poids convertis des poids ADTOF => CC BY-NC-SA 4.0 ; 16 Mo sur GitHub | torch + librosa seulement : torch 2.2.2 / numpy<2 OK | **retenu** |
| Omnizart drums | 13 cl. | MIT, poids Google Drive | TF 2.5 + madmom, Python 3.8 | écarté (installation) |
| YourMT3+ | multi-instr. | Apache-2.0, poids HF | ~500 M param., CPU lent, lightning | écarté (lourd) |
| Noise-to-Notes (2509.21739) | 7 | ni code ni poids publiés ; MERT-330M (CC BY-NC) | diffusion + MERT | écarté |
| Séparation de batterie (LarsNet, DrumSep, 2509.24853) | stems kick/snare/… | poids CC BY-NC ou non publiés | type Demucs, lent | écarté (sépare, ne transcrit pas) |
| Magenta OaF-Drums (E-GMD) | 9 | Apache-2.0, poids GCS | TF1 / magenta | écarté (installation) |

Classes manquantes d'ADTOF complétées par le signal (déjà dans drums.py) :
- cymbales -> crash / ride (décroissance, continuité dans la section) ;
- charley -> fermé (HH) / ouvert (HO, nouvelle voie) par la tenue de l'aigu ;
- toms -> T1 / T2 / FT par la hauteur.

## Architecture
- `reacue_drums.py` (racine) : tourne dans `.venv-drums`, importe `adtof_pytorch.model` depuis
  `drums/ADTOF-pytorch/src` (révision figée), sort les onsets JSON
  `{"engine": "adtof", "fps": 100, "onsets": {"BD": [[t, p], …], "SD", "TT", "HH", "CY"}}`.
- `reacue_mcp/drums.py` : `detect_drums` = moteur modèle si disponible (réglage `drums_engine`), sinon règles
  maison ; quantification sur la grille, sous-classes par le signal, puis `_cymbal_lanes` / `group`
  réutilisés => même format.

## Avancement
- [ ] module + script + installeurs + tests
