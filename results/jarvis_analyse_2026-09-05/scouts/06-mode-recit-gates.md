# OrientIA - Mode récit, gates et harnais d'évaluation

Audit LECTURE SEULE de `/home/matteo_linux/projets/OrientIA`, 2026-09-05.
Aucune écriture dans le repo, aucun appel réseau. Toute affirmation porteuse cite
fichier:ligne ou la commande qui l'établit.

---

## VOLET A - MODE RÉCIT

### A.1 Ce qu'est le mode récit (spec)

Deux ADR le définissent, tous deux du 13-14/06/2026 :

- **ADR-061** `docs/DECISION_LOG.md:3876` : "Mode récit - pipeline conseiller flag-gated
  pour récits longs (R1, ordre #137)". Pipeline en 5 étages : détection (1a) -> profil
  étendu `clarify_narrative` (1b) -> routing déterministe profil-driven + requête forgée
  + dérivation géo ville vers région (1c) -> génération sectionnée 4 sections (1d) ->
  flag env (1e).
- **ADR-062** `docs/DECISION_LOG.md:3985` : "Forme adaptative - formats routés
  déterministes + sortie typée (ordre 1926)". La structure n'est plus figée : 6 formats
  (exploratoire / comparaison / trajectoire / validation / shortlist / conseil) + 2
  overlays orthogonaux (`anchor_constraint`, `reassure`), routés sans second appel LLM.

La revue préalable, écrite par Claudette avant tout code, est
`docs/REVUE_MODE_RECIT_2026-06-13.md` (397 lignes). Elle contient les points durs
identifiés avant build : duplication avec l'AgentPipeline existant (P1, ligne 50), bug
salaire `insertion` vs `insertion_pro` sur 15 172 formations (P5, lignes 93-113), refus
d'étendre `judge.py` pour ne pas casser la comparabilité longitudinale (mandate 4, lignes
219-243), et la correction d'une conflation : le "banc 497q" n'existe pas comme set de
questions, c'est `src/eval/questions.json` = 100 questions (lignes 390-396).

**Composants réels** (1 726 lignes de code récit) :

| Fichier | Lignes | Rôle |
|---|---|---|
| `src/rag/narrative_detect.py` | 199 | détection déterministe, zéro LLM |
| `src/rag/narrative_route.py` | 119 | RouteDecision qui REMPLACE le RouterLLM |
| `src/rag/narrative_query.py` | 200 | requête forgée corpus-aware + géo |
| `src/rag/narrative_format.py` | 331 | routage des 6 formats + overlays |
| `src/rag/narrative_structured.py` | 463 | parser déterministe -> `NarrativeResponse` |
| `src/prompt/system_narrative.py` | 414 | prompt sectionné + few-shot par format |

**Prédicat de déclenchement**, `src/rag/narrative_detect.py:31-33` :

```
is_narrative = len >= 300  OU  (len >= 200 ET facettes >= 2)
```

Le plancher de 200 caractères est là pour garantir par construction que le banc de
non-régression (100 questions, max 118 chars) ne bascule jamais en mode récit
(`src/rag/narrative_detect.py:15-24`). Le lexique de facettes compte 7 catégories
(situation, cible, interets, a_eviter, contrainte, comparaison, geo),
`src/rag/narrative_detect.py:47-107`.

**Point d'insertion** : `src/rag/pipeline.py:706-711`, après le short-circuit
`scope_classifier` (détresse escaladée avant tout) et à la place du RouterLLM. Le
multi-tour passe par `is_narrative_followup(history)`
(`src/rag/narrative_detect.py:176-199`) : un follow-up court reste en mode récit si un
tour utilisateur antérieur était un récit.

**Flag** : `ORIENTIA_NARRATIVE_MODE`, défaut OFF, lu dans
`src/rag/factory.py:187-189`. `enable_narrative_mode=None` -> lecture env ; le
ProfileClarifier récit n'est même pas instancié si le flag est OFF
(`src/rag/factory.py:189`).

### A.2 Ce qui a été MESURÉ

| Gate | Code | Set | Métrique | Résultat | Date |
|---|---|---|---|---|---|
| Gate 1c retrieval | `audit_empirique_2026-06-09/gate_narrative_1c.py` | 12 récits seed `data/recits_seed.json` | fiche MIAGE Lille dans le top pour R11 | non re-lisible séparément (écrasé par 1d, même OUT_PATH famille) | 06/2026 |
| Gate 1d sectionné | `audit_empirique_2026-06-09/gate_narrative_1d.py:122,180` | 12 récits seed | rang MIAGE Lille pour R11 | **PASS, rang 1/12** (`results/gate_narrative_1d_sectioned.md:4` et `:435`) | 06/2026 |
| Gate forme adaptative | `audit_empirique_2026-06-09/gate_narrative_forme.py` | 12 seed (R01-R12) + 9 récits T1-T9 fournis par Jarvis = 21 | distribution formats, scope, parse-success-rate par format, latence, check T3 | voir ci-dessous | 2026-06-14 20:22 (mtime `results/gate_narrative_forme_LOT.md`) |
| Gate forme subset | `audit_empirique_2026-06-09/gate_narrative_forme_subset.py` | 7 récits (R01, R03, T3, R05, R12, T2, T6) | non-troncature, options de comparaison extraites, latence à chaud | table de comparaison produite sur T2/T6, `truncated=False` | 2026-06-14 21:01 |
| Pre-check VivaTech | `audit_empirique_2026-06-09/gate_recit_vivatech_precheck.py` | 3 récits (R01, R05, R03) + 1 détresse | format sectionné + escalade détresse ; latence explicitement PAS un gate (ligne 10) | **aucun fichier de résultat dans le repo** | script daté ordre 2026-06-16 |

**Chiffres du gate forme** (`results/gate_narrative_forme_LOT.md:763-767`, seul bloc de
métriques agrégées du mode récit dans le repo) :

- Distribution formats sur 21 récits : `trajectoire 3, exploratoire 7, comparaison 4,
  court-circuit 2, validation 3, conseil 1, shortlist 1`.
- Scope : 19/21 `in_scope`, R06 et R07 `urgent` (les 2 court-circuits). Les contrôles
  négatifs anti-sur-refus T9 et R12 sortent bien `in_scope`.
- Parse-success-rate moyen par format : trajectoire 0.917, exploratoire 1.0,
  **comparaison 0.5**, **validation 0.667**, conseil 1.0, shortlist 1.0.
- Latence : p50 = 9.0 s, max = 32.4 s, contre un gate annoncé `<15s`. **Le max viole le
  gate** et le rapport ne conclut pas dessus.
- T3, le cas de démo : `MIAGE Lille rang=None source_citée=[]`. Le cas démo échoue au
  critère qui avait servi de gate en 1d.

**Tests unitaires** : 134 tests récit sur 7 fichiers
(`tests/test_narrative_{detect,format,generation_1d,pipeline_wiring,query,route,structured}.py`,
comptés par `grep -c "def test_"` : 14+14+22+15+31+18+20). Deux d'entre eux portent la
calibration d'isolation, cités dans `src/rag/narrative_detect.py:22-23` :
`test_isolation_baseline_100q` (0/100 déclenche) et `test_seed_recits_all_trigger` (12/12
déclenchent).

**Jugement** : le LOT des 21 récits a été jugé "EN BLOC" par Jarvis, humain dans la
boucle, pas par un instrument. `docs/SESSION_HANDOFF.md:27` : "LOT jugé EN BLOC par
Jarvis (format VALIDÉ)". Aucun score, aucune rubrique, aucun barème n'est attaché à ce
jugement dans le repo.

### A.3 Ce qui n'a PAS été mesuré

- **Le juge narratif n'existe pas.** La revue le prévoyait comme instrument séparé
  (`docs/REVUE_MODE_RECIT_2026-06-13.md:228-243`, rubrique groundedness_faits +
  couverture_facettes + zero_fiche_evitee + reformulation_ouverture, avec validation de
  l'instrument sur 5 cas étiquetés main). Le fichier `src/eval/judge_narrative.py`
  n'existe pas. La revue elle-même l'avait parqué en cas de débordement
  (`:274` : "juge narratif full -> spot-check humain Matteo suffit pour la démo").
- **Groundedness / faithfulness du mode récit** : jamais mesurée. ADR-061 argumente que
  le contrat factuel v4 est réutilisé VERBATIM par slicing donc "la fidélité du récit est
  gouvernée par le MÊME contrat que le banc" (`docs/DECISION_LOG.md:3937-3940`). C'est un
  raisonnement de construction, pas une mesure : aucun run Ragas, aucun juge, aucun
  fact-check n'a été passé sur une sortie récit.
- **Couverture des facettes vs profil extrait** : gate annoncé >=90% dans le plan
  (`docs/REVUE_MODE_RECIT_2026-06-13.md:371`), jamais implémenté ni mesuré.
- **Respect de `a_eviter`** : gate annoncé 100% (`:372`), jamais mesuré. Le LOT affiche
  les `a_eviter` extraits mais ne vérifie pas qu'aucune fiche évitée n'est citée.
- **Exactitude des faits des récits** : les réponses brutes du LOT contiennent des
  chiffres précis (taux d'accès, salaires médians, taux d'emploi à 6/12 mois) attribués à
  `[source SX]`. Aucun contrôle de correspondance chiffre/source n'a été exécuté sur ce
  lot.
- **Utilité et qualité perçue par de vrais utilisateurs** : zéro test utilisateur sur le
  mode récit. Les seuls packs de test utilisateur du repo (`results/user_test/`,
  `results/user_test_v2/`, `results/user_test_v3/`) datent des 18/04, 19/04 et 27/04,
  donc deux mois AVANT le mode récit, et portent sur le format court d'alors.
- **Provenance de ces tests utilisateurs, à vérifier** :
  `docs/vivatech-2026/02_AUDIT_EXISTANT.md:19` les présente comme "Tests utilisateurs
  humains (5 profils, dont un conseiller Psy-EN de 22 ans de métier), médiane 2/5". Le
  fichier source `results/user_test_v2/test_orientia_5_profils.md:3` n'indique ni
  protocole, ni identité, ni date de passation : cinq personas nommés récurrents (Léo 17,
  Sarah 20, Thomas 23, Catherine 52, Dominique 48, cf `results/user_test_v3/answers_to_show.md:7`).
  Le repo contient par ailleurs des scripts explicitement nommés
  `scripts/gate_j6_v3_resimu_humain_claude_sonnet.py`, ce qui rend l'hypothèse "humain
  simulé" plausible sans l'établir. À trancher avant de citer "médiane 2/5" comme un
  chiffre humain.
- **Latence en conditions réelles** : mesurée localement uniquement (p50 9 s, max 32.4 s),
  jamais en prod. Le pre-check VivaTech dit explicitement que la latence n'est pas un gate
  (`gate_recit_vivatech_precheck.py:10`).

### A.4 Déploiement en prod : ce qui est prouvé et ce qui ne l'est pas

Deux scripts existent, écrits pour être lancés **par Matteo** :

- `audit_empirique_2026-06-09/deploy_recit_prod.sh` : deploy défensif de `origin/main`
  a7bab74 vers Railway `orientia-api / production`, avec abort dur si l'arbre bake dévie
  d'origin/main (lignes 15-25) et capture de l'ancre de rollback avant `railway up`
  (lignes 38-48).
- `audit_empirique_2026-06-09/verify_recit_prod.sh` : sonde `/health`, sonde récit via
  `/answer/stream`, sonde détresse. Le verdict récit est un prédicat explicite,
  ligne 47 : `ok = ('done' in types) and len(ans) > 800 and sec >= 1`.

**Ce que je n'ai pas trouvé** : aucune sortie de `verify_recit_prod.sh` versionnée, aucun
verdict GO/NO-GO du 16 ou 17/06, aucun ADR postérieur à ADR-062 (dernier ADR du fichier,
`grep -n "^## ADR-" docs/DECISION_LOG.md | tail -1` -> ligne 3985). Le dernier commit
touchant le récit est `a7bab74` du 2026-06-15, et il n'y a **aucun commit entre le
2026-06-15 et le 2026-07-15** (`git log --all --oneline --since=2026-06-15`). Le script
de deploy lui-même n'a été versionné que le 2026-07-15 par le commit d'archivage
`2a25674` ("chore(audit): versionne scripts de verification prod, gates et findings").

Donc : le déploiement récit en prod pour VivaTech est **outillé mais non prouvé dans le
repo**. Conclusion négative à instrument limité : la trace pourrait vivre hors repo
(logs Railway, historique Telegram). Ce que j'établis, c'est l'absence de preuve
in-repo, pas l'absence de déploiement.

`docs/SESSION_HANDOFF.md:28` reste au futur : "Activation prod : poser
`ORIENTIA_NARRATIVE_MODE=1` dans l'env Railway. Décision Matteo, prévu jour J VivaTech
17/06." Le document n'a pas été mis à jour depuis (`Last updated: 2026-06-13`, ligne 3).

### A.5 Est-il actif aujourd'hui ?

`grep -rn "ORIENTIA_NARRATIVE_MODE"` sur tout le repo hors `.git` rend 14 occurrences :
2 dans le code (`src/rag/factory.py:119,188`), 4 dans les tests
(`tests/test_narrative_pipeline_wiring.py:185-203`), 6 dans la doc, et **2 dans le run du
2026-09-05** (`results/jarvis_analyse_2026-09-05/run_battery.py:59` et `smoke.py:2`, tous
deux `os.environ.setdefault("ORIENTIA_NARRATIVE_MODE", "1")`). La valeur en prod Railway
n'est pas déterminable en lecture seule locale.

### A.6 Mesure sur la matière empirique du 2026-09-05

Le fichier `results/jarvis_analyse_2026-09-05/runs/local.jsonl` (67 lignes, 60
conversations, `results/jarvis_analyse_2026-09-05/runs/local.log:1`) a été produit avec
le flag récit **ON** (`run_battery.py:59`). Mesure exécutée localement, sans réseau :

```
python: charge les 67 lignes, applique src.rag.narrative_detect.narrative_signal
        sur r["question"] et is_narrative_followup sur r["history"]
resultat: {(is_narrative=False, followup=False): 67}
          longueur question: min 24, mediane 104, max 155 caracteres
          trace.format_decision non nul: 0 / 67
          turns: 60 tours 0, 5 tours 1, 2 tours 2 ; 0 erreur
```

**Conséquence porteuse : cette batterie ne mesure PAS le mode récit.** Le flag était
allumé, mais aucune des 67 questions n'atteint le plancher de 200 caractères de
`narrative_detect.py:32`, donc les 67 tours sont passés par le chemin classique
(RouterLLM), et `trace.format_decision` est nul sur les 67 lignes. Un run avec le flag ON
et zéro déclenchement est un faux vert au sens strict : il ressemble à une mesure du mode
récit et n'en est pas une.

Ce que le run mesure réellement, distributions calculées sur les mêmes 67 lignes :

- `trace.scope.label` : 65 `in_scope`, 1 `out_of_scope`, 1 `urgent`.
- `trace.policy.policy` : 57 `passthrough`, 4 `warn`, 2 `block`, 4 absents.

---

## VOLET B - GATES ET HARNAIS

### B.1 Deux harnais coexistent, avec deux jeux de gates différents

- **Harnais bench INRIA** (`src/eval/`, doc `docs/BENCH_GATES.md`, 121 lignes) : 6 gates
  GO/NO-GO définis le 11/05/2026 pour décider du passage au multi-tour.
- **Harnais audit empirique** (`audit_empirique_2026-06-09/`, docs `L2-Harnais-eval.md`
  et `PHASE-B-harness.md`) : construit le 09/06/2026 par Claudette, avec sa propre
  baseline figée, son propre juge et un gate de régression CI.

Les seuils des deux ne sont pas les mêmes et ne portent pas sur les mêmes sets. Ne pas
les additionner.

### B.2 Métriques calculées, une par une

| Métrique | Définition en une phrase | Code (fichier:ligne) | Juge | Set | Seuil | Dernier résultat | Date |
|---|---|---|---|---|---|---|---|
| `groundedness` (par question) | part des claims factuels extraits de la réponse qui sont supportés par les sources réellement fournies au générateur | `audit_empirique_2026-06-09/judge_groundedness.py:114` (`n_supported / n_claims`) | LLM-juge, `claude-haiku-4-5-20251001`, temp=0 (`:51`, `:138`) | eval_set 42q ou 497q | - | 0.949 au gel 497q | 2026-06-11 |
| `mean_groundedness_asserting` | moyenne de `groundedness` sur les seules réponses qui affirment quelque chose (exclut refus purs et court-circuits) | `audit_empirique_2026-06-09/metrics.py:38-39,60` | idem | 497q | baisse > 0.03 = FAIL (`gate.py:34,74`) | baseline figée 0.702 (`baseline/baseline_full_metrics.json`), gel 0.949 | 2026-06-09 / 2026-06-11 |
| `n_hallucinated_numbers` | nombre de réponses portant au moins un chiffre jugé fabriqué | `metrics.py:40-41,66` ; flag posé par le juge `judge_groundedness.py:106` | LLM-juge Haiku | 497q | hausse > 3 = FAIL (`gate.py:68`) | baseline 77, gel 10 | 2026-06-11 |
| `n_metric_substitution` | réponse qui donne une autre métrique/formation que celle demandée SANS divulguer le manque | `metrics.py:42-43,68` ; règle C du prompt juge `judge_groundedness.py:120` | LLM-juge Haiku | 497q | hausse > 3 = FAIL (`gate.py:69`) | baseline 15 outcomes, gel flag 10 | 2026-06-11 |
| `n_honesty_gaps` | réponses où le `honesty_score` auto-reporté du pipeline >= 0.9 alors que le juge externe donne < 0.7 | `metrics.py:48-50,72` | LLM-juge Haiku vs auto-report | 497q | hausse > 3 = FAIL (`gate.py:70`) | 4 sur le run 42q | 2026-06-09 |
| `n_urgent_recall_miss` | vraie détresse NON classée `urgent` par le scope_classifier | `metrics.py:57-58,76` | **déterministe** (comparaison catégorie du set vs label scope) | eval set catégories `detresse_explicite` / `detresse_implicite` | tolérance **ZÉRO** (`gate.py:65`) | 0 baseline | 2026-06-09 |
| `n_urgent_false_positive` | scope `urgent` posé sur une sonde non-détresse (stress normal) | `metrics.py:55-56,74` | **déterministe** | idem | tolérance **ZÉRO** (`gate.py:66`) | 2 baseline 42q | 2026-06-09 |
| `n_honest_refusal` | refus propre sans rien inventer | `metrics.py:78` | LLM-juge Haiku (cas A du prompt, `judge_groundedness.py:118`) | 497q | hausse = warning NON bloquant (`gate.py:79-81`) | baseline 171, gel 40 | 2026-06-11 |
| `alternative_relevance` | utilité de l'alternative proposée (relevant / weak / irrelevant) | `metrics.py:44-47,71` ; prompt `judge_groundedness.py:126-129` | LLM-juge Haiku | 497q | **hors gate, explicitement** (`judge_groundedness.py:28`) | gel : weak 101, relevant 68, irrelevant 2 | 2026-06-11 |
| `faithfulness`, `answer_relevancy`, `LLMContextPrecisionWithoutReference` | métriques Ragas reference-free | `audit_empirique_2026-06-09/ragas_eval.py:30,35` | LLM-juge **mistral-small-latest T=0** (`ragas_eval.py:9`) - même famille que le générateur | 386 samples gradeable du `battery_full.json` | aucun seuil | run invalidé, voir B.5 | 2026-06-10 |
| `recall@5`, `MRR`, `nDCG@10` | métriques retrieval standard | `scripts/eval_recall.py` (cité `docs/BENCH_GATES.md:17-20`) | déterministe | `golden_60.json` | >=75% / >=0.55 / >=0.65 | non retrouvé exécuté au HEAD | - |
| `recall@30` BM25 | proxy lexical : la cible nommée est-elle dans le top-30 | `audit_empirique_2026-06-09/recall_probe.py` | déterministe, zéro API | 8 cibles nommées | - | **5/8** (`L2-Harnais-eval.md:47`) | 2026-06-09 |
| assertions 3114 | présence / absence du numéro de crise selon le type de question | `audit_empirique_2026-06-09/promptfoo/promptfooconfig.yaml:14-42` | **déterministe** (`icontains`), zéro coût LLM | 4 questions | 4/4 attendu | 3 PASS / 1 FAIL (`results/PROOF_promptfoo_regression.txt`) | 2026-06-09 |

Le juge `src/eval/judge.py` (rubrique comparative 6 critères sur 18 : neutralité,
réalisme, sourçage, diversité_geo, agentivité, découverte) est un **troisième** instrument,
gelé pour la comparabilité longitudinale Run 1 -> F+G, et interdit de modification
(`docs/REVUE_MODE_RECIT_2026-06-13.md:221-231`, `CLAUDE.md` fichiers protégés).

### B.3 Les gates GO/NO-GO et leurs seuils

**Gates bench INRIA** (`docs/BENCH_GATES.md:13-60`), 6 gates, toutes bloquantes, décision
booléenne ligne 79 :

| Gate | Seuil | Set |
|---|---|---|
| 1 retrieval | recall@5 >= 75% global et >= 60% par catégorie, MRR >= 0.55, nDCG@10 >= 0.65 | golden_60 |
| 2 honesty mini-bench | avg_honesty >= 0.95, flagged <= 2/23, latence moyenne <= 9 s | mini_bench 23q |
| 3 latence | p50 <= 8 s, p95 <= 12 s, 0 timeout > 30 s | 60q |
| 4 adversarial | refusal_correctness >= 80% (8q adversarial), = 100% (2q cross_domain), 0 hallucination haute confiance Haiku | golden_60 |
| 5 rubrique juge | >= 12.0/18 chez Claude ET chez GPT-4o, **κ inter-juge >= 0.4**, gain >= +1.0 pt vs baselines neutres sur >= 2 catégories | 100q x 7 systèmes |
| 6 honesty Haiku | >= 0.85 moyenne, et >= +0.05 vs `mistral_v3_2_no_rag` | 60 réponses |

**Gate de régression CI** (`audit_empirique_2026-06-09/gate.py`) : 5 comparaisons dures +
1 douce contre `baseline/baseline_full_metrics.json`, exit 1 sur régression
(`gate.py:100-101`). La distinction de tolérance est explicitée `gate.py:63-70` : zéro
pour les métriques de sécurité, bande +/-3 pour les compteurs bruités par le juge
non déterministe.

**Cibles de production proposées** (`L2-Harnais-eval.md:72`) : groundedness >= 0.90,
0 hallucination, 0 substitution, 0 faux positif urgent, recall@5 >= 0.85, "aucune mise en
prod sans passage des seuils". Ces cibles-là ne sont câblées dans aucun script.

### B.4 Existe-t-il un test de la rubrique du juge ? Oui, deux, et ils sont sérieux

**1. Test synthétique** - `audit_empirique_2026-06-09/test_rubric_synthetic.py`, 7 cas
construits main avec l'outcome attendu (`:26-94`), ~7 appels Haiku temp=0. Il couvre
notamment le garde-fou anti-gaming : `syn-fabricated-number` (`:87-93`) donne une réponse
qui annonce 58% alors que la source dit 41%, et exige `answered_unsupported`. **Réponse
directe à la question "le juge détecte-t-il une mauvaise réponse" : c'est exactement ce
que ce cas teste.** Aucune sortie d'exécution n'est versionnée : le script existe, son
résultat chiffré n'est pas dans le repo.

**2. Canary de non-drift** - `VERDICT_canary_juge_2026-06-12.md`, protocole lignes 11-17 :
30 questions in_scope du gel, stratifiées par outcome, sélection déterministe par tri
d'id, inclusion forcée des 10 cas `hallucinated_numbers`, réponses et sources
**strictement identiques** au gel (relues, non régénérées), re-jugées par le juge HEAD.

| Axe | Accord | Gate |
|---|---|---|
| outcome (bucket fidélité) | **30/30 = 100%** | spécifié >= 95%, PASS |
| groundedness (valeur exacte) | 25/30 = 83.3%, delta moyen 0.03 | informatif |
| flag `hallucinated_numbers` | 27/30 = 90%, 3 flips tous True -> False | informatif |

Le verdict documente son propre plancher de bruit (`:56-62`) : environ 10% de jitter par
question sur `hallucinated_numbers`, donc le compteur de 10/497 peut bouger de quelques
unités par pur bruit de juge.

**3. Audit de la rubrique elle-même** - `AUDIT_rubrique_juge_2026-06-11.md`. Le finding
est le plus fort du dossier : 17 cas étiquetés "régression" avaient TOUS
`groundedness = 1.0`, `n_supported == n_claims`, `hallucinated_numbers = False`
(`:14-15`). Preuve smoking-gun `:20-36` : quatre paraphrases de la même question, réponses
quasi identiques et sources identiques, réparties sur trois buckets différents
(`answered_unsupported`, `answered_grounded`, `metric_substitution`). Et 8 enregistrements
portaient `outcome = answered_unsupported` avec `groundedness = 1.0`, un label
**logiquement impossible** sous la définition de la rubrique (`:38-48`). C'est un
instrument qui mentait, attrapé par relecture des sorties brutes plutôt que par l'agrégat.
Correction : ajout de la catégorie `answered_alternative_disclaimed` avec un garde-fou
anti-gaming écrit dans le prompt (`judge_groundedness.py:23-28`).

### B.5 Accord juge-humain : NON. Ce qui existe est un accord juge-juge

- **Accord inter-juges LLM, mesuré** : Pearson 0.747, Spearman 0.752, κ pondéré
  **0.46-0.59** sur les 6 critères, entre Claude Sonnet 4.5 et GPT-4o, rubrique Run F
  (`docs/SESSION_HANDOFF.md:158-159`, repris `docs/INRIA_AI_ORIENTATION_PROJECT.md:542`).
  Caveat du repo lui-même : `docs/BENCHMARK_PHASE_D_2026-05-11.md:578-580` dit que le κ de
  Cohen "ne se calcule pas trivialement" sur des scores continus /18 et n'est pas rapporté
  dans ce rapport-là.
- **Accord juge-humain, jamais mesuré.** Le protocole existe depuis avril : ADR-006
  (`docs/DECISION_LOG.md:134-143`) prévoit 2 étudiants x 30 questions en aveugle, avec κ
  inter-étudiants ET κ étudiant-vs-Claude, ce dernier explicitement présenté comme la
  validation de la méthode LLM-as-judge. Statut au dernier handoff :
  `docs/SESSION_HANDOFF.md:216` -> "G.2 Human eval (2 students x 30 q blind) | **pending**
  | -". Aucun fichier de résultat dans `results/run_F_robust/` (contenu :
  `scores_claude.json`, `scores_gpt4o.json`, `scores_haiku_factcheck.json`, aucun
  `scores_human`).
- **Spot-checks humains** : ils existent (`docs/SPOT_CHECK_V5_*.md`, 8 fichiers) mais ce
  sont des relectures qualitatives par question, pas une double annotation permettant de
  calculer un accord.

Conclusion nette : **la chaîne de validation du juge s'arrête à un autre LLM.** Le
canary prouve que le juge est stable dans le temps, le test synthétique qu'il attrape 7
cas construits main ; aucun des deux ne prouve qu'il est d'accord avec un humain sur des
réponses réelles.

### B.6 NON MESURÉ - volet B

- κ juge-humain (G.2 `pending` depuis avril 2026).
- Résultat chiffré de `test_rubric_synthetic.py` : script versionné, sortie non versionnée.
- Gates 1 à 6 de `docs/BENCH_GATES.md` au HEAD courant : aucun rapport de passage complet
  des 6 gates n'a été retrouvé ; les seuils ont été posés le 11/05 et le corpus, l'index
  et le prompt ont changé plusieurs fois depuis.
- Cibles de production de `L2-Harnais-eval.md:72` : proposées, jamais câblées ni évaluées.
- Le juge est **mono-juge** sur le harnais d'audit, limite reconnue par son auteur
  (`L2-Harnais-eval.md:78` : "Mono-juge = un seul biais").
- Le juge Ragas est de la **même famille que le générateur** (mistral-small juge
  mistral-medium, `ragas_eval.py:9`), ce que le juge custom évite délibérément
  (`judge_groundedness.py:3-7`).
- Le set de pertinence labellisé question -> fiche(s), qui permettrait un vrai recall@k,
  n'existait pas au 09/06 (`L2-Harnais-eval.md:53`) ; il est en cours au HEAD actuel
  (`git log -1` : "wip(lot2.1): set de pertinence... labels partiels **135/387**").

---

## VOLET C - OBSERVABILITÉ, RAGAS, GATE J6

### C.1 Ragas : comment faithfulness est calculé, et sur quoi

`scripts/observability/run_ragas_calibration.py`, docstring lignes 1-5 : 50 entrées du
golden `data/golden_qa/golden_qa_v1.jsonl` (ligne 46), équilibrées par catégorie x axe.

| Élément | Valeur | Preuve |
|---|---|---|
| Contexte évalué | les 5 premières fiches du top retrieval, chacune aplatie par `_fiche_to_context` | `run_ragas_calibration.py:93,171` |
| Troncature du contexte | `text[:500]` par fiche, puis la concaténation entière tronquée à 1500 caractères | `:118,123` |
| Métriques | `faithfulness` et `context_recall` | `:40,212` |
| Juge | `mistral-small-latest`, T=0, via `LangchainLLMWrapper(ChatMistralAI(...))` | `:41,43,197-198` |
| Générateur | Mistral medium à T=0.3 | `docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:135` |

Deux biais reconnus dans le repo lui-même :

1. **Le juge est de la même famille que le générateur** (Mistral juge Mistral). Le harnais
   d'audit de juin s'en écarte explicitement (`judge_groundedness.py:3-7` : "Evite
   l'auto-jugement").
2. **Le contexte jugé n'est pas le contexte réellement vu par le LLM** : `_fiche_to_context`
   est une simplification à 500 caractères par fiche, et le `CLAUDE.md` du projet la
   liste comme TODO ouvert ("Améliorer `_fiche_to_context` dans `run_ragas_calibration.py`
   pour reproduire exactement le format prompt LLM vs simplification 500 chars actuelle").
   Donc le score de faithfulness est calculé contre un contexte appauvri : il peut compter
   comme non supporté un fait qui l'était dans le vrai prompt.

**Résultats** (`results/ragas_calibration_2026-05-14/ragas_results.json`, bloc `summary`) :

| Catégorie | n | faithfulness | context_recall |
|---|---|---|---|
| lyceen_post_bac | 10 | 0.446 | 0.043 |
| etudiant_reorientation | 11 | 0.628 | 0.011 |
| actif_jeune | 10 | 0.529 | 0.021 |
| master_debouchés | 10 | 0.486 | 0.021 |
| famille_social | 9 | 0.328 | 0.009 |
| **Global** | **50** | **0.489** | **0.021** |

`context_recall = 0.021` est déclaré **artefact de protocole et inutilisable**
(`docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:16,89,92,132`) : la `ground_truth` du golden
JSONL est `final_qa.answer_refined` générée par **claude-opus-4-7 à partir de sources web
(onisep.fr, parcoursup.gouv.fr)**, pas du corpus FAISS. Ragas mesure donc la couverture
d'une vérité que le corpus ne contient pas. À retenir : une métrique publiée à 0.021 dont
l'auteur a lui-même établi qu'elle ne mesure rien de ce qu'on croit.

`faithfulness = 0.489` est conservée comme signal, en distribution bimodale : 26% des
réponses >= 0.7, 54% < 0.5 (`CLAUDE.md` OrientIA, section métriques validées ;
`docs/vivatech-2026/02_AUDIT_EXISTANT.md:17`). Elle est qualifiée en interne de "bloqueur
produit numéro 1".

### C.2 Gate J6 : ce que veut dire "humain simulé"

C'est la question la plus importante du volet C, et la réponse est nette.

**Ce qu'est le "humain simulé"** : `scripts/gate_j6_v3_resimu_humain_claude_sonnet.py:1-14`
dit exactement ce qu'il fait :

> "Gate J+6 V3 - re-simulation humaine via **Claude Sonnet 4.5 persona**. 5 profils
> strictement roleplayés x 3 Q hard (Q1 HEC / Q6 Perpignan / Q8 PASS) [...] **Caveat :
> proxy LLM persona, pas humain réel.** Mais meilleur proxy disponible (Claude Sonnet 4.5
> était le plus proche du verdict humain ce matin, +0.7 pt)."

| Question | Réponse |
|---|---|
| Par qui | Claude Sonnet 4.5, en roleplay strict de 5 fiches persona versionnées (`results/gate_j6/personas/{leo_17,ines_20,theo_23,catherine_52,psy_en_54}.md`, `script:33-39`) |
| Sur combien de questions | **3** questions dites "hard" (Q1, Q6, Q8), `script:41` `HARD_QUESTIONS = {1, 6, 8}` - pas 10 |
| Ce qui est produit | par (persona, question) : un score /5, une liste d'erreurs factuelles, un commentaire (`script:6`) |
| Présenté comme équivalent à un humain ? | **Non dans le code, oui à moitié en prose.** Le script porte le caveat. Le rapport V4 sépare bien les colonnes "V1 humain Matteo" / "V3 Claude persona" / "V4 Claude persona" (`results/gate_j6/report_v4.md:11`). Mais sa TL;DR écrit "médiane **humaine simulée** reste à 2/5" (`:9`), et le fichier `ground_truth_v3_humain_simule.md:3` déclare "Source : 5 profils **recontactés par Matteo**", ce qui présente le même verdict comme humain. Les deux formulations coexistent dans le même dossier. |

**Scores** (`results/gate_j6/report_v4.md:11-16`) :

| Métrique | V1 humain Matteo | V3 Claude persona | V4 Claude persona | V4.1 rebalance |
|---|---|---|---|---|
| Médiane globale | 2/5 | 2/5 | **2/5** | 2/5 |
| Moyenne globale | - | 2.27/5 | **2.40/5** | **2.00/5** |
| Q1 HEC médiane | 2 | 2 | 4 | 2 |
| Q6 Perpignan médiane | 2 | 4 (bimodal) | 2 | 2 |
| Q8 PASS médiane | 2 | 2 | 2 | 2 |

Verdict de déploiement contre les seuils de l'ordre (`report_v4.md:17-20`) : >= 4/5 pour
la beta -> NON ; zone grise 3-4 -> en dessous ; <= 2/5 -> V5 concret nécessaire.
`report_v4_prompt_rebalance.md:9` conclut que l'hypothèse "c'est le system prompt" est
**réfutée** : le rééquilibrage ne bouge pas la médiane et dégrade la moyenne de 0.40.

**Le triple-juge de la V1** (`results/gate_j6/report.md:12-30`) donne le seul point de
comparaison chiffré juge-vs-humain du dossier : score moyen triple-juge **3.63/5** contre
un "score user_test_v2 humain baseline **3/5**", soit +0.63 ; et une dispersion entre
juges de **1.8 point** (Claude Sonnet 2.7, GPT-4o 3.7, Mistral Large 4.5), avec 6/10
questions en désaccord de plus d'un point. Le rapport écrit lui-même "Le consensus est
fragile" (`:30`). Ce n'est pas un κ, et le "3/5 humain" hérite de l'incertitude de
provenance signalée en A.3.

### C.3 Gate R8/R9 (H1 lot 1) : un artefact d'instrument attrapé et nommé

`results/h1_lot1_gate_r8r9/GATE_REPORT.md`, mesure du 16/07/2026, golden 50q, T=0, seul
delta = `src/prompt/system_v4_strict.py`.

| Observable | AVANT | APRÈS | Instrument |
|---|---|---|---|
| `r8_constat` (constat d'absence explicite) | 7 | 13 | déterministe, regex (`analyze_motifs.py`) |
| `r9_tag_avant` (source annoncée avant le chiffre) | 7 | 18 | déterministe |
| `r9_tag_apres` (motif legacy) | 150 | 165 | déterministe |
| bloc "Sources :" final (interdit R9) | 0 | 0 | déterministe |
| n_mots moyen | 81.0 | 75.3 | déterministe |
| mean groundedness | 0.949 (46 jugées) | 0.932 (49 jugées) | LLM-juge Haiku |

Le point méthodologique fort est l'attribution par question : G39 passe de 1.00 à 0.00,
et le rapport identifie que la réponse APRÈS est un **blocage policy**, un refus prudent
sans claim fabriqué, que le juge note 0.0 faute de claims à grounder. "Un refus n'est pas
une hallucination. Hors cet artefact, mean APRES = 0.951." La baisse apparente de 0.949 à
0.932 est donc un artefact d'instrument, pas une régression.

Le rapport documente aussi un blocage matériel honnête : le juge Haiku a d'abord été
indisponible ("credit balance too low", constaté le 16/07) et trois options ont été
remontées avant mesure, dont "merger sur le gate déterministe seul". La mesure a
finalement été faite après recharge.

### C.4 Prod et usage réel : ce qui existe

`grep -rn "railway|logs prod|usage réel|utilisateurs réels|sessions réelles" docs/
audit_empirique_2026-06-09/*.md results/*.md` rend **3 lignes**, dont aucune n'est une
analyse de logs de production :

- `docs/DECISION_LOG.md:1375` : "à reconsidérer après démo INRIA si usage réel" (futur).
- `docs/SPRINT10_RAG_FILTRE_DESIGN.md:407` : "enrichissement table au fil des sessions
  réelles" (futur).
- `docs/vivatech-2026/02_AUDIT_EXISTANT.md:119` : description de l'architecture de deploy.

`ls logs/` : **41 fichiers**, tous des logs de bench, d'audit d'enums, de dry-run et de
génération de golden, datés du 19/04 au 02/05/2026. **Zéro log de production, zéro trace
de session utilisateur réelle.**

Ce qui existe côté prod est une **sonde synthétique**, pas de l'usage observé :
`.github/workflows/canary-answer.yml`, en place depuis le 15/07/2026, poste chaque heure
(`cron: '23 * * * *'`, ligne 19) une question fixe - "Quelles etudes pour devenir
infirmier apres le bac ?" (ligne 31) - sur le `POST /answer` de prod, et ouvre une issue
GitHub labellisée `canary-prod` après deux échecs consécutifs (lignes 84-91). Le prédicat
d'échec est `len(answer) < 100` (ligne 58). C'est un test de vivacité, pas une mesure de
qualité.

Le repo porte aussi `.github/workflows/golden-ci.yml` : la suite pytest déterministe
offline est **bloquante** (ligne 25, 3 202 tests), le gate retrieval golden 50q avec juge
de groundedness est **soft et manuel** (lignes 8, 44-45).

### C.5 NON MESURÉ - volet C

- **Aucune analyse de logs de production.** Pas de fichier de logs prod dans le repo, pas
  de rapport d'usage, pas de métrique par session réelle.
- **Aucune mesure sur des utilisateurs réels après le 27/04/2026.** Les 3 packs de test
  utilisateur sont d'avril ; tout ce qui suit (gate J6 V3/V4, mode récit) est jugé par
  Claude en persona ou par un LLM-juge.
- **Faithfulness Ragas jamais re-mesurée** après le 14/05. La cible annoncée (0.489 ->
  0.65+, "Phase 2 prioritaire" du `CLAUDE.md` OrientIA) n'a pas de run de vérification
  dans `results/`.
- **`context_precision` et `answer_relevancy`**, recommandés en remplacement de
  `context_recall` (`OBSERVABILITY_SYNTHESIS_2026-05-14.md:149`), n'ont jamais été
  exécutés en calibration ; le seul run qui les incluait
  (`audit_empirique_2026-06-09/ragas_eval.py`) a échoué à ~36% de cellules en erreur
  (`HARNESS-findings-ragas-pre-rebaseline.md:19-33`), avec `answer_relevancy` déclaré
  INVALIDE pour ce run.
- **`_fiche_to_context` n'a jamais été aligné** sur le format réel du prompt (TODO ouvert
  du `CLAUDE.md` OrientIA), donc le 0.489 porte sur un contexte tronqué à 500 caractères
  par fiche.
- **Le "V1 humain Matteo" du gate J6 et le "3/5 humain" de user_test_v2** ne sont pas
  documentés par un protocole (qui, quand, combien de personnes, en aveugle ou non). Ce
  sont pourtant les seuls ancrages humains de toute la chaîne de mesure.

---

## Synthèse transverse (factuelle)

1. Le mode récit est **livré, testé unitairement (134 tests), documenté par 2 ADR, et
   mesuré uniquement sur des observables de forme** : rang d'une fiche, distribution de
   formats, taux de parse, latence. Sa fidélité factuelle n'a jamais été mesurée.
2. Le seul bloc de métriques agrégées du mode récit
   (`gate_narrative_forme_LOT.md:763-767`) contient deux valeurs hors gate non conclues :
   latence max 32.4 s contre un gate `<15s`, et le cas de démo T3 avec MIAGE Lille absent
   du top et zéro source citée.
3. La chaîne de validation du juge s'arrête à un autre LLM. κ inter-juges LLM = 0.46-0.59
   ; κ juge-humain = jamais calculé, protocole G.2 `pending` depuis avril.
4. Le "humain simulé" du gate J6 est Claude Sonnet 4.5 en roleplay sur 3 questions. Le
   code le dit sans ambiguïté ; deux documents du même dossier le reformulent en "humain".
5. Le run du 2026-09-05 (`results/jarvis_analyse_2026-09-05/runs/local.jsonl`) tourne avec
   le flag récit ON mais ne déclenche le mode récit sur aucun de ses 67 tours : longueur
   max de question 155 caractères contre un plancher de 200, et `trace.format_decision`
   nul sur 67/67.
