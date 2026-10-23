# Composants tiers et licences / Third-party components and licences

*Vérifié le 22 octobre 2026 (PyPI, dépôts GitHub, pages Hugging Face). Ce document n'est pas un avis
juridique. / Checked on 22 October 2026 (PyPI, GitHub repositories, Hugging Face pages). This document is
not legal advice.*

ReaCue lui-même est sous **licence MIT** ([LICENSE](LICENSE)). Il est fourni « tel quel », sans aucune
garantie. / ReaCue itself is under the **MIT licence** ([LICENSE](LICENSE)), provided “as is”, without
any warranty.

**Ce dépôt ne contient aucun poids de modèle ni aucun fichier audio.** Les modèles sont téléchargés par
l'utilisateur, au moment de l'installation, directement depuis les sites de leurs auteurs ; chaque
utilisateur est responsable du respect de leurs licences. / **This repository contains no model weights
and no audio.** Models are downloaded by the user, at install time, directly from their authors; each user
is responsible for complying with their licences.

## ⚠️ Usage non commercial / Non-commercial use

L'**analyse de structure (SongFormer)**, composant facultatif, télécharge les poids **MuQ-large-msd-iter**,
publiés sous **CC BY-NC 4.0 : usage non commercial uniquement**. Le modèle MusicFM (MSD) n'a pas de
licence propre clairement indiquée (voir plus bas). N'utilise pas ce composant dans un cadre commercial
(produit ou service payant) sans l'accord des ayants droit. De même, la **transcription de batterie
(ADTOF)**, composant facultatif, télécharge des poids sous **CC BY-NC-SA 4.0 (non commerciale)**. Le reste
de ReaCue n'est pas concerné.

The optional **structure analysis (SongFormer)** component downloads the **MuQ-large-msd-iter** weights,
released under **CC BY-NC 4.0: non-commercial use only**. The MusicFM (MSD) checkpoint has no clearly
stated licence of its own (see below). Do not use this component commercially (paid product or service)
without the rights holders' permission. Likewise, the optional **drum transcription (ADTOF)** component
downloads weights under **CC BY-NC-SA 4.0 (non-commercial)**. The rest of ReaCue is not affected.

## Inclus dans le dépôt / Included in this repository

| Composant / Component | Rôle / Role | Auteurs / Authors | Licence | Fichier |
|---|---|---|---|---|
| [luaqrcode](https://github.com/speedata/luaqrcode) | QR code du prompteur / prompter QR code | Patrick Gundlach and contributors | BSD 3 clauses / 3-clause BSD | `reaper/ReaCue_qrcode.lua` (copié sans modification, en-tête de licence conservé / unmodified, licence header kept) |

## Modèles téléchargés par l'utilisateur / Models downloaded by the user

| Modèle / Model | Utilisé par / Used by | Source | Licence du code / Code licence | Licence des poids / Weights licence |
|---|---|---|---|---|
| **Demucs** `htdemucs`, `htdemucs_6s` | Séparation de stems (facultatif) / stem separation (optional) | [facebookresearch/demucs](https://github.com/facebookresearch/demucs) (A. Défossez, Meta AI) — modèles téléchargés par Demucs depuis les serveurs de Meta | MIT | Pas de licence séparée indiquée pour les modèles ; le dépôt est sous MIT / no separate licence stated for the models; the repository is MIT |
| **SongFormer** (`SongFormer.safetensors`) | Analyse de structure (facultatif) / structure analysis (optional) | [ASLP-lab/SongFormer](https://github.com/ASLP-lab/SongFormer), [HF ASLP-lab/SongFormer](https://huggingface.co/ASLP-lab/SongFormer) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (attribution obligatoire / attribution required) | Page HF : badge CC BY 4.0, pas d'étiquette de licence formelle / HF page: CC BY 4.0 badge, no formal licence tag |
| **MuQ** `OpenMuQ/MuQ-large-msd-iter` | Dépendance de SongFormer / SongFormer dependency | [tencent-ailab/MuQ](https://github.com/tencent-ailab/MuQ) (Tencent AI Lab), [HF OpenMuQ/MuQ-large-msd-iter](https://huggingface.co/OpenMuQ/MuQ-large-msd-iter) | MIT | **[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — non commercial** (fichier `LICENSE_weights` du dépôt et étiquette HF / `LICENSE_weights` file and HF tag) |
| **MusicFM** MSD (`pretrained_msd.pt`, `msd_stats.json`) | Dépendance de SongFormer / SongFormer dependency | [minzwon/musicfm](https://github.com/minzwon/musicfm) (Minz Won, Yun-Ning Hung, Duc Le — ByteDance), [HF minzwon/MusicFM](https://huggingface.co/minzwon/MusicFM) | MIT (+ Apache-2.0 pour `modules/flash_conformer.py`) | **Incertaine / uncertain** : le dépôt HF est étiqueté MIT mais n'a pas de carte et rien n'est dit sur `pretrained_msd.pt` ; ce modèle est entraîné sur le Million Song Dataset, et le README des auteurs ne publie volontairement que le modèle FMA « pour éviter des complications de licence ». / The HF repo is tagged MIT but has no model card and says nothing about `pretrained_msd.pt`; this checkpoint is trained on the Million Song Dataset, and the authors' README says they chose to release the FMA model “to avoid potential licensing complications”. |
| **ADTOF** Frame_RNN (`adtof_frame_rnn_pytorch_weights.pth`, 16 Mo / MB) | Transcription de batterie (facultatif) / drum transcription (optional) | [MZehren/ADTOF](https://github.com/MZehren/ADTOF) (Mickaël Zehren, Marco Alunno, Paolo Bientinesi) ; poids convertis pour PyTorch par / weights converted to PyTorch by [xavriley/ADTOF-pytorch](https://github.com/xavriley/ADTOF-pytorch) (Xavier Riley), téléchargés depuis GitHub / downloaded from GitHub | ADTOF : **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)** ; ADTOF-pytorch : **aucune licence indiquée / no licence stated** | **CC BY-NC-SA 4.0 — non commercial** (poids d'origine d'ADTOF, fichier `LICENSE` du dépôt ; la conversion PyTorch en dérive / original ADTOF weights, repository `LICENSE` file; the PyTorch conversion derives from them) |
| Configuration `facebook/wav2vec2-conformer-rope-large-960h-ft` | Configuration lue par MusicFM (pas de poids) / config read by MusicFM (no weights) | [Hugging Face](https://huggingface.co/facebook/wav2vec2-conformer-rope-large-960h-ft) (Meta) | — | Apache-2.0 (étiquette HF / HF tag) |

## Code source téléchargé par l'installateur / Source code fetched by the installer

Révisions figées (voir `reacue_mcp/structure.py`) / Pinned revisions: SongFormer (CC BY 4.0), MuQ (MIT),
MusicFM (MIT / Apache-2.0) — téléchargés dans `structure/`, jamais redistribués par ce dépôt.

Transcription de batterie (voir `reacue_mcp/drums.py`) / Drum transcription: ADTOF-pytorch, révision
figée / pinned revision `85c192e78f716ea0b111cc8a5ee4a8f6a3a4f8a9` (code sans licence indiquée + poids
CC BY-NC-SA 4.0 / code with no stated licence + CC BY-NC-SA 4.0 weights) — téléchargé dans `drums/` après
l'accord « J'accepte », jamais redistribué par ce dépôt ; ReaCue n'en utilise que le chargement du modèle
(son propre code fait le reste) / fetched into `drums/` after the “I accept” step, never redistributed by
this repository; ReaCue only uses its model loading (its own code does the rest).

## Paquets Python / Python packages

Installés par l'installateur depuis PyPI dans `.venv`, `.venv-demucs` ou `.venv-structure` ; jamais
redistribués par ce dépôt. Licences relevées sur PyPI le 22/10/2026. / Installed from PyPI by the
installer; never redistributed by this repository.

| Paquet / Package | Environnement | Licence (PyPI) |
|---|---|---|
| mcp (Model Context Protocol SDK) | `.venv` | MIT |
| librosa | `.venv`, `.venv-structure` | ISC |
| soundfile | tous / all | BSD 3-Clause |
| numpy | tous / all | BSD-3-Clause (+ 0BSD, MIT, Zlib, CC0-1.0 pour des parties incluses / for bundled parts) |
| scipy | tous / all | BSD |
| demucs | `.venv-demucs` | MIT |
| torch | `.venv-demucs`, `.venv-structure` | BSD-3-Clause (+ Apache-2.0 / LLVM exception et autres pour des parties incluses / for bundled parts) |
| torchaudio, torchvision | `.venv-demucs`, `.venv-structure` | BSD |
| numba, llvmlite | `.venv`, `.venv-structure` | BSD (llvmlite : BSD-2-Clause + Apache-2.0 with LLVM exception) |
| omegaconf | `.venv-structure` | BSD |
| hydra-core | `.venv-structure` | MIT |
| einops | `.venv-structure` | MIT |
| x-transformers, x-clip, ema-pytorch | `.venv-structure` | MIT |
| transformers, safetensors, huggingface-hub | `.venv-structure` | Apache-2.0 |
| nnAudio | `.venv-structure` | MIT |
| easydict | `.venv-structure` | **LGPL-3.0** (bibliothèque utilisée telle quelle, non modifiée, non redistribuée / used unmodified, not redistributed) |
| pandas | `.venv-structure` | BSD 3-Clause |
| matplotlib | `.venv-structure` | Licence matplotlib (de type PSF / PSF-based) |
| requests | `.venv-structure` | Apache-2.0 |
| tqdm | `.venv-structure` | MPL-2.0 AND MIT |
| uv (installateur / installer, Astral) | outil / tool | MIT OR Apache-2.0 |
| Tests : pytest, lupa, playwright | développement / development | MIT, MIT, Apache-2.0 |

Les dépendances indirectes de ces paquets suivent leurs propres licences (voir PyPI). / Transitive
dependencies follow their own licences (see PyPI).

## Logiciels et services utilisés, non fournis / Software and services used, not provided

| Élément / Item | Licence / Terms | Remarque / Note |
|---|---|---|
| [REAPER](https://www.reaper.fm/) (Cockos Incorporated) | Logiciel commercial, licence propre / commercial software, own licence | REAPER est une marque de Cockos Incorporated. ReaCue n'est ni affilié à Cockos ni approuvé par Cockos. / REAPER is a trademark of Cockos Incorporated. ReaCue is not affiliated with or endorsed by Cockos. |
| Voix système : macOS `say`, Windows SAPI, Linux `espeak-ng` (GPL-3.0) | Celles du système / the system's | Appelées comme programmes externes, non fournies / called as external programs, not provided |
| [js_ReaScriptAPI](https://github.com/juliansader/ReaExtensions) (facultatif, ReaPack) | Licence de son auteur (non vérifiée ici) / its author's licence (not checked here) | Utilisée seulement si l'utilisateur l'a installée lui-même / used only if the user installed it |
| Claude / Claude Desktop (Anthropic) — mode MCP facultatif / optional | Conditions d'Anthropic / Anthropic's terms | ReaCue n'est ni affilié à Anthropic ni approuvé par Anthropic. / ReaCue is not affiliated with or endorsed by Anthropic. |
| Moises (cité dans la doc / mentioned in docs) | — | Marque de son propriétaire ; aucun lien avec ReaCue / trademark of its owner; no relationship with ReaCue |

## Références / References

- Chunbo Hao, Ruibin Yuan, Jixun Yao, Qixin Deng, Xinyi Bai, Yanbo Wang, Wei Xue, Lei Xie (ASLP-lab),
  *SongFormer: Scaling Music Structure Analysis with Heterogeneous Supervision*, arXiv:2510.02797. https://arxiv.org/abs/2510.02797
- Haina Zhu, Yizhi Zhou, Hangting Chen et al. (Tencent AI Lab), *MuQ: Self-Supervised Music Representation Learning with Mel Residual
  Vector Quantization*, arXiv:2501.01108, 2025. https://arxiv.org/abs/2501.01108
- Minz Won, Yun-Ning Hung, Duc Le, *A Foundation Model for Music Informatics*, arXiv:2311.03318, 2023.
  https://arxiv.org/abs/2311.03318
- Mickaël Zehren, Marco Alunno, Paolo Bientinesi, *ADTOF: A large dataset of non-synthetic music for
  automatic drum transcription*, ISMIR 2021, pp. 818–824 ; *High-Quality and Reproducible Automatic Drum
  Transcription from Crowdsourced Data*, Signals 4(4), 768–787, 2023. https://doi.org/10.3390/signals4040042
- Simon Rouard, Francisco Massa, Alexandre Défossez, *Hybrid Transformers for Music Source Separation*,
  ICASSP 2023, arXiv:2211.08553. https://arxiv.org/abs/2211.08553
