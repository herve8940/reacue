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

## Validation ici (conteneur Linux, 2 cœurs, torch 2.2.2 CPU depuis PyPI, vrai modèle cloné de GitHub)
- `reacue_drums.py check` : BD / SD / HH 100 % sur la batterie synthétique ; inférence ~2,6 s pour 33 s
  d'audio (=> ~20 s pour 4 min, + ~5 s de chargement ; 1er appel plus lent : compilation numba de librosa).
- Bout en bout (tests/drum_synth.demo_score, 20 mesures, intro/couplet/refrain, charley ouvert, ride,
  crash, fills de toms) : règles 194/260 coups exacts (voie + pas), **ADTOF 245/260** ; ratés = toms
  synthétiques (sinusoïdes) que le modèle prend pour du charley — artefact probable du son de synthèse.
- Shuffle 100 BPM (triolets) : règles 60/156 (grille 16), **ADTOF 156/156 en grille 12** (une grosse caisse
  en trop par mesure : double déclenchement sur le kick synthétique long).

## Avancement
- [x] lanceur reacue_drums.py, moteur dans drums.py (quantification, triolets, sous-classes, repli, cache)
- [x] voie HO dans le prompteur, installeurs Mac/Windows, requirements-drums.txt, docs, licences
- [x] tests/test_drums_model.py (faux ADTOF + faux torch), tools/compare_drums.py
- [ ] non fait : purge de .venv-drums/drums par reacue_setup.py --purge (le dossier d'installation reste),
      pastille « Batterie » / réglage dans l'onglet Réglages Lua (réglage via reacue_settings.json seulement),
      avertissement de repli remonté à l'interface (il est dans le JSON : clé « warning » ; server.py non modifié).
