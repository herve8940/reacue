# Instructions GitHub Copilot pour ReaCue / GitHub Copilot Instructions

> **Installation dans votre copie locale :**
> - Copiez le contenu ci-dessous dans le fichier `.github/copilot-instructions.md`.
> - GitHub Copilot prendra automatiquement en compte ces directives dans l'IDE (VS Code, Visual Studio, JetBrains) et dans GitHub Copilot Chat.
>
> *(Note : Le fichier `.github/copilot-instructions.md` est ignoré par `.gitignore` pour préserver vos réglages locaux).*

---

```markdown
# Directives GitHub Copilot — Projet ReaCue

ReaCue est une suite d'outils professionnels pour Cockos REAPER (prompteur de scène temps réel, régie live, analyse audio IA).
Technologies : Python 3.12+ (FastMCP, PyTorch, Librosa, Whisper, Demucs) et ReaScript (Lua).

## Directives d'Assistance & Génération de Code

1. **Parité Multiplateforme (Windows & macOS)** :
   - Tout script d'installation Windows (`.bat`) a son strict équivalent macOS (`.command`).
   - Ne jamais modifier l'un sans proposer immédiatement l'adaptation de l'autre.
   - Chemins : `%APPDATA%\REAPER` sous Windows, `~/Library/Application Support/REAPER` sous macOS.

2. **Documentation Miroir Bilingue** :
   - Toute mise à jour de `README.md` doit être répercutée dans `LISEZMOI.md`.
   - Les guides dans `docs/` fonctionnent par paires (`*_en.md` / `*_fr.md`).

3. **Typage et Qualité Python** :
   - Appliquer des type hints stricts (`typing`, `Optional`, `Dict`, `List`, modèles Pydantic).
   - Ne pas utiliser `Any` sauf nécessité absolue.
   - Dépendances gérées via `uv` et virtualenvs dédiés (`.venv`, `.venv-chords`, etc.).

4. **Tests & Validation** :
   - Proposer systématiquement des tests unitaires `pytest` pour chaque nouvelle fonction ou classe.
   - Commande de validation : `uv run pytest tests/` ou `.\.venv\Scripts\pytest.exe tests/`.

5. **Conventions Git** :
   - Cible obligatoire des PR : branche `DEV`.
   - Message de commit au standard Conventional Commits (`feat(...)`, `fix(...)`, `docs(...)`, `refactor(...)`).
```
