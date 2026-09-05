# OrientIA - Inventaire des sets de questions d'évaluation et des traces utilisateurs

Audit en lecture seule sur `/home/matteo_linux/projets/OrientIA` (aucune écriture dans le repo ni le vault).
Date de l'audit : 2026-09-05. Toutes les affirmations portent une référence fichier:ligne ou une commande.

---

## 1. Tableau des sets de questions

| Set | Chemin | n | Date (mtime / build_date) | Origine des questions (preuve) | Répartition persona | Répartition type | Usage |
|---|---|---|---|---|---|---|---|
| Banc 100q Run F | `src/eval/questions.json` | 100 | mtime 2026-04-13 13:10 | Rédigé à la main dans le repo, aucune trace d'origine utilisateur. Champ `_metadata.splits` documente une calibration interne : "32 questions used during prompt v3.x calibration (Runs 6-10)" / "68 hold-out questions added in Phase F.1" (`src/eval/questions.json`, clé `_metadata`) | **Non typé.** Aucun champ persona ; les catégories sont thématiques (biais_marketing 12, realisme 12, decouverte 12, diversite_geo 12, passerelles 12, comparaison 12, honnetete 10, adversarial 10, cross_domain 8) | normal 82, adversarial 10, cross_domain 8 ; split test 68 / dev 32 | Run F robust (`results/run_F_robust*`), fact-check Haiku, judges GPT-4o/Claude |
| Réponses idéales 100q | `src/eval/ideal_answers.json` | 8 entrées (A1, A4, B1, B4, C4, D5, E5, F1) | mtime 2026-04-10 18:03 | Rédigées à la main. Couvre 8 des 100 questions seulement | n/a | n/a | Ancrage qualitatif du juge |
| `data/eval_questions.json` | - | - | - | **ABSENT** (vérifié : `os.path.exists` faux) | - | - | - |
| Golden 50 | `data/golden_eval/golden_50.json` | 50 | `build_date: "2026-05-08"` | `build_context` : "Vague 1.5 (post-promotion v6). Ground-truth 50 questions × catégories pour mesurer recall@k et MRR". Écrit dans le repo, pas collecté | Typage **implicite par catégorie** : lyceen_parcoursup 10, reorientation 10, metier 10, geographique 10, calendaire 5, vie_etudiante 5 | 100 % factuel court (aucun adversarial) | `results/eval_recall/v6_baseline_2026-05-08.json` et `v7_post_vague_3.json` (metadata `golden_path`) ; CI golden (`src/eval/golden_ci.py`) |
| Golden 60 (en fait 71) | `data/golden_eval/golden_60.json` | **71** questions (malgré le nom) | `build_date: "2026-05-11"` | `build_context` : "ADR-060 - patch soir avant rendu INRIA AI Grand Challenge". Extension de golden_50 par l'agent | lyceen_parcoursup 10, reorientation 10, metier 10, geographique 10, calendaire 5, vie_etudiante 5, vie_etudiante_periph 5 | + adversarial 10, cross_domain 2, live 2, paraphrase 2 | Bench Phase D, gates refus (`refusal_markers_default`) |
| Baseline hallucination | `data/audit/hallu_questions_baseline.json` | 15 | `_meta.created: "2026-05-03"` | `_meta.source` : "10 questions Sprint 11 P0 item 4 - toutes flaguées INFIDELE par juge claude-haiku-4-5" + "5 stress-test jury INRIA explicites". Origine = sorties du système + rédaction agent | 15 catégories distinctes toutes à 1 (reorientation_terminale, reorientation_l1, burnout_prepa, logement_boursier, echec_pass_paramedical...) : profils lycéen ET post-bac | Adversarial / hallucination | Audit anti-hallucination chantier 1.A purge prompt |
| Baseline SELECT | `data/audit/select_baseline_v1.json` | 20 | `_meta.created: "2026-05-05"` | `_meta.purpose` : "Mini-bench SELECT-ciblé pour mesurer le vrai taux d'activation du SELECT déterministe". Rédigé pour le mécanisme, pas pour l'utilisateur | Non typé | entity_based_existing_school 8, entity_based_absent_school 4, ambiguous_multi_match 4, new_pattern_coverage 4 | Chantier 2 SELECT |
| Seed mode récit | `data/recits_seed.json` | 12 | mtime 2026-06-14 | `_meta.description` : "Seed d'evaluation du MODE RECIT (ordre Jarvis 2026-06-13-1522). 12 recits longs realistes (>=300 chars, multi-facettes) representatifs de l'usage reel". Rédigés par l'agent sur ordre Jarvis | Profils explicites dans le texte : L2 droit Lille, terminale Bordeaux maths/SVT, 24 ans vendeur Lyon, BUT GEA, terminale STMG Nantes, L1 psycho, 26 ans intérim Marseille | parametrique 6, adversarial 6 | Calibration détecteur récit 1a, génération R1 1c, gates |
| Smoke 42q | `audit_empirique_2026-06-09/eval_set.json` | 42 | mtime 2026-06-09 14:14 | Sous-ensemble du générateur (voir ligne suivante) | Non typé | factuelle_precise 8, edge_geo 5, adversarial 5, hors_perimetre 4, mal_formulee 4, baseline_inscope 4, detresse_implicite 3, comparaison 3, detresse_explicite 2, detresse_precision 2, substitution_metrique 2 | Pré-run batterie |
| **Banc gelé 497q** | `audit_empirique_2026-06-09/eval_set_full.json` (`version: 2026-06-09-full-v1`) | 497 | mtime 2026-06-09 14:14 | **Généré par script** : `audit_empirique_2026-06-09/build_eval_set.py`. Docstring l.1-11 : "Genere l'eval set COMPLET versionne (cible 500+) [...] Deterministe (aucune aleatoire)". Combinatoire de pools d'entités codés en dur (FORMATIONS l.24-33, ECOLES l.34-36, METIERS l.37-40, VILLES l.41-42, REGIONS l.43-45, DOMTOM l.46) × patterns de question | Non typé. Répartition thématique : metier 120, factuelle_precise 100, edge_geo 52, hors_perimetre 48, comparaison 32, reconversion_adulte 28, baseline_inscope 28, mal_formulee 24, adversarial 24, anti_biais_sociodemo 18, detresse_explicite 8, detresse_precision 8 | adversarial 24 + hors_perimetre 48 ; **0 multi-tour** | Gel VivaTech (`VERDICT_gel_497q_2026-06-11.md` l.1-5), re-gel 0825 (`regel_0825.sh`), re-baseline post-C4 (`rebaseline_postc4.sh` l.24 "attendu 497") |
| Smoke 2q | `audit_empirique_2026-06-09/eval_set_smoke.json` | 2 | 2026-06-09 | Extrait du 497q | - | 1 factuelle + 1 detresse | Smoke test |
| Bench e2e typage | `audit_empirique_2026-06-09/bench_e2e_questions_1403.json` | 25 | mtime 2026-06-14 15:10 | Rédigé pour tester le typage de diplôme (`RAPPORT_bench_e2e_1403_2026-06-14.md`) | Non typé | Questions définitionnelles ("C'est quoi un titre professionnel RNCP ?") | Bench e2e 14/03 |
| Probes typage v2 | `audit_empirique_2026-06-09/bench_v2_typage_questions_1252.json` | 18 | mtime 2026-06-14 15:10 | Idem, ciblé "quel niveau de diplôme" | Non typé | Sondes mécanisme | `VERDICT_probes_v2_typage_1252_2026-06-14.md` |
| Probes pointeur | `audit_empirique_2026-06-09/probes_pointeur_questions_1302.json` | 10 | 2026-06-14 | Sondes mécanisme | Non typé | - | `VERDICT_pointeur_pattern_1302_2026-06-14.md` |
| Subsets du 497q | `subset_A1_detresse.json` (23), `subset_A2_factuel.json` (220), `subset_A2_witness.json` (5), `subset_A3_geo.json` (52), `subset_C2a_reconversion.json` (28), `subset_gardefou.json` (76), `subset_salaire_base.json` (15), `subset_select48.json` (48) | - | 2026-06-09 au 2026-06-11 | Découpes du même banc généré | Non typé | Par catégorie source | Mesures ciblées C2a, garde-fou, salaire, SELECT |
| Golden gate R8R9 | `results/h1_lot1_gate_r8r9/golden_eval_set.json` | 50 | mtime 2026-07-16 09:57 | **Copie de golden_50** (mêmes ids, mêmes catégories, même répartition 10/10/10/10/5/5) | Idem golden_50 | Idem | Gate H1 lot 1, 16/07 |
| Panel personas v4 (avril) | `results/bench_persona_complet_2026-04-26/_ALL_QUERIES.json` | 48 requêtes dont 18 personas | 2026-04-26 | Rédigées par l'agent. Structure `suite: personas_v4`, `persona_id`, `query_type` | **6 personas × 3 questions** : lila (lycéenne lettres), theo (L1/L2 droit), emma (M1 info), mohamed (CAP cuisine/apprentissage), valerie (parent), psy_en (professionnel) | Par persona : `factuelle`, `orientation_ambigue`, `contextuelle_riche` | `docs/VERDICT_BENCH_PERSONA_COMPLET_2026-04-26.md` |
| Personas gate J+6 | `results/gate_j6/personas/*.md` | 5 personas, 3 questions "hard" | 2026-04-22 | Fiches de rôle écrites pour être **jouées par un LLM** (voir §3) | leo_17 (lycéen terminale), ines_20 (L2 réorientation), theo_23 (M1 IAE), catherine_52 (parent DRH), psy_en_54 (Psy-EN) | Notation 1-5 + erreurs factuelles | Gate J+6 V1→V4.1 |
| Pack user test v1/v2/v3 | `results/user_test/answers_to_show.md`, `user_test_v2/responses.json`, `user_test_v3/responses.json` | 10 questions | 2026-04-19 / 22 / 27 | Extraites des runs par `scripts/prepare_user_test_pack.py` (docstring : "Extracts the 6 cyber/data + 4 santé responses from the existing diff files") | Catégories = celles du banc 100q (realisme, biais_marketing, comparaison, honnetete, passerelles, diversite_geo + 4 variantes santé) | 10 questions ouvertes de conseil | Tests dits "utilisateurs" v1/v2/v3 |
| Transcript session prod | `~/obsidian-vault/09-Recherche/OrientAI-Session-Utilisateur-Transcript-2026-07-16.md` | 8 questions | 2026-07-16 | Frontmatter l.5 `author: jarvis` ; l.11 "Test demande par Matteo : 8 questions realistes [...] jouees sur orientai-platform.fr en prod lot 1" | u1 court, u2 court précis, u3 récit, u4+u5 **multi-tour**, u6 reconversion 34 ans, u7 ado casual, u8 salaire | 2 tours multi-tour balisés `[MULTI-TOUR]` | Avis qualité lot 1 |

### Où est le banc "497 questions" gelé

- Fichier : `audit_empirique_2026-06-09/eval_set_full.json`, `"version": "2026-06-09-full-v1"`, `"n": 497`.
- Générateur : `audit_empirique_2026-06-09/build_eval_set.py` (314 lignes), `main()` l.269-314.
- Runs de gel : `gel_497q.sh` l.2 "Run gel 497q (J3 étape 6, GO Matteo 2026-06-11 14h53)" ; `regel_0825.sh` l.2 ; `rebaseline_postc4.sh` l.24.
- Verdicts : `VERDICT_gel_497q_2026-06-11.md` l.5 "497/497 générés (1 err réseau geo-006-v3 exclue), juge 497/497, 0 parse_error" ; `VERDICT_regel_0825_2026-06-12.md` ; `HARNESS-findings-ragas-pre-rebaseline.md` l.13 "une battery FIGÉE (497 records...)".

**Point structurant sur le 497q** : il ne contient que **155 questions de base**, les 342 autres sont des variantes lexicales déterministes de ces mêmes bases. `build_eval_set.py` l.287-302 :

```python
q_forms = ["{q}", "Dis-moi : {q}", "J'aimerais savoir, {q_low}", "Peux-tu m'aider : {q_low}"]
```

Vérification (commande exécutée) : `python -c` sur `eval_set_full.json`, filtre des ids sans suffixe `-v\d` → 155 bases / 342 variantes. La diversité sémantique réelle du banc gelé est donc de 155 questions, pas 497. Les sondes sensibles (détresse, anti-biais) sont explicitement exclues de la densification (l.297-299), ce qui est correct méthodologiquement mais confirme que le reste est bien du gonflage de volume.

---

## 2. Analyse de réalisme

### 2.1 Ce que le banc gelé demande vs ce qu'un lycéen tape

Les questions du 497q sont des **gabarits paramétrés**, pas des énoncés observés. `build_eval_set.py` l.53-66 :

```python
out.append((f"Quel est {m} pour {f} à {ville} ?", "factuelle_precise", exp))
```

produit par exemple `"Quel est le taux d'accès sur Parcoursup pour BUT Informatique à Lyon ?"`. Comparaison directe avec ce qu'un utilisateur tape réellement dans le transcript prod du 16/07 :

| Banc généré (497q) | Session prod 16/07 (`Transcript-2026-07-16.md`) |
|---|---|
| "Quel est le taux d'accès sur Parcoursup pour BUT Informatique à Lyon ?" | l.26 : "il faut quelle moyenne pour rentrer en PASS a Lyon ?" |
| "Quelles études faut-il faire pour devenir développeur web ?" | l.143 : "j'ai 34 ans, cariste depuis 12 ans, je veux devenir developpeur web. possible sans le bac ?" |
| "Quel est le salaire d'un infirmier en début de carrière ?" | l.165 : "on gagne combien en tant qu'infirmiere ?" |
| "Quelles formations en informatique sont disponibles à la Martinique après le bac ?" | l.154 : "je suis nul en maths mais je veux bosser dans les jeux video, c'est mort ou pas ?" |

Les vraies formulations sont plus courtes, sans accent, sans majuscule, avec la contrainte personnelle collée à la question ("j'ai 34 ans, cariste depuis 12 ans"). Le banc a bien une catégorie `mal_formulee` (24 items, soit 6 bases) qui vise ce registre (`build_eval_set.py` l.147-156, ex. "c koi le mieux apres un bac pro commerce ?"), mais elle pèse **6 bases sur 155**, soit 3,9 %.

Longueurs mesurées sur le 497q (commande python, `len(question)`) : min 22, médiane 80, max 161 caractères. Aucune question ne dépasse 161 caractères, alors que `data/recits_seed.json` définit l'usage récit comme ">=300 chars" (`_meta.description`). **Le banc principal exclut donc structurellement le format long qui est celui du mode récit livré en prod.**

### 2.2 Présence du profil et des contraintes

Comptages sur les 497 items (regex, commande python) :

| Élément | Occurrences / 497 |
|---|---|
| notes / moyenne / mention | 18 (soit 3 bases : les 3 bases anti-biais socio-démo, `build_eval_set.py` l.233-260) |
| spécialités ("spé maths") | 6 |
| budget / coût / frais | 40 |
| bourse | 7 |
| mobilité ("loin de chez moi", "déménager") | 4 |
| lycée | 11 |
| terminale / première / seconde | 6 |

Les seules questions du banc portant un profil complet sont les 18 items `anti_biais_sociodemo` (3 bases × 6 variantes socio-démo), construites l.233-260 pour tester la **non-variation** de la réponse, pas la qualité du conseil. Le budget apparaît 40 fois mais presque toujours comme métrique demandée ("les frais de scolarité annuels de..."), pas comme contrainte personnelle.

À l'inverse, les vraies contraintes existent dans les jeux réalistes non gelés :
- `data/recits_seed.json` R01 : "je suis en deuxieme annee de licence de droit a Lille mais je me rends compte que ca ne me passionne pas du tout. Depuis quelques mois je code un peu le soir..."
- Transcript 16/07 l.44 : "[RECIT] terminale spe maths/SES pres de Nantes, hesite droit vs ecole de commerce, budget serre, parents veulent medecine" - profil + géo + budget + pression familiale en une phrase.
- `data/audit/hallu_questions_baseline.json` : "Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?"

Ces trois sources totalisent 12 + 8 + 15 = 35 questions. Elles sont **hors du banc longitudinal gelé** : les mesures de référence (gel 497q, re-gel 0825, re-baseline post-C4) ne les incluent pas.

### 2.3 Multi-tour

- **Aucun set JSON ne contient de champ de conversation.** Vérifié : `grep -rl "history\|tour_2\|turns"` sur `data/golden_eval/*.json`, `src/eval/questions.json`, `audit_empirique_2026-06-09/eval_set*.json`, `data/audit/*.json` → aucun résultat.
- Le seul artefact multi-tour du repo est `audit_empirique_2026-06-09/sim_multitour.py` (150 lignes), docstring l.1-3 : "Simulation multi-tour RÉCIT (R2) - flag ON, local, pour validation Matteo. **4 conversations de 2 tours.**" Les seconds tours sont codés en dur (l.35-60), ex. "Finalement je veux rester à Lyon, et en alternance si possible.", "Entre les deux, lequel si je veux bosser vite ?".
- **Son output n'existe pas dans le repo** : `OUT_PATH = "audit_empirique_2026-06-09/results/sim_multitour_lot.md"` (l.29) et `find . -name "*multitour*"` ne rend que le script lui-même et deux refs git (`.git/refs/heads/pr/mode-recit-r2-multitour`). Le résultat de la simulation multi-tour n'est donc pas conservé comme mesure.
- Les seuls tours 2 réellement joués et tracés sont u4 et u5 du transcript prod du 16/07 (l.98 et l.135), soit **2 tours de suite, sur une session**.

### 2.4 Défauts de réalisme dans les questions elles-mêmes

Les séries de bac supprimées en 2021 apparaissent **dans les questions d'évaluation**, alors que le système les traite par ailleurs comme une hallucination rédhibitoire (`results/gate_j6/personas/psy_en_54.md` : "Séries bac A/B/C/D supprimées 1995 [...] ES/S/L supprimées 2021 (Blanquer)") :

- `results/bench_persona_complet_2026-04-26/_ALL_QUERIES.json` l.417 : "Je suis en **Terminale L**, j'ai 14 de moyenne..."
- idem l.3083 : "Mon fils est en **Terminale S**, moyenne 13..."
- `data/golden_eval/golden_50.json` l.28 et `golden_60.json` l.92 (id G14) : "Taux de réussite L1 STAPS pour un **bac S** mention bien ?"

Un lycéen de 2026 ne peut pas être en Terminale L ni en bac S. Ces questions mesurent donc le système sur un monde qui n'existe plus, et le golden 50/60 est utilisé en CI de non-régression (`src/eval/golden_ci.py`, `results/eval_recall/*.json` metadata `golden_path`).

---

## 3. Tests utilisateurs : ce qui a été collecté, et sa nature

### 3.1 Vue d'ensemble

| Vague | Chemin | Date | "Profils" | Questions | Verdict chiffré | Version système |
|---|---|---|---|---|---|---|
| user_test v1 | `results/user_test/` (feedback_17ans, feedback_20ans, feedback_23ans, answers_52ans, answers_CO) | commit `8d54847` du 2026-04-22 ; mtime des 5 fichiers **identique à la nanoseconde** (2026-04-22 09:42:25.570244591) | 5 : Léo 17 (terminale Maths+NSI), Sarah 20 (L2 éco Paris 1), Thomas 23 (M1 info Dauphine), Catherine 52 (parent DRH), Dominique 48 (Psy-EN CIO Grenoble) | 10 | Notes Clair/Utile/Confiance sur 5 par question ; 9 convergences cross-profils (`docs/SESSION_HANDOFF.md` §14.3) | Pré-Tier 2 |
| user_test v2 | `results/user_test_v2/` | pack généré 2026-04-18, responses.json mtime 2026-04-19 19:04 | mêmes 5 | 10 | **3/5 profils : "non recommandable pour mineur en autonomie"**, ~7 hallucinations distinctes (`docs/SESSION_HANDOFF.md` §15.2 ; `docs/DECISION_LOG.md` l.967) | post-Tier 2 |
| user_test v3 | `results/user_test_v3/` | 2026-04-27 19:39 | mêmes 5 | 10 | 3 progrès / 3 régressions nouvelles (`results/user_test_v3/answers_user` l.7-22) | post-Sprint 7 |
| Gate J+6 | `results/gate_j6/` | 2026-04-22 après-midi/soir | mêmes 5 personas, fiches formalisées dans `personas/*.md` | 3 questions "hard" | **médiane 2/5**, stable de V3 à V4.1 (`docs/SESSION_HANDOFF.md` §18.3 ; `report_v4_prompt_rebalance.md` l.13) | Validator V1→V4.1 |
| Session prod | vault, transcript 16/07 | 2026-07-16 | 1 session jouée par Jarvis | 8 | 7 FIDELE / 1 INFIDELE (u3 récit, faithfulness 0.9) | prod lot 1 |

### 3.2 Nature de ces "tests utilisateurs" : simulés, pas humains

Trois preuves convergentes, à opposer aux affirmations des documents de communication.

**Preuve A - un fichier de "feedback" commence par un prompt de jeu de rôle.**
`results/user_test/answers_CO.md` l.1 : *"Ok je change encore. Dominique, 48 ans, conseiller d'orientation-psychologue (Psy-EN EDO) depuis 22 ans, actuellement au CIO de Grenoble, mais aussi formateur pour de jeunes collègues et intervenant ponctuel à l'INETOP (Cnam Paris). Très respecté dans le métier."* puis l.2 : *"Dominique teste OrientIA en mode audit professionnel."* C'est une consigne de persona adressée à un modèle, conservée en tête du fichier de retour.

**Preuve B - le vocabulaire interne dit "simulé".**
- `docs/SESSION_HANDOFF.md` l.1080 : "**Verdict humain terrain Matteo (ground truth v3 simulé)** : 2/5 médiane sur 3 Q hard, cohérent avec Claude Sonnet persona".
- `docs/SESSION_HANDOFF.md` §18.1, ordre de 13h35 : `v3-resimu-humaine-claude-sonnet-persona`.
- Fichiers : `results/gate_j6/ground_truth_v3_humain_simule.md`, `ground_truth_v3_humain_resimule_claude_sonnet.json`, `ground_truth_v4_humain_resimule_claude_sonnet.json`, `report_humain_simule_v3.md`.
- `results/gate_j6/personas/leo_17.md` contient une section "Format de notation (strict JSON)" avec `{"score": <int 1-5>, "erreurs_factuelles": [...]}` : c'est un prompt de juge LLM, pas une fiche remise à un adolescent.

**Preuve C - mtime identiques.** Les 5 fichiers de `results/user_test/` (`stat -c "%y"`) portent tous l'horodatage 2026-04-22 09:42:25, à 8 millisecondes près entre eux. Cinq personnes distinctes ne rendent pas leur copie dans la même seconde.

**Ce que les documents affirment par ailleurs**, et qui n'est pas établi par ces artefacts :
- `docs/SESSION_HANDOFF.md` l.646 : "Matteo a recruté 4 profils hétérogènes" (suivi d'une liste de 5).
- `docs/INRIA_AI_ORIENTATION_PROJECT.md` l.38 : tableau d'indicateurs, "Personas humains testés (panel) | 5".
- `docs/INRIA_AI_ORIENTATION_PROJECT.md` l.723 : "Cinq personas humains ont testé le moteur IA **dans des conditions réelles**", suivi de verbatims attribués nominativement ("- Léo, 17 ans, terminale Maths-NSI").

Ces trois affirmations sont **porteuses** (elles soutiennent une validation humaine dans un dossier de candidature INRIA) et **non référencées** vers une trace de recrutement, un consentement, un canal de collecte ou un horodatage individuel. Les artefacts disponibles pointent dans l'autre sens. À traiter comme non établi tant qu'une trace de collecte réelle n'est pas produite.

**Confirmation côté vault, par Jarvis lui-même** : `~/obsidian-vault/01-Projets/Actifs/OrientAI-Audit-Startup-2026-07-15.md` l.34, sur le mode récit livré en prod : *"C'est le pari utilite, jamais evalue en batterie complete **ni par de vrais utilisateurs**."*

### 3.3 Verbatims marquants (quelle que soit leur origine, le contenu est exploitable)

1. `results/user_test/feedback_17ans.md` l.19 : *"Ce qui me ferait perdre confiance : le mix '(source: Parcoursup 2025)' + '(connaissance générale)' dans le même bloc. Je sais jamais ce qui est solide et ce qui est de la broderie."*
2. `results/user_test/feedback_20ans.md` l.38 : *"ChatGPT sait dire 'je sais pas'. OrientIA invente toujours un chiffre."*
3. `results/user_test/feedback_23ans.md` l.41 : *"À mon âge, OrientIA dans sa forme actuelle ne me sert pas. C'est un outil pour faire Parcoursup, pas pour penser sa carrière."*
4. `results/user_test/answers_CO.md` l.14 (bloc Q10) : *"'100% de femmes → Environnement potentiellement plus accessible si tu es une candidate' - dans le contexte d'un outil destiné à des mineurs, c'est une formulation discriminante et sexiste."*
5. `results/user_test/answers_52ans.md` l.32 : *"Un vrai conseiller d'orientation pourrait perdre son agrément pour moins que ça. Si Chloé prend une décision basée sur ces affirmations, qui est responsable ?"*
6. `results/user_test_v2/test_orientia_5_profils.md` l.26 (Léo, Q7) : *"'15 880 vœux pour 650 places' = stress pur. Rien qui me dit comment choisir entre PASS et L.AS."*

### 3.4 Erreurs factuelles récurrentes remontées (6 erreurs, `docs/SESSION_HANDOFF.md` §14.3 item 9)

MBA HEC "plus accessible avec expérience" ; École 42 "gratuite en alternance" ; passerelle VAP Infirmier→Kiné "possible" ; prépas médecine privées "2x de chances" ; CentraleSupélec classée en "Plan A réaliste" ; "L'Orthophonie pour les Nuls" recommandé pour un concours à <15 %. Toutes qualifiées d'hallucinations LLM, pas de bugs data.

### 3.5 Spot-check InserSup (le seul contrôle manuel documenté comme fait par Matteo)

`results/user_test/Spot-check_manuel_InserSup.md` l.272 : "5 échantillons avec écart (taux d'emploi 12m manquant sur les 5, et incohérence `obtention_diplome` sur 2/5) → Bug structurel, rollback InserSup de main". Confirmé côté handoff : `docs/SESSION_HANDOFF.md` l.630-643, "Matteo a vérifié 5 échantillons vs source officielle ESR - résultat : 3 bugs structurels". C'est la seule vérification du corpus dont un humain nommé est l'auteur explicite.

### 3.6 Le verdict "2/5"

Origine et propagation :
- `results/gate_j6/ground_truth_v3_humain_simule.md` l.26 : "médiane 2/5 sur les 3 Q hard. **Pire que la baseline 3/5 du pack v2 originel**, mais ces 3 Q ont été sélectionnées précisément pour leur ambiguïté juges LLM - ce n'est pas représentatif du pack complet."
- `results/gate_j6/report_humain_simule_v3.md` l.5 : "2/5 médiane globale → V4 obligatoire avant déploiement" ; l.39-52, détail par persona : Inès 2/5, Théo 2/5, Psy-EN 2/5 ("Refus déontologique OK, mais la phase projet est absente"), Catherine 2/5 ("Hugo va chercher ailleurs").
- `results/gate_j6/report_v4_prompt_rebalance.md` l.13 : médiane 2/5 avant et après rééquilibrage prompt, "stable".
- `docs/DECISION_LOG.md` l.1142 et l.1153 : "Le rééquilibrage prompt ne suffit PAS car le plateau 2/5 a des causes [plus profondes]".

**Nuance importante et documentée** : `results/gate_j6/report_v3.md` §2 constat 3 : *"Le triple-judge LLM n'est PAS le bon proxy pour 'recommandable mineur en autonomie'. Le panel humain originel (5 profils) avait noté 3/5 en baseline sur un pack de 10 Q. Les juges LLM donnent 3.23-3.63/5 sur ces mêmes Q - ils sont systématiquement plus généreux."* Le 2/5 porte donc sur **3 questions choisies pour leur difficulté**, jugées par un LLM jouant 5 personas. Ce n'est pas une note produit sur un échantillon représentatif.

### 3.7 La session prod du 16/07 (transcript vault)

- Utilisateur : Jarvis lui-même (frontmatter l.5 `author: jarvis`, l.11 "Test demande par Matteo").
- 8 questions, dont 2 tours enchaînés (u4, u5) sur le fil ouvert par le récit u3.
- Ce qui a marché : u1 BUT vs BTS (faithfulness 1, 12 sources, chiffres sourcés) ; u2 refus honnête ("Je n'ai pas de PASS à Lyon dans mes sources", l.29) accompagné du warning automatique sur l'interdiction de redoublement PASS (l.35) ; u6 reconversion 34 ans sans bac (l.146-151, réponse pertinente et prudente) ; u8 salaire infirmière sourcé INSEE (l.168).
- Ce qui n'a pas marché : **u3, le récit, verdict INFIDELE** (l.45). Demande "près de Nantes", réponse propose une licence de droit à **Draguignan** (l.54-56) et deux formations parisiennes, puis recommande Le Mans à 1h30 (l.81-84). La géo demandée n'est pas couverte, et l'outil le dit lui-même l.64-65 : "Je n'ai **pas de licence de droit à Nantes** dans mes données". Le mode récit accepte donc de recommander à 900 km faute de couverture locale.
- u5 (coût école de commerce) : refus par absence de donnée (l.138), la question de budget la plus banale du domaine n'a pas de réponse dans le corpus.
- Verdict de la session : renvoyé à la note d'ordre H1 et à Telegram 6217-6219 (l.11), non repris dans le transcript.

---

## 4. Ce qui n'existe pas (vérifié, pas supposé)

1. **Aucun utilisateur réel n'a été mesuré.** Aucun artefact du repo ne trace une personne identifiable ayant utilisé le système. Le seul document du vault qui se prononce le dit : `OrientAI-Audit-Startup-2026-07-15.md` l.34, "jamais evalue en batterie complete ni par de vrais utilisateurs". Le panel "5 personas humains" du dossier INRIA (l.38, l.723) n'est adossé à aucune trace de collecte, et les artefacts (§3.2) indiquent une simulation LLM.

2. **Pas de logs de production analysés.** `logs/` (276 Ko, `du -sh`) ne contient que des logs de bench (`bench_gen_20260419.log`, `bench_persona_complet_run1.log`, `audit_enums.log`...). Aucun fichier de trafic utilisateur, aucun export d'analytics. Langfuse est mentionné comme outil d'observabilité (`docs/OBSERVABILITY_BASELINE_2026-05-13.md`, `audit_empirique_2026-06-09/langfuse_dataset.py`, `results/PROOF_langfuse.txt`), mais sur des runs de bench, pas sur des sessions réelles.

3. **Pas de multi-tour dans les bancs d'évaluation.** Aucun champ `history`/`turns` dans les 15 fichiers de questions inspectés. Le seul harnais multi-tour est `sim_multitour.py` (4 conversations × 2 tours, seconds tours codés en dur) et **son output `results/sim_multitour_lot.md` n'existe pas** (`find . -name "*multitour*"`). Le mode récit multi-tour est livré en prod (`OrientAI-Audit-Startup-2026-07-15.md` l.34, ADR-061) sans banc d'évaluation dédié.

4. **La réorientation post-bac est quasi absente du banc gelé.** Sur les 497 items, 4 seulement mentionnent une réorientation ou un niveau L1/L2 - et ce sont les 4 variantes lexicales d'**une seule base** : "Je suis en L2 d'éco et je veux me réorienter vers l'informatique, comment faire ?" (`build_eval_set.py` l.205). C'est le segment que les retours identifient comme l'avantage concurrentiel potentiel (`results/user_test/feedback_20ans.md` l.67 : *"on sent que c'est moins bien traité que les questions 'terminale standard'. Pourtant c'est là que ton outil devrait briller"*) et que l'audit startup désigne comme niche cible (`OrientAI-Audit-Startup-2026-07-15.md` l.81, "missions locales / decrochage / reorientation post-bac"). Il est mieux couvert par golden_50/60 (10 items `reorientation`) et par `hallu_questions_baseline.json`, mais pas par la mesure longitudinale.

5. **Aucun typage persona formalisé dans le code d'évaluation.** `grep -rn "persona" src/eval/*.py` → 0 résultat. `grep -rn "persona" docs/BENCH_GATES.md` → 0 résultat. Le mot n'apparaît dans `src/` que côté produit (`src/prompt/system.py`, `src/agents/hierarchical/empathic_agent.py`, `src/agent/tools/query_reformuler.py`). Le typage lycéen / étudiant / adulte n'existe donc que sous forme de **catégories thématiques** (golden_50/60 : `lyceen_parcoursup`, `reorientation`) ou de fiches markdown de jeu de rôle (`results/gate_j6/personas/`), jamais comme dimension d'analyse des résultats. `docs/DECISION_LOG.md` ADR-036 le note d'ailleurs comme non livré : "Pré-filtrage public par situation [...] le `user_level classifier` (Tier 2.2) existe mais n'est pas encore branché sur le composer", et conclut : "les deux autres enrichissements (couche métier, pré-filtrage public) sont **intacts, non implémentés**".

6. **Pas de mesure d'accessibilité ni de public non scolaire hors reconversion adulte.** 28 items `reconversion_adulte` dans le 497q (7 bases), aucun sur les publics en situation de handicap, allophones, décrochage scolaire, ou parents (le persona `catherine_52` n'a pas de questions dédiées dans les bancs, seulement 3 Q hard partagées).

7. **Pas de mesure de satisfaction ou de préférence A/B contre ChatGPT**, alors que la comparaison est le critère de succès annoncé : `docs/STRATEGIE_VISION_2026-04-16.md` l.685, "Test utilisateur B4 | Préférence > 70% pour OrientIA vs ChatGPT" et l.784, "**5-10 étudiants réels, pas un seul LLM**". Le test B4 n'a laissé aucun artefact dans `results/` (aucun répertoire `b4`, aucune préférence chiffrée). La comparaison avec ChatGPT n'existe que comme opinion dans les feedbacks simulés.

8. **Les 100 questions du banc Run F n'ont que 8 réponses idéales** (`src/eval/ideal_answers.json`, 8 clés pour 100 questions) : 92 % du banc historique n'a pas de référence humaine.

---

## Synthèse en trois lignes

Tous les bancs d'évaluation d'OrientIA sont **écrits ou générés par l'agent**, dont le banc longitudinal de référence (497q = 155 questions de base gonflées ×4 par variantes lexicales, `build_eval_set.py` l.287-302). Les cinq "tests utilisateurs" et le verdict 2/5 proviennent de **personas LLM**, pas de personnes (`answers_CO.md` l.1, `ground_truth_v3_humain_resimule_claude_sonnet.json`, mtime identiques), ce que le vault confirme (`OrientAI-Audit-Startup-2026-07-15.md` l.34) et que le dossier INRIA contredit sans référence (l.38, l.723). Ce qui n'est pas mesuré : le multi-tour, la réorientation post-bac au-delà d'une seule question, le trafic réel, et la préférence vs ChatGPT qui est pourtant le critère de succès affiché.
