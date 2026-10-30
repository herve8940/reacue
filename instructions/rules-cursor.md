# Configuration Cursor pour ReaCue / Cursor Rules for ReaCue

> **Installation rapide dans votre copie locale :**
> - **Option 1 (Fichier unique)** : Copiez ce contenu dans un fichier `.cursorrules` à la racine de votre dépôt.
> - **Option 2 (Cursor Rules v2)** : Enregistrez ce contenu sous `.cursor/rules/reacue.mdc`.
>
> *(Note : Ces fichiers racines sont automatiquement ignorés par le `.gitignore` de ReaCue pour ne pas impacter le dépôt).*

---

```markdown
---
description: Règles de développement et d'architecture pour le projet ReaCue
globs: *
alwaysApply: true
---

# Directives Développeur ReaCue (Cursor Rules)

Vous agissez en tant que Tech Lead et développeur senior sur ReaCue (Cockos REAPER, ReaScript Lua, Python 3.12+ FastMCP).

## RÈGLES CRITIQUES NON NÉGOCIABLES

### 1. Parité Multiplateforme Stricte (Windows <-> macOS)
- Tout installateur `.bat` (Windows) modifié ou créé DOIT avoir son équivalent `.command` (macOS) mis à jour à l'identique.
- Chemins REAPER :
  - Windows : `%APPDATA%\REAPER`
  - macOS : `~/Library/Application Support/REAPER`
- Scripts existants : `Install ReaCue.bat` / `.command`, `Uninstall ReaCue.bat` / `.command`, `Optimize ReaCue Mac.command`.

### 2. Documentation Bilingue Stricte (FR <-> EN)
- `README.md` (anglais) <-> `LISEZMOI.md` (français) doivent rester strictement synchronisés.
- `docs/TUTORIAL_en.md` <-> `docs/TUTORIEL_fr.md`.
- `docs/BEST_PRACTICES_AND_HARDWARE.md` <-> `docs/BONNES_PRATIQUES_ET_MATERIEL.md`.
- Images dans `docs/images/` : paires `*_en.png` et `*_fr.png`.

### 3. Stack Technique & Tests
- Utiliser `uv` pour la gestion des environnements virtuels (`.venv`, `.venv-chords`, `.venv-drums`, etc.).
- Typage strict en Python (`typing`, Pydantic). Pas de `Any` non justifié.
- Valider systématiquement toute modification avec `pytest` :
  `uv run pytest tests/` ou `.\.venv\Scripts\pytest.exe tests/`.

### 4. Workflow Git Supervisé
- Ne JAMAIS proposer de commit direct sur `main` ou `master`.
- Toutes les Pull Requests doivent obligatoirement cibler la branche `DEV`.
- Branches de travail : `feat/<nom>`, `fix/<nom>`, `docs/<nom>`.
- Commits : Format Conventional Commits (ex: `feat(prompter): update tempo cues`).
```
