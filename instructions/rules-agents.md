# Directives pour Agents Autonomes / Autonomous Agents Guidelines

> **Installation dans votre copie locale :**
> - Copiez le contenu ci-dessous dans un fichier `AGENTS.md` à la racine de votre dépôt (standard suivi par Aider, OpenHands, etc.), ou référencez directement ce fichier dans le prompt de votre agent.
>
> *(Note : `AGENTS.md` à la racine est ignoré par `.gitignore` pour préserver votre configuration locale).*

---

```markdown
# Instructions pour Agents Autonomes — Projet ReaCue

## 1. Contexte du Dépôt
- Nom : ReaCue
- Nature : Outils de prompteur live et régie de spectacle pour Cockos REAPER.
- Technologies : Python 3.12+ (FastMCP, PyTorch, Librosa, Whisper, Demucs), Lua (ReaScript), scripts Batch (`.bat`) et Shell (`.command`).

## 2. Règles Absolues d'Exécution
- **Parité d'installation OS** :
  - Tout script `.bat` (Windows) correspond à un script `.command` (macOS).
  - Modifier les deux simultanément en respectant les spécificités de chaque shell.
  - Windows : `%APPDATA%\REAPER` | macOS : `~/Library/Application Support/REAPER`.
- **Documentation Miroir** :
  - `README.md` (EN) = `LISEZMOI.md` (FR).
  - `docs/TUTORIAL_en.md` = `docs/TUTORIEL_fr.md`.
  - `docs/BEST_PRACTICES_AND_HARDWARE.md` = `docs/BONNES_PRATIQUES_ET_MATERIEL.md`.
- **Typage & Tests** :
  - Python avec typage statique strict (`typing`).
  - Validation systématique : `uv run pytest tests/` (ou `.\.venv\Scripts\pytest.exe tests/`).
  - Aucun code ne doit être validé si les tests échouent.
- **Workflow Git** :
  - Branche cible pour toute Pull Request : **`DEV`** (interdiction de cibler `main`).
  - Format de commit : Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).
```
