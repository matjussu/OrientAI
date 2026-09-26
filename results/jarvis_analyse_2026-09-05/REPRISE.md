# Point de reprise OrientAI, ecrit le 05/09/2026 (Jarvis), mis a jour le 23/09/2026 (Claudette)

> **Plan de référence du cerveau v2 (depuis le 25/09/2026)** : `docs/cerveau/` - contrat v1.2
> (`CONTRAT-cerveau.md`, feuille de route section 13, méthode section 14), gate F
> (`gate_f/requetes_gate_f.json`, 30 questions-tests) et contrat de l'étape 3
> (`etape3/CONTRAT-etape3.md` v2). Ce fichier reste le journal de reprise ; en cas d'écart, c'est
> `docs/cerveau/` qui fait foi pour le plan.

## Reprise au 25/09/2026, soir (étape 3 du cerveau : v2 minimal livré et mesuré)

1. Code : `src/v2/` (pipeline, outils, profil, vérificateur, prompt v0), version `v2` du lanceur,
   banc `gatef`, mesures `src/eval/multiversion/gate_f.py`. Branche `feat/cerveau-v2-minimal`, PR à
   merger sur go de Matteo relayé par Jarvis. Code joué aux bancs : `52a0b14`.
2. Rapport : `results/multiversion/2026-09-25_v2/RAPPORT.md`. Gate F rouge par la clarification seule
   (2/5) ; banc vertical contre la prod : erreur de fait 19,0 % contre 31,6 %, refus 2 contre 26, note
   4,27 contre 2,26, critère 1 61,9 % contre 27,9 %, adossés 100 % contre 72,7 % ; latence p90 43,5 s.
   Contre ChatGPT + recherche (34 tours) : 14,7 % contre 0 %, note 4,29 contre 4,67.
3. Prochaine étape (section 13) : 4, la réponse (prompt travaillé, vérificateur réglé), gate = planchers
   de la section 8. Pistes écrites dans le rapport, section 4 et 5 : nommer chaque chiffre par le
   libellé de l'outil, dire qu'un résultat tronqué n'a pas tout lu, pas d'absence affirmée sans la
   recherche qui la prouve, clarification à 2 questions, une définition par notion quand plusieurs
   fiches sont lues (latence, coût).
4. Budget du tag : 10,53 USD sur 15 (registre `results/multiversion/2026-09-25_v2/budget.json`). Juge :
   un passage de 111 verdicts fait ; tout rejugement demande un nouveau go de Matteo.
5. Pièges : GLM 5.3 envoie des paramètres objet en chaîne JSON (décodés par `src/v2/outils.py`) ;
   la clé Mistral est lue seule du `.env` par la version v2 (`_cle_mistral`), aucun autre secret
   chargé ; le juge tourne en `claude -p` par `judge_v2/juge_stdin.sh`, qui refuse une
   `ANTHROPIC_API_KEY` dans l'environnement.

A lire en premier par quiconque reprend le projet (Matteo, Ella, Claudette, Jarvis apres /clear).
Ce fichier dit ce qui est etabli, ce qui est perime, ou vit chaque chose, et par quoi on commence.

## Etat au 23/09/2026 (lire d'abord)

- **Cap** (Matteo, 23/09) : reussir une demo devant des investisseurs dans quelques mois (date non
  fixee), avec des reponses nettement meilleures et un projet techniquement propre. On vend la
  plateforme ; son argument : chaque chiffre est verifiable.
- **Perimetre** : Informatique + Sante (PASS, LAS, IFSI, paramedical, acces medecine), avec les maths
  en porte d'entree. Pas d'Info-com en informatique ; GEII en ingenierie industrielle ; ECG et ecoles
  qui « exigent la spe maths » hors maths.
- **Modele de generation** : Mistral ou open-weights de tout pays, **jamais un modele americain
  proprietaire**. Le juge du banc est un outil interne (Opus autorise). Recherche structuree pour les
  chiffres, recherche semantique pour les textes (decisions de l'ordre 2026-09-23-0817).
- **Etape B reduite** (« ne pas etre trop gourmand », Matteo, 23/09, Telegram 10584) : cout,
  alternance, insertion (B-1), puis sante (B-2). Mis de cote : Parcoursup 2026, specialites, fiches
  Parcoursup, suite d'etudes, insertion ARS regionale (`_orientai-ref/verticale-2026-09/CAHIER-DES-CHARGES-donnee.md` §4).
- **Fait** : lot 0 (banc, section 0), etape A (texte des fiches, section 0 bis), B-1 (section 0 ter),
  B-2 (section 0 quater), C (section 0 quinquies), correctif C (#184). Merge sur main : 0d55da4.
- **Etape C validee par Matteo et mergee** (ordres 2026-09-23-1358 et -1424 ; #183, 98e9b09, qui embarque
  le contrat #182 ; Telegram 10623). Base SQLite derivee du corpus B-2 : 3 945 formations, 172 981 valeurs
  sourcees, gate C 20/20, audit tout vert (section 0 quinquies). Correctif insertion InserSup (#184,
  0d55da4, contrat C v1.4) : base `data/processed/base_etape_c.sqlite` sha `9667b95521c2`, audit 24/24,
  12 sabotages rouges sur leur cible.
- **Etape D jouee, en attente de validation** (ordre 2026-09-23-1515, section 0 sexies) : grille 3 formats x
  3 modeles, 2 generations, juge a l'aveugle. Regle ecrite : on garde A x mistral-medium-2604. Constat hors
  regle a trancher par Matteo : GLM 5.2 fait nettement moins d'erreurs factuelles (-27 pts) a critere 1
  equivalent. **Etat au soir du 23/09** : PR #185 (branche `feat/etape-d-grille`) ouverte, NON mergee,
  verifiee par Jarvis ; worktree `~/projets/OrientIA-etape-d` en place (son data/processed porte des COPIES
  du corpus B-2 et de la base C corrigee, et un .venv) ; presentee a Matteo (Telegram 10652), en attente de
  sa decision sur GLM et de son go de merge ; banc de confirmation Medium contre GLM propose, NON lance.
  Detail en section 4, dettes en section 5.
- **Validation** : Matteo valide chaque etape dans l'explorateur prive de Jarvis (avant/apres, sources
  cliquables, signalements) ; rien n'est merge sans son go.
- **La prod ne bouge pas** : elle sert le lot 1 de juillet (`/health` prompt `601adcee86b9`, corpus
  `2e4276e6155b`). Les corpus A, B-1 et B-2 sont a part, hors git (section 3).

## Reprise au 25/09/2026, après-midi : concordance avec la page publique (Claudette, ordre 2026-09-25-1320)

- **Base C concordante** : chaque chiffre que la page publique affiche (Parcoursup, MonMaster) est montré au modèle
  avec la valeur et le libellé exact de la page ; les doublons open data (propositions envoyées et admis au bilan final,
  parts de bac chez les néo-bacheliers, candidats de phase principale et complémentaire des masters...) sont renommés
  sans ambiguïté et cachés au modèle (colonne `montre_au_modele` de la table `champ`, appliquée par `lire_fiche` et les
  outils). Contrat et rapport : `results/concordance/`.
- **Contrôle 100 %** `python -m src.eval.concordance` : vert, 25 747 chiffres, 0 écart inexpliqué, 0 doublon montré,
  2 témoins qui rougissent. Relevé des pages : `python -m src.collect.releve_pages` (cache `data/raw/pages_publiques/`).
- **Formations absentes de la session 2026** : 355 (135 Parcoursup, 138 apprentissage, 82 masters), marquées
  `fiche_publique_annee_en_cours = absente`, jamais présentées comme actuelles.
- **Rejugement de la référence** (addendum du RAPPORT multi-version) : ChatGPT + recherche passe de 23,5 % à 0 %
  d'erreur de fait (ses 8 erreurs étaient des écarts de définition) ; la prod de 22,8 % à 31,6 % (elle cite des
  chiffres de bilan final sous les noms de la page). L'écart devient mesurable.
- **Après merge** : reconstruire la base de main (`python -m src.collect.base_etape_c`), le cache des pages y est déjà.

## Reprise au 25/09/2026 : étape 1, instrument multi-version et référence figée (Claudette, ordre 2026-09-25-1126)

- **Instrument** : `python -m src.eval.multiversion run|juger|rapport`, versions branchables
  (`src/eval/multiversion/versions/` : `prod`, `chatgpt`, `chatgpt_web` ; le v2 s'y ajoute sans toucher au lanceur).
  Protocole v0.3 : `results/multiversion/PROTOCOLE.md`.
- **Référence figée** (gelée avant jugement, commit 1bd16ef) : `results/multiversion/2026-09-25_reference/`
  (`RAPPORT.md`, `MANIFESTE.json`, exports au format état des lieux dans `export/`). Échantillon de comparaison figé :
  `results/multiversion/echantillon_vertical_25.json` (25 conversations, 34 tours).
- **Mesures** (RAPPORT.md §1) : erreur de fait prod 22,8 % [14,9 ; 33,2] sur 79 tours, 20,6 % sur l'échantillon ;
  ChatGPT + recherche 23,5 % [12,4 ; 40,0] sur l'échantillon. Juge 4 critères : prod 2,24, ChatGPT 4,53. Critère 1 :
  prod 0,23, ChatGPT 0,34 (échantillon). Les erreurs de la prod sont des absences affirmées à tort, celles de ChatGPT
  des chiffres précis décalés.
- **Coûts** : OpenAI 7,07 USD, Mistral 1,94 USD, juge sur l'abonnement (un passage, vertical seulement).
- **Suite** : étape 3 (v2 minimal), mesurée par ce même instrument sur la même base.

## Reprise au 24/09/2026, soir : banc E (modèle de la démo)

Ordre 2026-09-24-1020, branche `feat/banc-confirmation-modeles` (worktree `~/projets/OrientIA-etape-e`). Rapport :
`results/banc_e/RAPPORT.md` ; protocole `results/banc_e/PROTOCOLE.md` v0.3.2.

1. **Décision (règle écrite, g1)** : C x GLM 5.3 (`zai-glm-5-3`, carte courte + `lire_fiche`, consigne d'outil
   explicite). Erreur factuelle jugée avec les fiches 12,7 % contre 75,9 % pour la prod (dE -63,3 pts, IC95
   [-74,7 ; -51,9]), critère 1 0,805 contre 0,817. Pas de g2. Vérifié indépendamment par Jarvis. **GO de Matteo le
   24/09 à 16h48 (Telegram 10697) : C x zai-glm-5-3 = modèle du cerveau v2.** Rien n'est branché en prod.
2. **Rejugement** : 5 lots minimaux `g1_rejugemin_*` préparés, **non joués** sur décision de Matteo (24/09, 16h48).
   Accord du juge dans cette configuration non mesuré (rapport, section 8).
3. **Juge** : transport par stdin obligatoire (lanceur `results/banc_e/judge/traces_lanceur/juge_stdin_v2.sh`) ; la
   lecture par tranches produit des lectures partielles (témoin `8bf2a1383d`). Binaire nvm en chemin absolu : le PATH
   retombe sur `/usr/bin/claude` 2.1.126 pendant les mises à jour automatiques (400 sur Opus 5.5).
4. **Prix publiés** (24/09) : Medium 3.5 1,5 / 7,5 ; GLM 5.2 et 5.3 1,4 / 4,4 ; Small 4 0,15 / 0,6. Coût réel de D :
   23,25 USD (et non 12,9). Banc E : 10,44 USD.
5. **Dettes pour le cerveau, chacune avec sa mesure** :
   - Medium ignore `tool_choice` any/required sur l'API Mistral (0 appel sur 8, `diag_outil/RESUME.md`) : ne jamais
     compter sur le forçage générique ; forcer par nom de fonction si besoin.
   - Débit de GLM 5.2 : 5 à 10 tours/min à 3 fils, 129 erreurs 429 sur 158 tours ; GLM 5.3 : 13 à 14 tours/min,
     0 erreur 429 (manifestes `results/banc_e/runs/*/manifest_g1.json`).
   - Latence de GLM 5.3 en C : 11,6 s médiane par tour (contre 9,5 s pour la prod).
   - Extracteur du critère 1 aveugle aux tableaux : C x GLM 5.2 écarté à l'étape 1 mais passe en comptant les
     tableaux (0,827 contre 0,836).
   - Exposition oracle (attendus + BM25) : borne haute ; la recherche réelle reste à mesurer au lot « cerveau ».
   - Dettes de D toujours ouvertes : manques de la base C (niveau bac+N, autres voies, précision des capacités,
     mention non renseignée, insertion des masters), rattachement d'insertion trop large (doubles licences, psup:28456).

## Reprise au 24/09/2026

Carry-over de Claudette du 23/09 au soir (eod-recap envoye a Jarvis a 20h52), recopie ici le 24/09 : apres
un /clear, la trace la plus fraiche n'etait que dans le journal de Jarvis, pas dans ce fichier.

1. Lire ce fichier sur la branche `feat/etape-d-grille` (worktree `~/projets/OrientIA-etape-d`), pas sur
   main : sur main, D n'existe pas encore. Rapport : `results/donnee_etape_d/RAPPORT.md` ; protocole :
   `PROTOCOLE.md` v0.2.
2. PR #185 ouverte, NON mergee. Merge seulement sur merge-approval relaye par Jarvis
   (`gh pr merge 185 --merge`). Apres le merge : fast-forward du checkout principal, puis retrait annonce
   du worktree `OrientIA-etape-d`. Son `data/processed` ne contient que des COPIES (corpus B-2
   `2e6a93a5cda6`, base C `9667b95521c2`) et son propre `.venv` ; rien a recopier.
3. Decision en attente de Matteo : adopter GLM 5.2 ou garder Medium. Reco : banc de confirmation
   A x Medium contre A x GLM, 2 generations jugees, juge qui VOIT les fiches. Non lance. Ne rien lancer
   sans ordre.
4. Si GLM est retenu : regler les 429 (1 fil a suffi en g1) et le prix de GLM, non publie, suppose
   1 / 4 USD par million de tokens.
5. Dettes pour le cerveau (section 5) : extracteur du critere 1 aveugle aux tableaux ; Medium sans appel
   d'outil ; manques de la base C (niveau bac+N, autres voies, precision des capacites, mention non
   renseignee, insertion des masters) ; rattachement d'insertion trop large (doubles licences,
   psup:28456).
6. Pieges d'outillage : le juge tourne en `claude -p` (l'agent `juge-aveugle` n'est charge qu'au
   demarrage d'une session). Le lanceur refuse de demarrer si `ANTHROPIC_API_KEY` est presente. Ne jamais
   sourcer le `.env` d'OrientIA dans ce shell, il contient une cle. La generation Mistral, elle, a besoin
   du `.env` (`set -a ; . ../OrientIA/.env`).
7. Checkout principal `~/projets/OrientIA` : main `0d55da4`, pas de `.venv`, `DEPLOY_LOT1_RUN_ME.sh` non
   suivi (dette connue, ne pas y toucher).

## 0. Lot 0 livre et merge le 23/09/2026 (Claudette, ordre 2026-09-23-0817, #177, 89e0f27)

Le banc est versionne dans `src/eval/battery/` (README dans ce dossier). Une commande :
`python -m src.eval.battery bench --tag <nom> --systems local,mistral_large_norag`. Chaque passage
ecrit `results/battery/<tag>/` avec un manifeste (commit, sha de la batterie et du corpus, modeles,
couts). Les scripts de ce dossier (`run_battery.py`, `judge.py`, `aggregate.py`, `spike_agent.py`,
`smoke.py`, `battery.json`) y ont ete deplaces ; les runs bruts du 05/09 restent ici, dans `runs/`.

Mesures du 23/09 (traces : `results/battery/2026-09-23_lot0/REPORT.md` et `manifest.json`) :

| systeme | moy. 4 criteres | refus | err. fact. (juge) | chiffres adosses a une fiche (temoin de hasard) |
|---|---|---|---|---|
| local (prod) | 1,99 | 33 % | 24 % | 58 % (33 %) sur 438 chiffres |
| mistral-large-2512 sans fiche | 3,20 | 0 % | 94 % | 0 % par construction, 805 chiffres |

- **local = la prod** : empreinte de provenance identique a `/health` le 23/09 a 06:49Z (prompt
  `601adcee86b9`, corpus `2e4276e6155b`, index `8c91dfcf5323`, modeles epingles).
- **Delta local contre 05/09 (2,04) : -0,06, du bruit.** Tours apparies : IC95 [-0,14 ; +0,03],
  59 tours sur 67 a 0,25 pres alors que 66 reponses sur 67 ont change (temperature 0,3). Le drapeau
  `erreur_factuelle` du juge est instable d'un passage a l'autre (11 puis 16 tours, 7 en commun) :
  ne pas conclure sur l'ecart d'un seul passage.
- **Mistral Large sans donnees** : mieux note que le produit servi (3,20) mais le juge releve une
  erreur factuelle sur 94 % des tours, et aucun chiffre n'est montrable. Ses reponses font 604 mots
  en mediane (le prompt en demande 250 a 450) : plus de faits exposes au juge.
- **Controle des chiffres (nouveau)** : part des chiffres cites presents dans une fiche que le
  systeme a exposee, comparaison typee (%, EUR, places), toujours publiee avec son temoin de hasard.
  Sur les runs du 05/09 : local 61 % (32 %), claude_ctx 80 % (30 %), agent_sonnet 42 % (7 %),
  agent_mistral 63 % (15 %), GPT et Sonnet sans fiche 0 % (`results/battery/2026-09-05_runs-jarvis/`).
- **Juge** : les 8 verdicts manquants du 05/09 etaient des JSON tronques (plafond de 1 200 tokens) ;
  corrige a 4 000.

Set de pertinence (`scripts/relevance_set/`, `STATE.md` y dit tout) :
- **`eval_retrieval.py` vit dans `scripts/relevance_set/eval_retrieval.py`**. Il venait du WIP `c7402d3`
  et n'etait pas sur main avant ce lot : le RAPPORT le citait sans chemin.
- La cle d'identite est corrigee (position dans `formations.json`, sha du corpus verifie). Le bug
  touchait les modes dense ET bm25 du miner. Les 1 172 references des 135 labels migrent, 0 perdue.
- **recall@10 = 0,419 en raw, 0,616 en serving** (recall@5 : 0,314 et 0,547), sur 86 questions
  scorables. **Ce sont des bornes basses** : 49 % du pool re-mine n'a jamais ete juge. L'ancienne cle
  aurait rendu 0,198 en raw, et non 0 comme l'ecrivait le RAPPORT l.112.
- **Pas de recall sur golden_qa** : ses 676 entrees n'ont aucune verite terrain de pertinence
  (question et reponse, aucun identifiant de fiche). Erreur du RAPPORT du 05/09 (l.112 et 176).

Dette laissee au lot retrieval : le RRF de la prod reste casse (`_orig_index` absent cote dense,
RAPPORT l.107). Le lot 0 ne l'a pas corrige, pour que `local` reste le code servi.

## 0 bis. Donnee verticale, etape A livree et mergee le 23/09/2026 (Claudette, ordre 2026-09-23-0958, #178, 7aeed78)

Rapport complet, chiffres et traces : `results/donnee_etape_a/RAPPORT.md`. ADR-063.

- Nouveau corpus **a part** : `data/processed/formations_etape_a.json` (hors git), sha256
  `9eae9c25108b`, 53 281 fiches dont 14 252 Parcoursup (13 011 avant). La reference de la prod
  (`2e4276e6155b`) est intacte. Rejouer : `python -m src.collect.sources_officielles --telecharger`
  puis `python -m src.collect.corpus_etape_a --reference <formations.json de la prod>`.
- Texte Parcoursup (`src/rag/texte_parcoursup.py`, appele par `fiche_to_text`) : 0 defaut sur les 10
  controles (`python -m src.eval.donnee.controles`) contre 12 996 fiches en defaut avant.
- Banc vertical : chiffres attendus presents dans le texte de leur fiche 317/341 -> 336/341
  (temoin 6 %) ; audit de 50 fiches contre l'API officielle : 0 ecart non explique.
- **Piege** : le texte est 4 fois plus long (bloc de definitions commun). Ne pas re-embedder
  avec ce texte sans mesurer le recall.
- Dette restante : texte MonMaster sans capacite d'accueil (5 chiffres du banc) ; 53 domaines hors
  verticale non revus ; developpe des voies de CPGE a verifier ; RRF prod toujours casse.

## 0 ter. Donnee verticale, etape B-1 livree et mergee le 23/09/2026 (Claudette, ordre 2026-09-23-1044)

Rapport, chiffres et traces : `results/donnee_etape_b/RAPPORT.md`. Forme des champs :
`results/donnee_etape_b/CONTRACT.md` (v1.2 pour B-1). ADR-064. **Validee par Matteo dans
l'explorateur et mergee** (#179, 7629780).

- Corpus a part : `data/processed/formations_etape_b1.json` (hors git), sha256 `9863d2b40d3f`,
  53 807 fiches (+526 formations en apprentissage). C'est la reference avant/apres de B-2.
- Champs `cout`, `alternance`, `insertion`, enveloppe commune, toujours presents, « non disponible »
  avec raison. Sur les 2 395 fiches Parcoursup des 3 domaines : cout disponible 2 099, alternance
  existante 170, insertion propre a la formation 219 (l'ancienne insertion discipline x region, 482
  fiches, n'est plus ecrite).
- **Cout de l'apprentissage** (v1.2, ajout valide par Matteo) : gratuit pour l'apprenti sur les 526
  fiches d'apprentissage, source Code du travail article L6211-1 (« La formation est gratuite pour
  l'apprenti et pour son representant legal. »). Second temoin en ligne (code.travail.gouv.fr) ajoute
  en B-2. IFSI : droits en reserve, deux sources officielles se contredisent.
- Alternance : listes regroupees par etablissement, resumees au-dela de 5, CFA partenaires nommes.
  Insertion des LAS : « non disponible » (valide par Matteo : pour un candidat PASS/LAS, le chiffre
  qui compte est le passage en MMOPK, traite en B-2).
- Controles 0 defaut, banc 336/341 inchange, audit independant 0 ecart sur 50 fiches + 107 ciblees,
  sabotages tous rouges ; verification de Jarvis 127/127 contre les sources publiques.

## 0 quater. Donnee verticale, etape B-2 (sante) livree et mergee le 23/09/2026 (Claudette, ordre 2026-09-23-1252)

Rapport, chiffres et traces : `results/donnee_etape_b2/RAPPORT.md`. Forme des champs :
`results/donnee_etape_b/CONTRACT.md` v1.3.1 (sections 10 et 10 bis). ADR-065. Validee par Matteo
(Telegram 10605) et mergee (#180, a0ee8a6).

- Corpus a part : `data/processed/formations_etape_b2.json` (hors git), sha256 `2e6a93a5cda6`,
  53 808 fiches (B-1 + la fiche concept `reforme_sante_2027`). B-1 n'est pas reecrit.
- Les 800 fiches PASS (287) et LAS (513) portent `sante`, quatre sous-champs, chacun avec sa portee
  (`nationale` | `universite`) :
  - passage national (SIES, Note Flash n°31, novembre 2025, session 2024) : 800/800. PASS 47,5 %,
    LAS 25,7 % d'admis en MMOPK en 1 ou 2 ans, par filiere, en 1 an, en 2 ans ;
  - places MMOPK publiees par l'universite : 216 fiches, 9 universites sur 10 du panel (les 10 qui
    recoivent le plus de voeux PASS + LAS, 59,4 % des voeux) ;
  - taux de passage publie par l'universite : **0**, aucune du panel n'en publie (2 chiffres ecartes :
    Montpellier minimum theorique 2021, Paris Cite repartition des admis) ;
  - reforme 2027 : fiche concept, annonce du 17/04/2026, **aucun decret ni arrete au Journal officiel
    au 23/09/2026** (recherche Legifrance avec temoin positif).
- Texte lu par le modele : chiffre national d'abord, portee dite dans chaque proposition qui porte un
  taux ; un controle rougit sinon.
- Verification : 49 tests B-2, 8 controles sante qui rougissent sur levier, audit vert sur 171 valeurs
  de capacites et 8 lignes SIES (5 sabotages rouges), banc 336/341 inchange ; Jarvis : 89 valeurs
  relues a la main, 0 ecart.
- **Points ouverts** (RAPPORT, fin) :
  - Aix-Marseille : rentree 2024 seulement (derniere deliberation trouvee) ;
  - Toulouse : libelle « 2025/2026 » ambigu ;
  - Paris-Saclay : non disponible (rien de chiffre sur ses pages, deliberations en HTTP 403) ;
  - Nantes (scan) et Lyon 1 (couche texte corrompue) : relus a l'image, audit NON MESURE ;
  - rafraichir le panel a chaque publication de rentree (kine de Bordeaux en 2025/2026) et la fiche
    reforme des qu'un texte parait.
- **Une commande rejoue toute la donnee** : `python -m src.collect.pipeline_donnee` (controle des 22
  empreintes, puis A, B-1, B-2). Bruts verrouilles dans `data/reference/sources_officielles.json`.

## 0 quinquies. Donnee verticale, etape C (base structuree) construite le 23/09/2026 (Claudette, ordres 2026-09-23-1358 et -1424)

Contrat v1.3.1 : `results/donnee_etape_c/CONTRACT.md` (decisions de Matteo Q1-Q6 « go reco pour tout »,
Telegram 10619). ADR-066. Rapport : `results/donnee_etape_c/RAPPORT.md`.

- Une commande : `python -m src.collect.base_etape_c` (etape 5 de `pipeline_donnee`). Sorties hors git :
  `data/processed/base_etape_c.sqlite`, son manifeste (copie dans `results/donnee_etape_c/manifest_base.json`),
  l'export de l'explorateur (13,8 Mo) et un CSV pour tableur.
- Contenu : 3 465 formations post-bac (table de domaines A, maths par M01-M03, 5 fiches ENS arts et design
  exclues par regle comptee) + 480 masters info et maths (MonMaster 2025, nouveau brut verrouille) ;
  172 981 valeurs, chacune avec source, millesime, identifiant de ligne source et portee ; « non disponible »
  porte sa raison (contraintes CHECK). Chiffres lus dans le corpus (Q6 = B), coordonnees dans les bruts.
- Interrogation : `src/base_c/outils.py`, fonctions a filtres fermes (chercher_formations, chercher_masters,
  lire_fiche, trouver_commune, lister_valeurs) ; `*_min` inclusif, `*_max` strict, distance a vol d'oiseau.
- Gate C (20 requetes de Jarvis, sha `227a2c9bfaf6`) : 20/20, 69 valeurs a l'egalite stricte ;
  `python -m src.eval.gate_c --requetes <fichier>`. Temoins : perimetre de l'explorateur 16/20, valeur sabotee 19/20.
- Audit : `python -m src.eval.audit_base_c` (100 % des valeurs contre le corpus et contre les bruts, dans
  les deux sens) et `--sabotages` (8 leviers `ORIENTIA_SABOTAGE_C`, chacun rouge sur son controle).
- A savoir : 4 formations ont leur GPS officiel a plus de 40 km de leur commune (psup:35500, PASS de Rennes,
  GPS pres de Vannes : hypothese site / siege non etablie) ; 18 masters sans coordonnees ; l'historique
  2023-2024 n'existe que pour les 11 champs que le corpus porte.
- **Correctif du 23/09 (`fix/base-c-insertion`, contrat C v1.4)** : la base mergee (sha `3e9dfaff7e8b`) avait
  perdu tous les indicateurs InserSup (0 taux sur 108 lignes, lus sous les noms InserJeunes) ; l'audit ne
  lisait pas `insertion_ligne`. Corrige : chaque indicateur officiel a sa colonne, une cle sans colonne arrete
  la construction, l'audit compare les tables annexes et controle l'inventaire des tables (24/24, 12
  sabotages rouges sur leur cible ; rejoue sur l'ancienne base, le controle d'insertion rougit avec 947
  ecarts). Nouvelle base : sha `9667b95521c2`, empreinte `6dfa2e8d684d`, gate C 20/20.

## 0 sexies. Etape D, format de fiche x modele, jouee le 23/09/2026 (Claudette, ordre 2026-09-23-1515)

Protocole : `results/donnee_etape_d/PROTOCOLE.md` v0.2 (ecrit avant tout appel payant). Rapport :
`results/donnee_etape_d/RAPPORT.md`. Une commande rejoue l'analyse : `python -m src.eval.rapport_d`.

- Grille : formats A (texte actuel), B (carte structuree depuis la base C), C (carte courte + outil
  `lire_fiche`) x Medium 3.5, Large 3, GLM 5.2 (`zai-glm-5-2`), 2 generations, memes 8 fiches exposees par
  conversation (borne haute a recuperation correcte). Juge : Opus 5.5 effort low a l'aveugle, 711 verdicts,
  144 rejuges (accord 82 % sur l'erreur factuelle, kappa 0,63). Cout 13,0 USD.
- **Critere 1** (chiffres attendus cites justes sur 323) : R = A x Medium 0,810 (temoin 0,068) ; aucune
  combinaison au-dessus hors du bruit. **Decision selon la regle : on garde A x Medium.**
- **Constat hors regle** : A x GLM 0,783 (dans le bruit) mais erreur factuelle 16,5 % contre 43,0 %
  (dE -26,6 pts [-37,2 ; -15,6]) et note moyenne 3,89 contre 3,50. A trancher par Matteo ; banc de
  confirmation propose, non lance.
- **Pour le cerveau** : Medium 3.5 n'appelle pas l'outil, meme force, avec ce prompt et 8 cartes ; Large 3
  sait mais ne le fait pas en auto ; GLM l'appelle de lui-meme (33 % des tours, 0 erreur).
- Format B : n'aide pas (critere 1 plus bas pour les 3 modeles). Carte courte seule : -15 a -18 pts.

## 1. Ce qui est etabli (mesure dans la nuit du 4 au 5 septembre 2026)

Source : `RAPPORT.md` (ce dossier, chaque chiffre cite fichier et ligne), version lisible :
https://claude.ai/code/artifact/4046b246-e9db-412a-b16f-0e200a2819b2

- Le produit servi (Mistral medium + RAG, mode strict v4) fait **2,04/5** sur une batterie neuve de
  60 conversations lyceens et etudiants, juge Opus 5 aveugle. GPT-5.5 sans aucune fiche : 4,28.
  Sonnet 5 sans fiche : 3,98. Sonnet 5 avec les fiches que le pipeline sert : 3,64.
- **Les fiches retrouvees n'apportent rien**, meme a un bon modele (3,35 avec vs 3,47 sans, critere
  references). Le retrieval a une contribution nulle ou negative.
- **Le mode strict detruit** ce qui reste (40 % de refus, 2 puces, 90 mots) mais c'etait le seul
  garde-fou : Mistral medium libere passe a 3,28 avec **62 % d'erreurs factuelles**.
- **Le lookup structure** (spike `spike_agent.py`) retrouve ce que le RAG rate (LAS Psycho Bordeaux,
  Licence Info Toulouse III) ; agent Sonnet 4,01, egal a Sonnet seul en moyenne : un juge LLM ne
  voit pas la valeur du corpus, seul un controle deterministe des chiffres la verra (lot 0).
- Contre-juge GPT-5.5 (30 tours x 4 systemes, partiel par credits OpenAI) : meme ordre, pas
  d'auto-preference Opus.

Causes par maillon (section 4 du rapport) : textualisation qui dit faux sur 13 011 fiches et tait le
type de formation, 0 cout, 12 831 sans ville, session 2025 servie en 09/2026 ; embedding qui ne
discrimine pas (3,2 % d'ecart rang 1 / rang 100), hybride BM25 mort, 5 fiches lues sur 10-12,
requete = message courant seul ; generation strict v4, corpus_check qui rend faux en dur, streaming
sans post-traitement ; evaluation sans humain depuis le 22/04, bancs incompatibles, recall@5 jamais
mesure.

## 2. Ce qui est perime (ne plus s'appuyer dessus sans le relire a la lumiere du rapport)

| Document | Pourquoi perime |
|---|---|
| `CLAUDE.md` racine (statut 16/04, matrice 7 systemes, "V2 RAFT") | decrit l'etat d'avril ; la banniere en tete renvoie ici. Reecriture prevue au palier 3 du menage |
| `docs/STRATEGIE_VISION_2026-04-16.md` | roadmap V2 (agentic + RAFT) non executee ; remplacee par les lots 0-5 |
| `docs/SESSION_HANDOFF.md` | etat operationnel d'avant l'ete |
| Roadmap H0/H1/H2 de l'audit du 15/07 et l'ordre H1 lot 2 (set de pertinence, commit `c7402d3` WIP) | remplaces par les lots 0-5 ; le set de pertinence 135/387 reste reutilisable dans le lot 0 |
| Gel du 11/06 (groundedness 0,949, "hallucinations 54 -> 10") | mesure sur les affirmations seulement, correction de rubrique incluse, pas un etat du produit |
| Bancs `results/_archive_pre_2026-06/`, `run1..run10`, `run_F_robust` | historiques, non comparables entre eux ni avec la batterie 2026-09-05 |
| `LLM_Final.md`, README (corpus "47k") | chiffres perimes, corpus reel 52 040 |

Ce qui reste valide : le corpus (52 040 fiches, muet mais reel), l'infra (pipeline, 3 485 tests au 23/09,
Langfuse), le controle deterministe des chiffres du lot 1 de juillet (`src/eval/`), le banc gratuit de
676 questions embarquees (`golden_qa.index`, mais sans verite terrain de pertinence : cf section 0), la note de vision fondateur du 16/07 (vault) pour le
cap produit.

## 3. Ou vit chaque chose

- **Rapport technique et traces** : ce dossier sur `main` (merge 05/09). Runs bruts dans `runs/`,
  jugements dans `AGGREGATE_*.md`, 11 rapports de scouts dans `scouts/`. Batterie et scripts
  deplaces le 23/09 dans `src/eval/battery/` (section 0).
- **Branche d'experimentation** `jarvis/analyse-2026-09-05` : meme contenu, posee sur le WIP
  `c7402d3` de Claudette. Ne pas merger (elle porte le WIP), on peut la supprimer une fois ce dossier
  sur main.
- **Corpus de la donnee verticale** (`data/processed/`, hors git, regenerables par
  `python -m src.collect.pipeline_donnee`) :
  - `formations.json` : prod, sha256 `2e4276e6155b`, **ne pas toucher** ;
  - `formations_etape_a.json` : `9eae9c25108b` (53 281 fiches) ;
  - `formations_etape_b1.json` : `9863d2b40d3f` (53 807) ;
  - `formations_etape_b2.json` : `2e6a93a5cda6` (53 808), le plus recent.
  Chacun a son manifeste `.manifest.json`. Bruts dans `data/raw/` (dont `data/raw/sante/` : note SIES
  et 11 documents d'universites), 22 empreintes au verrou.
- **Zone de reference de Jarvis** (lecture seule) : `~/projets/_orientai-ref/verticale-2026-09/`
  (cahier des charges, `sources-donnees.md`, banc `battery_verticale.json` de 57 conversations,
  explorateur `explorateur/export_data.py`).
- **QG partage** : https://orientai-hq.vercel.app (repo `~/projets/orientai-hq`, remote prive
  `matjussu/orientai-hq` depuis le 05/09). `content/decisions.json` porte les 3 decisions,
  `content/chantiers.json` les lots 0-5 (statut `propose`).
- **Vault Obsidian** : `01-Projets/Actifs/OrientAI-Analyse-Complete-2026-09-05.md` (pointeur +
  verdict), `OrientAI-Vision-Direction-2026-07-16.md` (cap produit).
- **Memoire Jarvis** : `project_orientia.md` (bloc de reprise 05/09 prioritaire).
- **Dossiers sur le PC** apres menage du 05/09 : `~/projets/OrientIA` (backend), `OrientAI_Platform`
  (front, 7 fichiers non commites depuis le 15/07 a traiter), `orientai-hq` (QG), `_orientai-ref`
  (dossier concours, pitch, refonte-ia-2026). Les archives `~/orientia-*-20260614` (10,4 G) ont ete
  supprimees ; reconstruction d'index assumee (`scripts/embed_unified.py`, ~5-10 EUR Mistral).

## 4. Par quoi on commence

Les 3 decisions du 05/09 sont tranchees (ordre 2026-09-23-0817, voir « Etat au 23/09 »), le lot 0 et
les etapes A, B-1, B-2 sont faites. Ordre de la suite (cahier des charges §5-6, cap de Matteo) :

1. **Etape C, base structuree** (faite, validee et mergee le 23/09, #183, 98e9b09, section 0 quinquies) : les chiffres du corpus (admission, cout, alternance, insertion,
   sante) interrogeables par outils, avec leur source, au lieu du texte seul. Estimation du cahier des
   charges (non mesuree) : 2 a 3 jours.
2. **Etape D, meilleur format pour le modele** (jouee, section 0 sexies ; reste la validation de Matteo et
   sa decision sur le constat GLM) ; texte d'embedding distinct du texte lu (le texte des fiches est 4 fois
   plus long qu'avant l'etape A, pas de re-embedding sans mesure).
3. **Le « cerveau »** : outils de recherche structuree branches sur la base C, clarification quand la
   question est vague, ton de conseiller ; mesure au banc face a un modele generaliste sans donnees
   (Mistral Large seul : 3,20 mais 94 % de tours avec erreur factuelle, section 0).
4. **Proprete et mise en ligne** : reparer le build Railway (section 5), menage du depot (palier 3 :
   reecrire `CLAUDE.md`, regrouper `docs/`), puis deploy.

Chaque etape : contrat d'abord, audit d'exactitude avec controle positif, avant/apres dans
l'explorateur, validation de Matteo avant merge.

## 5. Dettes (regroupees au 23/09/2026)

| Dette | Trace |
|---|---|
| Build Railway rouge a chaque merge (`formations.json` est gitignore) : la prod reste figee au lot 1 de juillet (`/health` prompt `601adcee86b9`). A regler avant la demo | `gh pr checks 180` : « orientia-api Deployment failed » ; section 0 pour `/health` |
| RRF de la prod casse (`_orig_index` absent cote dense) | RAPPORT du 05/09 l.107, section 0 |
| Le Mistral du pipeline ne remonte pas ses tokens | `results/battery/2026-09-23_lot0/manifest.json` l.22-24 : `local` (mistral-medium-2604) a `tokens_in`, `tokens_out`, `cost_usd` a null, alors que `mistral_large_norag` a les siens (l.42-43) |
| 2 385 niveaux bac+N encore deduits par l'heuristique historique | `results/donnee_etape_a/RAPPORT.md` l.99 |
| 252 questions du set de pertinence a labelliser (recall@10 actuel = borne basse) | `scripts/relevance_set/STATE.md` l.41 |
| Test du juge qui appelle un vrai modele hors CI : lancer la suite avec `OFFLINE_JUDGE_TESTS=1` et sans cles, le rendre hors ligne par defaut | `results/donnee_etape_b/RAPPORT.md` l.171 |
| Pas de `.venv` dans `~/projets/OrientIA` : le recreer (`uv venv` + `requirements.lock`) | constat du 23/09 apres retrait du worktree B-2 |
| Menage : `DEPLOY_LOT1_RUN_ME.sh` non suivi a jeter ; branche `jarvis/analyse-2026-09-05` a ne jamais merger, a supprimer | `git status`, `git branch -a` le 23/09 |
| Texte MonMaster sans capacite d'accueil (5 chiffres du banc absents) ; 53 domaines hors verticale non revus | section 0 bis |
| Table A, regle M01 : 5 fiches « ENS Paris-Saclay arts et design » classees prepa scientifique (exclues par C, a corriger dans la table) | `src/collect/base_etape_c.py` EXCLUSIONS ; CONTRACT.md de C section 2 |
| 18 masters sans coordonnees (lieux MonMaster qui ne sont pas des communes, Evry fusionnee absente du COG) | `results/donnee_etape_c/audit/audit.json`, info_lieux_sans_coordonnees |
| B-1 : 442 fiches d'apprentissage sur 526 sans code INSEE (departement ecrit sur 3 chiffres, « 044 ») ; MonMaster du corpus : 75 masters info/maths 2025 manquants sur 480 | `results/donnee_etape_c/mesures_contrat/mesures_contrat.json` (CONTRACT.md de C, section 13) ; contourne dans C par normalisation, a corriger dans B-1 |
| Points ouverts de B-1 (droits IFSI, ecoles d'ingenieurs a plusieurs diplomes) et de B-2 (section 0 quater) | RAPPORT de chaque etape |
| Rattachement d'insertion trop large : une double licence ou un parcours porte l'insertion InserSup d'un diplome plus large (ex. psup:28456, double licence Lettres-Informatique, insertion de la licence LETTRES) | verification de Jarvis sur #184, 23/09 |
| Base C : pas de niveau (bac+N), pas de capacites MMOPK « autres voies », pas de precision textuelle des capacites (Lyon Est / Sud), pas de part « mention non renseignee » ; insertion des masters non collectee | `results/donnee_etape_d/RAPPORT.md` section 7 et controle A dans B |
| Medium 3.5 n'appelle pas l'outil avec un prompt charge (meme force) : bloquant pour le cerveau si Medium reste le modele | `results/donnee_etape_d/sonde_outil/RESUME.md` |
| ~~Extracteur du critere 1 aveugle aux tableaux~~ **corrigé le 25/09** dans `numbers.py` (unité de la colonne, sinon de la ligne ; sans unité, rien) et utilisé par le critère 1 de l'instrument ; `critere_d.py` inchangé pour que D et E restent rejouables. Sur E, C x GLM 5.3 passe de 0,805 à 0,836, témoin inchangé | `tests/eval_battery/test_numbers_tableaux.py` (levier ORIENTIA_NUMBERS_SANS_TABLEAUX=1), `tests/eval_multiversion/test_mesures.py` |
| Prod : « [source S1] » affiché en clair à l'élève ; absences affirmées à tort (« aucune formation à Paris ») | `results/multiversion/2026-09-25_reference/RAPPORT.md` section 2 |
| Places 2025 : 240 formations (228 IFSI) où la page et l'open data (`capa_fin`) diffèrent ; la page est montrée, cause non établie | `results/concordance/RAPPORT.md` section 4 |
| MonMaster : 3 écarts de 1 à 2 entre « candidatures » de la page et `n_can_pp + n_can_pc` (inventaire de Jarvis), cause non établie ; sans effet sur ce qui est montré (la page) | `_orientai-ref/verticale-2026-09/concordance/masters/inventaire_masters.json` |
| Contrôle « A dans B » du format D : le motif `doublon_non_montre` peut couvrir une coïncidence de valeur avec un champ caché | `src/eval/format_d.py` |
| ~~Places et vœux 2026 stockés, non montrés : décision attendue~~ **tranché le 25/09** : on garde ce que le modèle voit aujourd'hui, rien de 2026 ajouté, rien de retiré (places et vœux 2026 restent non montrés) | Matteo, Telegram 10783 ; `docs/cerveau/etape3/CONTRAT-etape3.md` section 5 |
| v2 : latence p90 43,5 s au banc vertical (plancher 15 s) ; raisonnement de GLM et boucles à plusieurs appels ; `lire_fiche` à plusieurs ids rend jusqu'à 20 000 caractères (définitions répétées par fiche) | `results/multiversion/2026-09-25_v2/RAPPORT.md` section 5 |
| v2 : 21 erreurs de fait au juge sans chiffre non adossé (connaissances hors outils 11, chiffre mal nommé 5, absence affirmée sans tout lire 4, contradiction avec la fiche 1) | même rapport, section 4 |
| v2 : clarification 2/5 au gate F (3 ou 4 questions posées) : prompt, étape 4 | même rapport, section 3 |
| v2 : réponse vide de GLM 5.3 sans appel d'outil (20 tours relancés sur 178) ; cause non établie | traces `relance_vide`, même rapport section 5 |
| v2 : `trouver_formation` rend 10 candidats classés par identifiant à score égal (13 PASS à Lille : la fiche attendue n'est pas rendue) | gate F, F-HSAN-02 |
| Lanceur : une réponse vide jetait l'usage du tour (corrigé le 25/09) ; le registre du tag v2 porte une estimation majorante de 0,16 USD pour les 2 tours perdus | `budget.json` du tag, entrées « hors tours » |
| ~~`openai` absent des manifestes~~ **déclaré le 25/09** dans `requirements-eval.txt` (hors image de prod) | #190 |
| Latence prod p90 9,3-9,6 s le 25/09 contre 6,8 s le 23/09 (même mesure en processus) : non expliqué | RAPPORT multiversion section 3 |
| Repère de latence de l'état des lieux du 24/09 calculé avec un p90 à rang trop bas (6,24 au lieu de 6,82) : corrigé par Jarvis dans build_etat_lieux.py ; le contrat §8 cite encore 6,2 s | PROTOCOLE multiversion, amendement p90 |
| GLM 5.2 via l'API Mistral : 78 erreurs 429 sur 158 tours (A et B) en generation 1, a regler avant une demo si GLM est retenu | `results/donnee_etape_d/RAPPORT.md` section 6 |

Suite de tests : 3 485 reussis, 45 ignores, 0 echec (branche B-2, commit b9554e4, 23/09/2026, meme
code que main a0ee8a6).

Regle du projet a garder en tete (regle 13 Jarvis/Claudette) : une affirmation qui porte une decision
cite sa mesure. Le rapport est ecrit comme ca ; les lots doivent l'etre aussi.
