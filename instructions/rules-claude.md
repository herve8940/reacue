# Instructions Claude Code pour ReaCue / Claude Code Guidelines

> **Installation dans votre copie locale :**
> - Copiez le contenu ci-dessous dans un fichier `CLAUDE.md` situé à la racine du dépôt.
> - Claude Code (CLI ou extension) chargera automatiquement ce fichier en début de session.
>
> *(Note : `CLAUDE.md` est ignoré par le `.gitignore` à la racine pour préserver votre configuration locale).*

---

```markdown
# Instructions Claude Code — ReaCue

## Commandes Fréquentes
- **Lancer les tests** : `uv run pytest tests/` ou `.\.venv\Scripts\pytest.exe tests/`
- **Lancer un test spécifique** : `uv run pytest tests/test_prompter.py -k "test_scroll"`
- **Démarrer le serveur FastMCP** : `uv run run_server.py`
- **Exécuter la CLI ReaCue** : `uv run reacue_cli.py --help`

## Architecture & Stack
- **Langages** : Python 3.12+ (FastMCP, Librosa, Whisper, Demucs, PyTorch) et Lua (ReaScript pour REAPER).
- **Gestionnaire d'environnements** : `uv` avec virtualenvs dédiés (`.venv`, `.venv-chords`, `.venv-drums`, etc.).
- **Dossiers majeurs** :
  - `reaper/` : Scripts Lua et layouts prompteur pour REAPER.
  - `reacue_mcp/` : Implémentation du serveur FastMCP.
  - `tests/` : Suite de tests pytest.
  - `install/` : Scripts et installeurs modulaires.
  - `docs/` : Documentation bilingue.

## Règles d'Or Impératives
1. **Parité Windows / macOS** :
   - Tout installateur `.bat` (Windows) doit avoir son pendant exact `.command` (macOS).
   - Chemins REAPER : `%APPDATA%\REAPER` (Win) vs `~/Library/Application Support/REAPER` (Mac).
2. **Parité Bilingue FR / EN** :
   - `README.md` (EN) <-> `LISEZMOI.md` (FR).
   - `docs/TUTORIAL_en.md` <-> `docs/TUTORIEL_fr.md`.
   - `docs/BEST_PRACTICES_AND_HARDWARE.md` <-> `docs/BONNES_PRATIQUES_ET_MATERIEL.md`.
3. **Typage Strict** : Type hints explicites en Python, zéro `Any` non motivé.
4. **Git Workflow** :
   - Ne jamais commiter directement sur `main`.
   - Les Pull Requests ciblent toujours la branche `DEV`.
   - Commits au format Conventional Commits.
```
