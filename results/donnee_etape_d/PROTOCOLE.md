# Etape D : protocole de la grille formats x modeles (v0.2, 23/09/2026)

v0.1 (23/09, avant tout appel payant) : amendements de Jarvis sur la v0 (5ab87d0) inscrits en section 8
(contexte neutre du juge, juge sur la generation 1) ; titre du rapport en section 10 ; garde-fou forme
(etape 3 bis de la section 10, demande de Matteo, Telegram 10634-10635) ; prix Medium et GLM gardes
« supposes », go de Matteo tel quel.

Ordre 2026-09-23-1515. Ecrit AVANT tout appel payant, avec les precisions de Matteo relayees par Jarvis
(Telegram 10630-10631). Toute modification apres le premier appel payant = nouvelle version annoncee
avant le run suivant. Aucun ajustement du banc, du critere ou de la regle apres avoir vu des resultats.

## 1. Ce qui est compare

9 combinaisons = 3 formats x 3 modeles, tous les autres parametres identiques.

| Format | Contenu expose au modele |
|---|---|
| A (reference) | `fiche_to_text` du corpus B-2 (`formations_etape_b2.json`, sha `2e6a93a5cda6`), ce que le modele lit aujourd'hui |
| B | carte structuree generee depuis la base C (sha `3e9dfaff7e8b`, empreinte `39f774bd5cbb`) : chaque chiffre avec libelle, unite, millesime, source et definition courte (table `champ`) |
| C | carte courte (5 a 7 chiffres cles, regle par type ecrite en section 4) + outil `lire_fiche(id)` qui rend la carte B |

| Modele | Identifiant epingle (API Mistral, `GET /v1/models` le 23/09) | Capacites annoncees par l'API |
|---|---|---|
| Medium 3.5 (prod) | `mistral-medium-2604` | function_calling, reasoning |
| Large 3 | `mistral-large-2512` | function_calling, pas de reasoning |
| GLM 5.2 | `zai-glm-5-2` | function_calling, reasoning |

Piege mesure le 23/09 : l'alias `zai-glm-5` et `zai-glm-latest` pointent vers GLM 5.3 (licence propre). Seul
`zai-glm-5-2` est appele ; le manifeste recopie le `model` que rend chaque reponse et le run s'arrete s'il differe.

## 2. Banc

`~/projets/_orientai-ref/verticale-2026-09/battery_verticale.json` : 57 conversations, 79 tours, 341 chiffres
attendus (sha recopie au manifeste). Joue tel quel, historique de 6 messages comme le serving.

Mesure du 23/09 sur ce banc :
- 323 chiffres attendus sur 341 portent sur une fiche presente dans la base C. Les 18 autres (ecoles
  d'ingenieurs cod 59 et 130, parcours licence MESRI, 2 valeurs MonMaster 2024, etc.) ne peuvent pas etre
  rendus en B ou C : ils sortent du critere principal pour les 9 combinaisons et sont rapportes a part ;
- unites des 341 : % 172, places 139, voeux 11, candidats 10, euros 6, propositions 3 ;
- 6 conversations vagues n'ont aucun chiffre attendu : elles comptent pour le juge, pas pour le critere 1.

## 3. Fiches exposees : identiques pour les 9, gelees une fois

Proposition (a valider, c'est le choix qui pese le plus) : **fiches attendues + distracteurs, gelees**.
- Pour chaque conversation : les fiches de ses chiffres attendus qui sont dans la base C (2,5 en moyenne,
  5 au plus), completees jusqu'a **8** par les premiers resultats BM25 (`Corpus.search`, gratuit,
  deterministe) sur le texte de ses tours, restreints au perimetre de la base C et hors fiches attendues ;
  ordre melange par une graine fixe. Les memes 8 fiches sont exposees a chaque tour de la conversation.
- Ecrit une fois dans `exposition.json` (sha au manifeste). Les 9 combinaisons le relisent, rien n'est
  recalcule.
- Pourquoi pas la recuperation de prod : recall@10 de 0,419 en brut (REPRISE section 0). Plus de la moitie
  des chiffres attendus ne seraient exposes a aucune combinaison, et le banc mesurerait le retrieval, pas
  format x modele. La recuperation sera l'affaire du lot « cerveau » (outils sur la base C).
- Ce que ce choix ne mesure PAS : la capacite a trouver la fiche. Le resultat est une borne haute du
  gain de format a recuperation correcte, et le rapport le dira.

## 4. Formats B et C : generation et controle

- B et C sont generes depuis la base C par une commande deterministe (`python -m src.eval.format_d`),
  teste en pytest.
- **Controle de contenu (rougit sur levier)** : pour chaque fiche exposee, l'ensemble des chiffres types
  (%, euros, places, voeux, candidats, propositions) lisibles dans A doit etre egal a celui de B. Un chiffre
  qui differe ou manque = rouge. Les ecarts structurels (un chiffre que A porte et que la base C n'a pas pris,
  par exemple les debouches, Q4) sont listes et comptes AVANT le premier run, dans `controle_formats.json`,
  jamais filtres. Sabotage : levier `ORIENTIA_SABOTAGE_D=carte_b_valeur` (une valeur modifiee) et
  `carte_b_manque` (un champ retire), chacun doit rougir.
- Carte courte C, regle ecrite avant le run : taux d'acces et places de la derniere session, cout,
  alternance (oui/non + nombre), insertion principale si elle existe ; pour PASS et LAS, passage MMOPK
  national ; pour un master, capacite et candidats. Au plus 7 chiffres, chacun avec son unite et son
  millesime.
- Outil C : `lire_fiche(id)` restreint aux 8 fiches exposees (un autre identifiant rend « fiche non
  disponible dans ce contexte »), pour que l'exposition reste identique. Au plus 4 appels par tour.

## 5. Prompt, parametres, repetitions

- Prompt systeme : `SYSTEM_PROMPT_CTX` de `src/eval/battery/config.py`, identique pour les 9 ; seul le bloc
  `<fiches>` change selon le format, plus, pour C, une phrase qui decrit l'outil.
- temperature 0,3 (comme le lot 0), parametres de raisonnement laisses par defaut (ceux de la prod pour
  Medium), sans plafond de sortie autre que celui du modele ; une reponse coupee (`length`) est rejouee
  une fois puis marquee en erreur.
- Repetitions : **2 generations** par combinaison si la projection de la 1re combinaison le permet sous
  35 USD (section 9), sinon 1, et le rapport le dit.

## 6. Format C : ce qui se passe si l'outil est mal utilise (mesure, pas supposition)

Avant la grille, une **sonde outil** : 5 tours du banc (ids fixes : V-INF-01, V-SAN-08, V-MAT-03, V-INF-21,
V-SAN-17), format C, sur les 3 modeles. Cout estime sous 0,50 USD. Elle mesure, par modele : appel de
l'outil oui/non, arguments valides, identifiant existant, nombre d'appels, reponse finale produite.
Regle fixee maintenant, quel que soit le resultat de la sonde :
- le modele n'appelle pas l'outil : sa reponse est gardee telle quelle, c'est le comportement reel du format ;
- arguments invalides ou identifiant inconnu : l'erreur est rendue au modele comme resultat d'outil ;
- plus de 4 appels : dernier appel sans outil, reponse forcee ;
- tous ces cas sont comptes et publies (taux d'appel, taux d'erreur d'outil) ; aucun tour n'est exclu.
Si la sonde montre qu'un modele ne sait pas du tout appeler l'outil via l'API (0 appel valide sur 5), je le
signale avant la grille au lieu de jouer 79 tours degeneres.

**Resultat de la sonde et decision (v0.2, 23/09)** : Medium 0/6 et Large 0/6 tours avec appel, GLM 4/6 (detail :
`sonde_outil/RESUME.md`). Option (a) retenue par Jarvis : C est joue tel quel ; C x Medium et C x Large sont
nommes « carte courte seule (l'outil n'a pas ete appele) », avec le taux d'appel par modele en tete de la
ligne C. Pas de consigne d'outil renforcee : ajuster le prompt de C seul casserait la comparaison.

## 7. Criteres

**Critere 1, sans juge : part des chiffres attendus cites justes.**
- Pour chaque chiffre attendu (323), il est « cite juste » si la reponse de son tour, ou d'un tour suivant de
  la meme conversation, contient un chiffre de meme unite egal a la tolerance de `numbers.py` (%, 0,51 ;
  places et comptes, 0,5 ; euros, 0,5).
- L'extracteur de `numbers.py` ne lit que %, euros et places ; il est etendu (module separe, `numbers.py`
  intouche) a voeux, candidats et propositions, avec un test par unite et un test de falsification.
- **v0.2 (23/09, avant tout calcul du critere 1)** : voeux, candidats et propositions forment **une seule
  unite « effectif »**. Raison mesuree : le texte A lui-meme ecrit « 1017 candidats » pour le champ voeux
  (psup:7596), une comparaison mot a mot rejetterait une citation juste. Le temoin de hasard dit ce que
  ce regroupement coute. Code : `src/eval/critere_d.py`.
- **Temoin de hasard** : les memes reponses confrontees aux chiffres attendus d'une AUTRE conversation
  (graine 7). Publie a cote de chaque taux ; on lit l'ecart au temoin.
- Aussi, deterministes : taux de chiffres « adosses » aux fiches exposees (`NumberChecker.check`, avec son
  temoin) et nombre de chiffres cites non retrouves dans les fiches exposees (candidats a l'invention).

**Criteres secondaires** : erreur_factuelle et refus du juge (section 8), longueur (mots), cout et tokens par
tour (lus dans l'usage de chaque reponse, prix en section 9), latence (secondes par tour), et pour C le
taux d'appel de l'outil.

## 8. Juge : sous-agents, a l'aveugle (demande de Matteo, 23/09)

- Pas de juge Opus via l'API. Mesure : lot 0, le juge a coute 4,194 USD pour 134 tours contre 0,12 USD de
  generation (`results/battery/2026-09-23_lot0/manifest.json`).
- Jugement par des sous-agents Claude Code (abonnement, 0 cout d'API), avec la **rubrique `RUBRIC` de
  `src/eval/battery/judge.py` mot pour mot**, le meme `build_prompt` et la meme sortie JSON, lue par le meme
  `parse_verdict` / `valid_scores`.
- **Aveugle** : les 9 x 79 reponses sont melangees (graine fixe, `seed.txt`), chacune recoit un identifiant
  opaque ; la correspondance vers combinaison vit dans `label_mapping.json`, jamais montree aux juges. Les
  titres des fiches exposees sont les memes pour les 9, ils ne revelent donc ni le format ni le modele.
  Limite : le style d'un modele peut se reconnaitre, on ne peut pas l'effacer.
- **Contexte du juge neutre (v0.1)** : pour les 9 combinaisons, le juge recoit le MEME rendu des 8 fiches
  exposees (la carte B complete), jamais le format lu par la combinaison ; pour C, les appels d'outil et leurs
  resultats sont retires du transcript juge, seule la reponse finale reste. Un test verifie que deux
  combinaisons d'une meme conversation donnent au juge un contexte identique octet pour octet (hors reponse).
- **Contexte retenu (v0.2, accord de Jarvis du 23/09)** : le juge recoit la liste des 8 fiches exposees en
  titres, etablissements et villes, exactement comme le `build_prompt` du lot 0, identique pour les 9
  combinaisons. **Limite** : le juge ne voit pas le contenu des fiches ; `erreur_factuelle` se juge donc sur
  sa propre connaissance, et l'exactitude des chiffres est couverte par le critere 1 (deterministe).
- **Juge retenu (v0.2, ecrit le 23/09/2026 17:25, avant la lecture de tout verdict retenu ; demande de Matteo)** :
  Opus 5.5 (`claude-opus-5-5`), **effort `low`**, agent `juge-aveugle` (`~/projets/.claude/agents/`,
  commit f4363a5 de ce depot), lance par `claude -p --model claude-opus-5-5 --effort low
  --setting-sources project --strict-mcp-config`, outils Read et Write seulement, sans CLAUDE.md.
  Abonnement Claude, pas l'API : le lanceur refuse de demarrer si `ANTHROPIC_API_KEY` est dans
  l'environnement (temoin `cle_api=0` dans chaque trace ; le lanceur ne source aucun `.env`, celui
  d'OrientIA contient une cle), et le levier a ete vu rougir. `modelUsage` de chaque sortie = claude-opus-5-5
  seul, verifie.
- **Verdicts ecartes** : les 8 premiers juges tournaient sur Opus 5.5 avec l'effort par defaut (high). Ils ont
  ete arretes avant la fin ; leurs 20 verdicts sont gardes dans `judge/abandon_effort_defaut/` et n'entrent
  dans aucun calcul. Seul controle fait sur les verdicts du lot 01 retenu : 25 fichiers lisibles sur 25
  (`valid_scores`), sans lecture des notes.
- **Limite** : effort faible = moins de verification par verdict ; le taux d'accord du rejugement dit ce que
  ce reglage coute.
- Lots d'environ 25 tours par juge ; un fichier de verdict par tour (`judge/verdicts/<id_opaque>.json`).
- **Charge (v0.1)** : le juge ne note que la generation 1 (9 x 79 = 711 reponses) ; le rejugement de 20 %
  porte sur celle-ci. Le critere 1 (sans juge) utilise les 2 generations. Juger la generation 2 demanderait
  une v0.2 annoncee avant.
- **Instabilite du juge mesuree** : un echantillon stratifie de 20 % des tours (graine fixe, au moins 15 par
  combinaison) est rejuge par d'autres sous-agents. Publies : accord brut et kappa de Cohen sur
  erreur_factuelle et sur refus, ecart absolu moyen par critere. Sans cette mesure, pas de conclusion sur la
  ligne erreurs factuelles.
- Comparabilite avec le lot 0 : meme rubrique, mais un autre juge (sous-agent au lieu d'Opus API) ; les
  notes absolues ne se comparent pas au lot 0, seulement entre les 9 combinaisons.

## 9. Budget et arret

- Generation seule (le juge ne coute rien en API). Prix : `mistral-large-2512` 0,5 / 1,5 USD par million de
  tokens (mistral.ai/pricing, lu le 23/09, exemple de la FAQ, version non precisee) ; `mistral-medium-2604`
  0,4 / 2,0 et `zai-glm-5-2` **non publies sur la page lue : supposes**, a confirmer par Matteo ou par la
  console Mistral. Le cout rapporte est tokens x prix, avec le prix marque « suppose » quand il l'est.
- **Correction du 24/09/2026** : prix publies (docs.mistral.ai, lus au banc E) : `mistral-medium-2604` 1,5 / 7,5,
  `zai-glm-5-2` 1,4 / 4,4, `mistral-large-2512` 0,5 / 1,5. Cout reel de D : 23,25 USD (voir `results/banc_e/RAPPORT.md`).
- Estimation non mesuree : 8 fiches x ~3 800 caracteres (mediane du texte A mesuree sur les 309 fiches
  Parcoursup attendues) donnent ~9 000 tokens d'entree par tour, soit ~0,7 M par combinaison. Les tokens
  de raisonnement de Medium et GLM ne sont pas connus.
- Ordre : sonde outil (section 6), puis **une** combinaison (A x mistral-medium-2604), cout reel envoye a
  Jarvis, projection sur 9 x repetitions. **Au-dessus de 35 USD projetes : arret et message**, rien d'autre
  n'est joue.
- Pendant la grille, arret si le cumul depasse la projection de plus de 50 %.

## 10. Regle de decision (ecrite avant, seuils chiffres)

Reference R = A x mistral-medium-2604. Pour chaque combinaison X :
1. **Gain** : dP = P(X) - P(R), critere 1. Dispersion par bootstrap apparie sur les conversations
   (10 000 tirages, graine 7), IC95. X **gagne** si la borne basse de l'IC95 de dP est > 0 et, s'il y a 2
   generations, si dP depasse l'ecart entre les 2 generations de R.
2. **Garde-fou erreurs** : dE = taux erreur_factuelle(X) - taux(R). X est **ecartee** si dE > 0 et que la
   borne basse de l'IC95 bootstrap de dE est > 0, **ou** si dE depasse le taux de desaccord du juge sur
   erreur_factuelle (section 8).
3. **Garde-fou refus** : meme regle sur le taux de refus.
3 bis. **Garde-fou forme** (demande de Matteo, 23/09) : X est **ecartee** si, sur au moins un des criteres
   `expression`, `comprehension` ou `couverture` du juge (generation 1), la moyenne baisse par rapport a R
   avec une borne HAUTE de l'IC95 bootstrap apparie < 0, **ou** d'un ecart plus grand que l'ecart absolu
   moyen du rejugement de 20 % sur ce critere. `references` reste un critere secondaire, publie : il
   recoupe le critere 1.
4. **Choix** : parmi les X qui gagnent et ne sont pas ecartees, la meilleure P. Si l'IC95 de l'ecart entre
   deux candidates contient 0 (egalite), on prend la plus simple puis la moins chere : format A, puis B,
   puis C ; a format egal, le cout par tour mesure le plus bas.
5. **Aucune candidate** : on garde R (A x Medium). En cas de doute, A et Medium.

Titre du rapport : il dit que le resultat est une **borne haute a recuperation correcte** (section 3).
Le rapport publie la matrice P, dP et IC95, le temoin de hasard, dE, refus, et l'application de chaque
etape de la regle, combinaison par combinaison.

## 11. Traces

`results/donnee_etape_d/` : `PROTOCOLE.md` (ce fichier), `exposition.json`, `controle_formats.json`, un
dossier par combinaison et par generation avec `manifest.json` (commit, sha du banc, de la base, du corpus
et de l'exposition, modele rendu, tokens, cout, duree), les reponses brutes jsonl, `judge/`,
`label_mapping.json`, `RAPPORT.md`, et l'export de l'explorateur (format propose a Jarvis avant d'etre code).
Prod intouchee, corpus B-2 et base C en lecture seule (sha verifies avant et apres).
