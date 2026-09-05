# Bench SELECT-ciblé (Sprint refonte 2026-05-05)

**Source** : `data/audit/select_baseline_v1.json`
**Pipeline** : `try_select_or_none` (déterministe, no LLM)
**Fiches** : 55606 entrées

## Métriques agrégées

| Métrique | Valeur |
|---|---|
| Questions testées | 20 |
| **Pass** | 5/20 (25%) |
| via_select=True attendu | 10 |
| via_select=True obtenu | 1 |
| Fallback correctement déclenché | 4/10 |

## Par catégorie

| Catégorie | Pass | Total |
|---|---|---|
| entity_based_existing_school | 1 | 8 |
| entity_based_absent_school | 0 | 4 |
| ambiguous_multi_match | 3 | 4 |
| new_pattern_coverage | 1 | 4 |

## Détail par question

### ❌ S1 — entity_based_existing_school

**Question** : Quel est le taux d'accès Parcoursup 2025 d'EFREI Bordeaux Bachelor Cybersécurité ?

- Attendu : via_select=True / field=taux_acces_parcoursup_2025
- Obtenu : via_select=False / reason=select_ambiguous / field=taux_acces_parcoursup_2025 / fuzzy_score=90
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)

### ❌ S2 — entity_based_existing_school

**Question** : Combien de places en BUT MMI à Bordeaux ?

- Attendu : via_select=True / field=nombre_places
- Obtenu : via_select=False / reason=select_ambiguous / field=nombre_places / fuzzy_score=86
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)

### ❌ S3 — entity_based_existing_school

**Question** : Quelle est la sélectivité de Sciences Po Paris ?

- Attendu : via_select=True / field=taux_acces_parcoursup_2025
- Obtenu : via_select=False / reason=select_ambiguous / field=taux_acces_parcoursup_2025 / fuzzy_score=86
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)

### ❌ S4 — entity_based_existing_school

**Question** : Combien de places en EPF Montpellier ?

- Attendu : via_select=True / field=nombre_places
- Obtenu : via_select=False / reason=select_ambiguous / field=nombre_places / fuzzy_score=90
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)

### ✅ S5 — entity_based_existing_school

**Question** : Quel taux d'emploi à 3 ans pour Master Informatique Université de Bordeaux ?

- Attendu : via_select=True / field=insertion_pro.taux_emploi_3ans
- Obtenu : via_select=True / reason=None / field=insertion_pro.taux_emploi_3ans / fuzzy_score=86
- Verdict : OK — via_select=True attendu et obtenu

### ❌ S6 — entity_based_existing_school

**Question** : Quel salaire après le BTS NDRC à Lyon ?

- Attendu : via_select=True / field=insertion_pro.salaire_median_embauche
- Obtenu : via_select=False / reason=select_ambiguous / field=insertion_pro.salaire_median_embauche / fuzzy_score=86
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)

### ❌ S7 — entity_based_existing_school

**Question** : Combien coûte EFREI Paris ?

- Attendu : via_select=False / reason=select_invalid_value
- Obtenu : via_select=False / reason=select_ambiguous / field=frais_annuels / fuzzy_score=86
- Verdict : FAIL — attendu reason=select_invalid_value, obtenu select_ambiguous
- Comment : Field frais_annuels rare/absent, donc fallback unifié attendu — défendable jury vs hallu RAG

### ❌ S8 — entity_based_existing_school

**Question** : Quel est le taux de CDI après EPITA Paris ?

- Attendu : via_select=True / field=insertion_pro.taux_cdi
- Obtenu : via_select=False / reason=select_ambiguous / field=insertion_pro.taux_cdi / fuzzy_score=86
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)

### ❌ S9 — entity_based_absent_school

**Question** : Quel est le taux d'accès Parcoursup d'Assas Master Droit International ?

- Attendu : via_select=False / reason=select_no_match
- Obtenu : via_select=False / reason=select_ambiguous / field=taux_acces_parcoursup_2025 / fuzzy_score=86
- Verdict : FAIL — attendu reason=select_no_match, obtenu select_ambiguous
- Comment : Assas pas dans corpus formations.json (Sprint 12 Audit B confirmé)

### ❌ S10 — entity_based_absent_school

**Question** : Combien coûte HEC Paris en programme grande école ?

- Attendu : via_select=False / reason=select_no_match
- Obtenu : via_select=False / reason=select_invalid_value / field=frais_annuels / fuzzy_score=86
- Verdict : FAIL — attendu reason=select_no_match, obtenu select_invalid_value
- Comment : HEC pas dans corpus (post-bac vs PGE bac+5)

### ❌ S11 — entity_based_absent_school

**Question** : Quel est le taux d'admission de Polytechnique X ?

- Attendu : via_select=False / reason=select_no_match
- Obtenu : via_select=False / reason=no_pattern_match
- Verdict : FAIL — attendu reason=select_no_match, obtenu no_pattern_match
- Comment : Polytechnique X pas dans corpus (sélection sur concours, pas Parcoursup)

### ❌ S12 — entity_based_absent_school

**Question** : Quel est le salaire après Mines ParisTech ?

- Attendu : via_select=False / reason=select_no_match
- Obtenu : via_select=False / reason=select_ambiguous / field=insertion_pro.salaire_median_embauche / fuzzy_score=86
- Verdict : FAIL — attendu reason=select_no_match, obtenu select_ambiguous
- Comment : Mines ParisTech pas dans corpus

### ❌ S13 — ambiguous_multi_match

**Question** : Quelle est la sélectivité du Bachelor Cybersécurité ?

- Attendu : via_select=False / reason=select_ambiguous
- Obtenu : via_select=False / reason=select_invalid_value / field=taux_acces_parcoursup_2025 / fuzzy_score=95
- Verdict : FAIL — attendu reason=select_ambiguous, obtenu select_invalid_value
- Comment : Bachelor cyber existe à plusieurs écoles, devrait demander précision

### ✅ S14 — ambiguous_multi_match

**Question** : Combien coûte la Licence Informatique ?

- Attendu : via_select=False / reason=select_ambiguous
- Obtenu : via_select=False / reason=select_ambiguous / field=frais_annuels / fuzzy_score=86
- Verdict : OK — fallback select_ambiguous
- Comment : Licence Informatique = N universités françaises

### ✅ S15 — ambiguous_multi_match

**Question** : Quel est le taux d'accès du Master Droit ?

- Attendu : via_select=False / reason=select_ambiguous
- Obtenu : via_select=False / reason=select_ambiguous / field=taux_acces_parcoursup_2025 / fuzzy_score=86
- Verdict : OK — fallback select_ambiguous
- Comment : Master Droit = N universités, sans précision

### ✅ S16 — ambiguous_multi_match

**Question** : Combien de places en BUT Informatique ?

- Attendu : via_select=False / reason=select_ambiguous
- Obtenu : via_select=False / reason=select_ambiguous / field=nombre_places / fuzzy_score=86
- Verdict : OK — fallback select_ambiguous
- Comment : BUT Info = 30+ établissements

### ❌ S17 — new_pattern_coverage

**Question** : Quel est le taux d'insertion à 18 mois pour BUT Informatique IUT Paris ?

- Attendu : via_select=True / field=insertion_pro.taux_emploi_18m
- Obtenu : via_select=False / reason=select_invalid_value / field=insertion_pro.taux_emploi_18m / fuzzy_score=86
- Verdict : FAIL — attendu via_select=True, obtenu False (select_invalid_value)
- Comment : Pattern 'insertion 18 mois' ajouté Sprint refonte 2026-05-05

### ❌ S18 — new_pattern_coverage

**Question** : Combien de candidats ont postulé en Bachelor Cybersécurité EFREI Bordeaux ?

- Attendu : via_select=True / field=admission.volumes.voeux_totaux
- Obtenu : via_select=False / reason=select_ambiguous / field=admission.volumes.voeux_totaux / fuzzy_score=90
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)
- Comment : Pattern voeux/candidats ajouté Sprint refonte 2026-05-05

### ✅ S19 — new_pattern_coverage

**Question** : Quel taux d'insertion à 6 mois pour BTS NDRC ?

- Attendu : via_select=False / reason=select_ambiguous
- Obtenu : via_select=False / reason=select_ambiguous / field=insertion_pro.taux_emploi_6m / fuzzy_score=86
- Verdict : OK — fallback select_ambiguous
- Comment : Pattern 6 mois ajouté + ambigu sans ville/établissement

### ❌ S20 — new_pattern_coverage

**Question** : Nombre de vœux pour BUT MMI Bordeaux 2025 ?

- Attendu : via_select=True / field=admission.volumes.voeux_totaux
- Obtenu : via_select=False / reason=select_ambiguous / field=admission.volumes.voeux_totaux / fuzzy_score=86
- Verdict : FAIL — attendu via_select=True, obtenu False (select_ambiguous)
