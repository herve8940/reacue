# Tutoriel ReaCue — pas à pas

*[English version: TUTORIAL_en.md](TUTORIAL_en.md)*

Ce tutoriel t'emmène de l'installation jusqu'à la répétition avec le groupe. Il suppose que tu sais lancer
REAPER et lire un morceau, rien de plus. Chaque étape dit **où cliquer**, **ce que tu dois voir** et **quoi
faire si ça ne marche pas**.

À la fin, pour chaque morceau, tu auras dans REAPER :

- une carte de tempo calée sur le morceau, des régions nommées et colorées (Intro, Couplet 1, Refrain…) ;
- une piste **CLICK** avec 2 mesures de décompte, une piste **VOIX** qui annonce « Refrain » avant chaque
  section et compte « one two three four » ;
- un **prompteur** sur le téléphone de chaque musicien : structure, accords, paroles, batterie.

Durée : 30 à 45 minutes la première fois (installation comprise), puis 5 à 10 minutes par morceau.

---

## Sommaire

1. [Ce qu'il te faut](#1-ce-quil-te-faut)
2. [Télécharger ReaCue](#2-télécharger-reacue)
3. [Préparer REAPER pour l'installation](#3-préparer-reaper-pour-linstallation)
4. [Lancer l'installateur](#4-lancer-linstallateur)
5. [Vérifier dans REAPER](#5-vérifier-dans-reaper)
6. [Activer l'interface web de REAPER (une seule fois)](#6-activer-linterface-web-de-reaper-une-seule-fois)
7. [Créer le projet d'un morceau](#7-créer-le-projet-dun-morceau)
8. [Importer l'audio : des stems ou un seul MP3](#8-importer-laudio--des-stems-ou-un-seul-mp3)
9. [Séparer un MP3 en stems](#9-séparer-un-mp3-en-stems)
10. [Préparer le morceau](#10-préparer-le-morceau)
11. [Vérifier la structure](#11-vérifier-la-structure)
12. [Ajouter les paroles](#12-ajouter-les-paroles)
13. [Ouvrir le prompteur sur les téléphones](#13-ouvrir-le-prompteur-sur-les-téléphones)
14. [Régler le click, les annonces et les in-ears](#14-régler-le-click-les-annonces-et-les-in-ears)
15. [En répétition](#15-en-répétition)
16. [Dépannage](#16-dépannage)
17. [Pense-bête : un nouveau morceau](#17-pense-bête--un-nouveau-morceau)

---

## 1. Ce qu'il te faut

| Élément | Détail |
|---|---|
| Ordinateur | Mac (macOS 12 ou plus, Intel ou Apple Silicon) ou PC Windows 10/11 (Windows : version bêta) |
| REAPER | Version 7 ou plus récente, déjà installé ([reaper.fm](https://www.reaper.fm/)) |
| Espace disque | 1,5 Go pour ReaCue, + 1,5 Go si tu installes la séparation de stems |
| Internet | Seulement pendant l'installation |
| Audio | Les stems d'un morceau (un fichier par instrument), **ou** un seul MP3/WAV |
| Téléphones | Sur le **même Wi-Fi** que l'ordinateur, avec un navigateur (Safari, Chrome…) |

> Les stems donnent les meilleurs résultats. Si tu n'as que le MP3, ReaCue peut le séparer en stems sur
> ton ordinateur (étape 9).

---

## 2. Télécharger ReaCue

1. Sur la page GitHub du projet, clique sur le bouton vert **Code**, puis **Download ZIP**.
2. Ouvre le fichier ZIP téléchargé : un dossier `reacue-main` apparaît.
3. **Déplace ce dossier à son emplacement définitif**, par exemple dans *Documents*, et renomme-le `ReaCue`.

**Tu dois voir** dans le dossier `ReaCue` : `Install ReaCue.command`, `Install ReaCue.bat`,
`Install ReaCue Stems.command`, `Install ReaCue Stems.bat`, `README.md`, `LISEZMOI.md` et les dossiers
`reacue_mcp`, `reaper`, `install`, `docs`.

> ⚠️ Ne déplace plus ce dossier après l'installation. Si tu dois le déplacer, relance l'installateur depuis
> le nouvel emplacement.

---

## 3. Préparer REAPER pour l'installation

1. **Lance REAPER une fois**, puis **quitte-le** (macOS : *REAPER → Quit REAPER* ; Windows : *File → Quit*).

Pourquoi : au premier lancement, REAPER crée son dossier de réglages ; et l'installateur ne peut enregistrer
les actions ReaCue que si REAPER est **fermé**.

---

## 4. Lancer l'installateur

### Sur Mac

1. Dans le dossier `ReaCue`, **double-clique sur `Install ReaCue.command`**.
2. Si macOS affiche « impossible d'ouvrir … développeur non identifié » : clique sur **OK**, puis
   **clic droit** (ou Ctrl + clic) sur `Install ReaCue.command` → **Ouvrir** → **Ouvrir**.
   Sur les versions récentes de macOS, il peut falloir aller dans *Réglages Système → Confidentialité et
   sécurité*, tout en bas, et cliquer sur **Ouvrir quand même**.
3. Une fenêtre Terminal s'ouvre.

### Sur Windows

1. Dans le dossier `ReaCue`, **double-clique sur `Install ReaCue.bat`**.
2. Si Windows affiche « Windows a protégé votre ordinateur » (SmartScreen) : clique sur **Informations
   complémentaires**, puis **Exécuter quand même**.
3. Une fenêtre noire (console) s'ouvre.

### Les questions (Mac et Windows)

| Question | Quoi répondre |
|---|---|
| `Langue / Language [fr/en]` | `fr` puis Entrée |
| `Déclarer ReaCue dans Claude Desktop … ? [o/N]` | `n` si tu n'utilises pas Claude Desktop (tu pourras le faire plus tard) |
| `Installer la séparation de stems … ? [o/N]` | `o` si tu as des morceaux en MP3 seulement (environ 1 Go à télécharger, 5 à 15 minutes) ; sinon `n` |

**Tu dois voir** défiler 5 étapes (`== 1/5 Vérifications` … `== 5/5 Séparation de stems`) :

- à la fin de l'étape 4 : une ligne `Adresse(s) IP probable(s) de cet ordinateur : …` → **note cette
  adresse** (ex. `192.168.1.20`), elle servira pour les téléphones ; puis `Installation terminée. Redémarre
  REAPER…` (ReaCue est installé) ;
- à l'étape 5, si tu as répondu `o` : le téléchargement de PyTorch et Demucs, deux lignes `modèle … prêt`,
  deux lignes `vitesse … environ N min pour un morceau de 4 min`, puis `Séparation de stems installée`.

Appuie sur Entrée pour fermer la fenêtre.

**Si ça ne marche pas :**

| Message | Solution |
|---|---|
| `dossier REAPER introuvable` | Lance REAPER une fois, quitte-le, relance l'installateur |
| `installation de uv impossible (internet ?)` | Vérifie la connexion internet, relance l'installateur |
| `REAPER est ouvert : les actions ne peuvent pas être enregistrées` | Pas grave : quitte REAPER et relance l'installateur, ou charge les actions à la main (étape 5) |
| `séparation de stems non installée` | Le reste de ReaCue marche. Réessaie plus tard avec `Install ReaCue Stems.command` / `.bat` |

> L'installateur peut être relancé autant de fois que tu veux : il répare l'installation et garde tes réglages.

---

## 5. Vérifier dans REAPER

1. Lance REAPER.
2. Menu **Actions → Show action list…**
3. Dans le champ **Filter** en haut, tape `ReaCue`.

**Tu dois voir** trois actions :

- `Custom: ReaCue - Préparer le morceau`
- `Custom: ReaCue - Republier le prompteur`
- `Custom: ReaCue - Séparer les stems`

**Astuce : des boutons dans la barre d'outils.** Clic droit sur la barre d'outils principale (en haut à
gauche) → **Customize toolbar…** → **Add…** → filtre `ReaCue` → choisis l'action → **Select/close**. Recommence
pour les autres actions, puis **Save**.

**Si les actions n'apparaissent pas** (REAPER était ouvert pendant l'installation) :

1. Dans la liste des actions, clique sur **New action… → Load ReaScript…**
2. Va dans le dossier des scripts : menu *Options → Show REAPER resource path in explorer/finder*, puis
   `Scripts` → `ReaCue`.
3. Choisis `ReaCue_Preparer.lua` → **Ouvrir**. Recommence avec `ReaCue_Republier_prompteur.lua` et
   `ReaCue_Separer_stems.lua`.

---

## 6. Activer l'interface web de REAPER (une seule fois)

Le prompteur des téléphones passe par le petit serveur web intégré à REAPER.

1. Mac : menu **REAPER → Settings…** ; Windows : menu **Options → Preferences…**
2. Dans la liste de gauche, tout en bas : **Control/OSC/web**.
3. Clique sur **Add**.
4. **Control surface mode** : choisis **Web browser interface**.
5. **Port** : `8080` (garde cette valeur si possible).
6. Laisse le reste tel quel, clique **OK**, puis **OK** pour fermer les préférences.

**Pour vérifier :** sur l'ordinateur, ouvre un navigateur à l'adresse `http://localhost:8080/` : une page
de REAPER doit s'afficher.

**Si ça ne marche pas :** un autre programme utilise peut-être le port 8080 → recommence avec `8081` (et
utilise ce port partout dans la suite). Sous Windows, si le pare-feu demande l'autorisation pour REAPER,
coche **Réseaux privés** et clique **Autoriser**.

---

## 7. Créer le projet d'un morceau

**Un projet REAPER par morceau.** ReaCue remplace les régions, le tempo et les pistes CLICK / CUES / VOIX à
chaque préparation : ne mets pas plusieurs morceaux dans le même projet.

1. Crée un dossier pour le morceau, par exemple `Documents/REAPER Media/Demo Song/`.
2. **Copie dedans les fichiers audio du morceau** (stems ou MP3).
   > ⚠️ Sur Mac, évite de laisser les fichiers dans *Téléchargements* : macOS peut empêcher REAPER de les
   > lire (l'item affiche alors « OFFLINE »).
3. Dans REAPER : **File → New project**.
4. **File → Save project as…**, choisis le dossier du morceau, nomme le projet (`Demo Song`), et coche
   **Copy all media into project directory** si l'option est proposée. **Save**.

---

## 8. Importer l'audio : des stems ou un seul MP3

### Cas A : tu as les stems

1. Sélectionne tous les fichiers de stems dans le Finder / l'Explorateur.
2. **Glisse-les ensemble** dans la zone des pistes de REAPER, tout au début (à gauche).
3. Si REAPER demande comment placer plusieurs fichiers, choisis **« One per track »** (un par piste).

**Tu dois voir** une piste par stem, tous les items commençant au même endroit.

Les noms de fichiers comptent : ReaCue reconnaît le rôle de chaque stem grâce à des mots dans le nom :

| Rôle | Mots reconnus dans le nom du fichier |
|---|---|
| Batterie | `drum`, `batterie`, `kick`, `perc` |
| Basse | `bass`, `basse` |
| Guitare | `guitar`, `guitare`, `gtr` (`lead` ou `solo` = guitare solo) |
| Chant | `vocal`, `voice`, `vox`, `chant`, `voix` |
| Autre | tout le reste (claviers…) |

> Bonus : la tonalité et le tempo dans le nom (ex. `Demo Song-A minor-112bpm-drums.wav`) améliorent les
> accords et évitent les erreurs de tempo double/moitié.

Passe directement à l'**étape 10**.

### Cas B : tu n'as qu'un MP3 (ou un WAV)

1. Glisse le fichier dans la zone des pistes de REAPER, tout au début.

Tu peux préparer directement le morceau (étape 10), mais avec moins de détails (pas de vue batterie, pas
d'entrées/sorties par instrument, accords et sections moins sûrs). **Mieux : sépare-le d'abord en stems
(étape 9).**

---

## 9. Séparer un MP3 en stems

*Nécessite la séparation de stems installée (réponse `o` à l'étape 4, ou `Install ReaCue Stems`).*

1. **Clique sur l'item du MP3** dans REAPER pour le sélectionner (il devient plus clair).
2. Lance **ReaCue - Séparer les stems** (bouton de la barre d'outils, ou *Actions → Show action list…* →
   filtre `ReaCue` → sélectionne l'action → **Run**).
3. Une fenêtre **« Séparation des stems : N % »** s'affiche avec une barre de progression.
   - Compte **5 à 8 minutes pour un morceau de 4 minutes** sur un Mac Intel, moins sur un Mac récent.
   - Tu peux fermer cette fenêtre et continuer à travailler : l'import se fera tout seul à la fin.
   - Ne ferme pas REAPER pendant la séparation.
4. À la fin, un message **« Stems importés »** s'affiche.

**Tu dois voir** six nouvelles pistes sous la piste d'origine : **Chant, Batterie, Basse, Guitare, Piano,
Autres**, calées exactement comme le MP3. L'item du MP3 a été retiré du projet (le fichier, lui, est toujours
sur le disque ; *Edit → Undo* le remet).

Les fichiers des stems sont rangés à côté du MP3, dans `<nom du morceau>-stems/htdemucs_6s/`. Si tu relances
l'action sur le même MP3, l'import est immédiat (pas de nouvelle séparation).

> Écoute les pistes en solo (bouton **S**) : voix, batterie et basse sont en général très propres ; guitare
> et piano peuvent garder un peu des autres instruments. C'est normal et suffisant pour ReaCue. Une piste
> presque vide (par exemple Piano dans un morceau sans clavier) n'est pas un problème.

**Si ça ne marche pas :**

| Message | Solution |
|---|---|
| « Sélectionne l'item audio du morceau » | Clique sur l'item du MP3, puis relance l'action |
| « Fichier audio introuvable… OFFLINE » | Le fichier n'est pas lisible : voir [Dépannage](#16-dépannage) |
| « La séparation de stems n'est pas installée » | Double-clic sur `Install ReaCue Stems.command` / `.bat` dans le dossier ReaCue |
| « La séparation a échoué » | Lis la fin du journal affichée ; le journal complet est `…-stems/demucs.log` |
| La fenêtre reste longtemps à 0 % | Normal pendant la première minute (chargement du modèle) |

---

## 10. Préparer le morceau

1. Lance **ReaCue - Préparer le morceau**. (Pas besoin de sélectionner quoi que ce soit.)
2. Une fenêtre **« Préparation du morceau en cours »** tourne de 20 secondes à 1 minute environ.
3. Une fenêtre de résultat s'affiche : tempo, nombre de mesures, **structure** (mesures et longueur de
   chaque section), ce qui a été publié pour le prompteur (accords, paroles, batterie).

**Tu dois voir** dans le projet :

- des **régions** colorées en haut (Intro, Couplet 1, Refrain 1…) ;
- des marqueurs **« → Refrain »** avant chaque section ;
- trois nouvelles pistes : **CUES**, **VOIX**, **CLICK** ;
- l'audio décalé de 2 mesures pour laisser la place au décompte.

Appuie sur **Espace** : tu entends 2 mesures de click avec « one two three four », puis le morceau, le click
et les annonces.

> Enregistre le projet (**Cmd+S** / **Ctrl+S**).

**Si ça ne marche pas :**

| Message | Solution |
|---|---|
| « Le pont ReaCue ne tourne pas dans REAPER » | Redémarre REAPER ; sinon relance l'installateur (REAPER fermé) |
| « Programme ReaCue introuvable » | Le dossier ReaCue a été déplacé : relance l'installateur depuis son nouvel emplacement |
| « Une préparation est déjà en cours » | Attends la fin de la précédente (1 minute max) |
| Le tempo est le double ou la moitié du vrai | Ajoute le tempo dans le nom des fichiers (ex. `-94bpm`) et relance *Préparer* |

---

## 11. Vérifier la structure

Lis la structure dans la fenêtre de résultat et en haut du projet. Points à regarder :

- **les longueurs inhabituelles** : une section qui ne fait pas 4, 8 ou 16 mesures est souvent une erreur
  (deux sections collées, ou une section coupée en deux) ;
- **les noms** : couplet et refrain peuvent être inversés, un pré-refrain peut être collé au refrain ;
- la fin : une longue « Outro » peut contenir un dernier refrain ou un solo.

Écoute les débuts de section : **clique dans la règle** (la barre des temps, en haut) au début d'une région
pour y placer le curseur, puis **Espace**.

**Pour corriger :**

- Les régions déplacées ou renommées **à la main** dans REAPER ne sont **pas** relues par ReaCue : elles
  seront écrasées à la préparation suivante.
- Avec **Claude Desktop** (mode facultatif, voir le README) : dis simplement « le refrain 1 commence mesure
  37 » ou « renomme la section 6 en Solo » ; tout est reconstruit (régions, click, annonces, prompteur).
- Relancer *Préparer* sur le même projet **garde la structure validée** et reconstruit le reste.

---

## 12. Ajouter les paroles

ReaCue ne télécharge jamais de paroles : **c'est toi qui fournis le texte**.

1. Ouvre un éditeur de texte :
   - Mac : **TextEdit**, puis menu **Format → Convertir au format texte** (important : texte brut) ;
   - Windows : **Bloc-notes**.
2. Écris (ou colle) les paroles : **une ligne = une phrase chantée**, une ligne vide entre les blocs
   (couplet, refrain…). Les lignes comme `[Refrain]` ou `Couplet 2 :` sont ignorées. `(x2)` en fin de ligne
   la répète.
3. Enregistre le fichier sous le nom **`paroles.txt`** (encodage **UTF-8**), **dans le dossier des stems**.
   Pour un MP3 séparé par ReaCue, tu peux le mettre **à côté du MP3 d'origine** (ou dans le dossier
   `…-stems/htdemucs_6s/`).
4. Dans REAPER, lance **ReaCue - Republier le prompteur** (rien n'est modifié dans le projet).

**Tu dois voir** dans la fenêtre de fin : `Prompteur publié : … N lignes de paroles`. Sur le téléphone, en vue **Chant**, les lignes
défilent avec le morceau.

Les lignes sont calées automatiquement sur le stem de voix. Si une ligne tombe mal, tu peux la caler à la
main avec un fichier d'ancres `paroles_calage.json` (voir la section *Paroles* du LISEZMOI).

---

## 13. Ouvrir le prompteur sur les téléphones

1. Connecte le téléphone au **même Wi-Fi** que l'ordinateur.
2. Trouve l'adresse IP de l'ordinateur (si tu ne l'as pas notée à l'étape 4) :
   - Mac : *Réglages Système → Wi-Fi → Détails…* (à côté du réseau connecté) → **Adresse IP** ;
   - Windows : *Paramètres → Réseau et Internet → Wi-Fi → propriétés du réseau* → **Adresse IPv4**.
3. Sur le téléphone, ouvre le navigateur et tape : **`http://<adresse IP>:8080/prompteur.html`**
   (exemple : `http://192.168.1.20:8080/prompteur.html`). Attention : `http`, pas `https`.
4. Choisis ton rôle : **Batterie**, **Basse**, **Guitare rythm.**, **Guitare solo**, **Chant** ou **Général**
   (le choix est mémorisé sur ce téléphone ; le bouton **Rôle** permet d'en changer).
5. Lance la lecture dans REAPER : le prompteur suit la position (section, mesure, temps).

**Tu dois voir** un point vert (liaison avec REAPER active), la section en cours et la suivante.

Conseils :

- **Écran d'accueil** : iPhone : bouton *Partager → Sur l'écran d'accueil* ; Android : menu **⋮ → Ajouter à
  l'écran d'accueil**. La page s'ouvre alors en plein écran, comme une application.
- **Mise en veille** : touche le bouton **⛶** (plein écran), qui demande au téléphone de rester allumé. Si
  l'écran s'éteint quand même, désactive le verrouillage automatique pendant la répétition (iPhone :
  *Réglages → Luminosité et affichage → Verrouillage automatique → Jamais* ; Android : *Affichage → Mise en
  veille de l'écran*).
- **Adresse qui change** : la box peut donner une autre adresse IP à l'ordinateur d'un jour à l'autre, et les
  favoris des téléphones ne marchent plus. Dans l'interface de ta box ou de ton routeur, cherche
  **« Réservation DHCP »** (ou « bail statique », « IP fixe ») et réserve l'adresse actuelle pour
  l'ordinateur. En concert, un petit routeur de voyage dédié au groupe évite toute surprise.
- Le bouton **FR/EN** change la langue du prompteur sur ce téléphone.

---

## 14. Régler le click, les annonces et les in-ears

Les réglages sont dans le fichier **`reacue_settings.json`**, dans le dossier des ressources de REAPER :
menu *Options → Show REAPER resource path in explorer/finder* → dossier **`ReaCueMCP`**.

1. Ouvre `reacue_settings.json` avec TextEdit (Mac) ou le Bloc-notes (Windows).
2. Modifie les valeurs voulues **en respectant la syntaxe** : guillemets autour des textes, `true` / `false` /
   `null` sans guillemets, une virgule entre chaque ligne sauf la dernière.
3. Enregistre, puis relance **ReaCue - Préparer le morceau** (la structure validée est gardée).

Exemples courants :

| Je veux… | Réglage |
|---|---|
| 1 seule mesure de décompte | `"count_in_bars": 1` |
| Le décompte en français | `"count_lang": "fr"` |
| Pas d'annonces vocales, seulement le click | `"voice_cues": false` |
| Click plus fort | `"click_volume": 0.8` |
| Click et voix seulement dans les in-ears (sorties 3/4 de la carte son), pas en façade | `"click_hw_output": 2` et `"click_to_master": false` |
| Séparation en 4 stems au lieu de 6 | `"stems_model": "htdemucs"` |

Pour `click_hw_output` : `0` = sorties 1/2, `2` = sorties 3/4, `4` = sorties 5/6, etc.

Pour les voix des annonces (`announce_voice`), voir la section *Réglages* du LISEZMOI.

---

## 15. En répétition

- Ouvre le projet du morceau, place le curseur au tout début (**Home**), appuie sur **Espace**.
- Les musiciens entendent (ou voient sur le prompteur) le décompte, puis les annonces avant chaque section.
- Pour reprendre à une section : **clic dans la règle** au début de sa région, puis **Espace**. Le prompteur suit.
- Pour boucler une partie : clique sur la région (barre des régions, en haut) pour la sélectionner, puis
  active la répétition (**R**, ou le bouton de boucle du transport).
- Seul REAPER doit tourner pendant la répétition : ReaCue et Claude ne sont pas nécessaires.

---

## 16. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| L'item affiche **OFFLINE** (Mac) | REAPER n'a pas le droit de lire le fichier, souvent dans *Téléchargements* | Copie le fichier dans le dossier du projet, puis glisse-le à nouveau dans REAPER (ou clic droit sur l'item → *Item properties…* → *Choose new file*). Autre solution : *Réglages Système → Confidentialité et sécurité → Fichiers et dossiers → REAPER*, active le dossier concerné, redémarre REAPER |
| « Le pont ReaCue ne tourne pas » | Le pont n'a pas démarré | Redémarre REAPER ; une fenêtre restée ouverte dans REAPER peut aussi le bloquer |
| Le prompteur affiche « REAPER ne répond pas » | Mauvais Wi-Fi, mauvaise adresse, interface web non activée, pare-feu | Vérifie l'étape 6 et l'étape 13 ; essaie `http://localhost:8080/` sur l'ordinateur |
| Les téléphones ne trouvent plus la page | L'adresse IP de l'ordinateur a changé | Nouvelle adresse (étape 13), puis réservation DHCP |
| Pas d'annonces vocales | Voix absente | Mac : *Réglages Système → Accessibilité → Contenu énoncé* ; Windows : *Paramètres → Heure et langue → Voix* |
| Séparation de stems très lente | Processeur occupé | Ferme les autres applications ; compte 1,5 à 2 fois la durée du morceau |
| Structure fausse | Détection automatique imparfaite | Étape 11 (Claude, ou tempo dans le nom des fichiers) |
| Journaux | — | Préparation : `ReaCueMCP/cli.log` (dossier des ressources REAPER) ; séparation : `…-stems/demucs.log` à côté du morceau |

---

## 17. Pense-bête : un nouveau morceau

1. Dossier du morceau dans `Documents/REAPER Media/`, fichiers audio copiés dedans.
2. REAPER : *File → New project*, puis *File → Save project as…* dans ce dossier.
3. Glisser les stems (un par piste) **ou** le MP3.
4. MP3 seul : sélectionner l'item → **ReaCue - Séparer les stems** (5 à 8 min).
5. **ReaCue - Préparer le morceau**.
6. Vérifier la structure (longueurs inhabituelles, noms).
7. Facultatif : `paroles.txt` à côté des fichiers → **ReaCue - Republier le prompteur**.
8. Enregistrer le projet (**Cmd+S** / **Ctrl+S**).
9. Téléphones : `http://<IP>:8080/prompteur.html`, choisir son rôle.
