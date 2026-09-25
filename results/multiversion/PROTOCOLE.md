# Instrument multi-version : protocole du premier run (étape 1 du cerveau v2)

v0.1, 25/09/2026, Claudette. Ordre `2026-09-25-1126-claudette-orientai-etape1-instrument-multiversion`.
Écrit AVANT tout appel payant (contrat `docs/cerveau/CONTRAT-cerveau.md` §14.2). Aucun appel payant, aucun juge
avant le GO de Jarvis sur ce texte. Un amendement se date ici avant la lecture des résultats.

## 1. Ce que l'instrument mesure

Une version du pipeline = une classe branchable (`src/eval/multiversion/versions/<nom>.py`, qui expose
`VERSION`). Le lanceur la charge par son nom et ne connaît aucune version : brancher le v2 à l'étape 3 = ajouter
`versions/v2.py`, sans toucher au lanceur.

```
python -m src.eval.multiversion run    --version prod|chatgpt|<nouvelle> --banc vertical|lot0 [--tag ...]
python -m src.eval.multiversion juger  --tag ...      # prépare les lots anonymisés (le juge tourne à part, section 5)
python -m src.eval.multiversion rapport --tag ...     # critère 1, chiffres adossés, juge, coût, latence + export explorateur
```

## 2. Versions jouées dans ce premier run

| Version | Ce qu'elle joue | Modèle(s) |
|---|---|---|
| `prod` | le chemin de l'app : `pipeline.answer_stream` (celui de `/answer/stream`, appelé par la plateforme via `/api/ask/stream`), en processus, vraie recherche. Question passée par `_sanitize_question` du serveur, historique = 6 derniers messages dont le contenu assistant est le texte streamé (`OrientAI_Platform/src/app/home-chat.tsx:109`). Réponse = concaténation des événements `token` (ce que l'élève lit). Pas de policy ni de post-traitement, puisque le chemin stream les saute (`src/rag/pipeline.py`, `_validate_for_stream` : « pas de policy replacement, pas de post_process »). | mistral-medium-2604 (génération), mistral-small-2603 (auxiliaire), mistral-embed-2312 |
| `chatgpt` | GPT-5.5 seul, sans fiche, même prompt système que le 05/09 (`SYSTEM_PROMPT_BASELINE`), paramètres par défaut (pas d'effort de raisonnement imposé) : la cible « ChatGPT seul » du contrat §12, comparable au 4,28 du 05/09 | gpt-5.5 |

Identité du `prod` joué, mesurée le 25/09 à 11h27 : l'empreinte `build_fingerprint` du worktree (ORIENTIA_NARRATIVE_MODE=1,
seul drapeau posé sur Railway en plus des chemins, lu par `railway variables`) est identique à `/health` en prod :
prompt 601adcee86b9, corpus 2e4276e6155b, index 8c91dfcf5323, modèles medium-2604 / small-2603 / embed-2312.
Elle est recalculée au lancement et écrite dans le manifeste ; le run refuse de partir si elle diffère.

Limites connues du `prod` joué (écrites avant le run) :
- **Latence** : mesurée en processus sur ce poste (WSL), sans réseau ni CPU Railway. Ce n'est pas la latence que voit
  l'élève ; elle se compare au 6,2 s p90 du banc lot 0 (même mode de mesure).
- **Réponse structurée** : en mode récit, la plateforme peut afficher l'événement `structured` à la place du texte.
  Il est gardé dans la trace ; le juge et le critère 1 lisent le texte streamé. Part des tours concernés : publiée au rapport.
- **Tokens** : comptés par un client Mistral enveloppé (tous les appels passent par le client unique donné à
  `make_production_pipeline`). En stream, le générateur quitte la boucle à la balise de fin, avant le bloc qui porte
  l'usage : l'enveloppe lit le reste du flux à la fermeture pour récupérer l'usage, et chronomètre cette lecture
  (publiée ; attendue en millisecondes). Un appel sans usage lu est compté « non mesuré », jamais zéro.
- **Un seul fil** pour `prod` : `pipeline._last_trace` est partagé, deux tours en parallèle mélangeraient leurs traces.

## 3. Bancs

| Banc | Fichier | sha256 | Conversations / tours |
|---|---|---|---|
| vertical | `~/projets/_orientai-ref/verticale-2026-09/battery_verticale.json` | f467374be3d7 (même que D et E) | 57 / 79 |
| lot0 | `src/eval/battery/battery.json` | 5b268bf34d91 (même que le lot 0 du 23/09) | 60 / 67 |

Le banc lot 0 n'a **aucun chiffre ni fiche attendus** (champs : id, persona, turns, domaine, tags ; mesuré le 25/09).
Conséquences en section 4 et 5.

## 4. Mesures

1. **Critère 1, chiffres attendus cités justes** (banc vertical seulement) : même définition que D et E
   (`src/eval/critere_d.py` : attendu cité juste si la réponse de son tour ou d'un tour suivant contient un chiffre de
   même unité à la tolérance ; périmètre = attendus dont la fiche est dans la base C, `exposition.json`), avec son témoin de
   hasard (graine 7). Extracteur corrigé pour les tableaux (section 6). Sur lot0 : non calculable, dit comme tel.
2. **Chiffres affichés adossés** (`numbers.py`, les deux bancs) : part des chiffres cités présents dans une fiche que la
   version a exposée sur ce tour, avec le témoin de hasard. `chatgpt` : 0 % par construction (aucune fiche), publié tel quel.
3. **Juge à l'aveugle** (section 5) : 4 critères de 1 à 5, refus, erreur factuelle.
4. **Coût réel** par tour et par run (tokens remontés x prix publié), **latence** médiane et p90, **mots** médians.
5. Pour `prod` en plus : décision du routeur, court-circuits, nombre de sources, verdict de fidélité du stream.

Traces : un fichier par (version, banc) au format de l'onglet « État des lieux »
(`_orientai-ref/verticale-2026-09/explorateur/etat_lieux.json` : `meta`, `synthese`, `tours` ; par tour question,
history, latence, modèle, router, sources avec rang / score / texte, réponse, erreurs), plus `version`, `banc`, `tokens`,
`cout_usd`. Déposés dans `results/multiversion/<tag>/export/` pour l'explorateur.

## 5. Juge

Même juge qu'en D et E : agent `juge-aveugle`, `claude -p`, Opus 5.5 (`claude-opus-5-5`) effort low, abonnement.
Transport : lot entier sur **stdin** ; binaire nvm en chemin absolu ; `DISABLE_AUTOUPDATER=1` ; aucun `.env` sourcé,
refus si `ANTHROPIC_API_KEY` est présent (lanceur `juge_stdin_v2.sh` du banc E, chemins adaptés). Rubrique `RUBRIC`
mot pour mot, `build_prompt` inchangé. Aveugle : les 4 runs mélangés, identifiants opaques, correspondance dans
`label_mapping.json`, jamais dans un lot.

Fiches vues par le juge :
- **vertical** : les 8 fiches de `results/banc_e/exposition.json` (attendues + distracteurs) rendues en carte B, les
  mêmes pour les deux versions d'une conversation, comme en E. **Une phrase change** : celle de E disait « montrées à
  l'assistant », ce qui serait faux ici (`prod` a ses propres fiches, `chatgpt` aucune). Proposée :
  « Les fiches ci-dessous sont des données officielles de référence pour cette question ; l'assistant ne les a pas
  forcément eues. Un chiffre ou un fait qui les contredit est une erreur factuelle. Une information absente des fiches
  n'est pas une erreur en soi : juge-la sur tes connaissances. » Conséquence : le taux d'erreur factuelle se compare
  entre versions de CE run, et seulement de près à E (même fiches, phrase différente).
- **lot0** : **aucune fiche**, pour les deux versions (il n'existe pas de fiche de référence ; montrer à `prod` ses
  propres fiches et rien à `chatgpt` rendrait le juge asymétrique). Le juge note sur ses connaissances. Écart assumé
  avec le 23/09, où le juge voyait les titres des fiches servies : la note de `prod` sur lot0 n'est donc pas strictement
  comparable à 1,99 ; elle est publiée à côté, avec cette mention.

Volume : 2 versions x 146 tours = 292 tâches, **un seul passage, sans rejugement** (le go de Matteo couvre un passage).
Lots de 6 tâches pour vertical (fiches longues, comme E), de 12 pour lot0. Coupure (quota, erreur) : arrêt, ping Jarvis,
aucune relance sans nouveau go ; les verdicts obtenus sont gardés, les manquants comptés.

## 6. Correction de l'extracteur (tableaux markdown)

Défaut mesuré en D (`results/donnee_etape_d/RAPPORT.md` §7, `biais_tableaux.json`) : un nombre dans un tableau
markdown dont l'unité est dans l'en-tête de colonne (`| Taux d'accès (%) |`) ou dans le libellé de ligne
(`| Candidats | 3 779 |`) n'est pas extrait. Correction, dans `numbers.py` et partagée avec le critère 1 : dans une
ligne de tableau, un nombre nu prend l'unité de son en-tête de colonne, sinon celle du libellé de sa ligne ; sans unité
identifiable, il reste hors périmètre (pas de comptage sans unité : c'est ce qui créait les coïncidences du « 33 »).
Tests : un tableau connu extrait (unité en colonne, unité en ligne), une ligne sans unité non extraite, et le témoin :
le test rougit quand on coupe la correction par un levier (`ORIENTIA_NUMBERS_SANS_TABLEAUX=1`), règle 9.
Effet publié sur les données existantes de E (C x GLM 5.3) avant et après, pour dire ce que la correction change.

## 7. Prix et budget

Prix publiés (USD / M tokens, entrée / sortie), relus le 25/09 :
- gpt-5.5 : **5 / 30** (developers.openai.com/api/docs/pricing, tableau standard ; 2,5 / 15 = batch). `config.py` disait
  2,5 / 15 « supposé » : le coût du 05/09 affiché 1,20 USD vaut 2,40 USD.
- mistral-medium-2604 1,5 / 7,5 ; mistral-small-2603 0,15 / 0,6 (docs.mistral.ai/models, lus le 24/09, banc E §2).
- mistral-embed-2312 : 0,1 (docs.mistral.ai/models/mistral-embed-23-12, lu le 25/09).
- mistral-large-2512 : 0,5 / 1,5 déjà sourcé le 23/09 (`grille_d.py`) ; claude-* inchangés (juge hors API).

Estimations (supposées, pas des mesures) :
- `chatgpt` : lot0 = 2,40 USD (tokens réels du 05/09 au prix publié) ; vertical 79 tours, même longueur de sortie
  supposée, environ 2,9 USD. **Total environ 5,3 USD.**
- `prod` : non mesuré à ce jour (le pipeline ne remontait pas ses tokens). Borne supposée : environ 15 k tokens d'entrée
  et 0,7 k de sortie par tour sur Medium, plus les auxiliaires, soit environ 4 USD pour 146 tours, sur la clé Mistral.

Plafonds, appliqués par le lanceur sur le coût cumulé de l'ordre (registre `results/multiversion/<tag>/budget.json`,
somme de tous les runs du tag) :
- **OpenAI : 8 USD tout compris.** Avant chaque conversation, le lanceur s'arrête si cumulé + coût de la conversation la
  plus chère déjà vue dépasse 8. Un run arrêté est incomplet, dit comme tel, jamais complété sans go.
- **Mistral : 8 USD** (proposé, rien n'est fixé dans l'ordre), même mécanique.

## 8. Règle d'arrêt et ordre d'exécution

1. Témoins gratuits d'abord : tests de l'extracteur ; enveloppe de comptage testée sur un faux client ; empreinte `prod`
   égale à `/health`.
2. `prod` sur un tour (L01), vérification de la trace et de l'usage lu, puis `prod` x lot0, puis x vertical.
3. `chatgpt` x lot0, puis x vertical (3 fils).
4. Préparation des lots du juge ; relecture d'un lot ; puis un passage du juge.
5. Arrêt immédiat, ping Jarvis : plafond atteint, plus de 10 % de tours en erreur sur un run, empreinte `prod` différente,
   ou coupure du juge.

## 9. Ce qui est décidé sans lecture des résultats

Ce premier run **ne décide rien** : c'est la photo « avant » (prod) et la cible (ChatGPT seul), pour que le v2 soit
mesuré par le même instrument. Il ne tranche aucun seuil ; les planchers du contrat §8 s'appliquent au v2.

## 10. Amendements (GO de Jarvis le 25/09 à 11h32, écrits avant le premier appel payant)

Les 7 points de la v0.1 sont acceptés tels quels (phrase du juge vertical, lot0 sans fiche, un passage de 292 tâches,
plafond Mistral 8 USD, enveloppe de comptage, un fil pour `prod`, correction de l'extracteur).

- **§5, lot0** (demande de Jarvis) : sans fiche, l'erreur factuelle du juge sur lot0 repose sur ses connaissances ; elle
  est donc faible sur les chiffres précis (taux, places). La note lot0 est secondaire : la valeur de lot0, ce sont les
  traces (état des lieux) et les chiffres adossés.
- **A. §2, limite de `chatgpt`** : c'est l'API GPT-5.5 **sans recherche web**. L'app ChatGPT grand public peut chercher
  sur le web et faire mieux sur les chiffres. La cible mesure « le modèle seul », pas le produit ChatGPT ; on ne la
  compare pas à l'app.
- **B. §8.2, recalcul du coût `prod`** : après L01, puis après `prod` x lot0, l'estimation de `prod` x vertical est
  recalculée avec les tokens réels et écrite dans `budget.json` avant de continuer. Si elle dépasse le plafond Mistral
  de 8 USD : arrêt et ping Jarvis.
- **C. §2, réponse structurée** : la part des tours de `prod` qui ont émis un événement `structured` est publiée. Si
  elle dépasse 10 % : ping Jarvis avant le juge (il faudra juger ce que la plateforme affiche vraiment, à établir dans
  OrientAI_Platform : quelle vue gagne quand les deux existent).
- Points de contact : ping au premier arrêt du §8.5, sinon à la fin du §8.3 (runs faits, avant le juge), avec les
  coûts réels.

## 11. Protocole v0.2 (25/09, GO de Jarvis à 11h40 sur le choix de Matteo, Telegram 10730), écrit avant tout appel payant

**Versions jouées** : `prod` et `chatgpt_web`. La version `chatgpt` (API sans web) n'est **pas** jouée ; elle reste
dans le code, branchable. Motif (Matteo) : comparer à ChatGPT tel que tout le monde l'utilise, donc avec recherche.

`chatgpt_web` (`src/eval/multiversion/versions/chatgpt_web.py`) : Responses API, outil `web_search`, `tool_choice`
auto (le modèle décide de chercher, comme dans l'app), même prompt système qu'au 05/09 (en `instructions`),
localisation approximative France (sans elle l'outil suppose les États-Unis : défaut `country: US` de la doc, lue le
25/09 via context7). Sources = les `url_citation` de la réponse (rang, titre, url). Elle remplace l'amendement A pour
le run : on compare à « ChatGPT avec recherche », mais toujours par l'API, pas l'app (voir limite ci-dessous).

**Prix** (page de prix OpenAI relue le 25/09) : tokens gpt-5.5 à 5 / 30 ; « Web search (all models) : 10 USD / 1 000
appels + tokens de contenu de recherche facturés au tarif du modèle ». Seuls les appels dont l'action est `search`
sont comptés comme appels (doc : `open_page` et `find_in_page` ne le sont pas) ; ils entrent au budget sous
`openai-web-search` (0,01 USD l'appel).

**Plafond OpenAI : 15 USD** tout compris (remplace 8). Mistral inchangé (8). Mécanique du lanceur : avant chaque
conversation, arrêt si dépensé + (conversations en vol + 1) x coût de la plus chère vue dépasse le plafond ; tant
qu'aucun coût n'est connu, une conversation à la fois (trou trouvé et fermé par test le 25/09 : sans réservation des
conversations en vol, 2 fils franchissaient un plafond de 0,20 à 0,21). Le plafond est garanti à une conversation près
plus chère que toutes les précédentes.

**Estimation `chatgpt_web`** : non mesurée ; le nombre de recherches par tour et les tokens de contenu sont inconnus.
Elle est calculée sur l'essai à blanc (ci-dessous) puis écrite dans `budget.json` avant le plein run ; au-dessus de
15 USD extrapolés : arrêt et ping Jarvis.

**Essai à blanc avant chaque plein run** : `prod` sur L01 (lot0) ; `chatgpt_web` sur 2 tours du vertical. Traces
(réponse, sources, tokens, appels de recherche, coût) envoyées à Jarvis, qui relit, puis GO plein run.

**Référence figée** (demande de Matteo) : ces deux runs sont la référence de toute la construction du v2 et ne sont
pas refaits. Sont stockés et versionnés : réponses et traces (`<version>__<banc>.jsonl`), manifeste (`budget.json` :
sha des bancs, empreinte prod, commit, date ; id exact du modèle OpenAI rendu par l'API dans la trace de chaque tour).
Toute version v2 est jouée avec le même lanceur, les mêmes bancs, le même juge et la même rubrique. Si l'un des trois
change un jour, on **rejuge les réponses stockées**, on ne les régénère pas.

**Limite écrite** : ChatGPT évolue (modèle mis à jour, web qui change). La référence est une photo datée du 25/09 ;
un rafraîchissement avant la démo se décide à part. Et c'est l'API avec son outil de recherche, pas l'app : leurs
résultats peuvent différer.

**Juge** : pas dans cette étape. Arrêt à la fin du §8.3 (runs faits) ; la décision sur le juge vient à ce point (reco
de Jarvis : vertical seulement, lot0 plus tard si besoin, sur les réponses stockées). `chatgpt_web` : chiffres adossés
non calculables contre nos fiches (sources web), publié comme tel, jamais 0 %. Pour le juge, les marqueurs
`utm_source=chatgpt.com` des liens sont retirés de la copie lue par le juge (ils nommeraient la version).

**Juge, précision du 25/09 à 11h42 (Matteo, Telegram 10732)** : go pour **un** passage du juge sur le **banc vertical
seulement** (`prod` + `chatgpt_web`, 158 tâches), lancé seulement après la relecture des runs par Jarvis (fin du
§8.3). lot0 : pas de juge pour l'instant. Tout rejugement ou relance après coupure = nouveau go. Toutes les traces
sont exportées au format état des lieux pour l'explorateur (onglet construit par Jarvis).

**Amendement du 25/09 à 11h50 (p90)** : le repère de latence cité en §2 (« 6,2 s p90 du banc lot 0 ») vaut **6,8 s**
(6,82). Cause : `build_etat_lieux.py` prenait `xs[int(0.9 * (n - 1))]`, qui rend un rang trop bas (le minimum sur
2 valeurs, défaut relevé par Jarvis sur l'essai) ; recalculé par Jarvis sur les mêmes 67 tours avec le rang le plus
proche (`ceil(0.9 * n) - 1`), la formule de `export._p90`. Seule cette valeur change. Le §2 n'est pas réécrit : cet
amendement le remplace.

## 12. Protocole v0.3 (25/09 à 12h05, GO de Jarvis sur la décision de Matteo, Telegram 10734 et 10736), écrit avant l'appel

**Recadrage (Matteo)** : ChatGPT avec recherche est un **repère** (ce que donne un modèle frontière dans une app
classique), pas une cible à battre. Le but d'OrientAI : aussi utile, souverain, et sans erreur de fait. Le critère
qui compte : le **taux d'erreur factuelle**.

**Échantillon de comparaison figé** (`results/multiversion/echantillon_vertical_25.json`) : 25 conversations du banc
vertical, stratifiées par domaine au prorata du banc (informatique 21/57 x 25 = 9,21 ; santé 9,21 ; maths 6,58 :
parties entières 9 / 9 / 6, le reste restant va à la plus grande partie décimale, maths : **9 / 9 / 7**). Tirage
`random.Random("multiversion-echantillon-2026-09-25|<domaine>").sample(ids triés, quota)`, tous les tours de chaque
conversation retenue. 34 tours (25 premiers tours, 9 suites). Liste figée pour toutes les versions futures :

V-INF-01, V-INF-04, V-INF-05, V-INF-08, V-INF-10, V-INF-11, V-INF-13, V-INF-17, V-INF-18,
V-MAT-03, V-MAT-05, V-MAT-06, V-MAT-08, V-MAT-10, V-MAT-11, V-MAT-13,
V-SAN-02, V-SAN-04, V-SAN-06, V-SAN-07, V-SAN-08, V-SAN-11, V-SAN-13, V-SAN-14, V-SAN-17.

**`chatgpt_web`** : joue seulement ces 34 tours ; ni lot0, ni le reste du vertical. L'essai V-INF-02 (hors
échantillon) reste dans le tag d'essai, hors comparaison.

**Plafond OpenAI : 8 USD tout compris** (0,40 déjà dépensés inclus), même arrêt automatique. Estimation (supposée, sur
les 2 tours de l'essai : premier tour 0,266, suite 0,129) : 25 x 0,266 + 9 x 0,129 = **7,82 USD**, soit 8,22 avec le
déjà-dépensé : **au-dessus du plafond**, signalé à Jarvis avant tout appel.

**Juge** (go de Matteo, un passage) : `prod` sur tout le vertical (79 tours) + `chatgpt_web` sur les 34 tours de
l'échantillon, mélangés à l'aveugle. Le rapport publie `prod` sur les 79 tours ET `prod` restreinte aux 25
conversations, pour comparer à `chatgpt_web` sur la même base.

**Rapport, dans cet ordre** : erreur factuelle (avec IC95), critère 1, juge 4 critères, coût, latence.

**Plafond OpenAI, 25/09 à 12h04 (GO final de Jarvis, option a)** : **9,5 USD tout compris** (0,40 déjà dépensés
inclus), dans l'enveloppe de 15 USD validée par Matteo (Telegram 10730). Remplace les 8 USD ci-dessus. Mistral : 8.
