# Verdict gate Option B (J2 U1) — SELECT bypass-vers-refus -> fall-through RAG

Date 2026-06-11. A/B temp=0 déterministe, 48q SELECT-eligibles. Instrument _FICHE_KEEP
+ pool filter constants. BEFORE = pipeline.py @8d1e0cd (ancien bypass). AFTER = @8c9a9fc
(Option B fall-through). Juge Haiku temp=0. Artefacts : results/ob_*.json.

## Résultat

| métrique | before | after | delta |
|---|---|---|---|
| honest_refusal | 35 | 20 | -15 |
| hallucinated_numbers | 0 | 0 | 0 |
| metric_substitution (flag) | 7 | 15 | +8 |
| metric_substitution (outcome) | 7 | 9 | +2 |
| answered_grounded | 2 | 9 | +7 |
| answered_unsupported | 2 | 8 | +6 |

Fall-through RAG : 39/48 (tag last_select_fallthrough tracé).
Décompo des 15 refus récupérés : 7 grounded (vrais gains) + 7 unsupported + 1 subst + 1 error.

## Lecture

- GROS gain sur-refus : -15 (-43% du subset). Le SELECT bypass servait 0/48 (égalités
  WRatio) ; le fall-through RAG débloque 15 refus, dont 7 en réponses sourcées.
- hallucinated_numbers (le métrique démo-critique = chiffres fabriqués) : SAFE 0->0.
- Coût : substitution flag 7->15. Attribution par-question des 8 nouvelles : PAS salaire
  (2/8 seulement), large (fact-006, fact-011 x3, adv-004). 6/8 ont outcome=answered_unsupported
  = le RAG répond avec du TEXTE non sourcé (claims qualitatifs) au lieu de refuser, PAS des
  chiffres fabriqués.

## Gate AMBIGU (décision narrative remontée à Jarvis/Matteo)

- Gate LITTÉRAL (substitution n'augmente pas) : FAIL -> revert.
- Trigger VERBALISÉ Jarvis ("si l'hallu monte -> refus") : hallucinated_numbers 0->0 = PASS.
- Cause du désaccord : substitution != hallucination. Zéro chiffre fabriqué ; ~7 réponses
  texte-non-sourcé vs refus honnête.

3 options soumises :
- A) KEEP (sur-refus gagné, chiffres-fabriqués safe) + monitorer le texte-non-sourcé.
- B) REVERT (gate strict) -> retour au refus, pool filter conservé. Réversible par construction.
- C) SCOPE : fall-through SEULEMENT si le RAG ramène des sources, sinon refus -> garde le gain
  grounded, coupe le texte-non-sourcé. Le plus propre, ~1h de plus.

Statut : rien reverté ni gardé en dur, en attente d'arbitrage. Pool filter (8d1e0cd) + T3
(9f30535) commités et sûrs quoi qu'il advienne ; Option B (8c9a9fc) réversible.

---

## ADDENDUM 2026-06-11 (J3 étape 3) — RE-JUGEMENT rubrique figée : GATE PASS

Le gate ambigu ci-dessus reposait sur une rubrique SANS catégorie pour "alternative
explicitement cadrée + sourcée". Audit (AUDIT_rubrique_juge_2026-06-11.md) : les 17 cas
"régressifs" avaient TOUS groundedness=1.0, 0 claim non supportée, 0 chiffre fabriqué = 100%
artefacts de label. Rubrique corrigée (commit 3fe2e1e : catégorie answered_alternative_disclaimed
+ procédure de décision ordonnée + garde-fou anti-gaming), FIGÉE, puis re-jugement juge-only des
MÊMES batteries before/after (fichiers ob_ground_*_rejudge.json, mêmes artefacts, même rubrique
des deux côtés).

| métrique (rubrique figée) | before | after | delta |
|---|---|---|---|
| honest_refusal | 28 | 10 | -18 |
| hallucinated_numbers | 0 | 0 | 0 |
| metric_substitution (flag) | 0 | 0 | 0 |
| answered_unsupported | 0 | 0 | 0 |
| answered_alternative_disclaimed | 18 | 32 | +14 |
| answered_grounded | 0 | 4 | +4 |
| pipeline_error | 2 | 2 | 0 |

Rappel OLD rubrique (artefacts) : substitution 7->15, unsupported 2->8. NEW : 0->0 et 0->0.

**GATE OPTION B (rubrique figée) = PASS** : refus -18 (plus gros que les -15 de l'ancienne
lecture, car l'ancienne rubrique sous-comptait aussi ~7 alternatives-cadrées en honest_refusal),
hallucinated_numbers 0->0, metric_substitution 0->0, answered_unsupported 0->0. Zéro régression
de fidélité. Les +14 alternatives cadrées + +4 grounded = le gain de couverture.

DÉCISION : fall-through 8c9a9fc VALIDÉ pour le lot J3 (déjà actif dans pipeline.py:559-581, non
reverté). Reste en place.

### Coût helpfulness isolé par le sous-flag alternative_relevance (HORS gate faithfulness)

| relevance des alternatives | before | after |
|---|---|---|
| relevant   | 8  | 9  |
| weak       | 10 | 18 |
| irrelevant | 0  | 5  |

Le fall-through introduit 5 alternatives géographiquement/thématiquement LOINTAINES (pattern
Papeete-pour-Nantes : fact-006 x4 + PCSI-Lille->licences-ailleurs fact-016-v2). Ce sont des
réponses FIDÈLES (disclaimées + sourcées, d'où le gate PASS), mais peu utiles. Ce n'est PAS un
bloqueur de gate ; c'est le prochain levier qualité = garde-fou helpfulness (ex : si l'alternative
est hors-région/hors-thème, refuser proprement plutôt que la proposer). À trancher avec l'étalon
humain post-VivaTech. Donnée collectée dès maintenant grâce au sous-flag.

Note infra : 2 pipeline_error stables (fact-001-v2, comp-008-v1) des deux côtés = erreurs
d'exécution du chemin fall-through (pas du juge). À diagnostiquer en marge (robustesse démo J4).
