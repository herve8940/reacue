# Migration depuis l'ancienne installation (macOS, `~/Documents/reacue-mcp`)

Objectif : remplacer l'ancienne version par la 0.9 **sans perdre les morceaux préparés** ni les actions
REAPER déjà en place.

## Ce qui est conservé tel quel

| Élément | Emplacement | Comportement |
|---|---|---|
| Dernier morceau préparé | `~/Library/Application Support/REAPER/ReaCueMCP/last_session.json` | relu sans modification (anciennes options acceptées) |
| Caches du prompteur | `ReaCueMCP/prompter_*.json` | accords, batterie, activité : clés inchangées ; paroles : inchangées en français |
| Voix déjà générées | `ReaCueMCP/voice/` | mêmes noms de fichiers sur macOS (pas de nouvelle synthèse) |
| Ligne de démarrage du pont | `Scripts/__startup.lua` (`-- ReaCue MCP`) | reconnue, pas de doublon |
| Actions déjà chargées | `reaper-kb.ini` (ID `RS…` → `~/Documents/reacue-mcp/reaper/…`) | gardées ; l'installateur n'en ajoute pas de nouvelles en double |
| Réglages par défaut | — | identiques (fr, count-in 2, annonce sur l'avant-dernière mesure, décompte anglais) |

## Procédure conseillée (garder le même dossier)

1. Quitter **REAPER** et **Claude Desktop**.
2. Optionnel : sauvegarder `~/Documents/reacue-mcp` (copie du dossier) et
   `~/Library/Application Support/REAPER/ReaCueMCP/`.
3. Remplacer le contenu de `~/Documents/reacue-mcp` par celui de la nouvelle version (garder le **même
   chemin** : les actions REAPER existantes pointent vers `~/Documents/reacue-mcp/reaper/`). Le dossier
   `.venv` peut rester, il est recréé.
4. Double-clic sur `Install ReaCue.command`, langue `fr`, Claude Desktop : **oui** (l'entrée `reacue` est
   réécrite vers le même chemin ; sauvegarde `claude_desktop_config.json.bak-reacue`).
5. Relancer REAPER (le pont 1.3.0 démarre), puis Claude Desktop.
6. Vérifier : bouton *Préparer* sur le dernier morceau → « Morceau reconstruit (structure conservée) ».

## Points de vigilance

- **Pont Lua** : l'installateur copie le nouveau `ReaCue_Bridge.lua` (1.3.0) dans `REAPER/Scripts/ReaCue` ;
  un redémarrage de REAPER est nécessaire pour qu'il soit pris en compte.
- **Python** : le `.venv` est recréé avec Python 3.12 via uv (plus de Python système). Durée : 1 à 3 min.
- **Actions** : les anciennes actions (ID `RS…`) restent et appellent maintenant les nouveaux scripts du
  dossier `reaper/`. Si tu installes la nouvelle version dans **un autre dossier**, les anciennes actions
  continueront d'appeler les anciens scripts : supprime-les dans la liste des actions (*Remove*) puis
  relance l'installateur REAPER fermé pour enregistrer les nouvelles (`ReaCue - Préparer le morceau`,
  `ReaCue - Republier le prompteur`), et réassigne tes boutons de barre d'outils.
- **Dossier d'installation** : il est maintenant mémorisé dans `ReaCueMCP/reacue_install.txt`. Un
  `ExtState` « ReaCue/install_dir » posé à la main reste prioritaire : l'effacer s'il pointe ailleurs
  (`reaper.DeleteExtState("ReaCue", "install_dir", true)` dans la console ReaScript).
- **Fichier de réglages** : `ReaCueMCP/reacue_settings.json` est créé avec les valeurs par défaut. Le
  premier *Préparer* après la migration ne modifie pas les options du morceau en cours (elles ne sont
  réappliquées que si le fichier change ensuite).
- **Copie sur le Mac** : vérifier les fichiers copiés par md5 comme d'habitude, en particulier
  `reaper/ReaCue_Bridge.lua`, `reaper/ReaCue_run.lua` et `reacue_mcp/web/prompteur.html`.
- **Serveur MCP déjà lancé** : `pkill -f "reacue-mcp/run_server.py"` si Claude Desktop n'a pas été quitté.
- **Retour arrière** : restaurer la copie du dossier et `claude_desktop_config.json.bak-reacue` ; recopier
  l'ancien `ReaCue_Bridge.lua` (1.2.0) dans `REAPER/Scripts/ReaCue` et redémarrer REAPER.
