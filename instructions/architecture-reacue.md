# Architecture Technique de ReaCue / ReaCue Technical Architecture

Ce document décrit l'architecture globale de ReaCue pour les contributeurs et les assistants IA.

---

## 1. Vue d'Ensemble / Overview
**ReaCue** est un système hybride temps-réel et d'analyse audio conçu pour Cockos REAPER. Il combine :
- **ReaScript (Lua)** : Interface directe avec REAPER (actions, transport, marqueurs, régions, fenêtres prompteur).
- **Python 3.12+ & FastMCP** : Moteur d'analyse audio avancée, IA (transcription, séparation de stems, accords, structure) et passerelle MCP (Model Context Protocol).
- **Scripts d'Installation Modulaires** : Déploiement automatisé sur Windows (`.bat`) et macOS (`.command`).

---

## 2. Arborescence du Dépôt / Repository Layout

```text
ReaCue Project/
├── .github/                     # Workflows CI/CD GitHub Actions
├── instructions/                # Hub de cadrage pour développeurs et assistants IA
├── reaper/                      # Scripts ReaScript (Lua) et assets REAPER
│   ├── Scripts/ReaCue/          # Logique Lua principale (prompteur, transport, tempo cues)
│   ├── ColorThemes/             # Thèmes visuels pour REAPER
│   └── ProjectTemplates/        # Templates de projet .RPP préconfigurés
├── reacue_mcp/                  # Serveur FastMCP (outils d'intégration REAPER <-> IA)
├── install/                     # Outils et scripts d'installation modulaires
├── tests/                       # Suite de tests unitaires et d'intégration (pytest)
├── docs/                        # Documentation bilingue (FR / EN)
│   ├── images/                  # Captures et diagrammes (paires _fr.png / _en.png)
│   ├── TUTORIEL_fr.md           # Guide utilisateur (Français)
│   ├── TUTORIAL_en.md           # User guide (English)
│   ├── BONNES_PRATIQUES_ET_MATERIEL.md
│   └── BEST_PRACTICES_AND_HARDWARE.md
├── reacue_cli.py                # Interface en ligne de commande
├── run_server.py                # Point d'entrée du serveur FastMCP
├── README.md                    # Présentation officielle (Anglais)
├── LISEZMOI.md                  # Présentation officielle (Français)
└── pyproject.toml / requirements*.txt # Gestion des dépendances Python
```

---

## 3. Environnements Virtuels Modulaires (`uv`) / Python Environments

ReaCue utilise un découpage modulaire pour isoler les dépendances lourdes (PyTorch, Torchaudio, modèles ML) :

| Environnement | Rôle | Fichier de dépendances |
|---|---|---|
| `.venv` | Racine, serveur FastMCP, CLI et tests | `requirements.txt`, `requirements-dev.txt` |
| `.venv-chords` | Détection et alignement d'accords | `requirements-chords.txt` |
| `.venv-drums` | Transcription de batterie (ADTOF / ADT_STR) | `requirements-drums.txt`, `requirements-drums-advanced.txt` |
| `.venv-demucs` | Séparation de pistes/stems (Demucs) | `requirements-stems.txt` |
| `.venv-structure` | Détection des sections et transitions (SongFormer) | `requirements-structure.txt` |
| `.venv-words` | Transcription mot-à-mot et alignement phonétique | `requirements-words.txt`, `requirements-whisper.txt` |

Gestionnaire recommandé : **`uv`** (ultra-rapide et déterministe).
- Création / synchronisation : `uv sync` ou `uv pip install -r <requirements>.txt`
- Exécution de commandes : `uv run <commande>`

---

## 4. Installateurs & Parité Multiplateforme / Cross-Platform Installers

Toute modification d'un script d'installation doit respecter la parité stricte Windows / macOS :

| Composant | Windows (Batch CMD) | macOS (Shell Bash/Zsh) |
|---|---|---|
| Master ReaCue | `Install ReaCue.bat` | `Install ReaCue.command` |
| Désinstallateur | `Uninstall ReaCue.bat` | `Uninstall ReaCue.command` |
| Optimisation Mac | — | `Optimize ReaCue Mac.command` |
| Chords | `Install ReaCue Chords.bat` | `Install ReaCue Chords.command` |
| Drums | `Install ReaCue Drums.bat` | `Install ReaCue Drums.command` |
| Advanced Drums | `Install ReaCue Advanced Drums.bat` | `Install ReaCue Advanced Drums.command` |
| Stems | `Install ReaCue Stems.bat` | `Install ReaCue Stems.command` |
| Structure | `Install ReaCue Structure.bat` | `Install ReaCue Structure.command` |
| Words | `Install ReaCue Words.bat` | `Install ReaCue Words.command` |

### Chemins REAPER Standard :
- **Windows** : `%APPDATA%\REAPER` (`C:\Users\<User>\AppData\Roaming\REAPER`)
- **macOS** : `~/Library/Application Support/REAPER`

---

## 5. Qualité, Typage et Tests / Code Quality & Tests

- **Typage Python** : Utilisation stricte des type hints (`typing`, Pydantic). Éviter `Any` sans justification impérative.
- **Exécution des tests** :
  ```bash
  # Windows
  .\.venv\Scripts\pytest.exe tests/
  # macOS / Linux / uv
  uv run pytest tests/
  ```
- **Règles ReaScript (Lua)** :
  - Respect de l'API Cockos REAPER native (`reaper.*`).
  - Tolérance aux versions et gestion gracieuse des erreurs utilisateur (boîtes de dialogue informatives, absence de crash silencieux).
