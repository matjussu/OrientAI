# Verdict garde-fou géo déterministe NARROW (J3 étape 4b)

Date 2026-06-11. Garde-fou helpfulness GO Matteo (option B). Remplace le prompt-only
RÈGLE 9 (reverté : un prédicat déterministe sur champ region nullable n'est pas un
travail de prompt — cas phare Papeete non coupé + sur-refus intra-région, mesuré).

Helper `src/rag/geo_coherence.py` (pur, testable), court-circuit post-retrieval dans
`pipeline._prepare_for_generation`. Commit f063abd. 18 tests TDD verts.

## Mesure — DÉTERMINISTE (instrument correct)

Un A/B full-run (geo OFF rf1b vs geo ON) est NOISE-DOMINATED : le pipeline a une
non-déterminisme run-to-run même à temp=0 (retrieval/RRF), ~12 questions NON-géo
changent d'outcome entre deux runs. Le garde-fou ne touche que les questions où il
tire (court-circuit pré-génération). Donc on mesure le garde-fou DÉTERMINISTIQUEMENT :
`geo_coherence_check(question, sources_fixées)` sur les sources d'un run figé (rf1b).

Résultat (sources rf1b, 48q) :
- LE GARDE-FOU TIRE sur EXACTEMENT 4 questions : la famille fact-006 (base/v1/v2/v3),
  toutes = "BTS Commerce International à Nantes" avec pour seule source un BTS à Papeete
  (Polynésie). Out-of-zone clair -> refus + relais. ACCEPTANCE OK.
- SUR-REFUS INTRA-RÉGION : AUCUN. Lyon, Annecy, Bordeaux, Rennes, Montpellier, Lille
  (toutes les villes intra-région du subset) -> abstention. NON-RÉGRESSION OK.
- Zones (None,None) = famille comp-008 (comparaison multi-villes) -> abstention. OK.
- hallu : le garde-fou ne fait que refuser, il ne peut pas halluciner. 0.

## Gate (b) géo : PASS

- irrelevant clairs (Papeete) convertis en refus : OUI (4/4 fact-006 en déterministe ;
  3/4 en live, le 4e a un retrieval live différent = bruit, pas un défaut garde-fou).
- zéro nouveau refus intra-région : OUI (déterministe, 0).
- hallu 0 : OUI.

## Caveat harnais (à reporter)

Le bruit de génération run-to-run à temp=0 sur le subset 48q (~12 questions churned
entre rf1b et geo) est un signal SÉPARÉ : le harnais n'est pas pleinement déterministe
(probablement retrieval FAISS/RRF/ordre async). Conséquence pour le gel 497q : la mesure
497q doit être lue en attribution PAR-QUESTION, pas en deltas d'agrégat sur petits N, et
idéalement une seule passe propre. Renforce la leçon feedback_gate_noise_single_run_ab.

## Désactivation

`enable_geo_coherence=False` à l'init du pipeline -> garde-fou off (revertable).
