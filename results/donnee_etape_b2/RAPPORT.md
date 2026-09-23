# Étape B-2 : accès aux études de santé (PASS, LAS)

23/09/2026, Claudette. Ordre 2026-09-23-1252. Contrat : `results/donnee_etape_b/CONTRACT.md`,
sections 10 et 10 bis (v1.3.1). Corpus d'entrée : `formations_etape_b1.json` (sha256
`9863d2b40d3f...`, jamais réécrit). Corpus de sortie : `formations_etape_b2.json` (sha256 donné
dans le manifeste et dans le message de livraison).

## Ce qui est livré

Les 800 fiches PASS (287) et LAS (513) portent `sante`, avec quatre sous-champs et leur portée :

| Sous-champ | Disponible | Non disponible | Source |
|---|---|---|---|
| `passage_national` (portée nationale) | 800 | 0 | SIES, Note Flash n°31, novembre 2025 |
| `passage_universite` | 0 | 800 | aucune des 10 universités ne publie de taux constaté |
| `capacites_universite` | 216 (116 PASS, 100 LAS) | 584 | documents des universités du panel |
| `reforme_2027` (renvoi à la fiche concept) | 800 | 0 | fiche `reforme_sante_2027` |

Mesure : manifeste `formations_etape_b2.manifest.json`, `remplissage`.

Par domaine de la démo (`python -m src.eval.donnee.mesure_sante <b1> <b2>`, trace
`mesure_domaines.txt`). Une fiche peut compter dans plusieurs domaines. Avant B-2, aucune fiche PASS
ou LAS ne portait ces champs.

| Domaine | Fiches PASS/LAS | Passage national | Chiffre de l'université | Capacités |
|---|---|---|---|---|
| santé | 800 | 800 | 0 | 216 |
| maths | 58 | 58 | 0 | 11 |
| informatique | 37 | 37 | 0 | 6 |

## Passage national (SIES)

PDF relu le 23/09/2026 (sha256 `bd4e38d26f30...`), 0 écart avec `sources-donnees.md` §1.1.
- Admis en MMOPK en 1 ou 2 ans : PASS 47,5 %, LAS 25,7 %, ensemble 40,1 % (néo-bacheliers
  inscrits en 2022, session 2024).
- Admis en 1 an : 33,8 / 19,5 ; en 2 ans : 13,8 / 6,3.
- Par filière (PASS / LAS) : médecine 29,4 / 14,1, pharmacie 7,9 / 3,9, kinésithérapie 4,2 / 4,4,
  odontologie 3,6 / 2,2, maïeutique 2,4 / 1,2.
- Effectifs : 34 200 néo-bacheliers, dont 22 500 en PASS et 11 700 en LAS.

Le PDF ne donne pas de taux « en 1 an » par filière : rien n'est écrit à ce niveau. Coquille du PDF :
le pied de la page 1 porte « novembre 2024 ».

## Panel de 10 universités

Panel mesuré et validé par Jarvis (vœux PASS + LAS du corpus B-1, 59,4 % des vœux, 231 fiches).
Sources primaires uniquement, recherchées par quatre sous-agents, puis **chaque document téléchargé,
verrouillé (sha256) et relu par Claudette**. Deux attributions de colonnes données par les
sous-agents étaient fausses (Montpellier : colonnes « DE auxiliaire » et « EUE » décalées) ou
incomplètes (Lyon 1 : couche texte corrompue) ; les valeurs retenues sont celles relues sur l'image.

| Université | Fiches | Rentrée publiée | Document | Kiné | Lecture |
|---|---|---|---|---|---|
| Paris Cité | 32 | 2026-2027 | diaporama de la journée portes ouvertes de la Faculté de Santé (07/02/2026) | oui (5 IFMK) | texte |
| Sorbonne Paris Nord | 18 | 2026-2027 | PDF UFR SMBH | non publié | texte |
| Lille | 24 | 2026 | PDF UFR3S (signé le 01/10/2024) | oui | texte |
| Lyon 1 | 20 | 2026-2027 | délibérations CA 23/09/2025 (MMOP) et 25/11/2025 (kiné) | oui | image (MMOP), texte (kiné) |
| Montpellier | 27 | 2026-2027 | PDF « répartition des capacités d'accueil par filière MMOP » | non publié | texte + image pour les colonnes |
| Aix-Marseille | 33 | **2024** | délibération CA 19/09/2023, dernière trouvée | non publié | texte |
| Paris-Saclay | 15 | non disponible | aucune capacité chiffrée sur les pages de l'université | | |
| Toulouse III | 24 | **2025/2026** (libellé ambigu) | numerus apertus du 21/07/2025 | oui | texte + image |
| Bordeaux | 16 | 2026/27 (kiné 2025/2026) | PDF du 25/11/2025 + PDF kiné | oui (2025/2026) | texte |
| Nantes | 22 | 2026-2027 | délibération CAc 19/09/2025 | oui | image (scan) |

Taux de passage publiés par l'université : **aucun**. Deux chiffres trouvés et écartés, avec la
raison dans le code : Montpellier « minimum pass rate 5.8% » (minimum théorique 2021-22), Paris Cité
« environ 50 % des admis provenaient du PASS » (répartition, pas un taux de passage). Les taux par
faculté qui circulent viennent de sites de prépa ou d'une question parlementaire sans source.

Rattachements (Q1 à Q3 validées par Jarvis) :
- LAS d'une université sans PASS dans le corpus : national seulement, « faculté partenaire non
  identifiée dans les données ouvertes ».
- Places LAS : « ouvertes aux étudiants de LAS de l'université, toutes mentions confondues ».
- EUPC Guyancourt : rattachée à l'UVSQ.

## Réforme 2027

Fiche concept `reforme_sante_2027`, statut `annonce`, vérifiée le 23/09/2026 :
- annonce gouvernementale du 17/04/2026 (L'Etudiant ; Service-Public, actualité A18890 du
  29/04/2026) ;
- proposition de loi « formations en santé » adoptée en 1re lecture au Sénat le 20/10/2025, déposée
  à l'Assemblée nationale le 21/10/2025 (n° 1981), aucune étape ensuite sur le dossier ;
- Journal officiel : aucun décret ni arrêté. Recherches Légifrance « portail santé » (0 texte) et
  « études de santé » (248 textes, aucun pertinent). Témoin positif « accès aux formations de
  médecine » : 75 textes, le plus récent daté du 27/07/2026. Cet arrêté (report des places non
  pourvues au titre de 2025-2026) règle le système actuel : hors sujet pour la réforme, et c'est
  écrit dans `recherches`.
- Piste CNESER du 07/07/2026 (AEF, presse payante) : dans `recherches` seulement, marquée non
  vérifiée ; absente du texte lu par le modèle.

## Texte lu par le modèle

Ordre : national, puis université, puis places, puis réforme. Chaque proposition qui porte un taux
dit sa portée. Exemple, une PASS de Toulouse :

```
Accès aux études de santé, chiffre national : au niveau national (SIES, Note Flash n°31 de novembre 2025, session 2024, néo-bacheliers inscrits en 2022), 47,5 % des néo-bacheliers inscrits en PASS sont admis en MMOPK (...) en 1 ou 2 ans, dont 33,8 % dès la première année ; au niveau national, par filière : médecine 29,4 %, ... ; ce chiffre national ne décrit pas cette université en particulier
Taux de passage en MMOPK propre à l'université : non disponible (l'université ne publie pas de taux de passage sur les pages consultées)
Places en MMOPK, Université Toulouse III, rentrée 2025/2026 (publiées par l'université) : médecine 410 (dont PASS 196, LAS 193, passerelles 21) ; ... ; précision : ...
Réforme : une voie unique remplaçant PASS et LAS a été annoncée par le gouvernement le 17/04/2026 pour la rentrée 2027 ; aucun décret ni arrêté publié au Journal officiel à la date du 23/09/2026 (voir la fiche « Réforme de l'accès aux études de santé »)
```

Longueur du texte des fiches PASS/LAS : médiane 3 787 caractères avant, 4 970 après (max 5 838).
Même réserve qu'aux étapes A et B-1 : pas de ré-embedding, l'étape D fixera le texte d'embedding.

## Contrôles

`python -m src.eval.donnee.controles --corpus <corpus>` : 0 défaut sur le corpus B-2
(`controles_apres.json`), 0 sur B-1 (`controles_avant.json`). Contrôles ajoutés, chacun rougit
sur une fiche ou un texte cassés par levier (`tests/test_etape_b2.py::test_controle_sante_rougit`,
8 leviers) :
- `sante_taux_sans_portee` : un taux dans un segment MMOPK sans « au niveau national » ni « publié
  par l'université » dans la même proposition ;
- `sante_31_pourcent_attribue_a_l_universite` ;
- `sante_absent`, `sante_<sous-champ>_absent`, `sante_<sous-champ>_sans_portee`,
  `sante_<sous-champ>_non_disponible_sans_raison`, `sante_*_sans_url_ou_empreinte`,
  `sante_national_non_ecrit`.

## Audit

`python -m src.eval.donnee.audit_sante --sortie results/donnee_etape_b2/audit_sante.json` :
- **sources** : 8 lignes du tableau SIES retrouvées dans le PDF, colonnes PASS / L.AS 2022
  vérifiées ; 171 valeurs de capacités, chaque extrait retrouvé dans son document verrouillé ; chaque
  nombre dans les extraits de son document, ou somme refaite ;
- **corpus** : 800 fiches, 216 avec capacités, valeurs identiques à la table, taux national écrit ;
- verdict : **VERT, sauf NON MESURÉ** pour deux documents sans couche texte exploitable, Nantes (scan)
  et Lyon 1 MMOP. Leurs extraits ont été relus à l'image par moi, pas par un instrument ; leurs
  sommes restent vérifiées.

Contrôle positif : 5 leviers (`--saboter sies|capacite|somme|extrait|corpus`), 5 rouges, chacun
sur le défaut introduit (traces `audit_sante.sabote-*.json`).

Limite de l'instrument : un nombre de capacité est « présent » s'il apparaît parmi les nombres
des extraits de son document. Une valeur remplacée par un autre nombre du même tableau passerait.
Le contrôle vérifie donc l'origine du nombre, pas sa case : c'est la relecture à l'image qui a
vérifié les colonnes. Jarvis, ton échantillon sur les pages est le témoin indépendant.

## Banc vertical

`python -m src.eval.donnee.banc_textes` : 336 / 341 chiffres attendus présents, avant (texte de
`origin/main` sur B-1) comme après (B-2). Témoin de hasard 6,2 % puis 7,9 %. La hausse est attendue :
le même taux national figure maintenant sur toutes les fiches PASS/LAS. Aucune valeur attendue du
banc ne change.

Conversations santé dont un trou « hors base » se comble en partie (à signaler pour
`battery_verticale.json`, que je ne modifie pas) :
- V-SAN-01 (Rennes), V-SAN-09 (Poitiers), V-SAN-10 (Grenoble), V-SAN-16 (ST2S), V-SAN-18 : le
  taux **national** PASS/LAS est désormais dans la base. Le taux par université reste absent (Rennes,
  Poitiers et Grenoble sont hors panel), comme le taux par type de bac.
- V-SAN-02 (Lille) : les places MMOPK de Lille sont dans la base (médecine 560 dont PASS 276...).
- V-SAN-05 (Toulouse, kiné) : les places de kiné par voie sont dans la base (28, dont PASS 23, LAS
  5, rentrée 2025/2026). La voie STAPS et le taux vers l'IFMK restent absents.
- V-SAN-12 (Clermont, maïeutique) : inchangé, Clermont est hors panel.

## Commandes

```
python -m src.collect.sources_officielles           # 22 empreintes, dont 12 documents santé
python -m src.collect.corpus_etape_b2               # B-1 -> B-2 (ou pipeline_donnee pour tout rejouer)
python -m src.eval.donnee.audit_sante --sortie results/donnee_etape_b2/audit_sante.json
python -m src.eval.donnee.controles --corpus data/processed/formations_etape_b2.json
python -m src.eval.donnee.mesure_sante data/processed/formations_etape_b1.json data/processed/formations_etape_b2.json
pytest tests/test_etape_b2.py                       # 49 tests
```

`pdftotext` (poppler-utils) est requis par l'audit ; les tests n'en ont pas besoin (fixture).

## Ce qui reste ouvert

- Aix-Marseille : rentrée 2024 seulement. Un document plus récent existe peut-être au recueil des
  actes administratifs, non consultable à distance.
- Toulouse : « 2025/2026 » ne dit pas si c'est l'année d'inscription en PASS/LAS ou celle d'entrée
  en 2e année. La page passerelles du même site met les mêmes places sous « 2026/2027 ».
- Paris-Saclay : non disponible. La page des délibérations des instances refuse la lecture
  automatique (HTTP 403) ; un navigateur y trouverait peut-être la délibération.
- Paris Cité : la source est un diaporama officiel, pas une délibération ; les 23 places de maïeutique
  « réservées pour UVSQ » ne sont pas reprises (rien ne dit si elles sont dans les 46).
- Second témoin L6211-1 : ajouté (`temoins` de la source lue), reporté sur les 526 coûts
  d'apprentissage du corpus B-2.
