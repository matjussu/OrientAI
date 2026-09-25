# Cerveau v2 : contrat et gate F

Copie versionnée du plan du cerveau v2 d'OrientAI, pour qu'il vive à côté du code (étape 0 de la
feuille de route, section 13 du contrat).

- `CONTRAT-cerveau.md` : contrat v1.2 du 25/09/2026 (Jarvis), dont les 7 choix ont été validés par Matteo le
  24/09/2026 à 17h12 (Telegram 10703). La v1.2 remplace la v1.1 versée par #187 : référence de mesure
  ChatGPT avec recherche web, objectif recadré, chiffres de la base alignés sur la page publique (#189).
  Architecture en 4 étages, catalogue d'outils, cibles, feuille de route (section 13), méthode de
  travail et pièges d'outillage (section 14).
- `gate_f/requetes_gate_f.json` : les 30 questions-tests du gate F, écrites avant le code.
- `gate_f/build_gate_f.py` : le script déterministe (sans appel d'API) qui produit le JSON.

## Source et empreintes

Source de travail : `~/projets/_orientai-ref/cerveau-2026-09/` (hors dépôt). Copies octet pour octet,
sha256 mesurés sur la source et sur la branche (contrat v1.2 le 25/09/2026 au soir, gate F inchangé depuis #187) :

| Fichier | sha256 |
|---|---|
| `CONTRAT-cerveau.md` | `07dee32b0949a490876389ef9e71406a320e7134aee9163bb300880f15fc1b41` |
| `gate_f/requetes_gate_f.json` | `5c78dc6e90017b3802e253f273468ad9f7566888ea78ccdcf4b1d3d9368fe0b3` |
| `gate_f/build_gate_f.py` | `8357e2f67cabd0b9379e5c2fe541b706c38f2db2ab019812939a4fdb61444988` |

## Rejouer le gate F

`build_gate_f.py` lit ses entrées dans `../../verticale-2026-09/` relativement à son propre dossier
(`gate_c/requetes_gate_c.json`, `battery_verticale.json`, `explorateur/base_c.json`), c'est-à-dire
dans `_orientai-ref`. **Il ne tourne pas depuis le dépôt** : ici, ce chemin pointe vers
`docs/verticale-2026-09/`, qui n'existe pas. Il écrit aussi `requetes_gate_f.json` à côté de lui.

Rejeu mesuré le 25/09/2026 depuis une copie hors dépôt (script copié dans `<tmp>/cerveau/gate_f/`,
`<tmp>/verticale-2026-09` en lien vers `_orientai-ref/verticale-2026-09`) : même sha256
`5c78dc6e9001...`, 30 questions (recherche 12, nom 8, clarification 5, multi-tour 2, honnêteté 3),
102 fiches attendues toutes présentes dans la base C.

## Règle de mise à jour

Ces fichiers ne s'éditent pas en place. Toute nouvelle version du contrat ou du gate F repasse par
une PR, avec un en-tête daté en tête du contrat (date, version, ce qui change, qui a validé) et les
sha256 de ce README mis à jour. Une correction repérée sans nouvelle version se note dans la PR ou
dans `REPRISE.md`, pas dans le fichier.
