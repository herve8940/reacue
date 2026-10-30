# Hub d'Instructions IA & Vibe Coding / AI & Vibe Coding Instruction Hub

Bienvenue dans le hub d'instructions de **ReaCue** !  
Ce dossier contient les directives, contraintes d'architecture et règles de qualité à fournir à votre assistant IA préféré pour collaborer efficacement et en toute sécurité (*vibe coding maîtrisé*).

Welcome to the **ReaCue** instructions hub!  
This directory contains guidelines, architectural constraints, and quality standards to feed your favorite AI assistant for smooth, safe, and robust collaboration.

---

## 🚀 Choisir le bon fichier selon votre outil / Pick the Right File

| Outil IA / AI Tool | Fichier source / Source file | Où le copier localement / Where to copy locally |
|---|---|---|
| **Cursor** | [`rules-cursor.md`](file:///e:/ReaCue%20Project/instructions/rules-cursor.md) | `.cursorrules` ou `.cursor/rules/reacue.mdc` |
| **GitHub Copilot** | [`rules-copilot.md`](file:///e:/ReaCue%20Project/instructions/rules-copilot.md) | `.github/copilot-instructions.md` |
| **Claude Code (CLI)** | [`rules-claude.md`](file:///e:/ReaCue%20Project/instructions/rules-claude.md) | `CLAUDE.md` (à la racine / at root) |
| **Windsurf / Cascade** | [`rules-windsurf.md`](file:///e:/ReaCue%20Project/instructions/rules-windsurf.md) | `.windsurfrules` (à la racine / at root) |
| **Agents (Aider, OpenHands)** | [`rules-agents.md`](file:///e:/ReaCue%20Project/instructions/rules-agents.md) | `AGENTS.md` (à la racine / at root) |
| **ChatGPT / Claude / DeepSeek Web** | [`prompt-system.md`](file:///e:/ReaCue%20Project/instructions/prompt-system.md) | Copier-coller dans votre premier message / Paste in your first prompt |
| **Architecture de référence** | [`architecture-reacue.md`](file:///e:/ReaCue%20Project/instructions/architecture-reacue.md) | Document d'architecture global / Complete architecture reference |

> [!TIP]
> **Pourquoi ces fichiers ne sont-ils pas directement à la racine ?**  
> Les fichiers de configuration locale (`.cursorrules`, `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`) sont volontairement ignorés par notre [`.gitignore`](file:///e:/ReaCue%20Project/.gitignore). Ainsi, vous pouvez copier le fichier correspondant à votre outil dans votre clone local sans risquer de polluer vos commits ou de créer des conflits avec d'autres contributeurs !

---

## 🛡️ Les 4 Piliers Non Négociables de ReaCue / Core Pillars

Si vous donnez ces instructions à une IA, rappelez-lui toujours ces 4 impératifs :

### 1. Parité Multiplateforme (Windows / macOS)
ReaCue tourne en live sur scène aussi bien sur Windows que sur Mac.
- Tout installateur `.bat` sous Windows **doit** avoir son pendant `.command` sous macOS.
- Chemins REAPER à respecter :
  - Windows : `%APPDATA%\REAPER`
  - macOS : `~/Library/Application Support/REAPER`

### 2. Parité Documentaire Bilingue (FR <-> EN)
Le projet est strictement bilingue :
- `README.md` (anglais) <-> `LISEZMOI.md` (français).
- Dossier `docs/` : toujours synchroniser les paires de guides (ex: `TUTORIAL_en.md` et `TUTORIEL_fr.md`).

### 3. Environnements Virtuels Modulaires (`uv`) & Tests (`pytest`)
- Dépendances gérées via `uv` avec des virtualenvs distincts (`.venv`, `.venv-chords`, `.venv-drums`, etc.) pour éviter les conflits PyTorch/Demucs.
- Tout ajout ou modification doit passer la suite de tests :
  ```bash
  uv run pytest tests/
  # ou sous Windows CMD/PowerShell :
  .\.venv\Scripts\pytest.exe tests/
  ```

### 4. Workflow Git & Pull Requests vers `DEV`
- **Interdiction formelle** de commiter ou de pousser directement sur `main` / `master`.
- Créez une branche de travail : `feat/<nom>`, `fix/<nom>`, `docs/<nom>`.
- **Toute Pull Request doit impérativement cibler la branche `DEV`**.
- Format des commits : **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

---

## 📚 En savoir plus / Learn More
Consultez la fiche complète [`architecture-reacue.md`](file:///e:/ReaCue%20Project/instructions/architecture-reacue.md) pour les détails techniques approfondis.
