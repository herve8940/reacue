# ReaCue

**Des morceaux prêts pour le live dans REAPER, en un clic — et un prompteur sur le téléphone de chaque musicien.**

*[English version: README.md](README.md)*

ReaCue s'adresse aux groupes qui jouent en live avec REAPER. À partir des stems d'un morceau (ou d'un seul
MP3, qu'il sait séparer lui-même en stems, en local), il détecte le tempo, la grille des mesures et la structure, puis construit tout dans le projet REAPER :
carte de tempo, régions nommées et colorées, click avec count-in, annonces vocales (« Refrain »…) et décompte
« one two three four » avant chaque section. Il publie aussi un **prompteur web** que chaque musicien ouvre
sur son téléphone, servi par l'interface web intégrée de REAPER : structure, accords (basse / guitares),
paroles calées (chant) et une vue batteur dédiée avec les grooves et les fills transcrits.

Tout tourne en local : ni IA ni internet une fois installé. Un mode facultatif permet de piloter ReaCue en
langage naturel avec Claude (serveur MCP).

> **Nouveau sur ReaCue ? Suis le tutoriel pas à pas : [docs/TUTORIEL_fr.md](docs/TUTORIEL_fr.md)**
> (anglais : [docs/TUTORIAL_en.md](docs/TUTORIAL_en.md)).

> **État : 0.12.0 bêta.** Développé et utilisé sur macOS. La prise en charge de Windows est nouvelle et
> **n'a pas encore été testée sur une vraie machine** — vos retours sont les bienvenus.

| Batterie | Basse | Chant | Guitare |
|---|---|---|---|
| <img src="docs/images/prompter_drums_fr.png" width="190"> | <img src="docs/images/prompter_bass_fr.png" width="190"> | <img src="docs/images/prompter_vocals_fr.png" width="190"> | <img src="docs/images/prompter_guitars_fr.png" width="190"> |

<img src="docs/images/prompter_drums_fr_tablet.png" width="780">

*(Captures d'un morceau fictif « Demo Song » : structure, accords, paroles et batterie sont inventés.)*

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Principe](#principe)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Activer l'interface web de REAPER (prompteur)](#activer-linterface-web-de-reaper-prompteur)
- [Séparation de stems (facultatif)](#séparation-de-stems-facultatif)
- [Utilisation](#utilisation)
- [Mode concert](#mode-concert)
- [Paroles](#paroles)
- [Réglages](#réglages)
- [Facultatif : piloter ReaCue avec Claude (MCP)](#facultatif--piloter-reacue-avec-claude-mcp)
- [Limites connues](#limites-connues)
- [Dépannage / FAQ](#dépannage--faq)
- [Désinstallation](#désinstallation)
- [Pour les développeurs](#pour-les-développeurs)
- [Crédits et licence](#crédits-et-licence)

## Fonctionnalités

Dans REAPER, à partir de l'audio déjà présent dans le projet :

- **Carte de tempo** calée sur le morceau : tempo fixe quand l'enregistrement est quantisé, ou un marqueur
  de tempo par mesure quand il a été joué sans click (le click suit alors le groupe). L'audio est déplacé
  pour que la mesure 1 tombe pile sur une barre de mesure.
- **Une région par section**, nommée et colorée (Intro, Couplet 1, Pré-refrain, Refrain, Pont, Solo,
  Break, Outro, Main Riff…), en français ou en anglais.
- **Piste CLICK** (source click native de REAPER) avec **count-in** de 2 mesures, envoyable sur une sortie
  physique dédiée pour les in-ears.
- **Piste VOIX** : annonce vocale (« Refrain ») sur l'avant-dernière mesure de chaque section et « one two
  three four » sur la dernière, routée comme le click. Utilise les voix du système (macOS `say`, Windows SAPI).
- **Piste CUES** et marqueurs « → Refrain », lisibles d'un coup d'œil.
- **Séparation de stems** (facultatif) : transforme un seul MP3/WAV en 6 stems (voix, batterie, basse,
  guitare, piano, autres) avec [Demucs](https://github.com/facebookresearch/demucs), sur ton ordinateur, sans
  abonnement ni envoi en ligne — puis ReaCue prépare le morceau à partir des stems.
- **Mode concert** : plusieurs morceaux préparés enchaînés dans un seul projet, arrêt automatique à la fin
  de chaque morceau, une fenêtre *ReaCue - Concert* pour piloter le concert, un **QR code** pour les
  musiciens et une télécommande **Régie** sur téléphone (code PIN) ; un bouton **Vérifier** (contrôle
  avant concert, avec corrections en un clic) et un mode **Répétition** : boucler une section ou une plage
  avec une mesure de décompte avant chaque reprise, vitesse 100 à 70 %.

Sur les téléphones et tablettes des musiciens (prompteur web) :

- section en cours, mesure et temps, mesures restantes, section suivante, décompte sur la dernière mesure ;
- **Basse / guitares** : accord en cours et suivant avec décompte, grille de la section, tonalité ;
- **Chant** : paroles défilantes calées sur le morceau, ligne suivante et décompte avant chaque entrée ;
- **Batterie** : groove de la section, grille 16 pas de la mesure en cours, fills, crashs, arrêts et reprises ;
- entrées et silences de chaque instrument détectés sur les stems (« STOP à la prochaine mesure »,
  « Entrée dans 2 mesures ») ;
- français / anglais ; suit le curseur de lecture de REAPER (sur scène, seul REAPER doit tourner) ;
- en mode concert : morceau x/N et morceau suivant ; rôle **Régie** pour piloter le concert depuis un téléphone.

## Principe

```
 Action REAPER « ReaCue - Préparer le morceau »          Claude (facultatif, MCP)
                 │                                         │
                 ▼                                         ▼
        Programme ReaCue (Python) : analyse audio, tempo, sections, accords, paroles, batterie
                 │  dépose des données (jamais de code) dans <ressources REAPER>/ReaCueMCP/
                 ▼
        ReaCue_Bridge.lua (tourne en fond dans REAPER) ──> API REAPER
                 │
                 └──> reaper_www_root/prompteur.html + reacue_song.json ──> téléphones (Wi-Fi)
```

## Prérequis

- **REAPER 7** ou plus récent (la 6.x marche probablement, non testée).
- **macOS 12+** (Intel ou Apple Silicon) ou **Windows 10/11** (bêta).
- Environ 1,5 Go d'espace disque (environnement Python et bibliothèques), plus 1,5 Go environ pour la
  séparation de stems facultative.
- **Internet seulement pendant l'installation** (téléchargement de Python et des bibliothèques). Rien n'est
  envoyé ensuite ; aucune parole n'est jamais téléchargée.
- Pour le prompteur : téléphones et ordinateur sur le même réseau Wi-Fi.

## Installation

1. Télécharge le projet (bouton vert **Code** → *Download ZIP*) et dézippe-le **là où il restera**, par
   exemple `Documents/ReaCue`. Ne déplace plus le dossier ensuite (ou relance l'installation si tu le fais).
2. Lance REAPER une fois (pour que son dossier de réglages existe), puis **quitte REAPER** : l'installateur
   peut alors enregistrer les actions tout seul.
3. Lance l'installateur :
   - **macOS** : double-clic sur **`Install ReaCue.command`**. Si macOS refuse de l'ouvrir (« développeur
     non identifié »), clic droit → *Ouvrir* → *Ouvrir*. Autre possibilité dans le Terminal :
     `bash "Install ReaCue.command"`.
   - **Windows** : double-clic sur **`Install ReaCue.bat`**. Si SmartScreen affiche un avertissement :
     *Informations complémentaires* → *Exécuter quand même*.
4. Réponds aux questions : langue (`fr` / `en`), déclaration de ReaCue dans Claude Desktop (facultatif,
   réponds *non* si tu n'utilises pas Claude) et installation de la **séparation de stems** (facultatif,
   environ 1 Go à télécharger, 5 à 15 minutes ; voir [Séparation de stems](#séparation-de-stems-facultatif)).
5. Lance REAPER. Le pont démarre tout seul et trois actions sont disponibles dans *Actions → Show action list* :
   - **ReaCue - Préparer le morceau**
   - **ReaCue - Republier le prompteur**
   - **ReaCue - Séparer les stems** (fonctionne une fois la séparation de stems installée)

   Astuce : ajoute-les à une barre d'outils (clic droit sur une barre → *Customize toolbar* → *Add*).

L'installateur peut être relancé à tout moment (changer de langue, réparer une installation) : tes réglages
et tes morceaux préparés sont conservés.

Ce qu'il fait : installe [uv](https://docs.astral.sh/uv/) (gestionnaire Python d'Astral) si besoin, crée un
environnement Python 3.12 privé dans le dossier `.venv` (paquets précompilés uniquement, aucun compilateur
nécessaire), copie les scripts REAPER dans `<ressources REAPER>/Scripts/ReaCue/`, ajoute le pont à
`Scripts/__startup.lua`, enregistre les actions dans `reaper-kb.ini` (seulement si REAPER est fermé) et
écrit `<ressources REAPER>/ReaCueMCP/reacue_settings.json`. Rien d'autre n'est modifié sur le système.

Si REAPER était ouvert pendant l'installation, charge les actions une fois à la main : *Actions → Show action
list → New action → Load ReaScript…* → choisis `ReaCue_Preparer.lua`, `ReaCue_Republier_prompteur.lua` et
`ReaCue_Separer_stems.lua` dans `<ressources REAPER>/Scripts/ReaCue/`. (*Options → Show REAPER resource path* ouvre ce dossier.)

## Activer l'interface web de REAPER (prompteur)

À faire une fois, à la main (REAPER n'offre pas de moyen sûr de le faire par script) :

1. REAPER → *Options → Preferences* (macOS : *REAPER → Settings*) → **Control/OSC/web** → **Add**.
2. Control surface mode : **Web browser interface**. Port : **8080** (ou un autre port libre). Le reste ne change pas.
3. OK, OK.

Sur chaque téléphone ou tablette, ouvre : **`http://<IP de l'ordinateur>:8080/prompteur.html`**, puis
choisis ton rôle.

Trouver l'adresse IP de l'ordinateur :

- **macOS** : *Réglages Système → Wi-Fi → Détails…* à côté du réseau → *Adresse IP* (ex. `10.0.1.23`).
- **Windows** : *Paramètres → Réseau et Internet → Wi-Fi → propriétés du réseau → Adresse IPv4*, ou
  `ipconfig` dans une invite de commandes.
- L'installateur affiche aussi l'adresse probable à la fin.

Conseils :

- **Réserve l'adresse IP** de l'ordinateur dans la box ou le routeur (réservation DHCP, parfois appelée
  « bail statique ») : l'adresse ne change plus et les favoris des téléphones restent valables. En concert,
  un petit routeur de voyage dédié est idéal.
- Ajoute la page à l'écran d'accueil (iOS : *Partager → Sur l'écran d'accueil* ; Android : *⋮ → Ajouter à
  l'écran d'accueil*) pour un affichage plein écran comme une application. Le bouton ⛶ passe aussi en plein écran.
- Le bouton **FR/EN** change la langue du prompteur sur ce téléphone (mémorisé).
- Le point vert indique que la liaison avec REAPER est active.

## Séparation de stems (facultatif)

ReaCue donne ses meilleurs résultats avec des stems (un fichier par instrument). Si tu n'as que le MP3 d'un
morceau, ReaCue peut le séparer pour toi avec [Demucs](https://github.com/facebookresearch/demucs)
(recherche Meta AI, licence MIT), entièrement sur ton ordinateur : rien n'est envoyé en ligne, aucun abonnement.

**Installation** (une fois) : réponds *oui* à la question de l'installateur sur la séparation de stems, ou
plus tard double-clic sur **`Install ReaCue Stems.command`** (macOS) / **`Install ReaCue Stems.bat`**
(Windows). Cela crée un environnement Python séparé `.venv-demucs` dans le dossier de ReaCue (PyTorch +
Demucs, environ 1 Go), télécharge les deux modèles et mesure la vitesse de ton ordinateur. L'environnement
de ReaCue lui-même n'est pas touché.

**Utilisation** :

1. Glisse le MP3 (ou le WAV) dans un projet REAPER vide et clique dessus pour le sélectionner.
2. Lance **ReaCue - Séparer les stems**. Une fenêtre montre l'avancement (tu peux la fermer).
3. À la fin, six pistes apparaissent (Chant, Batterie, Basse, Guitare, Piano, Autres), calées exactement
   comme l'item d'origine, qui est retiré du projet (un seul *Annuler* le remet ; le fichier reste sur le disque).
4. Lance **ReaCue - Préparer le morceau** comme d'habitude.

Détails :

- Durée : environ **5 à 8 minutes pour un morceau de 4 minutes** sur un Mac Intel récent (4 cœurs), plus
  rapide sur Apple Silicon. C'est le processeur qui travaille (aucune carte graphique nécessaire).
- Les stems sont écrits à côté du fichier d'origine, dans `<nom du morceau>-stems/htdemucs_6s/`, et gardent
  le nom du fichier d'origine (tonalité et tempo dans le nom restent lus par ReaCue). Relancer l'action sur le
  même fichier les importe immédiatement, sans refaire la séparation.
- `stems_model` dans les réglages : `"htdemucs_6s"` (6 stems, par défaut) ou `"htdemucs"` (4 stems : voix,
  batterie, basse, autres — guitare et claviers restent ensemble dans « autres »).
- Qualité : voix, batterie et basse sont très bonnes ; guitare et surtout piano sont moins propres qu'avec
  les services commerciaux (un peu de repisse). Guitare lead et rythmique ne sont pas séparées : la détection
  des solos, qui s'appuie sur un stem de guitare lead, n'est donc pas disponible.
- Mac Intel : PyTorch n'est plus publié pour les Mac Intel après la version 2.2.2 ; l'installateur choisit
  automatiquement les bonnes versions.

## Utilisation

1. **Importe le morceau** dans un projet REAPER, un stem par piste, tous calés au même départ (glisser-déposer
   des fichiers). Un seul MP3/WAV marche aussi, avec moins de détails — ou sépare-le d'abord avec
   **ReaCue - Séparer les stems** (voir plus haut).
   - Le rôle de chaque stem est lu dans le **nom du fichier** : `drum`/`batterie`/`kick`/`perc`,
     `bass`/`basse`, `guitar`/`guitare`/`gtr` (`lead`/`solo` = guitare solo), `vocal`/`voice`/`vox`/`chant`/`voix` ;
     tout le reste compte comme claviers/autre.
   - Facultatif : la tonalité et le tempo dans le nom des fichiers (ex. `Demo Song-A minor-112bpm-drums.wav`)
     aident les accords et le choix entre tempo double et moitié.
2. Lance **ReaCue - Préparer le morceau**. Une petite fenêtre montre l'avancement (de 20 s à 1 min environ) ;
   tu peux la fermer, le résultat s'affiche à la fin : tempo, structure (mesures et longueurs), ce qui a été publié.
3. Vérifie la structure (régions) et écoute. Pour la corriger, **modifie les régions à la main dans REAPER**
   (déplacer, renommer, ajouter, supprimer), puis relance *Préparer* : voir
   [Corriger la structure](#corriger-la-structure). Relancer *Préparer* sur le même projet **garde la
   structure validée** (ou reprend tes régions modifiées) et reconstruit tout (click, annonces, prompteur),
   en appliquant le fichier de réglages s'il a été modifié entre-temps.
4. Après avoir ajouté ou modifié un fichier de paroles, lance **ReaCue - Republier le prompteur** (rien
   n'est modifié dans le projet REAPER).

Chaque préparation **remplace** les régions, marqueurs, la carte de tempo et les pistes CLICK / CUES / VOIX
du projet (un seul *Annuler* revient en arrière). Prévois un projet par morceau.

### Corriger la structure

Deux méthodes, qu'on peut mélanger :

- **À la main dans REAPER, puis *Préparer*.** Double-clique sur une région dans la barre des régions (en haut
  de la fenêtre) pour changer son nom ou son début ; ajoutes-en une avec une sélection de temps et *Markers →
  Insert region from time selection* (Maj+R) ; supprimes-en une avec clic droit → *Remove region* ; ou fais
  simplement glisser ses bords, puis lance
  **ReaCue - Préparer le morceau**. Quand le morceau est déjà préparé (mêmes items audio), ReaCue lit les
  régions du projet et, si elles diffèrent de la structure enregistrée, **les adopte comme nouvelle
  structure** ; la fenêtre de fin indique alors « Structure reprise de tes régions REAPER ». Règles :
  - seul le **début** de chaque région compte : une section dure jusqu'au début de la région suivante ;
  - le début est placé sur la barre de mesure la plus proche (à moins d'un quart de mesure, sans rien dire ;
    au-delà, arrondi avec un avertissement) ;
  - les noms sont repris tels quels (français ou anglais) ; le type de section — couleur, annonce, rôle dans
    le prompteur — est déduit du nom (« Refrain 2 », « Chorus », « Solo »…) ;
  - une région avant la mesure 1, après la fin du morceau ou sur la même mesure qu'une autre est ignorée
    avec un avertissement ; si aucune région ne commence à la mesure 1, les premières mesures sont
    rattachées à la première région ;
  - régions, couleurs, marqueurs « → », CUES, VOIX, CLICK et prompteur sont ensuite reconstruits.
  Si aucune région n'a changé, rien ne change (structure conservée). Dans un autre projet (consolidé, autre
  morceau), les régions ne sont jamais lues et rien n'est modifié.
- **Avec Claude** (mode facultatif, plus bas) : « le refrain 1 commence mesure 37 », « renomme la section 6
  en Solo ».

*Republier le prompteur* ne reprend **pas** les régions modifiées (le prompteur doit rester d'accord avec les
annonces et le click déjà dans REAPER) : un avertissement demande de lancer *Préparer*.

## Mode concert

Enchaîne plusieurs morceaux **déjà préparés** (chacun dans son projet) dans un seul projet REAPER, et pilote
tout le concert depuis une fenêtre ou depuis un téléphone.

1. **Construire le concert** — avec Claude : *« concert “Samedi” : Demo Song, Second Demo, Third Demo »*
   (outil `build_concert`), ou en ligne de commande :
   `python -m reacue_mcp.cli concert --name "Samedi" --songs "Demo Song" "Second Demo"`
   (macOS/Linux, depuis le dossier de ReaCue avec `.venv/bin/python` ; Windows : `.venv\Scripts\python reacue_cli.py concert …`).
   Les morceaux sont cherchés par nom de projet dans le dossier des projets (réglage `projects_dir`, défaut
   `<Documents>/REAPER Media`) ou donnés par leur chemin `.RPP`. Rien n'est réanalysé : chaque morceau garde
   ses stems, sa carte de tempo (fixe ou un tempo par mesure), sa structure validée, ses annonces et son click.
2. **L'ouvrir** — action REAPER **ReaCue - Concert** : sans concert ouvert, la fenêtre liste les concerts
   (dossier : réglage `concert_dir`, défaut `<dossier des projets>/Concerts`) ; un clic l'ouvre dans un
   **nouvel onglet** (ton projet en cours reste ouvert).
3. **Jouer** — un seul projet : une piste par instrument commune à tous les morceaux (Chant, Batterie,
   Basse, Guitares…, une couleur par morceau), CLICK / VOIX / CUES en bas, régions « Morceau · Refrain 1 »,
   une ligne de règle « Morceaux » avec les marqueurs « 1 · Demo Song ». La lecture **s'arrête toute seule
   à la fin de chaque morceau** et le curseur attend sur le décompte du suivant : Espace quand le groupe est prêt.

Fichiers écrits côte à côte : `<nom>.RPP` (le concert), `<nom>.setlist.json` (l'ordre, réutilisable),
`<nom>.concert.lua` (temps des morceaux, lus par la fenêtre), `<nom>.prompteur.json` (prompteur de tout le
concert). Corrige un morceau **dans son propre projet**, puis *Reconstruire le concert* (bouton Setlist) :
les modifications faites directement dans le projet concert sont écrasées.

**La fenêtre ReaCue - Concert** (ancrable : clic droit) affiche « 2 / 6 · Morceau », tempo, tonalité,
section, « mesure x / N », une pastille Lecture / Pause / Arrêt, la progression et le temps restant du
morceau, le temps du concert et le morceau suivant ; de gros boutons **Précédent / Début / Lecture-Pause /
Stop / Suivant** (pendant la lecture, Stop, Précédent et Suivant demandent un **double appui** en 2 s, pour
éviter les accidents) ; les **sections** du morceau en pastilles de couleur (clic = y aller, la lecture
continue) ; les boutons **Setlist**, **PIN** et **QR**. Ancrée en bas, elle tient sur une ligne (état +
transport + QR). Actions en plus *ReaCue - Morceau suivant* / *Morceau précédent* pour une pédale ou un
raccourci. L'arrêt automatique et la télécommande ne marchent que si cette fenêtre est ouverte (même ancrée).

**QR code pour les musiciens** — le bouton QR affiche en grand l'adresse du prompteur
`http://<IP de cet ordinateur>:<port>/prompteur.html` : l'IP est calculée au moment du clic (macOS
`ipconfig`, Windows `ipconfig`, Linux `hostname -I`) et le port lu dans les réglages de l'interface web de
REAPER (`reaper.ini`). Les musiciens le scannent avec l'appareil photo du téléphone (même Wi-Fi).
Encodeur QR : [luaqrcode](https://github.com/speedata/luaqrcode) (licence BSD).

**Régie (télécommande sur téléphone)** — dans le prompteur, choisis le rôle **Régie** : Lecture/Pause, Stop,
Précédent / Suivant, Début du morceau, setlist et sections cliquables, avec un ✓ quand REAPER a exécuté la
commande. Le **code PIN à 4 chiffres** affiché dans la fenêtre Concert est demandé une fois (généré au
premier lancement, modifiable avec le bouton PIN, mémorisé sur le téléphone). Les commandes passent par
l'interface web de REAPER (`/_/SET/EXTSTATE/ReaCue/remote/…`) et sont vérifiées par la fenêtre Concert (PIN,
protection contre le rejeu). ⚠️ Le PIN évite les fausses manipulations, **pas les attaques** : toute personne
sur le même réseau peut joindre directement l'interface web de REAPER (`/_/…`). En concert, utilise un Wi-Fi
réservé au groupe.

**Vérifier (contrôle avant concert)** — le bouton **Vérifier** de la fenêtre Concert liste, avec une pastille
verte / orange / rouge : fichiers audio lisibles (pas d'« OFFLINE »), fichiers des annonces présents,
morceaux préparés (structure et tempo), concert à jour (aucun projet de morceau modifié depuis la
construction — empreinte enregistrée à la construction), pont ReaCue, interface web de REAPER, adresse
réseau, carte son active, sorties du click et des annonces (sorties matérielles existantes, piste non
coupée), prompteur publié, téléphones Régie vus. Un bouton **Corriger** apparaît quand c'est possible :
remettre les médias en ligne, reconstruire le concert, republier le prompteur. Disponible aussi sans concert
ouvert (partie système seulement).

**Mode répétition** — le bouton **Répétition** (fenêtre ou téléphone Régie) coupe l'arrêt automatique.
Touche une section pour la **faire boucler** ; touche une 2e section du même morceau pour boucler toute la
plage (ex. Couplet 2 → Refrain 2). Avant le début de la boucle et **avant chaque reprise, une mesure de
décompte** est jouée avec le click et les annonces seuls (les autres pistes sont coupées pendant cette
mesure), au tempo de cet endroit du morceau. **Vitesse** 100 / 90 / 80 / 70 % (hauteur préservée ; click,
annonces et prompteur suivent). *Boucle off* arrête la boucle ; *Quitter* (ou sortir de la répétition depuis
le téléphone) remet tout comme avant : vitesse 100 %, arrêt automatique, répétition et sélection de temps de
REAPER.

Pas à pas : [tutoriel, chapitre concert](docs/TUTORIEL_fr.md#16-mode-concert--plusieurs-morceaux-dans-un-projet).

## Paroles

ReaCue **ne télécharge jamais de paroles** : tu fournis ton propre fichier texte, à côté des stems (même dossier) :

- nom commençant par `paroles`, `parole` ou `lyrics`, extension `.txt` (UTF-8) ou `.rtf` ;
- une ligne = une phrase chantée ; une ligne vide sépare les blocs (couplet, refrain…) ;
- les lignes-étiquettes comme `[Refrain]` ou `Couplet 2 :` sont ignorées ; `(x2)` ou `bis` en fin de ligne la répète ;
- un refrain écrit une seule fois est retrouvé automatiquement quand il est rechanté (stem voix nécessaire).

Les lignes sont calées automatiquement sur le stem voix. Pour corriger une ligne, ajoute un **fichier
d'ancres** à côté des paroles : `paroles_calage.json` (ou `lyrics_timing.json`). Il ne contient aucun texte,
seulement des numéros de ligne et des positions sur la grille :

```json
{
  "_commentaire": "les clés commençant par _ sont ignorées",
  "1": "9:1.5",
  "2": "11:1.5-12:4",
  "5#2": "47:2.75",
  "8": null
}
```

- clé `"12"` = ligne 12 (à partir de 1, lignes non vides, étiquettes exclues), 1re fois qu'elle est chantée ;
  `"12#2"` = 2e fois qu'elle est chantée (refrain répété) ;
- valeur `"45"` = mesure 45, temps 1 ; `"45:2.75"` = mesure 45, temps 2,75 (temps à partir de 1, décimales
  permises) ; `"45:2.75-49:1.5"` = début et fin ; `{"debut": "45:2.75", "fin": "49:1.5"}` idem ;
  `null` = ligne jamais affichée.
- Si **chaque** ligne a son ancre (ou `null`), le calage automatique n'est pas utilisé du tout.

Lance ensuite *Republier le prompteur*.

## Réglages

Fichier : `<ressources REAPER>/ReaCueMCP/reacue_settings.json` (créé par l'installateur ; modifiable avec
n'importe quel éditeur de texte ; une clé absente prend sa valeur par défaut). Pris en compte au prochain
*Préparer*, y compris pour un morceau déjà préparé (sa structure validée est gardée). Le réglage `language`
nomme les sections des morceaux nouvellement analysés ; les noms de sections que tu as validés restent tels quels.

| Clé | Défaut | Rôle |
|---|---|---|
| `language` | `"fr"` | `"fr"` ou `"en"` : noms des régions, annonces, prompteur, messages |
| `count_in_bars` | `2` | mesures de click avant la mesure 1 |
| `cue_lead_bars` | `2` | annonce N mesures avant la section (2 = avant-dernière mesure) |
| `voice_cues` | `true` | annonce vocale des sections |
| `voice_count_in` / `voice_count_each` | `true` | « one two three four » sur le count-in / avant chaque section |
| `count_lang` | `"en"` | langue du décompte (`"en"` ou `"fr"`) |
| `announce_voice` / `count_voice` | `null` | nom d'une voix du système (macOS : `Thomas`, `Samantha`… Windows : `Microsoft Hortense Desktop`, `Microsoft Zira Desktop`…) ; `null` = automatique |
| `count_rate` | `240` | débit du décompte (mots par minute) |
| `voice_volume` / `click_volume` | `0.8` / `0.5` | volume des pistes |
| `click_to_master` | `true` | `false` = click et voix seulement sur `click_hw_output` (in-ears) |
| `click_hw_output` | `null` | sortie physique (0 = sorties 1/2, 2 = 3/4…) |
| `tempo_mode` | `"auto"` | `auto`, `constant` (un seul tempo) ou `beatmap` (un tempo par mesure) |
| `stems_model` | `"htdemucs_6s"` | modèle de séparation de stems : `"htdemucs_6s"` (6 stems) ou `"htdemucs"` (4 stems) |
| `projects_dir` | `null` | mode concert : dossier où chercher les projets des morceaux par leur nom ; `null` = `<Documents>/REAPER Media` |
| `concert_dir` | `null` | mode concert : dossier des concerts ; `null` = `<dossier des projets>/Concerts` |

Voix : sous Windows, on ajoute des voix (par exemple françaises) dans *Paramètres → Heure et langue →
Voix*. Seules les voix visibles par SAPI (voix « Desktop ») sont utilisées. Sans aucune voix, tout fonctionne
sauf les annonces (un avertissement s'affiche).

## Facultatif : piloter ReaCue avec Claude (MCP)

Si tu utilises [Claude Desktop](https://claude.ai/download), réponds *oui* pendant l'installation (ou relance
l'installateur). Le serveur `reacue` est ajouté à la configuration de Claude Desktop (sauvegarde gardée sous
`claude_desktop_config.json.bak-reacue`). Redémarre Claude Desktop puis demande par exemple :

- « Prépare le morceau dans REAPER. »
- « Le refrain commence mesure 29, pas 25. » → `set_sections`
- « Renomme la section 6 en Solo guitare. » → `rename_section`
- « 1 mesure de count-in, click seulement sur les sorties 3/4. » → `update_options`
- « C'est à 94 BPM, pas 188. » → `prepare_song` avec `bpm_hint`
- « J'ai déplacé les régions dans REAPER, reprends-les. » → `prepare_song` (régions reprises, sans réanalyse)

| Outil | Rôle |
|---|---|
| `reaper_status` | REAPER et le pont répondent ? |
| `prepare_song` | Préparation complète (peut importer un fichier) |
| `analyze_audio` | Analyse seule, sans toucher au projet |
| `set_sections` / `rename_section` | Corriger la structure ; tout est reconstruit (noms en français ou en anglais). `set_sections` **l'emporte** sur les régions modifiées à la main ; `rename_section` les reprend d'abord (numéros = régions actuelles) |
| `set_grid` | Imposer une grille à tempo fixe quand la détection se trompe |
| `update_options` | Count-in, mode de tempo, click, annonces, voix… sans réanalyser |
| `get_project_state`, `goto_section`, `transport` | État du projet, navigation, lecture/arrêt |

Les deux modes partagent la même mémoire du dernier morceau préparé : on peut préparer avec le bouton et
affiner avec Claude, ou l'inverse.

Les régions modifiées à la main dans REAPER sont reprises par `prepare_song` (morceau déjà préparé ;
`reanalyse=true`, `bpm_hint` ou `beats_per_bar` forcent une analyse complète), `update_options` et
`rename_section`. Sur un morceau déjà préparé dont les régions n'ont pas été modifiées, `prepare_song` refait
une analyse (le bouton *Préparer*, lui, garde la structure). `set_sections` et `set_grid` imposent la structure donnée et remplacent ces régions. Les
outils de Claude sont chargés au début d'une conversation : après une mise à jour de ReaCue, ouvre une
nouvelle conversation.

## Limites connues

- **La détection de structure n'est pas parfaite** : elle dépend des morceaux. Les limites de sections sont
  en général justes à une mesure près ; les noms (couplet ou refrain, pré-refrain collé au refrain…) sont à
  vérifier. Les longueurs qui ne font pas 4, 8 ou 16 mesures méritent un coup d'œil.
- **Un MP3 seul est moins précis que des stems** : pas d'entrées/silences par instrument, pas de transcription
  de batterie, noms de sections et accords moins fiables. Utilise d'abord *Séparer les stems*.
- **Séparation de stems** : les stems guitare et piano gardent un peu de repisse ; la séparation prend
  plusieurs minutes par morceau sur le processeur (une seule fois par morceau : le résultat est gardé).
- **Batterie** : grosse caisse, caisse claire et charley sont fiables ; toms et ride sont approximatifs. Les
  fills sont les mesures qui s'écartent du groove de la section.
- **Accords** : accords parfaits, septièmes, sus et power chords ; les voicings jazz complexes sont simplifiés.
- Régions modifiées à la main : seuls leurs débuts et leurs noms sont lus (pas leurs fins) ; une réanalyse
  complète d'un morceau déjà préparé n'est possible qu'avec Claude (`reanalyse`) ou en ligne de commande
  (`reacue_cli.py prepare --reanalyse`).
- Mesures en x/4 uniquement (4/4 et 3/4 détectés).
- **Windows : bêta, pas encore testé sur une vraie machine.** À vérifier en particulier : le lancement en
  arrière-plan depuis REAPER, les voix SAPI et les chemins avec accents. Merci de signaler les problèmes.
- Linux : pas d'installateur (le code tourne ; les annonces demandent `espeak-ng`).
- **Mode concert** : l'arrêt automatique et la télécommande demandent la fenêtre *ReaCue - Concert* ouverte ;
  Précédent / Suivant / Début arrêtent la lecture et placent le curseur (relance avec Lecture) ;
  *Reconstruire* écrase les modifications faites directement dans le projet concert. Le PIN de la Régie
  n'est pas une barrière de sécurité.
- **Boucle de répétition** : pilotée par la fenêtre Concert (pas par la boucle de REAPER), donc une reprise
  saute avec la latence habituelle d'un déplacement dans REAPER (quelques millisecondes) ; les pistes des
  instruments sont coupées pendant la mesure de décompte par la fenêtre (si REAPER est quitté pendant cette
  mesure, enlève le mute à la main). Les vitesses sous 100 % utilisent la vitesse de lecture de REAPER avec
  préservation de la hauteur (qualité selon le mode d'étirement du projet).
- **Vérifier** : « concert à jour » compare chaque projet de morceau à l'empreinte prise à la construction du
  concert — enregistrer un projet de morceau sans changement musical peut quand même le marquer comme
  modifié ; les médias hors ligne sont repérés par le fichier et sa fréquence d'échantillonnage (REAPER ne
  donne pas directement l'état OFFLINE).

## Dépannage / FAQ

**« Le pont ReaCue ne tourne pas dans REAPER. »** Le pont démarre avec REAPER via `Scripts/__startup.lua`.
Redémarre REAPER. Si ça ne suffit pas, lance l'action `ReaCue_Bridge.lua` à la main (*Actions → Load
ReaScript*) et vérifie que `__startup.lua` contient la ligne ReaCue (relancer l'installateur la rétablit).
Une fenêtre modale ouverte dans REAPER bloque aussi le pont.

**« Programme ReaCue introuvable. »** Le dossier a été déplacé ou supprimé : relance l'installateur depuis
son nouvel emplacement.

**Le prompteur affiche « REAPER ne répond pas ».** Vérifie que le téléphone est sur le même Wi-Fi que
l'ordinateur, que l'interface web est activée (voir plus haut) et que l'adresse et le port sont les bons. Un
pare-feu peut bloquer le port 8080 : autorise REAPER (Windows : *Autoriser une application via le pare-feu
Windows Defender*).

**L'adresse IP a changé et les téléphones ont perdu la page.** Réserve l'adresse IP de l'ordinateur dans la
box (réservation DHCP), voir plus haut.

**L'écran du téléphone se met en veille.** Touche ⛶ (plein écran) : la page demande alors au téléphone de
rester allumé (Screen Wake Lock, versions récentes de Chrome/Safari). Sinon, désactive le verrouillage
automatique pendant le concert (iOS : *Réglages → Luminosité et affichage → Verrouillage automatique* ;
Android : *Affichage → Mise en veille de l'écran*).

**Pas d'annonces vocales.** macOS : vérifie que les voix sont présentes dans *Réglages Système →
Accessibilité → Contenu énoncé*. Windows : installe une voix pour ta langue (*Paramètres → Heure et langue →
Voix*). L'avertissement de la fenêtre finale indique quelle voix manquait.

**Tempo faux (double ou moitié).** Indique le tempo dans le nom des stems (ex. `-94bpm`), ou passe par
Claude (`bpm_hint`).

**L'item audio affiche « OFFLINE » dans REAPER (macOS).** REAPER n'arrive pas à lire le fichier. Ça arrive
notamment avec les fichiers laissés dans *Téléchargements* : macOS peut refuser à REAPER l'accès à ce dossier.
Déplace ou copie le fichier dans le dossier du projet (par exemple `Documents/REAPER Media/<morceau>/`), puis
dans REAPER clic droit sur l'item → *Item properties…* → *Choose new file*, ou glisse simplement le fichier à
nouveau. Autre solution : autorise REAPER dans *Réglages Système → Confidentialité et sécurité → Fichiers et
dossiers* puis redémarre REAPER. *Séparer les stems* a aussi besoin de pouvoir lire le fichier.

**« La séparation de stems n'est pas installée. »** Double-clic sur `Install ReaCue Stems.command` / `.bat`
dans le dossier de ReaCue (internet nécessaire une fois).

**La séparation est lente / l'avancement reste à 0 %.** Le premier pour cent peut prendre une minute
(chargement du modèle). Compte 1,5 à 2 fois la durée du morceau sur un Mac Intel. Ferme les autres
applications gourmandes. Le journal est `<nom du morceau>-stems/demucs.log`, à côté du fichier d'origine.

**Concert : « Aucun concert dans ce projet ».** L'onglet en cours n'est pas un concert. Détache la fenêtre
Concert (clic droit) pour voir la liste des concerts, ou ouvre `<dossier des concerts>/<nom>.RPP` avec
*File → Open project*. Un morceau n'a pas de sections dans le concert : son projet a été enregistré avant
la préparation — prépare-le, enregistre-le (Cmd/Ctrl+S), puis *Reconstruire le concert*.

**Régie : « Ouvre la fenêtre ReaCue - Concert… ».** Le téléphone passe par cette fenêtre : lance l'action
*ReaCue - Concert* sur l'ordinateur. « Code PIN incorrect » : tape le code affiché par le bouton PIN de la
fenêtre. Le QR n'affiche pas d'adresse : l'ordinateur n'est pas connecté à un réseau.

**Où sont les journaux ?** `<ressources REAPER>/ReaCueMCP/cli.log` (préparation, concert) et
`<nom du morceau>-stems/demucs.log` (séparation de stems).

## Désinstallation

Double-clic sur **`Uninstall ReaCue.command`** (macOS) ou **`Uninstall ReaCue.bat`** (Windows), REAPER fermé.
Cela retire les scripts REAPER, la ligne de démarrage du pont, les actions et l'entrée Claude Desktop. Tes
réglages et le dernier morceau préparé restent dans `<ressources REAPER>/ReaCueMCP/` (ajoute `--purge` au
script de désinstallation pour les supprimer ; `--purge` supprime aussi l'environnement de séparation de
stems `.venv-demucs`). Supprime ensuite le dossier de ReaCue. Les modèles Demucs restent dans le cache de
PyTorch (`~/.cache/torch/hub/checkpoints`, quelques centaines de Mo) : supprime ce dossier si tu n'en as plus
besoin. Les stems séparés restent à côté de tes morceaux.

## Pour les développeurs

```bash
uv pip install -r requirements-dev.txt     # pytest, lupa, playwright
python -m pytest tests                     # tests légers : ni audio, ni REAPER
python tools/make_screenshots.py           # régénère docs/images (Playwright + Chromium)
```

Organisation :

| Chemin | Contenu |
|---|---|
| `reacue_mcp/` | Paquet Python : analyse, planification, client du pont, prompteur, accords, paroles, batterie, voix, i18n, réglages, CLI, serveur MCP |
| `reacue_mcp/web/prompteur.html` | La page du prompteur (un seul fichier) |
| `reaper/` | Scripts REAPER : le pont et les actions (`ReaCue_stems.lua` : séparation de stems ; `ReaCue_Concert.lua`, `ReaCue_concert_lib.lua` : fenêtre Concert et Régie ; `ReaCue_qrcode.lua` : encodeur QR, luaqrcode, BSD) |
| `reacue_stems.py`, `requirements-stems.txt` | Lanceur de la séparation de stems (tourne dans `.venv-demucs`) et ses dépendances figées |
| `install/` | Installateurs (macOS, Windows) et `reacue_setup.py` commun |
| `tests/` | Tests pytest (faux pont REAPER, Lua exécuté via `lupa`, installateur, page du prompteur) |
| `tools/` | **Outils de développement uniquement** (non utilisés par ReaCue) : `concert_demo.py` (projets de démonstration fictifs pour les tests du mode concert), `struct_eval.py` (banc d'essai de la détection de structure sur tes propres morceaux, configuré par un fichier JSON privé), `asr_anchor.py` (fichier d'ancres de paroles par reconnaissance vocale, modèles lourds, Linux), `make_screenshots.py` |

Migration depuis une ancienne installation (dossier `~/Documents/reacue-mcp`) : voir
[docs/MIGRATION_fr.md](docs/MIGRATION_fr.md).

## Crédits et licence

ReaCue par Hervé Naessens. Licence MIT, voir [LICENSE](LICENSE).

Séparation de stems par [Demucs](https://github.com/facebookresearch/demucs) (Alexandre Défossez, Meta AI,
licence MIT) sur [PyTorch](https://pytorch.org/).

QR codes par [luaqrcode](https://github.com/speedata/luaqrcode) (Patrick Gundlach et contributeurs,
licence BSD 3 clauses ; l'en-tête de licence est conservé dans `reaper/ReaCue_qrcode.lua`).

S'appuie sur [librosa](https://librosa.org/), [NumPy](https://numpy.org/), [SciPy](https://scipy.org/),
[soundfile](https://github.com/bastibe/python-soundfile), le SDK Python du
[Model Context Protocol](https://modelcontextprotocol.io/), [uv](https://docs.astral.sh/uv/) et, bien sûr,
[REAPER](https://www.reaper.fm/) de Cockos. ReaCue n'est affilié ni à Cockos ni à Anthropic.
