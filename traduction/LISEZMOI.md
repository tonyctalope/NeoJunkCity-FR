# Le texte de la traduction

**Attention : ces fichiers contiennent tout le texte du jeu en français, donc des spoilers du début à la fin.**

## Ce qu'il y a ici

| Fichier | Contenu |
| --- | --- |
| `dialogues/partie_00.jsonl` | Interface, objets, objectifs, noms, libellés |
| `dialogues/partie_01.jsonl` à `partie_22.jsonl` | Dialogues, dans l'ordre approximatif du jeu |
| `hors_dialogues.jsonl` | Textes que le jeu range ailleurs que dans sa table de dialogues |
| `ennemis.json` | Fiches d'ennemis |
| `emails.txt` | E-mails reçus en jeu |

Une ligne de dialogue ressemble à ceci :

```
{"id": 1234, "h": "9f3a1c2b", "fr": "Le texte affiché en jeu."}
```

- `fr` est le texte français : c'est la seule chose à modifier.
- `id` est le numéro de la ligne dans le jeu et `h` l'empreinte de la phrase d'origine. Ne les changez pas : ils servent à retrouver la ligne et à repérer une phrase que le jeu aurait modifiée dans une mise à jour.

Le texte d'origine du jeu n'est pas dans ce dépôt, et les lignes volontairement laissées en anglais (noms propres, titres, paroles de chansons citées) n'y figurent pas non plus.

## Corriger une ligne

1. Repérez la phrase fautive en jeu et cherchez-la dans ce dépôt (barre de recherche de GitHub, en haut de la page).
2. Ouvrez le fichier, cliquez sur le crayon, corrigez le texte de `fr`.
3. Validez avec « Propose changes » : GitHub crée une proposition de modification (pull request).

Vous pouvez aussi simplement ouvrir un ticket dans l'onglet Issues avec la phrase et sa correction.

## Règles à respecter

- Gardez les balises `<...>` et les jetons `[...]` exactement comme ils sont : ce sont des effets de texte et des variables du jeu.
- Gardez le même nombre de retours à la ligne (`\n`).
- Les polices du jeu n'ont pas tous les caractères : pas de `œ` (écrire `oe`), pas de `…` (trois points), pas de guillemets `« »` ni d'apostrophe courbe. L'outil les remplace tout seul si vous en mettez.
- Un guillemet droit à l'intérieur du texte s'écrit `\"`.
- Le français est plus long que l'anglais et la place est comptée : restez concis.
- Personnages : gardez les noms et le tutoiement ou vouvoiement déjà en place dans les lignes voisines.

Chaque proposition est contrôlée automatiquement (`dev/verifier_traduction.py`) : forme des fichiers et caractères interdits.

## Essayer sa correction en jeu

Voir « Reconstruire le patch soi-même » dans le [README](../README.md).
