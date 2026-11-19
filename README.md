# Neo Junk City — patch français (non officiel)

Traduction française complète de **Neo Junk City** (Steam), faite par un fan. Le jeu n'a pas de version française officielle.

- Environ 13 450 lignes traduites : dialogues, choix, objets, objectifs, menus, e-mails, fiches d'ennemis.
- Pour la version Steam du jeu du **19 novembre 2026** (build 26769435). Le patch est lié à une version précise du jeu : voir [Après une mise à jour du jeu](#après-une-mise-à-jour-du-jeu).
- Le patch ne contient **aucun fichier du jeu** : seulement les différences à appliquer aux fichiers que vous avez déjà, et un script qui les applique. Il faut posséder le jeu.
- Tout est ouvert : le texte de la traduction et les outils qui fabriquent le patch sont dans ce dépôt, pour que chacun puisse corriger une ligne ou reconstruire le patch.

## À savoir avant d'installer

- **Traduction faite et relue par une IA** (Claude), avec un glossaire et des règles de style pour garder les noms et le ton cohérents d'un bout à l'autre. Elle n'a pas été relue ligne par ligne par un humain, et elle n'a été vue en jeu que sur une partie de l'aventure. Il reste forcément des maladresses : signalez-les (voir plus bas).
- Le français **remplace l'anglais**. Dans le jeu, laissez la langue sur **English**.
- Une **partie déjà commencée en anglais** garde certains choix de dialogue et certains noms en anglais dans les lieux déjà visités (le jeu les enregistre dans la sauvegarde). Une nouvelle partie n'a pas ce défaut.
- Restent en anglais : les crédits, le texte dessiné dans des images, les noms de quelques boss, et quelques rares textes écrits en dur dans le programme.
- Le français est plus long que l'anglais : un texte peut parfois dépasser de son cadre.

## Installation sous Windows

1. Téléchargez le zip sur la page [Releases](../../releases/latest).
2. Extrayez **tout** le zip dans un dossier (clic droit > Extraire tout).
3. Fermez le jeu, puis double-cliquez sur **Installer.bat**.
   Si Windows affiche un avertissement, c'est parce que le fichier vient d'Internet : « Informations complémentaires » > « Exécuter quand même ». Le script est lisible (`vf.ps1`) et n'installe rien sur votre PC.
4. Lancez le jeu et laissez la langue sur **English**.

Le script trouve le jeu tout seul via Steam. S'il n'y arrive pas, il vous demande le dossier : dans Steam, clic droit sur le jeu > Gérer > Parcourir les fichiers locaux.

Il vérifie d'abord que vos fichiers sont bien ceux de la version attendue, garde une copie des originaux (dossier `VF_sauvegarde` dans le dossier du jeu, environ 540 Mo), puis applique le patch. Si quelque chose ne correspond pas, il s'arrête sans rien modifier.

## Installation sous Linux / Steam Deck

Il faut Python 3 (présent d'origine sur la plupart des systèmes, Steam Deck compris).

```
./installer-linux.sh
```

Si le jeu n'est pas trouvé, indiquez son dossier : `./installer-linux.sh "/chemin/vers/Neo Junk City"`

## Désinstallation

Double-cliquez sur **Desinstaller.bat** (ou `./desinstaller-linux.sh`) : les fichiers d'origine sont remis en place.

Autre moyen, sans le patch : dans Steam, clic droit sur le jeu > Propriétés > Fichiers installés > Vérifier l'intégrité des fichiers du jeu.

## Après une mise à jour du jeu

Quand Steam met le jeu à jour, il remet ses propres fichiers : le jeu repasse en anglais et l'installateur de l'ancienne version refuse de s'appliquer (il le dit, sans rien casser). Il faut alors attendre la version du patch correspondante sur la page [Releases](../../releases) et la réinstaller.

## Signaler ou corriger une erreur

- **Signaler** : ouvrez un ticket dans l'onglet [Issues](../../issues) avec, si possible, une capture d'écran et l'endroit du jeu. Merci d'éviter les spoilers dans le titre du ticket.
- **Corriger vous-même** : tout le texte français est dans le dossier [`traduction/`](traduction/) (attention, spoilers). La marche à suivre est dans [`traduction/LISEZMOI.md`](traduction/LISEZMOI.md) : on cherche la phrase, on la corrige, on propose la modification.

## Reconstruire le patch soi-même

Tout ce qu'il faut pour refaire le patch à partir du texte est dans ce dépôt. Il faut posséder le jeu, et Python 3.10 ou plus récent.

```
pip install -r build/requirements.txt
python build/construire.py
```

Le script trouve le jeu via Steam (sinon : `--jeu "chemin du jeu"`), lit vos fichiers sans les modifier et fabrique le dossier `patch/`. Lancez ensuite `Installer.bat` ou `./installer-linux.sh` comme d'habitude. Cela marche aussi si le patch est déjà installé : le script repart des fichiers d'origine gardés par l'installateur.

Après une mise à jour du jeu, le même script reconstruit le patch pour la nouvelle version : les lignes nouvelles ou modifiées par le jeu restent en anglais et sont comptées dans le résumé.

La construction a été vérifiée sous Linux, où elle redonne exactement le patch publié. Elle n'a pas encore été essayée sous Windows.

## Comment ça marche

- `traduction/` : le texte français, ligne par ligne, sans le texte d'origine du jeu.
- `build/` : lit les fichiers du jeu, y place le texte français (dans l'emplacement de l'anglais), remplace les quelques images propres à l'allemand par celles de l'anglais et choisit des polices qui ont les accents.
- `patch/` (dans le zip publié) : un fichier de différences par fichier du jeu modifié, et `manifest.json` avec les empreintes SHA-256 attendues avant et après.
- `vf.ps1` (Windows) et `vf.py` (Linux) : vérifient les empreintes, sauvegardent, appliquent, revérifient. Aucun programme tiers.
- `dev/` : l'outil qui fabrique les fichiers de différences, le contrôle des fichiers de texte et les essais automatiques des installateurs (lancés sur Windows et Linux à chaque modification, sur de faux fichiers).

## Mentions

Projet de fan, non officiel, sans lien avec le développeur ni l'éditeur du jeu. Neo Junk City et son contenu appartiennent à leurs ayants droit. Ce dépôt sera retiré sur simple demande de leur part.

Les scripts sont sous licence MIT (voir `LICENSE`). Le texte français est une traduction de fan du texte du jeu : il est partagé pour être corrigé et amélioré, et reste soumis aux droits des ayants droit du jeu.
