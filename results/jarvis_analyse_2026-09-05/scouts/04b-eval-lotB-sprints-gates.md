# LOT B - Sprints 1-12, gates, audits Phase 0, spot-checks, observabilite, ADR

Racine `R = /home/matteo_linux/projets/OrientIA`. Lecture seule, aucun fichier du repo modifie.
Continuite avec le lot A (`04a-eval-lotA-chronologie.md`) : le lot A s'arrete au bench Sprint 7 du 27/04 ;
ce lot reprend a la bascule agentique du 26/04 et va jusqu'a la Phase D du 11/05 et l'observabilite du 14/05.

## 1. Tableau chronologique (lot B)

| Date | Jalon | Ce qui est mesure | Set (n) | Juge / instrument | Metrique + resultat | Ce qui a change | Preuve |
|---|---|---|---|---|---|---|---|
| 2026-04-18 | user_test_v2, pack 5 profils | qualite percue des reponses | 10 q x 5 profils | Humains (Leo 17, Sarah 20, Thomas 23, Catherine 52, Dominique 48), grille clair/utile/confiance x /5 | pas d'agregat chiffre dans le repo ; verbatims par question | Tier 2.5 pack | `R/results/user_test_v2/test_orientia_5_profils.md:1-25` ; commit e172a6e |
| 2026-04-22 | user_test v1 (3 feedbacks archives) | idem | 10 q x 3 profils (17/20/23 ans) | Humains | notes /5 par question, pas de moyenne calculee | script `prepare_user_test_pack.py` ("2-3 lyceens") | `R/results/user_test/feedback_17ans.md`, `_20ans`, `_23ans` ; commit 8d54847 |
| 2026-04-26 apres-midi | Sprint 1 ProfileClarifier MVP (ADR-051) | extraction de profil par function-calling | 15 q integration (sous-ensemble baseline) | aucun juge, match sur verite attendue | success technique 15/15 ; age group 5/6 (83 %) ; intent type 7/12 (58 %) ; region 2/2 ; latence 2,0 s | 1er tool agentique, Mistral Large function-calling | `R/docs/SPRINT1_PROFILE_CLARIFIER_VERDICT.md:18-34` |
| 2026-04-26 fin AM | Sprint 2 QueryReformuler | decoupage en sous-requetes | 12 q integration + audit enum 48 q | aucun (comptages) | 12/12 success, 4,4 sous-requetes/q, 10 corpora distincts ; enum 95,8 % clean (46/48) ; latence cumulee 13,97 s/q | 2e tool ; bench Medium vs Large -> KEEP Large (marge 1,30x) | `R/docs/SPRINT2_QUERY_REFORMULER_VERDICT.md:13-38` |
| 2026-04-26 fin AM | Sprint 3 FetchStatFromSource + optims latence | verification de claim + latence | bench latence sur 5 appels | aucun | cache profil 2,09 s -> 0,0001 s (x20 890) ; fact-check parallele 19,11 s -> 8,85 s (x2,16) | 3e tool, LLM-as-fact-checker Mistral Large | `R/docs/SPRINT3_FETCH_STAT_AND_LATENCY_VERDICT.md:19-30` |
| 2026-04-26 fin journee | Sprint 4 pipeline agentique end-to-end | fact-check des claims + latence | 48 q, single run | FetchStatFromSource (Mistral Large, LLM-judge strict) | 48/48 success ; 220 claims : 6,8 % supported, 2,7 % contradicted, 77,7 % unsupported, 12,7 % ambiguous ; latence 39,87 s (vs 12,35 s baseline, x3,2) | pipeline agentique complet ; 213 sous-requetes sur 10 corpora | `R/docs/SPRINT4_AGENT_VS_BASELINE_VERDICT.md:77-107` |
| 2026-04-26 fin journee | Sprint 5 apples-to-apples + audit qualitatif | verified/halluc sur le MEME fact-checker que la baseline | 24 q balanced x 3 runs (IC95) | StatFactChecker des deux cotes ; audit des causes par Claude Sonnet 4.5 (n=20) | verified 23,0 % +-19,73pp vs baseline 39,4 % +-3,66pp = **-16,4pp** ; halluc 17,7 % +-27,85pp vs 17,9 % (-0,2pp) ; latence 23,12 s (+10,8 s) ; causes : 60 % sources insuffisantes, 40 % LLM hallucine, 0 % juge trop strict | serialisation des sources pour rejouer StatFactChecker | `R/docs/SPRINT5_APPLES_TO_APPLES_VERDICT.md:29-33,40-44,90-110,175-195` |
| 2026-04-27 | Sprint 6 enrichissement corpora 5 axes | idem | 24 q x 3 | StatFactChecker | verified 23,4 % +-8,89pp (+0,4pp vs Sprint 5, dans le bruit) ; halluc 16,2 % +-16,41pp (-1,5pp) ; latence 25,74 s ; gap vs baseline -16,0pp | +1 792 cells, index Phase E 56 089 vecteurs | `R/docs/SPRINT6_VERDICT.md:90-107` |
| 2026-04-27 | Sprint 6, decomposition per-axe (correlationnelle) | contribution par axe | 24 q x 3 = 72 paires | idem | axe 3b Inserjeunes 14/72 actif, 42,1 % verified quand actif, attribution 7,63pp ; axe 1 DARES 6,8 % ; axe 4 financement 0,0 % (muet) ; axe 2 DROM 0/72 non mesure | analyse `granularities_top_k` | `R/docs/SPRINT6_VERDICT.md:138-145` |
| 2026-04-27 | Sprint 7 bench 2 modes | verified/halluc, 2 configurations | 38 q (24 figees + 14 nouvelles) x 3 runs x 2 modes | StatFactChecker | Mode Baseline 30,8 % +-1,03pp verified / 16,8 % +-8,19pp halluc ; Mode Both 29,3 % +-12,07pp / 25,6 % +-20,65pp ; delta Both-Baseline -1,5pp verified, +8,8pp halluc | v3.3 strict R1-R6 + critic loop (mode Both) ; 5 actions data/methodo (mode Baseline) | `R/docs/SPRINT7_VERDICT.md:24-38` |
| 2026-04-27 | Sprint 7 bench-check axe 4 financement | unmute du verdict `verified_by_official_source` | 4 q, 45 stats | StatFactChecker v2 | verified 93,3 % (vs 0 % Sprint 6), halluc 0 % ; mais 39/42 verified sont "strict", seulement 3 par la nouvelle voie | Action 1 | `R/docs/SPRINT7_VERDICT.md:1-16` (section 3) |
| 2026-04-27 | user_test_v3, retours humains | qualite percue post-Sprint 7 | 10 q, 5 profils | Humains (memes 5 profils que v2), pas de LLM-judge | non agrege ; sortie = 3 bugs P0 bloquants + 5 erreurs persistantes non corrigees au tour 2 | Mode Baseline post-Sprint 7, corpus 58 093 vecteurs | `R/scripts/generate_user_test_v3.py:1-30` ; `R/docs/SPRINT8_WAVE1_VERDICT.md:26-34` |
| 2026-04-27 soir | Sprint 8 Wave 1, bench-check des fixes | correction des bugs et erreurs signales par les humains | 6 q critiques, 13 checks | heuristiques regex automatiques | **9/13 pass (69 %)** ; URL github.com 0/6 (100 % elimine) ; slug FOR.372 3 -> 2 occurrences ; HEC Tremplin toujours mentionne ; EPITA 8500 EUR toujours mentionne | post-process deterministe + 5 cells de correction factuelle, prompt v3.2 non touche | `R/docs/SPRINT8_WAVE1_VERDICT.md:66-80` |
| 2026-04-28 | Sprint 9 archi multi-agents hierarchique | rien de mesure en API (tests mockes) | 0 q | aucun | cout 0 $, pas de bench ; non-regression prouvee par tests mockes seulement | Coordinator + EmpathicAgent + AnalystAgent + SynthesizerAgent, pattern strangler fig | `R/docs/SPRINT9_ARCHI_VERDICT.md:1-12,44-52` |
| 2026-04-29 | Sprint 10 chantier C, RAG filtre metadonnees | tests seulement | 0 q bench | aucun | 97 nouveaux tests verts, suite 1 706 ; gain attendu "80 % de precision" annonce sans mesure directe | filtre metadonnees post-retrieve alimente par AnalystAgent | `R/docs/SPRINT10_RAG_FILTRE_DESIGN.md:15-30,48-52` |
| 2026-04-29 | Sprint 10 chantier E, test serving e2e | latence, pollution, saturation du filtre | 10 q | regex "pollution" (entites hors fiches) | latence p50 18 505 ms, p90 20 874 ms ; **pollution moyenne 87,3 %** (max 97,1 %) ; filtre sature 0/10 ; couverture Q&A Golden 10/10 | corpus unifie 55 606 entrees, filtre + golden QA actives | `R/docs/sprint10-E-test-serving-2026-04-29.md:12-58` |
| 2026-04-29 | Audit qualitatif Matteo sur ces 10 reponses | hallucinations reelles | 10 q | **humain (Matteo)** | 3 hallucinations identifiees : Q5 IFSI "concours post-bac", Q8 DEAMP fantome, Q10 terminale L | sert de verite terrain aux items suivants | `R/docs/sprint11-P0-item3-bench-judge-vs-regex-2026-04-29.md:8-20` |
| 2026-04-29 | Sprint 11 P0 item 3, juge de fidelite vs regex | detection des 3 hallucinations connues | 10 reponses en cache | Claude Haiku 4.5 vs regex naif | juge 3/3 detectees (recall 100 %), 0 faux positif ; regex 3/3 aussi mais sature (73-97 % de pollution partout) ; latence juge 36 985 ms mediane vs <50 ms | remplacement de `measure_pollution()` par le LLM-judge ; whitelist retiree apres recadrage (le v2 contenait les 3 verites terrain = test trivial) | `R/docs/sprint11-P0-item3-bench-judge-vs-regex-2026-04-29.md:8-24` ; `R/docs/sprint11-P0-item3-llm-judge-faithfulness-2026-04-29.md:12-24` |
| 2026-04-29 | Sprint 11 P0 item 1, re-run partiel | longueur de reponse | 4 q | aucun | 311 mots en moyenne (cible <=250), 0/4 sous la cible ; latence 10 747 ms | prompt v4 (strict grounding + glossaire + progressive disclosure) | `R/docs/sprint11-P0-item1-partial-rerun-2026-04-29.md:12-18` |
| 2026-04-30 | Sprint 11 P0 item 4, re-run e2e complet | fidelite, latence, longueur | 10 q (memes que le chantier E) | Claude Haiku 4.5 (faithfulness) | latence p50 18 505 -> **9 911 ms (-46 %)** ; longueur p50 4 182 -> **2 079 chars (-50 %)** ; faithfulness moyenne **0,10** ; **10/10 INFIDELE** ; 2/3 hallucinations Matteo corrigees (Q5, Q8), Q10 non corrigee | prompt v4 + buffer memoire + juge | `R/docs/sprint11-P0-item4-rerun-e2e-2026-04-30.md:20-40` |
| 2026-04-30 | Sprint 11 P1.1, A/B temperature | fidelite/empathie/format/ignorance | 11 q x 4 temperatures = 44 reponses | Haiku (faithfulness + empathie), regex (format), classifieur (ignorance) | temp 0,0 : faith 0,150, 1/10 FIDELE ; 0,1 : 0,220, 2/10 ; 0,2 : 0,035, 0/10 ; 0,3 : 0,295, 1/10. **Retenue 0,1** sur un score composite, alors que 0,3 a la meilleure fidelite brute | ajout d'un juge d'empathie | `R/docs/sprint11-P1-1-ab-temperature-2026-04-30.md:22-40` |
| 2026-04-30 | Sprint 11 P1.1, typologie des hallucinations | nature des 39 entites signalees | echantillon 15/39 | analyse manuelle | ~60 % stats chiffrees inventees, ~20 % ecoles inventees, ~10 % procedures fausses, ~5 % attribution erronee, ~5 % divers | constat : l'ordre "P1.1 stats" raterait ~40 % des cas | `R/docs/sprint11-P1-1-options-analysis-2026-04-30.md:11-22` |
| 2026-04-30 | Sprint 11 P1.1, prompt v5 vs v4 | idem 4 metriques | 10 q + 1 piege | Haiku + regex | faith 0,200 -> 0,211 (+0,011) ; FIDELE 2/10 -> 1/10 ; empathie 3,78 -> 4,11 ; format 82,2 % -> 60,0 % (-22,2pp) ; piege toujours PARTIAL_FUZZY | v5 : scaffolding 2 etapes + 4 few-shots + balises XML | `R/docs/sprint11-P1-1-rerun-e2e-vs-v4-2026-04-30.md:31-38` |
| 2026-05-01 | Sprint 11 P1.1, ablation v5b (sans balises XML) | idem | 10 q (+ 8 q on-topic pour le format) | Haiku + regex | faith v4 0,220 / v5 0,211 / **v5b 0,230** ; FIDELE 2 / 1 / 1 sur 10 ; format on-topic 82,2 % / 65,0 % / 73,3 % ; **1/5 criteres de succes atteints** | retrait des balises XML ; recalcul du format sur 8 q on-topic (changement de formule assume dans le doc) | `R/docs/sprint11-P1-1-rerun-e2e-v5b-vs-v5-vs-v4-2026-04-30.md:1-30` |
| 2026-05-01 | Sprint 11 P1.1, classifieur d'ignorance v3 | detection de l'aveu d'ignorance | 1 q piege | regex | v2 ratait "aucune donnee" et "ne concernent pas" -> faux PARTIAL_FUZZY malgre faithfulness 1,00 ; v3 additif | 2 patterns ajoutes | `R/docs/sprint11-P1-1-classifier-ignorance-v3-2026-05-01.md:12-30` |
| 2026-05-01 | Sprint 11 P1.1, backstop B soft | annotation des stats non verifiees | 17 entites signalees / 12 wraps | derive du juge Haiku deja calcule (pas de re-run Mistral) | catch rate **64,7 % (11/17)**, cible >=60 % OK ; faux positifs 8,3 % (1/12), cible <=5 % KO ; disclaimer 100 % ; faithfulness 0,12 inchangee par construction | couche d'annotation post-hoc, economie de 0,51 $ en rejouant le brut v5b | `R/docs/sprint11-P1-1-backstop-b-soft-rerun-2026-05-01.md:10-30` |
| 2026-05-01 | Sprint 12 D1, audit du champ `profil_admis` | couverture du corpus | 55 606 fiches | comptage | dict present 19 489 (35,0 %) ; **rempli non-zero 10 502 (18,9 %)** ; 7 sous-champs couverts 47-54 % | expose le profil des admis au RAG | `R/docs/sprint12-D1-profil-admis-audit-champs-2026-05-01.md:12-32` |
| 2026-05-01 | Sprint 12 D1, validation retrieval | presence de la section "Profil des admis" | 5 q ciblees | marqueur textuel dans le top-K | top-1 hit 80 % (4/5), cible >=60 % ; 3,8/5 fiches en top-5 ; suite 2 071 tests | index reconstruit (D1+D5), ~3 $ | `R/docs/sprint12-D1-rerun-retrieval-2026-05-01.md:12-24` |
| 2026-05-02 | Sprint 12, bench Mistral Large vs Medium | **non mesure** | 30 q prevues, 3 juges prevus | Claude Sonnet + GPT-4o + Haiku (prevu) | **toutes les cases du tableau sont "TBD"** ; decision GO_LARGE/NO_GO jamais tranchee dans le doc ; seuils poses a l'avance (GO si delta cumul > +1,5) | protocole ecrit, resultats jamais remplis | `R/docs/sprint12-mistral-large-vs-medium-bench-2026-05-02.md:9-20,76-96` |
| 2026-05-08 | Sprint 9, re-audit | reutilisabilite de l'archi hierarchique | revue de code, 0 q | aucun | Path B retenu ; `EmpathicAgent` reecrit les claims v4.1 (max_tokens 1500 vs 400) et n'est pas re-valide -> ecarte ; latence Coordinator 33-43 s en mode reco | leve l'ambiguite "Sprint 9 NO-GO" vs "95 % pret" | `R/docs/SPRINT9_REAUDIT.md:1-12,20-40` |
| 2026-05-11 | **Benchmark Phase D** (rapport INRIA) | 6 gates GO/NO-GO | 71 q `golden_60.json` v3.1, 11 categories, 7 systemes = 497 reponses | Claude Sonnet 4.5 + GPT-4o (rubrique /18) + Haiku 4.5 (factcheck) | voir le tableau des gates ci-dessous ; `our_rag` 10,75 /18 (Claude) et 8,18 /18 (GPT-4o) | v4.1 strict (250 mots, FactCard JSON), 71 q dont 5 ajoutees par ADR-060 le jour meme | `R/docs/BENCHMARK_PHASE_D_2026-05-11.md:14-61,234-500` |
| 2026-05-13/14 | Observabilite Langfuse + Ragas | domaine en top-5, part de `formation`, faithfulness | 13 spot-checks + 50 entrees golden | Langfuse (traces) + Ragas avec juge Mistral | `n_domain_match_top5 >= 1` : 4/13 -> 8/13 puis 9/13 ; part `(formation)` en top-5 60,7 % -> 24,6 % ; Ragas faithfulness **0,489 bimodale** ; context_recall **0,021 = inutilisable** | Chantier C+ puis fix Q11 | `R/docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md` ; `R/results/ragas_calibration_2026-05-14/ragas_results.json` |
## 2. Les 6 gates BENCH_GATES : definition, seuil, dernier statut mesure

Definitions et seuils : `R/docs/BENCH_GATES.md` (ecrit en Phase C3, seuils poses AVANT la Phase D, revendique explicitement pour "eviter le subjectif post-hoc", `:5`).
Dernier statut mesure : bench Phase D du 11/05, `R/docs/BENCHMARK_PHASE_D_2026-05-11.md:476-487`.

| Gate | Ce qu'elle mesure | Seuil (BENCH_GATES) | Dernier resultat mesure | Statut | Preuve |
|---|---|---|---|---|---|
| 1 Retrieval | recall@5, recall@5 par categorie, MRR, nDCG@10 sur `golden_60` | >=0,75 / >=0,60 par cat. / >=0,55 / >=0,65 | recall@5 **0,648** ; MRR **0,723** ; nDCG@10 **0,725** | partiel, recall@5 sous cible (le synthesizer automatique prononce NO-GO) | `BENCH_GATES.md:13-20` ; `BENCHMARK_PHASE_D:239-242,478` |
| 2 Honnetete interne | `avg_honesty` du validator, `flagged_count`, latence, sur le mini-bench v4.1 strict 23 q | >=0,95 ; <=2/23 flagged ; <=9 s | **non rapportee** par le synthesizer en Phase D. Derniere valeur connue : 0,987 avec 1/23 flagged, 8,56 s (ADR-059, 08/05) | non mesuree en Phase D | `BENCH_GATES.md:22-28` ; `BENCHMARK_PHASE_D:479` ; `DECISION_LOG.md:3676-3682` |
| 3 Latence production | p50, p95 sur 60 q, aucun timeout > 30 s | <=8 s / <=12 s / 0 | p50 **5,75 s**, p95 **11,24 s**, 0 timeout | PASS | `BENCH_GATES.md:30-36` ; `BENCHMARK_PHASE_D:275-286,480` |
| 4 Robustesse adversariale | `refusal_correctness` adversarial et cross_domain ; 0 hallucination Haiku a haute confiance | >=0,80 / =1,00 / 0 | adversarial **0,900** (9/10), cross_domain **1,000** (2/2), global 0,923 | PASS | `BENCH_GATES.md:38-44` ; `BENCHMARK_PHASE_D:294-299,481` |
| 5 Rubrique LLM-judge externe | note /18 Claude et GPT-4o, kappa inter-juges, ecart vs baselines neutres | >=12,0 chacun ; kappa >=0,4 ; >= +1,0 pt | `our_rag` **10,75 /18 (Claude)** et **8,18 /18 (GPT-4o)**, donc les deux sous 12,0 ; ecart vs neutres **+1,30 (Claude)** et **-3,63 (GPT-4o)** ; kappa **non calcule**, qualifie de "faible par construction" | FAIL cote GPT-4o, PASS partiel cote Claude sur le seul critere d'ecart | `BENCH_GATES.md:46-53` ; `BENCHMARK_PHASE_D:311-330,482` |
| 6 Honnetete externe Haiku | `honesty_score` moyen et ecart vs `mistral_v3_2_no_rag` | >=0,85 ; delta >= +0,05 | critere absolu (0 fabrication a confiance >=0,8) : **0 sur 497 reponses**, PASS. Critere relatif : honesty **0,621**, delta **-0,154** | absolu PASS, relatif FAIL (le rapport le qualifie d'artefact methodologique) | `BENCH_GATES.md:55-60` ; `BENCHMARK_PHASE_D:407-420,483-484` |

Gates informatives (non bloquantes, `BENCH_GATES.md:64-72`) : `answer_keyword_match` >=70 %, recall@1 >=50 %, recall@10 >=85 %, **spot-check 13 q >= 11/13**, cout <= 35 $. Le spot-check 13 q n'a jamais atteint 11/13 apres le 08/05 (voir section 4).

Regle de decision ecrite : une seule gate au rouge = NO-GO multi-tour (`BENCH_GATES.md:79-89`). Deux gates rouges (1 et 5) sont mesurees, le synthesizer automatique prononce NO-GO, et le rapport Phase D requalifie cette lecture en "defauts localises, interpretables et non bloquants" (`BENCHMARK_PHASE_D:53-61,487`). La regle GO/NO-GO ecrite avant le bench n'a donc pas ete appliquee telle quelle.

Ce que le bench Phase D ne mesure pas, de son propre aveu (`BENCH_GATES.md:94-102`) : UX qualitative utilisateur (aucun beta test dans la Phase D), multi-tour reel, latence multi-tour cumulee, regression hors des 60 questions.

## 3. Chiffres headline avec fichier et ligne

Sprints agentiques (avril) :
- verified 23,0 % +-19,73pp vs baseline figee 39,4 % +-3,66pp, **-16,4pp** : `R/docs/SPRINT5_APPLES_TO_APPLES_VERDICT.md:31`.
- causes des claims non soutenus : 60 % sources insuffisantes, 40 % LLM hallucine, **0 % juge trop strict** (n=20) : `SPRINT5_...:42-44`.
- 77,7 % unsupported / 6,8 % supported / 2,7 % contradicted sur 220 claims : `R/docs/SPRINT4_AGENT_VS_BASELINE_VERDICT.md:90-95`.
- latence 39,87 s (Sprint 4), 23,12 s (Sprint 5), 25,74 s (Sprint 6), 38,04 s (Sprint 7 baseline), vs 12,35 s baseline figee : `SPRINT4:83`, `SPRINT5:33`, `SPRINT6:94`, `SPRINT7:28`.
- Sprint 6 : +0,4pp verified, "dans le bruit IC95 8,89pp", gap toujours -16,0pp apres +1 792 cellules : `R/docs/SPRINT6_VERDICT.md:95-96,104-107`.
- axe 4 financement : 0,0 % verified quand actif (muet) puis 93,3 % apres changement de definition du verdict : `SPRINT6:143` puis `SPRINT7` section 3.
- Sprint 7 mode Both : halluc 16,8 % -> **25,6 %**, IC95 x11,7 plus instable, 266 modifications du critic : `R/docs/SPRINT7_VERDICT.md:26-27,32,66-68`.
- Sprint 8 : **9/13 checks (69 %)** ; URL github.com 0/6 ; FOR.372 3 -> 2 : `R/docs/SPRINT8_WAVE1_VERDICT.md:66-80`.

Sprints 10-12 (fin avril / debut mai) :
- pollution regex **87,3 % en moyenne, 97,1 % max** sur 10 reponses : `R/docs/sprint10-E-test-serving-2026-04-29.md:32-34`.
- latence p50 18 505 -> 9 911 ms (-46 %), longueur p50 4 182 -> 2 079 chars (-50 %) : `R/docs/sprint11-P0-item4-rerun-e2e-2026-04-30.md:22-25`.
- faithfulness moyenne **0,10** et **10/10 INFIDELE** apres le prompt v4 : `sprint11-P0-item4:28-29`.
- 2/3 hallucinations Matteo corrigees, Q10 non corrigee : `sprint11-P0-item4:24-26,34-36`.
- fidelite par temperature : 0,150 / 0,220 / 0,035 / 0,295 pour T = 0,0 / 0,1 / 0,2 / 0,3 : `R/docs/sprint11-P1-1-ab-temperature-2026-04-30.md:29-33`.
- v4 0,220 -> v5 0,211 -> v5b 0,230 de faithfulness, FIDELE 2 -> 1 -> 1 sur 10, **1/5 criteres atteints** : `R/docs/sprint11-P1-1-rerun-e2e-v5b-vs-v5-vs-v4-2026-04-30.md:3-12,20-26`.
- backstop B soft : catch 64,7 % (11/17), faux positifs 8,3 % (1/12) : `R/docs/sprint11-P1-1-backstop-b-soft-rerun-2026-05-01.md:12-14`.
- `profil_admis` rempli non-zero sur **18,9 %** du corpus (10 502 / 55 606) : `R/docs/sprint12-D1-profil-admis-audit-champs-2026-05-01.md:14-16`.
- top-1 hit "Profil des admis" 80 % (4/5) : `R/docs/sprint12-D1-rerun-retrieval-2026-05-01.md:14`.

Audits Phase 0 (mai) :
- **67 % du corpus partage 6 tuples d'insertion Cereq** (32 704 fiches), masque par `honesty=1.0` : `R/docs/AUDIT_PHASE_0.md:13` et `R/docs/DECISION_LOG.md:2986-2992` (ADR-054).
- 28 % de doublons (13 858 fiches), labels SecNumEdu/CTI **23 fiches sur 48 914 (0,05 %)** alors que le reranker les booste x1,5, couverture URL **10 %** : `AUDIT_PHASE_0.md:14-16`.
- 6 233 fiches (12,7 %) sans aucun chiffre exploitable : `AUDIT_PHASE_0.md:33-44`.
- audit v5 / v6 / v7 : `sans_region_formations_pct` **41,5 %** pour une cible <=10 % (seule metrique rouge), `url_verifiable_pct` 33 %, verdict **NO-GO** repete trois fois : `R/docs/AUDIT_PHASE_0_V5_2026-05-07.md:11-35` et les deux fichiers du 08/05.
- banniere de peremption ajoutee en tete de ces trois audits : la vraie valeur est **45,9 % de region manquante** et 47 220 fiches selon `audit_empirique_2026-06-09` : `AUDIT_PHASE_0_V5_2026-05-07.md:1`.

Phase D (11/05) :
- 71 questions, 11 categories, 7 systemes, **497 reponses** : `BENCHMARK_PHASE_D:14-20,42`.
- `our_rag` 10,75 (Claude) / 8,18 (GPT-4o) sur 18 ; meilleur systeme cote GPT-4o = `mistral_neutral` a 16,27 : `BENCHMARK_PHASE_D:311-320`.
- sourcage +0,86 /3 et neutralite +0,53 /3 vs `mistral_neutral` ; realisme -0,27 ; diversite geo -1,69 et decouverte -1,52 : `BENCHMARK_PHASE_D:22-33,336-340`.
- honesty Haiku par systeme : `our_rag` 0,621, `gpt4o_v3_2_no_rag` **0,933** (le meilleur est le systeme sans RAG) : `BENCHMARK_PHASE_D:409-415`.
- 0 hallucination a confiance >=0,8 sur 497 reponses : `BENCHMARK_PHASE_D:395`.
- refus correct 92,3 % global, 9 fausses premisses sur 10 : `BENCHMARK_PHASE_D:294-299`.

Observabilite (13-14/05) :
- domaine attendu present en top-5 : **4/13 -> 8/13** apres chantier C+, puis 9/13 apres le fix Q11 : `R/docs/OBSERVABILITY_SYNTHESIS_2026-05-14.md:13`, `R/docs/SPOT_CHECK_V5_2026-05-14-post-q11-fix.md:9`.
- part de `(formation)` dans le top-5 : 60,7 % -> **24,6 %** : `OBSERVABILITY_SYNTHESIS:14,28`.
- Ragas faithfulness **0,489** (verifiee : `summary.ragas_aggregate.faithfulness = 0.48934852484976327`), distribution bimodale, 26 % >= 0,7 et 54 % < 0,5 : `OBSERVABILITY_SYNTHESIS:65,67-77` ; `R/results/ragas_calibration_2026-05-14/ragas_results.json` cle `summary`.
- Ragas context_recall **0,021**, 92 % des questions sous 0,1, declare inexploitable (verite terrain generee par Claude Opus a partir de sources web, pas du corpus) : `OBSERVABILITY_SYNTHESIS:79-94` ; meme JSON.
- par categorie : famille_social 0,328 de faithfulness (n=9), etudiant_reorientation 0,628 (n=11) : `OBSERVABILITY_SYNTHESIS:58-65`.
- cout total de l'instrumentation ~1,88 $ : `OBSERVABILITY_SYNTHESIS:117-123`.

## 4. Evaluations humaines

Ordre decroissant de solidite.

1. **user_test v1 et v2 (18 et 22 avril), 5 profils.** Leo 17 ans, Sarah 20, Thomas 23, Catherine 52, Dominique 48. 10 questions, grille clair / utile / confiance sur 5 par question plus 7 questions ouvertes. `R/results/user_test_v2/test_orientia_5_profils.md`, `R/results/user_test/feedback_17ans.md`, `_20ans.md`, `_23ans.md`. Aucun agregat chiffre n'est calcule dans le repo (pas de moyenne, pas d'accord inter-profils). Verbatims exploites : longueur excessive, codes administratifs illisibles (`cod_aff_form`, RNCP, FOR.xxx), confiance annoncee autour de 50-70 % avec re-verification systematique des chiffres, formulations sur le pourcentage de femmes jugees genantes. Ces retours ont declenche ADR-025 (Tier 0 post-user-feedback), ADR-030, ADR-037.
   Reserve de comparabilite : les trois fiches v1 partagent exactement la meme mise en forme, les memes rubriques et plusieurs griefs mot pour mot ; le repo ne permet pas de verifier qu'elles ont ete redigees independamment.
2. **user_test_v3 (27 avril), memes 5 profils, tour 2.** `R/scripts/generate_user_test_v3.py:26-30` precise "Matteo distribue manuellement aux 5 profils du test v2. Pas de LLM-judge, retour qualitatif humain". Sortie : 3 bugs P0 bloquants et 5 erreurs persistantes non corrigees entre le tour 1 et le tour 2, ce qui a defini le perimetre du Sprint 8 (`SPRINT8_WAVE1_VERDICT.md:26-34`). Le bench-check de correction est ensuite automatique (heuristiques regex), pas humain : 9/13.
3. **Audit qualitatif de Matteo (29 avril), 10 reponses.** Trois hallucinations identifiees a la main (Q5 IFSI, Q8 DEAMP, Q10 terminale L) et utilisees comme verite terrain pour valider le juge Haiku (`sprint11-P0-item3-bench-judge-vs-regex-2026-04-29.md:8-10`). Echantillon de 3 positifs, aucun negatif etiquete : le "0 faux positif" annonce porte sur des cas presumes fideles, pas sur des cas verifies humainement.
4. **Spot-check Gate 3, 13 questions, 7 rapports du 07/05 au 14/05.** Chaque rapport porte "Evaluation manuelle requise" et se termine par une section "Decision Gate 3 (manuel)" avec trois cases GO / GO conditionnel / NO-GO. **Aucune des sept n'est cochee ni commentee** (verifie sur les 07/05, 13/05 post-C+ et 14/05 post-Q11). Seul le compteur automatique de correspondance de domaine en top-5 varie : 4/13 (07/05), 11/13 (08/05, corpus v6), 5/13 (10/05), 4/13 (11/05), 4/13 (13/05), 8/13 (13/05 post-C+), 9/13 (14/05 post-Q11). La partie humaine de cette gate n'a jamais ete rendue.
5. **ADR-026 (18/04), regle absolue : spot-check manuel de 3-5 echantillons contre la source officielle avant tout merge de source data** (`DECISION_LOG.md:556-580`). Motif : un audit automatique d'InserSup avait declare 0 outlier tout en ratant un taux d'emploi nul sur 194 fiches. Trace d'application : `R/results/user_test/Spot-check_manuel_InserSup.md` et `spot_check_insersup.md`.
6. **ADR-006 (13/04), evaluation humaine par 2 etudiants sur 30 questions en aveugle**, avec kappa inter-etudiants et kappa etudiant vs Claude comme validation de la methode LLM-as-judge (`DECISION_LOG.md:134-157`). **Jamais executee** : `R/docs/SESSION_HANDOFF.md:216` porte encore "G.2 Human eval (2 students x 30 q blind) | pending". La validation humaine du juge LLM, presentee dans l'ADR comme necessaire a la defendabilite du papier, n'existe pas.
7. Mention croisee hors lot : les "verdicts persona 2/5 mediane" cites par ADR-037 viennent du Gate J6 (`R/results/gate_j6/`), qui est un persona **simule par Claude Sonnet**, pas un humain (`DECISION_LOG.md:1139-1143,1180-1186`).

## 5. Incoherences et ruptures de comparabilite

1. **Le set de reference change a chaque sprint tout en gardant le meme point de comparaison.** La "baseline figee 39,4 % / 17,9 %" est mesuree sur 48 q x 3 (26/04) ; le Sprint 5 la compare a 24 q x 3, le Sprint 6 aussi, le Sprint 7 a 38 q x 3. `SPRINT7_VERDICT.md:66-71` affirme la comparabilite directe parce que les 24 questions strictes sont preservees, mais le chiffre 39,4 % auquel on compare, lui, vient des 48.
2. **Le fact-checker change en cours de route, le nom du chiffre non.** Sprint 4 utilise FetchStatFromSource (LLM-judge Mistral Large), Sprint 5 revient a StatFactChecker, Sprint 7 Action 1 ajoute le verdict `verified_by_official_source` qui fait passer l'axe 4 de 0 % a 93,3 % sans qu'une seule reponse n'ait change. Le Sprint 4 documente lui-meme la non-comparabilite (`SPRINT4:27-52`), le Sprint 7 la produit a nouveau.
3. **Trois instruments de fidelite coexistent sans pont** : StatFactChecker (% verified / hallucinated), le juge Haiku faithfulness 0-1 (Sprint 11), et Ragas faithfulness (14/05). Les trois donnent des ordres de grandeur incompatibles sur des periodes voisines : 30,8 % verified (27/04), 0,10 de faithfulness (30/04), 0,489 (14/05). Aucun document ne les met en regard.
4. **La metrique de pollution regex etait saturee et l'a masque.** 87,3 % de pollution moyenne, 73-97 % sur les 10 questions : elle signale tout, donc rien. Elle a servi de mesure de reference du chantier E avant d'etre remplacee (`sprint10-E:32-34` ; `sprint11-P0-item3-bench-judge-vs-regex:20`).
5. **Le premier juge de fidelite s'est mesure sur un test trivial.** La v2 injectait dans le prompt du juge une liste blanche contenant exactement les trois verites terrain a retrouver ; corrige apres recadrage (`sprint11-P0-item3-llm-judge-faithfulness:15,24`). Le "recall 100 %" retenu vient de la v1 minimale, sur n=3.
6. **La formule du critere format change au milieu de la comparaison v4/v5/v5b**, de 10 questions a 8 questions on-topic ; les deux versions sont affichees cote a cote et le doc l'assume, mais le verdict "1/5 criteres" est prononce avec la nouvelle (`sprint11-P1-1-rerun-e2e-v5b...:3-26`).
7. **Le choix de temperature ne suit pas la metrique cible.** T = 0,3 a la meilleure fidelite (0,295) et T = 0,1 est retenue via un score composite qui melange fidelite, empathie et format (`sprint11-P1-1-ab-temperature:29-40`). Sur n = 10 par temperature, l'ecart 0,035 -> 0,295 sans intervalle de confiance n'etablit rien.
8. **Le backstop B soft n'a pas ete rejoue.** Ses metriques sont derivees du brut v5b deja calcule, ce que le document justifie et documente (`backstop-b-soft-rerun:22-36`), mais "faithfulness inchangee" y est vrai par construction, pas mesure.
9. **Les trois audits Phase 0 v5 / v6 / v7 portent le meme titre "v5" et le meme verdict NO-GO**, avec des chiffres quasi identiques (47 193 puis 47 214 fiches, `sans_region` 41,5 % dans les trois). Ils sont ensuite tous marques perimes : la valeur reelle serait 45,9 %. Trois validations de gate successives se sont donc appuyees sur une metrique fausse d'environ 4 points.
10. **Le corpus bouge sous les benchs, plus vite que les benchs.** 48 914 fiches (07/05 audit) -> 47 193 (v5) -> 47 214 (v7) -> 55 606 (sprint 10, 29/04) -> 52 040 (chiffre du CLAUDE.md pour juillet). Les index passent de 54 297 vecteurs (phase D avril) a 56 089 (Sprint 6) puis 58 093 (Sprint 7). La numerotation des corpus et celle des sprints ne sont pas alignees chronologiquement.
11. **Le dataset de la Phase D a ete modifie apres un premier bench rouge.** Le bench du 10/05 sortait 3 gates rouges sur 6, dont Gate 4 refus cross_domain a 0 % ; ADR-060 (11/05) ajoute 52 marqueurs de refus et 5 questions `vie_etudiante_periph`, et le bench du 11/05 donne Gate 4 a 100 % et 90 % (`DECISION_LOG.md:3774-3800` ; `BENCHMARK_PHASE_D:117-124`). Le fichier s'appelle toujours `golden_60.json` et contient 71 questions. La correction du marqueur est legitime (le systeme refusait bien, la chaine ne matchait pas), l'ajout de 5 questions le meme jour ne l'est pas au meme titre.
12. **La regle GO/NO-GO ecrite a l'avance n'a pas ete appliquee.** Une gate rouge devait suffire a un NO-GO ; deux sont rouges, le verdict automatique est NO-GO, et le rapport conclut a une lecture "qualifiee" non bloquante (`BENCH_GATES.md:79-89` vs `BENCHMARK_PHASE_D:53-61,487`).
13. **Le kappa inter-juges de la Gate 5 n'est pas calcule** alors que le seuil >=0,4 est ecrit ; le rapport se contente de dire qu'il est "par construction faible" (`BENCHMARK_PHASE_D:326-330`). Le seul kappa reellement mesure du projet reste celui du Run F (lot A, 0,464-0,587).
14. **Le desaccord entre juges depasse l'ecart mesure.** Sur la meme Gate 5, Claude donne +1,30 et GPT-4o -3,63 pour la meme hypothese H1. Sur le meme run, le systeme le plus honnete selon Haiku est celui sans RAG (`gpt4o_v3_2_no_rag` a 0,933 contre 0,621).
15. **Le context_recall Ragas a ete mesure avant d'etre juge inexploitable** : la verite terrain venait de Claude Opus sur des sources web hors corpus. Le chiffre 0,021 existe, il est publie, et sa lecture est ensuite retiree (`OBSERVABILITY_SYNTHESIS:87-94`).
16. **Une seule passe pre et une seule passe post pour la mesure du chantier C+**, avec un pipeline a temperature 0,3 ; le document liste lui-meme cette limite (`OBSERVABILITY_SYNTHESIS:131`). Le "4/13 -> 8/13" est donc un delta a n=1 de chaque cote.
17. **Le bench Mistral Large vs Medium du 02/05 n'a jamais ete rempli.** Le document porte les seuils, la methodologie et une case "Decision : GO_LARGE / NO_GO / SIGNAL_MEDIOCRE" restee vide, avec 15 valeurs TBD. L'hypothese "le goulot est Mistral medium en generation" n'a donc jamais ete testee.
18. **Les Sprints 9 et 10 chantier C livrent des changements structurels sans mesure.** Sprint 9 : 0 $ de bench, non-regression prouvee par tests mockes (`SPRINT9_ARCHI_VERDICT.md:6,44-52`). Sprint 10 chantier C annonce une cible de "80 % de gain de precision" en citant un cout de "3-5 points" mesure au Run F, jamais re-mesure apres livraison (`SPRINT10_RAG_FILTRE_DESIGN.md:48-52`).
19. **La note Sprint 10 affirme un gain qu'elle ne mesure pas** : "le filtre cible 80 % de gain de precision sur cette classe de questions" est une cible, ecrite au present a cote d'une mesure Run F reelle ; les deux se lisent pareil.

## 6. Liste des ADR (`R/docs/DECISION_LOG.md`), ceux qui touchent l'evaluation en gras

| ADR | Date | Une ligne |
|---|---|---|
| 001 | 2026-03-10 | Mistral pour la generation et les embeddings (souverainete) |
| 002 | 2026-03-15 | Reranker a base de labels plutot que similarite pure |
| **003** | 2026-04-13 | **Matrice d'ablation a 7 systemes au lieu de 3 : separer "le RAG apporte" de "le prompt v3.2 apporte"** |
| **004** | 2026-04-13 | **`chatgpt_recorded` (reponses web recopiees a la main) remplace par des baselines API, juge non representatif** |
| **005** | 2026-04-13 | **Split dev/test 32/68 : les 32 questions ont servi a 10 runs de tuning, elles ne peuvent plus etre du test** |
| **006** | 2026-04-13 | **Evaluation humaine par 2 etudiants sur 30 questions en aveugle, avec kappa. Jamais executee (SESSION_HANDOFF:216 "pending")** |
| **007** | 2026-04-12 | **`NEUTRAL_MISTRAL_PROMPT` comme baseline equitable (c'est la rupture du Run 10)** |
| 008 | 2026-04-15 | MMR post-rerank, lambda 0,7 |
| 009 | 2026-04-15 | Classifieur d'intention a regles, pas LLM |
| 010 | 2026-04-15 | Abandon de l'extension manuelle des labels |
| **011** | 2026-04-15 | **Deux juges (Claude Sonnet + GPT-4o) au lieu d'un seul : le biais mono-juge est indetectable** |
| 012 | 2026-04-15 | Limiteur 12 RPM OpenAI plutot que passer au tier 2 |
| **013** | 2026-04-15 | **Run F progressif : une passe d'abord, decision sur la variance ensuite (d'ou l'absence d'IC sur le Run F)** |
| **014** | 2026-04-16 | **La couche de fact-check inverse le resultat du RAG : honesty brute 0,575 pour `our_rag` vs 0,562 sans RAG, delta Claude -0,14 -> +0,03. Base du "les baselines fabriquent des citations plausibles"** |
| **015** | 2026-04-15 | **Sauvegarde incrementale obligatoire pour tout run de juge (reprise apres coupure)** |
| 021 | 2026-04-17 | Repivot : le systeme qui gagne prime sur le papier qui demontre |
| 022 | 2026-04-17 | Format de citation stable en vue d'un futur RAFT |
| **023** | 2026-04-17 | **Sanity UX brievete + exploitation des signaux (c'est la vague qui fait tomber les mots de 1328 a 661, lot A)** |
| 024 | 2026-04-17 | Extension au domaine sante, trous de qualite data |
| **025** | 2026-04-18 | **Corrections Tier 0 critiques issues des retours utilisateurs** |
| **026** | 2026-04-18 | **Regle absolue : spot-check manuel de 3-5 echantillons contre la source officielle avant tout merge de source data (l'audit automatique avait rate un taux d'emploi nul sur 194 fiches)** |
| 027, 028 | 2026-04-18 | Plan Tier 0 a 4 ; fermeture des PR redondantes |
| 029 | 2026-04-19 | Tier 2 UX livre |
| **030** | 2026-04-19 | **Preuve empirique du plafond du prompt-engineering : la variante alpha ne corrige qu'1 hallucination sur 5, le LLM n'adopte jamais le pattern d'abstention (0/10)** |
| 031 | 2026-04-19 | Pivot vers l'agentique, RAFT reporte |
| 032 | 2026-04-19 | Mistral Large valide comme orchestrateur |
| 033, 034 | 2026-04-19 | Fixes UX independants du LLM ; ROME 4.0 hors ligne |
| **035** | 2026-04-22 | **Validator programmatique pre-livraison + rafraichissement cron** |
| 036 | 2026-04-22 | Enrichissements Psy-EN reportes |
| **037** | 2026-04-22 | **Hypothese refutee : alleger la section "pieges" ne fait pas bouger la mediane persona 2/5, la moyenne baisse meme de 2,40 a 2,00. La cause est la generation Mistral Medium, pas le prompt** |
| 038 a 044, 046 | 2026-04-23/24 | Ingestion et scope data (France Travail, Parcoursup, MonMaster, gitignore) |
| **047** | 2026-04-25 | **Cause racine des timeouts Mistral : le client par defaut, pas `fiche_to_text` (une hypothese ecartee par mesure)** |
| 048, 049, 050 | 2026-04-25 | RAG multi-corpus parallele ; reranker multi-domaine ; dedup Parcoursup |
| **051** | 2026-04-26 | **Architecture agentique : registre d'outils + boucle d'agent en function-calling Mistral (base des Sprints 1 a 5)** |
| **052** | 2026-05-06 | **Critic loop conserve en `src/experimental/`, decision conditionnee a un bench d'ablation Sprint 7.5 (jamais trouve dans le repo). Rappel des chiffres : halluc 16,8 % -> 25,6 %, axe DROM -23,6pp** |
| **053** | 2026-05-06 | **FactCard structuree + contrat strict v4. Constat fondateur : 37 hallucinations Layer3 sur 18 reponses alors que le validator affichait honesty 1,0 ; 88 % de la data est utilisable, le verrou est la fidelite de generation** |
| **054** | 2026-05-07 | **Purge des chiffres d'insertion Cereq agreges : 32 704 fiches (66,9 %) partageaient 6 tuples, une fiche BTS Cyber avait les chiffres d'un BTS Patisserie** |
| 055, 056 | 2026-05-07 | Liste blanche des sources par tier ; pas d'avis subjectifs dans le corpus |
| **057** | 2026-05-07 | **Corpus de reference v5 unifie multi-corpus (change la base de tous les benchs suivants)** |
| **058** | 2026-05-08 | **Retrieval hybride double index + BM25 + RRF, en reponse au 4/13 du spot-check Gate 3** |
| **059** | 2026-05-08 | **Promotion v5 en production sur un triple-gate : Gate 1 NO-GO structurel accepte, Gate 2 1/23 flagged et honesty 0,987, Gate 3 8/13. Verdict "GO conditionnel"** |
| **060** | 2026-05-11 | **Patch des marqueurs de refus + 5 questions ajoutees le jour du bench Phase D, apres un run a 3 gates rouges** |
| 061, 062 | 2026-06-13/14 | Mode recit flag-gated ; forme adaptative du mode recit |

Numerotation : ADR-016 a 020 et ADR-045 n'existent pas dans le fichier. Les ADR-038 a 044 sont marques `[DRAFT]` et ne l'ont jamais quitte.

## 7. Ce qui n'est pas mesure dans ce lot

- Aucun kappa inter-juges en Phase D, alors que la Gate 5 en pose un seuil.
- Aucune mesure post-livraison du filtre metadonnees (Sprint 10 chantier C) ni de l'architecture Sprint 9.
- Gate 2 non rapportee dans le bench Phase D.
- Bench Sprint 7.5 d'ablation (strict seul vs critic seul), promis par ADR-052 : introuvable dans `docs/` et `results/`.
- Bench Mistral Large vs Medium : document vide de resultats.
- Decision manuelle des 7 spot-checks Gate 3 : jamais renseignee.
- Evaluation humaine ADR-006 (2 etudiants, 30 questions, kappa) : jamais lancee.
- Aucun test avec des utilisateurs reels apres le 27/04 dans ce lot ; la Phase D declare explicitement ne pas en contenir.
