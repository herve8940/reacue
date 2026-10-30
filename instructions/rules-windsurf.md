# Configuration Windsurf pour ReaCue / Windsurf Cascade Rules

> **Installation dans votre copie locale :**
> - Copiez le contenu ci-dessous dans le fichier `.windsurfrules` à la racine de votre dépôt.
> - Windsurf (Cascade) l'appliquera automatiquement à toutes les requêtes.
>
> *(Note : `.windsurfrules` est ignoré par `.gitignore` pour préserver vos réglages locaux).*

---

```markdown
# Directives Cascade (Windsurf) — Projet ReaCue

## Rôle et Contexte
Tu es un ingénieur senior travaillant sur ReaCue, un écosystème hybride ReaScript (Lua pour REAPER) et Python 3.12+ (FastMCP, traitement audio, IA).

## Règles Critiques
1. **Double Parité OS (Windows / macOS)** :
   - Tout script d'installation `.bat` doit être synchronisé avec son homologue `.command`.
   - Chemins cibles : `%APPDATA%\REAPER` sous Windows, `~/Library/Application Support/REAPER` sous macOS.
2. **Double Parité Linguistique (FR / EN)** :
   - Ne jamais modifier `README.md` sans mettre à jour `LISEZMOI.md`.
   - Maintenir les paires miroirs dans `docs/` (`*_en.md` et `*_fr.md`).
3. **Environnements et Tests** :
   - Packager avec `uv` et respecter les virtualenvs modulaires (`.venv`, `.venv-chords`, etc.).
   - Utiliser des type hints stricts en Python.
   - Toujours valider avec `uv run pytest tests/` avant de clore une tâche.
4. **Git Workflow** :
   - Ne jamais pusher sur `main`.
   - Préparer les PR vers la branche `DEV`.
   - Format de commit : Conventional Commits.
```
