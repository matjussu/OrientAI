# Lot C - Gate J6, audit empirique juin, vivatech, git log

Scout lecture seule sur /home/matteo_linux/projets/OrientIA. Citations = fichier + ligne, ou commande.
Périmètre lot C : results/gate_j6/, results/h1_lot1_gate_r8r9/, audit_empirique_2026-06-09/ (en entier),
docs/vivatech-2026/, git log depuis 2026-04-01. Aucun fichier du repo n'a été modifié.

---

## 0. Ce qu'est le gate J6, et ce que veut dire "humain simulé"

"Gate J+6" = le gate de fin de première semaine (J+6), 2026-04-22, qui pose une question binaire :
l'ajout du Validator + de l'UX Policy fait-il passer le verdict "recommandable à un mineur qui utilise
l'outil seul, sans adulte pour vérifier" de 3/5 (baseline humaine user_test_v2) à 4-5/5 ?
Deux branches de stratégie en dépendent : >= 4/5 -> branche A "data-focused" ; <= 3,5/5 -> branche B
"agentic" ; 3,5-4 = zone grise, arbitrage humain (results/gate_j6/report.md:5, :98-101).

Pack testé : 10 questions, identiques au pack humain v2 (report.md:11). Pipeline : OrientIAPipeline + MMR
+ intent + Validator + UX Policy alpha/beta (report.md:12).

Trois instruments distincts, à ne pas confondre :

1. **triple-judge LLM** : Claude Sonnet 4.5 + GPT-4o + Mistral Large notent 1-5 sur le critère unique
   "recommandable à un mineur en autonomie", même formulation que le verdict humain (report.md:13).
   Budget ~3 $ pour 30 appels juges + 10 regen (report.md:14, :121).
2. **humain réel** : 5 profils recontactés par Matteo (Léo 17 lycéen, Inès 20 L2 socio, Théo 23 M1 IAE,
   Catherine 52 parent ingénieure, Psy-EN 54 avec 22 ans d'expérience) sur un pack papier de 3 questions
   dures, barème 1-5 explicité (ground_truth_pack_v3.md:27-35). Résultat consigné dans
   ground_truth_v3_humain_simule.md:3, :19-28.
3. **"humain simulé"** = Claude Sonnet 4.5 en role-play strict sur ces mêmes 5 personas, system prompt
   qui interdit la méta-analyse et force une sortie JSON, 15 évaluations (5 personas x 3 questions),
   ~1,50 $ (report_humain_simule_v3.md:11-16). Caveat écrit par l'auteur : "Claude Sonnet persona !=
   humain réel. C'est un proxy LLM calibré sur profil texte" (report_humain_simule_v3.md:17). Le choix de
   Claude comme proxy est justifié par le fait qu'il avait l'écart le plus faible (+0,7 pt) avec le
   verdict humain de Matteo le matin même (report_humain_simule_v3.md:19). Prompts des personas :
   results/gate_j6/personas/{leo_17,ines_20,theo_23,catherine_52,psy_en_54}.md.

Piège de nommage : le fichier `results/gate_j6/ground_truth_v3_humain_simule.md` porte "humain simulé"
dans son nom mais contient le ground truth HUMAIN RÉEL (ligne 3 : "Source : 5 profils recontactés par
Matteo"). Le commit correspondant confirme l'humain :
`git log --format='%ad %s' --date=short` -> `2026-04-22 docs(gate-j6+adr): ground truth v3 humain + ADR-036`.
Le fichier réellement simulé est `report_humain_simule_v3.md` (+ les JSON `*_resimule_claude_sonnet.json`).

---

## 1. Tableau chronologique (lot C)

| Date | Jalon | Ce qui est mesuré | Set (n) | Juge | Métrique + résultat | Ce qui a changé | Fichier preuve |
|---|---|---|---|---|---|---|---|
| 2026-04-19 | pack user_test_v2 généré | réponses servies au panel | 10 q | - | - | pack v2 | results/user_test_v2/responses.json (mtime 19/04) |
| ~2026-04-21 | user_test_v2, verdict humain | recommandable mineur autonome | 10 q | 5 humains | **3/5** ("non recommandable pour mineur en autonomie") | baseline du gate | cité gate_j6/report.md:5 |
| 2026-04-22 matin | ground truth humain pack v3 | idem, 3 Q ambiguës | 3 q x 5 profils | 5 humains (Matteo) | **médiane 2/5** (Q1 HEC 2, Q6 Perpignan 2, Q8 PASS 2) ; 4 erreurs factuelles disqualifiantes listées | sélection des 3 Q les plus ambiguës pour les juges LLM | ground_truth_v3_humain_simule.md:19-28, :34-77 |
| 2026-04-22 | Gate J+6 V1 | recommandable mineur | 10 q | triple-judge LLM | **3,63/5** ; Claude 2,7 / GPT-4o 3,7 / Mistral Large 4,5 ; écart Claude-Mistral 1,8 pt ; désaccord >1 pt sur 6/10 ; rule catch rate 3/3, 0 faux positif | Validator v1 + policy alpha+beta | report.md:21-34, :53-59 |
| 2026-04-22 | Gate J+6 V2 | idem | 10 q | triple-judge LLM | **3,23/5 (-0,40)** ; honesty score 0,96 -> 0,80 ; policy 7 pass/0 warn/3 block -> 1/7/2 ; **28 warnings layer3** ; règles violées 4 -> 6 | 4 règles dures Psy-EN + couche 3 Mistral Small + data cleanup "mention B" | report_v2.md:13-20, :68-82 |
| 2026-04-22 | Gate J+6 V3 | idem | 9 q (Q9 = ReadTimeout Mistral) | triple-judge LLM | **3,26/5** ; hypothèse "footer verbeux" RÉFUTÉE ; désaccord 4/10 | footer limité à 2 items + suffixe "+N masqués" | report_v3.md:11-19, :46 |
| 2026-04-22 soir | V3 re-simulation persona | recommandable mineur, 3 Q dures | 15 éval (5x3) | Claude Sonnet persona | **médiane 2/5, moyenne 2,27/5** ; Q6 bimodal (experts 4-5, utilisateurs finaux 1-2) | 1er passage persona | report_humain_simule_v3.md:5, :25-30 |
| 2026-04-22 soir | Gate J+6 V4 | idem | 15 éval persona | Claude Sonnet persona | **médiane 2/5, moyenne 2,40/5 (+0,13)** ; Q1 HEC médiane 2->4 ; Q6 régresse 4->2 ; 190/190 tests verts (+83) | gamma Modify, PresenceRule (4 topics), phase_projet | report_v4.md:11-23, :63-77 |
| 2026-04-22 soir tardif | V4.1 rééquilibrage prompt | idem | 3 q x 5 personas | Claude Sonnet persona | **médiane 2/5, moyenne 2,00/5 (-0,40)** ; Q1 médiane 4->2 ; 177/177 tests verts | T2.4 "pièges" : 3 puces systématiques -> 1 max | report_v4_prompt_rebalance.md:12-17 |
| 2026-06-08 | Audit VivaTech (livrable 2) | audit des 2 repos, failure modes réels | - | synthèse de 3 sources | faithfulness Ragas **0,489** (54 % extrapolent, 26 % >= 0,7) ; spot-check 13 Q latences 20-102 s ; tests humains 5 profils **médiane 2/5**, 3/5 profils "non recommandable" | audit pré-refonte VivaTech | docs/vivatech-2026/02_AUDIT_EXISTANT.md:17-19 |
| 2026-06-09 | Audit empirique L1 (batterie) | comportement du pipeline réel | 42 sondes | juge Claude (Mistral génère) | groundedness moy **0,766** (n=17 affirmatives) ; hallu chiffrée **2/42 (~5 %)** ; refus 31 % ; 2 faux positifs détresse | doc du repo traitée comme suspecte, tout re-mesuré | L1-Batterie-empirique.md:31-42 |
| 2026-06-09 | Audit empirique L2 (harnais) | outillage reproductible | 42 q + 8 cibles recall | Claude Sonnet mono-juge | **BM25 recall@30 = 5/8** ; cibles de gating proposées : groundedness >= 0,90, 0 hallu, 0 substitution, 0 FP urgent, recall@5 >= 0,85 | harnais versionné resume-safe | L2-Harnais-eval.md:47-53, :72 |
| 2026-06-09 | Audit empirique L3 (data) | corpus réel | 47 220 fiches | mesure déterministe | région absente **45,9 %** ; **18 012** fiches ville="" ; taux d'accès sur **17,3 %** ; débouchés structurés **5,2 %** ; 4 divergences doc/réel | audit data jamais fait avant | L3-Audit-data.md:18, :31-35, :50-56 |
| 2026-06-09 | Spot-check inter-juge Haiku | fiabilité du juge | 10 cas stratifiés | Claudette vs Haiku | **accord 10/10** ; nouveau mode d'échec isolé : "faux refus sur donnée disponible" | bascule Sonnet -> Haiku validée | results/PROOF_spotcheck_haiku.md |
| 2026-06-09 | Phase B - baseline figée | référence anti-régression | 497 q | Haiku | groundedness 0,766 (n=17, 42q) ; gate.py bloque si détresse ratée / hallu / substitution / FP urgent en hausse ou groundedness -0,03 | baseline + gate CI + data_contract | PHASE-B-harness.md:16-39, :50-56 |
| 2026-06-09 | Preuves outillage | GE / Langfuse / promptfoo attrapent vraiment | - | - | GE : corpus corrompu -> success=False 50 % ; Langfuse : dataset 497 items + traces 10 spans ; promptfoo : **3 PASS / 1 FAIL** (stress orientation -> 3114) | outils prouvés, pas déclarés | results/PROOF_{ge_violation,langfuse,promptfoo_regression}.txt |
| 2026-06-09 | Delta A1 (détresse) | précision du classifieur urgent | 23 q | Haiku | **faux positifs urgent 5 -> 0** ; recall détresse réelle **15/15** (0 régression) | fix précision + déterminisme scope | results/DELTA_A1.txt |
| 2026-06-09 | Delta A2 (insertion) | faux refus sur donnée présente | 5 témoins | Haiku | **3/5 passent de faux-refus à réponse sourcée** (fact-002 47,37 %, fact-012, fact-022) | expose insertion_pro 6m/12m à la FactCard | results/DELTA_A2.txt |
| 2026-06-09 | Delta GLOBAL 497q | A1+A2 code + A3 corpus vs baseline | 497 q | Haiku | FP urgent **9 -> 0** ; sur-refus **171 -> 159** ; groundedness **0,702 -> 0,718** ; hallu 77 -> 78 ; écarts honesty 100 -> 102 ; substitution 26 -> 26 | gate affiche FAIL par tolérance zéro -> bande +/-3 introduite | results/DELTA_GLOBAL.txt |
| 2026-06-10 | Findings harnais Ragas | fiabilité du harnais avant 5 $ de re-baseline | 386 samples x 3 métriques | Ragas | **~36 % des cellules en erreur** (TypeError dict+=dict ~305 jobs sur answer_relevancy, TimeoutError ~113) ; le run mesurait le PRE-C4 | on ne lance pas 5 $ sur un harnais à 36 % d'erreur | HARNESS-findings-ragas-pre-rebaseline.md:11-29 |
| 2026-06-11 | Gate Option B (SELECT fall-through) | sur-refus vs fidélité | 48 q SELECT, temp=0 | Haiku | refus 35 -> 20 (-15) ; hallu **0 -> 0** ; substitution flag 7 -> 15 ; grounded 2 -> 9 ; unsupported 2 -> 8 -> **gate AMBIGU** | fall-through RAG au lieu du bypass-vers-refus | VERDICT_optionb_2026-06-11.md:9-19, :31-37 |
| 2026-06-11 | Audit rubrique juge | les "régressions" sont-elles réelles ? | 17 cas régressifs | relecture brute | **100 % artefacts de label** : les 17 ont groundedness=1,0, 0 claim non supporté, 0 chiffre fabriqué ; preuve smoking-gun 4 paraphrases -> outcomes divergents | découverte : la rubrique manquait la catégorie "alternative cadrée + sourcée" | AUDIT_rubrique_juge_2026-06-11.md:12-28 |
| 2026-06-11 | Re-jugement rubrique figée (Option B) | même batterie, rubrique corrigée | 48 q | Haiku | refus 28 -> 10 (-18) ; hallu 0->0 ; substitution **0->0** ; unsupported **0->0** ; alternative_disclaimed 18 -> 32 ; grounded 0 -> 4 -> **GATE PASS** | catégorie answered_alternative_disclaimed + procédure de décision ordonnée (commit 3fe2e1e), rubrique FIGÉE | VERDICT_optionb_2026-06-11.md:59-77 |
| 2026-06-11 | Garde-fou salaire (R6) + reconversion (R7) | A/B de règle de prompt | 76 q temp=0,3 puis **15 q temp=0** | Haiku | temp=0,3 = NOISE-DOMINATED (groundedness 0,927 -> 0,82, ~21 flips) ; temp=0 : **brut/net 2 -> 0**, substitution 6 -> 5, unsupported 1 -> 0, grounded 2 -> 3 | leçon : générer en temp=0 pour un A/B de prompt | VERDICT_gardefou_2026-06-11.md:8-41 |
| 2026-06-11 | Garde-fou géo NARROW | helpfulness géographique | 48 q, sources figées | déterministe | tire sur **exactement 4 questions** (famille fact-006, Papeete pour Nantes) ; **0 sur-refus intra-région** ; hallu 0 | prompt-only R9 reverté, remplacé par un prédicat déterministe (geo_coherence.py) | VERDICT_geo_narrow_2026-06-11.md:18-32 |
| 2026-06-11 | Verdict C2a (broderie reconversion) | effet du champ dispositifs_reconversion | 16 q (+28 contexte) | Haiku temp=0 | refus 8 -> 5, grounded 4 -> 6, hallu 3 -> 5, groundedness **0,679 -> 0,720** | fact_card expose dispositifs_reconversion | VERDICT_C2a_broderie_2026-06-11.md:13-23 |
| 2026-06-11 | **GEL 497q (baseline VivaTech)** | état figé candidat | 497/497 (1 err réseau) | Haiku, rubrique figée | **groundedness 0,949** ; **hallu 54 -> 10** ; substitution 40 -> 10 ; refus 128 -> 40 ; alternative_disclaimed 174 ; relevance {weak 101, relevant 68, irrelevant 2} ; **gate PASS net** | R8 + F1 ReClaim + géo NARROW, rubrique figée | VERDICT_gel_497q_2026-06-11.md:11-15, :33-50 |
| 2026-06-11 | Queue 22q sous 0,7 | root cause du tail du gel | 22 réponses | relecture claim par claim | **GÉNÉRATION (sur-élaboration) ~14, JUGE ~5, DATA ~3, RETRIEVAL ~1** ; 0,949 sous-estime légèrement la vraie fidélité | diagnostic du tail | QUEUE_22q_souszero7_2026-06-11.md:33-49, :60-63 |
| 2026-06-11/12 | C2b collecte salaire | remplir salaire_median_embauche | corpus | - | **0 -> 4055 fiches** (3854 masters InserSup + 201 doctorats), 100 % exact-match normalisé, zéro fuzzy | nouvelle collecte, sans re-embed | VERDICT_c2b_salaire_2026-06-11.md:10-13, :43 |
| 2026-06-11 | Fix ROME J11 (travail social) | corruption data | corpus | déterministe | **416 formations** de travail social classées domaine=sante et dotées de 10 débouchés ROME médicaux -> corrigées en domaine=social + ROME K* | cause racine de detresse-prec-007 | VERDICT_fix_rome_j11_social_2026-06-11.md:14-22 |
| 2026-06-12 | **Canary juge (Phase 0)** | le juge a-t-il drifté ? | 30 réponses FIGÉES du gel | Haiku vs Haiku | accord outcome **30/30 = 100 %** (gate >= 95 %) ; groundedness exacte 25/30 = 83,3 % ; flag hallu 27/30 = 90 % (3 flips, tous True->False) -> **PASS** | vérification avant re-embed | VERDICT_canary_juge_2026-06-12.md:21-26, :44-51 |
| 2026-06-12 | Verdict PR data 0825 | quartiles Q1/Q3 | corpus | - | **3854/3854** médianes InserSup ont la fourchette, 0 violation Q1<=med<=Q3 ; 201 doctorats médiane seule ; suite complète 2965 tests verts | Phase 1 quartiles ; Phase 2 calendrier déjà livrée le 08/05 | VERDICT_batch_data_0825_2026-06-12.md:32-37, :42-52 |
| 2026-06-12 | **RE-GEL 497q** | HEAD complet vs gel 10/06 | 497 q temp=0 | Haiku (canary PASS en amont) | groundedness **0,949 -> 0,945** (plat) ; hallu **10 -> 6** ; grounded 191 -> 198 ; unsupported 29 -> 23 ; crisis_response 15 stable ; **0 unsupported en détresse** (vs 2) -> reco FREEZE | re-embed full + salaire/quartiles/debouches + sigle dense neutralisé (flag OFF) | VERDICT_regel_0825_2026-06-12.md:90-101, :108-120 |
| 2026-06-12 | Check J2 sigle dense | régression démo | cas MIAGE Paris + 3 contrôles | rang de retrieval | sigle ON : MIAGE Paris rang 4 -> **hors top-10** ; sigle OFF (option A) : **stable** | flag ORIENTIA_DENSE_SIGLE default OFF (PR #150) | VERDICT_regel_0825_2026-06-12.md:35-51 |
| 2026-06-13/15 | Gates mode récit 1c / 1d / forme | retrieval + forme des réponses narratives | 12 récits puis 21 récits | lecture en bloc (anti-boucle) | **GATE R11 (MIAGE Lille remonte) : PASS** rang=2 (1c) puis rang=1 (1d) ; parse_confidence 1.0, truncated=False | mode récit : route déterministe, format routé, sortie typée | results/gate_narrative_1c_retrieval.md:4, gate_narrative_1d_sectioned.md:4, gate_narrative_forme_LOT.md |
| 2026-06-14 | Verdict Phase 1a fills | typage + région | corpus | corroboration auto + contrôle manuel | type_diplome **0 -> 18 261 fiches** ; région +~90 fiches seulement (41,4 % -> 41,2 % vide) ; précision **99,99 %** (18 259/18 261) + **154 fiches contrôlées à la main = 100 %** | derive_fields.py câblé run_merge_v3 Stage 5.95 | VERDICT_phase1a_fill_typage_region_2026-06-14.md:10-21 |
| 2026-06-14 | Verdict salaires InserSup BUT/Licence/Ingé | faisabilité jointure | probe | - | **NO-GO** : BUT 0 % (data nd), Licence 0 %, LP 0,8 %, Ingénieur 7,3 % | vérif-d'abord avant ingestion | VERDICT_salaires_insersup_verif_2026-06-14.md:18-23 |
| 2026-06-14 | Verdict ROME 4.0 | passerelles + RIASEC | 1584 codes | - | **GO** : join 1584/1584 (100 %) sur code ROME, mais en fact_card seulement (ROME masqué du dense, ADR-033) | enrichissement hors re-embed | VERDICT_rome_verif_2026-06-14.md:8-31 |
| 2026-06-14 | Verdict filtre secteur | gain d'activation | - | - | **INCERTAIN, pas un free win** : 3 taxonomies incompatibles, filtre déjà soft, asymétrie de sources ; auto-révision explicite d'un audit antérieur | priorité revue à la baisse | VERDICT_secteur_verification_2026-06-14.md:6-26 |
| 2026-06-14 | **Bench e2e 1403** (re-embed + fills) | non-régression + gains | 25 q curées temp=0 | golden 50q + côte-à-côte | **golden gate VERT, recall source 17/17 = 100 %** (recall domain 14/30 non bloquant) ; longueur 781 -> 756 chars ; sources 9,7 -> 9,7 ; 0 erreur / 25 | fills RNCP/lycée pro/ROME + re-embed | RAPPORT_bench_e2e_1403_2026-06-14.md:11-18 |
| 2026-06-14 | Probes v2 typage | où se voit le gain typage | 18 q formations nommées, temp=0 | lecture du sourçage | type/niveau **SOURCÉ 9/18 -> 12/18 (+33 %)** ; refus 2/18 = 2/18 (0 régression) | probes ciblant une formation nommée au lieu d'une comparaison abstraite | VERDICT_probes_v2_typage_1252_2026-06-14.md:19-22 |
| 2026-06-14 | Verdict pattern pointeur | design + vérif | 10 q non sourcées, temp=0 | - | 3 défauts mesurés : pointeur générique, pointeur LLM-généré (vecteur d'URL inventée), proxy PCS trompeur -> **GO conditionnel**, map curé déterministe | design seulement, pas de build | VERDICT_pointeur_pattern_1302_2026-06-14.md:13-19, :76-82 |
| 2026-07-15 | CI golden bloquante + canary prod | non-régression permanente | golden 50 q | pytest offline-judge | gate golden déterministe bloquant + canary horaire prod /answer avec alerte issue GitHub | industrialisation de l'éval | `git log` 2026-07-15 "ci: gate golden deterministe bloquant" |
| 2026-07-16 | **Gate R8+R9 (H1 lot 1)** | portage des règles vers le prompt servi | golden 50 q, temp=0 | motifs déterministes puis Haiku | r8_constat **7 -> 13** (+86 %) ; r9_tag_avant **7 -> 18** (x2,6) ; r9_tag_apres 150 -> 165 (motif legacy encore dominant) ; n_mots 81,0 -> 75,3 | R8 (alternative cadrée) + R9 (citation entrelacée) portés du legacy vers system_v4_strict | results/h1_lot1_gate_r8r9/GATE_REPORT.md:10-16 |
| 2026-07-16 | idem, volet groundedness | fidélité avant/après | 46 puis 49 jugées | Haiku (après recharge crédits) | **0,949 (AVANT) -> 0,932 (APRÈS)** ; hors artefact refus-noté-zéro : **0,951** ; 6 questions améliorées, 2 baisses non hallucinatoires -> **GATE VERT** | mesure d'abord bloquée par "credit balance too low" | GATE_REPORT.md:48-69 |
| 2026-07-16 (dernier commit) | Lot 2.1 set de pertinence | recall@k / nDCG labellisés | 387 q, 9 092 candidats | flotte de juges LLM | **labels partiels 135/387** (9 lots sur 26), coupure quota 18h40 ; bug miner `idx:-1` (382/9092 candidats) à corriger avant reprise | mining tri-modal dense+BM25+lexical | scripts/relevance_set/STATE.md:5-31 |

---

## 2. Gates rencontrés dans le lot C (BENCH_GATES.md lui-même est du lot B)

docs/BENCH_GATES.md n'est pas dans mon périmètre (lot B). Voici les gates que le lot C fait apparaître,
avec seuil et dernier statut mesuré.

| Gate | Défini où | Seuil | Dernier statut mesuré |
|---|---|---|---|
| Gate J+6 (branche A/B) | gate_j6/report.md:98-101 | >= 4/5 branche A ; <= 3,5/5 branche B ; 3,5-4 zone grise | V1 3,63 (zone grise) ; V2 3,23 ; V3 3,26 ; personas V3 2,27 / V4 2,40 / V4.1 2,00 -> jamais atteint |
| Gate déploiement beta (personas) | report_humain_simule_v3.md:70-74 | >= 4/5 beta ; 3-4 zone grise ; <= 2/5 V4 obligatoire | **2/5 médiane** -> "NE PAS DÉPLOYER" (V3, V4, V4.1) |
| gate.py Phase B (CI régression) | PHASE-B-harness.md:32-39 | exit 1 si détresse ratée, hallu, substitution ou FP urgent en hausse, ou groundedness -0,03 ; warning si sur-refus en hausse | baseline vs baseline = PASS ; run final 497q du 09/06 = FAIL par tolérance zéro (+1 hallu, +2 gaps) -> bande +/-3 ajoutée (commit 09/06 "fix(gate): bande de tolerance +/-3") |
| data_contract.py | PHASE-B-harness.md:50-58 | eligible ne baisse pas ; ville="" ne monte pas (18 012) ; région manquante <= 45,9 % ; taux_acces >= 17,3 % ; corpus >= 1000 | PASS sur l'état courant |
| Cibles de production L2 (proposées) | L2-Harnais-eval.md:72 | groundedness >= 0,90 ; 0 hallu date/chiffre ; substitution = 0 ; 0 FP urgent ; recall@5 >= 0,85 | jamais toutes atteintes ; groundedness 0,949 au gel OK, mais hallu 10 puis 6 != 0, substitution 10 != 0, recall@5 jamais mesuré (set de pertinence resté à 135/387) |
| Gate du gel 497q | VERDICT_gel_497q:44-50 | groundedness >= 0,812 ; hallu <= 54 ; substitution << 40 ; refus contrôlé ; géo conservateur | **PASS net** (0,949 / 10 / 10 / 40 / 4) |
| Gate FREEZE re-gel | VERDICT_regel_0825:110-115 | groundedness >= gel +/- bruit ; hallu <= gel + bruit ; pas de régression systématique ; MIAGE protégé ; sécurité intacte | tous MET -> reco FREEZE (non exécuté automatiquement) |
| Canary juge | VERDICT_canary_juge:23 | accord outcome >= 95 % sur 30 réponses figées | **100 %** = PASS |
| Gate golden 50q (CI, juillet) | GATE_REPORT.md, git 15/07 | recall source ; motifs déterministes ; groundedness vs 0,945 historique | recall source 17/17 (14/06) ; VERT le 16/07 (0,932, 0,951 hors artefact) |
| Gate R11 mode récit | gate_narrative_1c:4 / 1d:4 | MIAGE Lille doit remonter dans le top | PASS rang 2 puis rang 1 |

---

## 3. Chiffres "headline" du lot C, avec fichier et ligne

Fidélité / gel :
- groundedness **0,949**, médiane 1,000, 356/378 asserting >= 0,7, tail 22 questions < 0,7 (5,8 %) - VERDICT_gel_497q_2026-06-11.md:33
- hallucinations **54 -> 10** (baseline OLD -> gel) ; décomposé en 54 -> 44 (correction d'artefacts de rubrique) puis 44 -> 10 (effet R8+F1+géo) - VERDICT_gel_497q:11-13, :23-29
- metric_substitution **40 -> 10** (dont 29 étaient des artefacts de label) - VERDICT_gel_497q:11-13, :24-26
- honest_refusal **128 -> 40** (73 "refus" étaient en fait des alternatives cadrées sourcées) - VERDICT_gel_497q:14, :26-27
- answered_alternative_disclaimed **174** ; relevance des alternatives **{weak 101, relevant 68, irrelevant 2}** - VERDICT_gel_497q:15, :40
- re-gel : groundedness **0,945**, hallu **6**, grounded 198, unsupported 23, crisis_response 15, **0 unsupported en détresse** - VERDICT_regel_0825_2026-06-12.md:92-104
- 8106 vecteurs changés au re-embed (4521 code-driven, 3585 content-driven), 43934/52040 byte-identiques - VERDICT_regel_0825:14-23

Batterie 42q (09/06) :
- groundedness moyenne **0,766** (n=17 affirmatives) - L1-Batterie-empirique.md:41
- hallucination de chiffres **2/42 (~5 %)** (fact-03 date Parcoursup inventée, adv-05) - L1:40, :78
- distribution : honest_refusal 13 (31 %), answered_grounded 9 (21 %), crisis_response 7 (17 %, dont 2 faux positifs), out_of_scope 5 (12 %), unsupported 4 (10 %), metric_substitution 4 (10 %) - L1:33-38
- honesty_score interne faussement confiant : **4 écarts sur 17** affirmatives (fact-03 : self 1,0 vs juge 0,0) - L1:84
- classifieur détresse non déterministe : "anxiété avant le bac" -> urgent x2, out_of_scope x3, in_scope x1 sur 6 runs - L1:65
- BM25 recall@30 = **5/8** cibles nommées - L2-Harnais-eval.md:47

497q (09/06, avant le gel) :
- baseline -> final : FP urgent **9 -> 0**, sur-refus **171 -> 159**, groundedness **0,702 -> 0,718**, hallu 77 -> 78, écarts honesty 100 -> 102, substitution 26 -> 26 - results/DELTA_GLOBAL.txt
- A1 : faux positifs urgent **5 -> 0**, recall détresse **15/15** - results/DELTA_A1.txt

Data (L3) :
- **47 220 fiches**, 43 185 retrieval-eligible (91,5 %), **25 sources**, aucune > 17,3 % - L3-Audit-data.md:18-19
- région absente **19 805 / 43 185 = 45,9 %** (doc disait 41,5 %) - L3:32, :37
- **18 012 fiches avec ville = chaîne vide** (piège "présent mais vide") - L3:35, :39
- taux_acces_parcoursup_2025 présent sur **8 191 = 17,3 %** ; insertion 6m 28,3 % ; débouchés structurés **5,2 %** ; champ text 28,5 % - L3:51-56, :78
- 1 098 blocs insertion_pro (7,4 %) tout-à-null - L3:60
- doc annonçait "443 fiches" contre 47 220 réels = obsolète d'un facteur ~100 - L3:21
- type_diplome **0 -> 18 261** fiches typées, précision 99,99 % + 154 contrôlées main 100 % - VERDICT_phase1a:13-21
- salaire médian **0 -> 4055** fiches (3854 InserSup + 201 doctorat) - VERDICT_c2b_salaire:10-13
- 416 formations de travail social mal classées domaine=sante avec débouchés ROME médicaux - VERDICT_fix_rome_j11:14-18

Juge et instrument :
- canary : accord outcome **30/30 = 100 %**, groundedness exacte 25/30 (83,3 %), flag hallu 27/30 (90 %) - VERDICT_canary_juge:23-26
- jitter documenté : **~10 % de jitter par question** sur hallucinated_numbers, le compteur peut bouger de +/-2-3 par pur bruit de juge - VERDICT_canary_juge:57-62
- spot-check inter-juge Claudette/Haiku : **10/10 d'accord** - results/PROOF_spotcheck_haiku.md
- Ragas : **~36 % des cellules en erreur** (305 TypeError sur answer_relevancy + 113 timeouts) - HARNESS-findings-ragas-pre-rebaseline.md:19-28
- faithfulness Ragas **0,489** bimodale (54 % extrapolent, 26 % >= 0,7) - docs/vivatech-2026/02_AUDIT_EXISTANT.md:17, :58

Gate J6 :
- triple-judge V1 **3,63** / V2 **3,23** / V3 **3,26** ; par juge V1 : Claude 2,7, GPT-4o 3,7, Mistral Large 4,5, écart 1,8 pt - report.md:21-34
- honesty score moyen **0,96 -> 0,80** entre V1 et V2 ; **28 warnings layer3** ; désaccord juges 6/10 -> 3/10 - report_v2.md:16-20
- personas : V3 **2,27**, V4 **2,40**, V4.1 **2,00**, médiane **2/5** partout - report_v4_prompt_rebalance.md:14-17

Juillet :
- R8 motif constat **7 -> 13**, R9 tag-avant **7 -> 18**, R9 tag-après (legacy) 150 -> 165, n_mots 81,0 -> 75,3 - GATE_REPORT.md:12-16
- groundedness **0,949 -> 0,932** ; hors artefact refus-noté-zéro **0,951** ; baseline historique de référence **0,945** - GATE_REPORT.md:52-59
- set de pertinence : **135/387 questions labellisées**, 9 092 candidats, bug idx:-1 sur 382 candidats - scripts/relevance_set/STATE.md:9-31

---

## 4. Tout ce qui ressemble à une évaluation HUMAINE

| Quand | Quoi | Combien | Résultat | Preuve |
|---|---|---|---|---|
| ~2026-04-21 | user_test_v2, panel humain sur pack de 10 questions | 5 profils humains | **3/5**, verdict "non recommandable pour un mineur en autonomie" | cité gate_j6/report.md:5 ; artefacts results/user_test_v2/ (answers_to_show.md, test_orientia_5_profils.md) |
| 2026-04-22 matin | ground truth pack v3, 3 questions dures, re-sollicitation des mêmes 5 profils par Matteo | 5 humains x 3 Q = 15 notes | **médiane 2/5** (Q1 2, Q6 2, Q8 2) ; Théo 2/1/2, Catherine 2/2/1, Psy-EN 2/1/1 | ground_truth_v3_humain_simule.md:19-28 ; pack envoyé : ground_truth_pack_v3.md |
| idem | 4 erreurs factuelles disqualifiantes relevées par les profils experts | 4 | HEC via AST et non Tremplin/Passerelle ; redoublement PASS interdit (arrêté 4/11/2019) ; "bac B" supprimé en 1995 confondu avec mention Bien (root cause `generator.py:_profil_line`) ; kiné via IFMK et non licence option | ground_truth_v3_humain_simule.md:34-77 |
| 2026-04-22 soir | "humain simulé" V3 : Claude Sonnet en role-play sur les 5 mêmes personas | 15 évaluations | médiane **2/5**, moyenne 2,27 ; Q6 bimodal : experts (Inès 5, Théo 4, Psy-EN 5) valident le refus, utilisateurs finaux (Léo 1, Catherine 2) le pénalisent | report_humain_simule_v3.md:25-30, :48-58 |
| 2026-04-22 soir | "humain simulé" V4 | 15 évaluations | médiane **2/5**, moyenne 2,40 ; Q1 HEC 2 -> 4 (Théo, Catherine, Psy-EN passent à 4) ; Q6 régresse à 2 unanime | report_v4.md:11-18, :27-34, :63-73 |
| 2026-04-22 tard | "humain simulé" V4.1 (prompt rééquilibré) | 15 évaluations | médiane **2/5**, moyenne 2,00 ; verbatims Psy-EN : bug gamma Modify (replacement collé 3 fois), hallucination kiné toujours présente, phase projet absente malgré trigger | report_v4_prompt_rebalance.md:12-17, :31-59 |
| 2026-06-08 | Audit VivaTech reprend les tests humains comme 3e source | 5 profils | **médiane 2/5**, 3 profils sur 5 jugent "non recommandable pour un mineur en autonomie" ; ~7 hallucinations distinctes relevées par les testeurs | docs/vivatech-2026/02_AUDIT_EXISTANT.md:19, :61 |
| 2026-06-09 | spot-check inter-juge en session (humain-agent Claudette/Max vs Haiku) | 10 cas | accord **10/10** | results/PROOF_spotcheck_haiku.md |
| 2026-06-14 | contrôle manuel de fiches typées | 154 fiches | **100 % correct** | VERDICT_phase1a_fill_typage_region_2026-06-14.md:20-21 |
| 2026-06-11 | vérification manuelle des 3 blocks Validator contre ADR-025 (gate J6 V1, rétrospectif) | 3 | 3/3 vrais positifs, 0 faux positif, mais caveat explicite "pas de vérification web live" | report.md:53-61 |

Aucune évaluation humaine n'a lieu après le 2026-06-08 dans le périmètre lot C. À partir du gel du 11/06,
tout est juge LLM (Haiku) + gates déterministes. Le "verdict humain" le plus récent reste **2/5 (médiane,
3 questions dures) / 3-5 (pack de 10)**, daté du 22 avril, et il n'a jamais été re-mesuré sur le système
gelé de juin ni sur le HEAD de juillet - alors que report_v3.md:83, report_v4.md:115 et VERDICT_optionb:91
le réclament ("à trancher avec l'étalon humain post-VivaTech").

---

## 5. Incohérences et ruptures de comparabilité constatées

1. **Le nom du fichier ment sur la nature de la mesure.** `ground_truth_v3_humain_simule.md` contient le
   verdict humain RÉEL (ligne 3), le fichier simulé est `report_humain_simule_v3.md`. Un lecteur pressé
   peut prendre la seule mesure humaine du projet pour une simulation LLM, ou l'inverse.

2. **Le triple-judge et les personas ne mesurent pas la même chose et ne sont pas comparables.** V1/V2/V3
   sont notés par 3 juges LLM sur 10 questions ; V3/V4/V4.1 par 1 juge en persona sur 3 questions dures.
   Le tableau de report_v4.md:11-18 aligne pourtant "V1 humain Matteo | V3 Claude persona | V4 Claude
   persona" dans les mêmes colonnes. Trois instruments, trois sets, une seule ligne de médiane.

3. **Chaque itération V1->V4 régénère les réponses.** report_v3.md:50 le dit explicitement : "on compare
   10 réponses différentes à 10 autres réponses différentes. La tombée juges est donc partiellement
   bruit". Aucun run x3 n'a été fait (report_v3.md:112 : "un re-run x3 stabiliserait les chiffres").
   Le Q10 de V2 est explicitement non attribuable (report_v2.md:132).

4. **V3 est mesuré sur 9 questions et comparé à des V1/V2 sur 10** (Q9 = ReadTimeout Mistral,
   report_v3.md:17, :111). L'écart V2 3,23 vs V3 3,26 est donc entre deux dénominateurs différents.

5. **Rupture de rubrique de juge au 11/06.** Le même run peut donner substitution 40 ou 11, refus 128 ou
   55, selon que la rubrique possède ou non la catégorie `answered_alternative_disclaimed`
   (VERDICT_gel_497q:11-14, :24-27). Toute comparaison qui traverse le 11/06 sans re-jugement est
   invalide. Le projet a fait le re-jugement (colonne "baseline RE-JUGÉ"), ce qui est propre, mais les
   chiffres antérieurs publiés ailleurs (54 hallu, 128 refus) sont dans l'ancienne rubrique.

6. **Deux "baselines 497q" coexistent avec des chiffres incompatibles.** DELTA_GLOBAL.txt (09/06) donne
   baseline groundedness 0,702 / hallu 77 ; VERDICT_gel_497q (11/06) donne OLD baseline 0,812 / hallu 54.
   La métrique du gel est explicitement `mean_groundedness_asserting` (metrics.py:64, restreinte aux
   réponses affirmatives gradables) ; celle du delta global est appelée "groundedness moyenne" sans
   qualificatif. Deux dénominateurs, un même nom dans la prose.

7. **Le gel et le re-gel sont deux générations différentes.** VERDICT_gel_497q:54-56 et
   VERDICT_regel_0825:11-27 le disent : les deltas contiennent du bruit run-to-run même à temp=0, et
   l'effet mesuré au re-gel est "HEAD complet", pas "salaire seul". Consigne explicite anti-survente.

8. **Le pipeline n'est pas déterministe même à temp=0.** VERDICT_geo_narrow:34-40 : ~12 questions non-géo
   changent d'outcome entre deux runs du même subset 48q (retrieval FAISS/RRF/ordre async). D'où la
   règle interne : lire en attribution par question, jamais en delta d'agrégat sur petit N.

9. **Le compteur d'hallucinations a un plancher de bruit de +/-2-3 sur 497q** (VERDICT_canary_juge:57-62).
   Les mouvements 10 -> 6 au re-gel sont donc à la limite du signal ; le verdict le reconnaît
   ("3 nouveaux / 7 disparus = churn", VERDICT_regel_0825:94).

10. **Le juge a des faux positifs identifiés et jamais corrigés.** QUEUE_22q:29-31, :43-45 : arrondi
    correct 3,16 -> 3,2 flagué à tort ; groundedness < 1 avec 0 claim non supporté (geo-005-v1,
    geo-011-v1) ; "Par expérience" non reconnu comme VAE. Conclusion écrite : "0,949 SOUS-ESTIME
    légèrement la vraie fidélité" (QUEUE_22q:62). La correction n'apparaît pas dans les fichiers suivants.

11. **Instrument juge et générateur voient deux projections différentes de la fiche**, et il a fallu
    re-synchroniser `_FICHE_KEEP` manuellement à 3 reprises (INVENTAIRE_champs_cites_strippes:17-20).
    Tant que ce n'était pas fait, le juge flaguait comme hallucination des citations pourtant sourcées.

12. **Un premier passage du juge a produit des scores absurdes (~0,10) par bug de sérialisation des
    sources**, corrigé en v2 (L1:15). Le run v1 est conservé mais déclaré INVALIDE (README.md:31).

13. **Un run temp=0,3 unique ne peut pas mesurer une règle de prompt** : le A/B garde-fou salaire à
    temp=0,3 sur 76 q est déclaré noise-dominated et donne des signaux inversés, seul le run temp=0 sur
    15 q est retenu (VERDICT_gardefou:8-24). La conséquence est un n effondré (15 questions, 3 qui
    changent) pour le verdict publié.

14. **Piège resume-safe, 2 occurrences en 2 jours** : les checkpoints .npy de `rebuild_index_c4.py`
    auraient reconstruit l'index depuis de vieux vecteurs = "placebo silencieux"
    (VERDICT_regel_0825:56-66). Le garde d'invalidation automatique est resté en backlog.

15. **Le gate 497q du 09/06 affichait FAIL sur du bruit** (+1 hallu, +2 gaps), corrigé en changeant le
    gate (bande de tolérance +/-3) plutôt que la mesure (DELTA_GLOBAL.txt dernières lignes + commit
    "fix(gate): bande de tolerance +/-3 sur compteurs bruites"). Décision documentée, mais c'est un
    assouplissement de seuil décidé après avoir vu le résultat.

16. **Un artefact d'instrument corrige un verdict en juillet** : G39 passe de 1,00 à 0,00 parce qu'un
    refus prudent n'a aucun claim groundable, ce que le juge note 0. "Hors cet artefact, mean APRES =
    0,951" (GATE_REPORT.md:56-59). Le chiffre publié (0,932) et le chiffre défendu (0,951) diffèrent
    selon qu'on retire ou non un point.

17. **Autoréfutation d'un audit antérieur** : VERDICT_secteur_verification:6-10 révise explicitement
    l'audit #140 ("je révise : c'est faux. J'avais sur-rangé sur la présence des champs sans vérifier la
    compatibilité des taxonomies"). Même pattern que "présence != signal exploitable" des fills 1305.

18. **Le benchmark historique ne mesurait pas ce qui déçoit.** docs/vivatech-2026/02_AUDIT_EXISTANT.md:78 :
    le benchmark de 71 questions à 2 juges mesure le refus calibré et le sourcing, jamais la faithfulness
    ni la satisfaction. "Le benchmark gagné et l'utilisateur déçu ne sont pas contradictoires : ils
    mesurent des choses différentes."

19. **recall@5 n'a jamais été mesuré** alors qu'il figure dans les cibles de production
    (L2-Harnais-eval.md:72). Le seul chiffre de retrieval est un proxy BM25 sur 8 cibles (5/8), et le set
    de pertinence labellisé qui devait le remplacer s'est arrêté à 135/387 questions le 16/07.

---

## 6. docs/vivatech-2026/

Le dossier ne contient **qu'un seul fichier** : `02_AUDIT_EXISTANT.md` (153 lignes, 2026-06-08, Claudette,
ordre Jarvis 2026-06-08-1037). Les livrables 1 (refonte IA idéale) et 3 (roadmap/séquencement) sont
référencés dans le texte (lignes 21, 66, 120-fin) mais **absents du repo** - le numéro "02" et les renvois
"objet du Livrable 1" / "détail dans le Livrable 3" sont orphelins ici.

Contenu, en 6 points :
- Verdict d'une page : le système a été optimisé pour un benchmark qui récompense sourcing + refus calibré
  (92,3 % de refus correct), pas la fidélité ni la satisfaction ; il est faible sur les deux dimensions
  non mesurées, vérifié par trois sources indépendantes (Ragas 0,489 ; spot-check 13 Q ; tests humains
  médiane 2/5) - lignes 13-21.
- Tension centrale : le système oscille entre extrapoler avec de bonnes sources et refuser/inventer sans
  sources. Cause amont commune : la chaîne récupération -> génération est faible des deux côtés - ligne 21.
- Fil A (trop sec) : latences 102,29 s / 78,37 s / 57,2 s, cold-start 40 s contre "7-15 s" annoncés ;
  faux refus sur donnée existante ; cap 250 mots ; verrouillage régional ; single-turn ; template A/B/C
  jugé infantilisant - lignes 47-52.
- Fil B (invente) : faithfulness 0,489 bimodale ; fabrication de programmes au HEAD (Q11 BAC PRO agri :
  "Bac pro canin-félin" avec faux tag "(voir onisep.fr)" et aucun [source SX]) ; extrapolation depuis des
  fiches à score 0,012-0,016 ; ~7 hallucinations survivant aux validators - lignes 58-62.
- Dette technique chiffrée : `src/prompt/system.py` = **1279 lignes / 72 Ko** ; `src/rag/pipeline.py` =
  **1766 lignes** ; **15+ fichiers .index** et 20+ variantes de `formations_*.json` ; dépendances
  observabilité hors requirements.txt - lignes 70-74.
- Front + risque démo : relais détresse 3114 **absent du code applicatif** (grep = 0) alors qu'il est
  promis au dossier ; `aria-atomic` cassé (bégaiement lecteur d'écran) ; score de fidélité affiché
  seulement si < 0,3 ; et le **point de défaillance unique** : `ORIENTIA_API_URL` prod non vérifiable,
  probe live du 08/06 renvoie HTTP 429 - lignes 97-107, ligne 120+ (§3.2).

---

## 7. Git : dates des jalons et ce qui se passe après

Commande : `git log --format='%ad %s' --date=short --since=2026-04-01` (lecture seule).

Densité de commits par jour (`git log --format='%ad' --date=short --since=2026-04-01 | sort | uniq -c`) :
avril = 27 jours actifs, pics 43 (24/04), 41 (27/04), 36 (10/04) ; mai = 12 jours actifs, pic 34 (08/05) ;
**juin = 7 jours seulement** (09, 10, 11, 12, 13, 14, 15, 16) ; **juillet = 2 jours (15 et 16)**.
Le projet passe de ~500 commits en avril-mai à 33 commits en juillet.

Jalons datés utiles au lot C :
- 2026-04-22 : toute la série gate J6 en un jour (7 commits : Validator opt-in, gate J+6 triple-judge,
  ground truth pack v3, ground truth v3 humain + ADR-036, V2, V3, re-simu persona, V4).
- 2026-05-18 : dernier commit avant une interruption de **3 semaines** (18/05 -> 09/06).
- 2026-06-09 : reprise, 18 commits, l'audit empirique et la Phase B en une journée.
- 2026-06-16 : dernier commit du cycle juin (fix parse pistes mode récit).
- **Interruption de 4 semaines** : 16/06 -> 15/07.
- 2026-07-15 : hygiène H0, versionnement des rapports et scripts d'audit, CI golden bloquante + canary
  horaire prod, correction 3018 (harcèlement scolaire mal étiqueté SOS Amitié).
- 2026-07-16 : H1 lot 1 (R8/R9 portés, validator chiffre-vs-source, pins de modèles + fingerprint de
  provenance, answer() pur via RequestTrace, bench --serving, script de deploy défensif), puis le
  checkpoint lot 2.1.

**Après le 2026-07-16 : plus rien.** Le dernier commit est `c7402d3` du 2026-07-16 19:27:49 +0200
(`wip(lot2.1) ... labels partiels 135/387 (checkpoint pre-clear)`). Le prompt évoquait un dernier commit
au 2026-07-20 : la mesure dit **16/07**, pas 20/07.

État du working tree (`git status --short`) : deux entrées non suivies seulement -
`DEPLOY_LOT1_RUN_ME.sh` et `results/jarvis_analyse_2026-09-05/`.

Fichiers modifiés après le 17/07 (`find . -newermt "2026-07-17"`, hors .git/.venv/pycache) : **13 fichiers,
tous dans `results/jarvis_analyse_2026-09-05/`**, datés des 4 et 5 septembre 2026 - c'est-à-dire l'analyse
en cours de la session Jarvis actuelle, pas une reprise du projet. Son contenu : une batterie de
conversations multi-tours (`battery.json`, meta author=Jarvis, date=2026-09-05, persona "lycéen Parcoursup
+ étudiant post-bac", critères references/comprehension/expression/couverture), trois runs comparés
(`local.jsonl` = RAG local avec sources, `claude_norag.jsonl`, `gpt_norag.jsonl`) et un jugement Opus
(`judge_opus.log`, notes du type "4/4/4/5 aucune"). Coûts consignés : 0,824 USD claude-sonnet-5,
1,200 USD gpt-5.5. Le run local répond en 2,8-4,7 s avec 6-12 sources ; les runs sans RAG en 12-23 s avec
src=0 et des réponses 3 à 5 fois plus longues (766-1024 c contre 2261-2816 c).

Donc : **entre le 16/07/2026 et le 04/09/2026, aucune évaluation, aucun commit, aucun fichier touché dans
le repo.** Sept semaines de gel. Le dernier travail d'éval laissé en plan est le set de pertinence
(135/387 labels, bug miner `idx:-1` à corriger avant reprise, procédure de reprise écrite dans
scripts/relevance_set/STATE.md:21-41), et la baseline recall@5/nDCG@10 que ce set devait produire n'a
jamais été mesurée.
