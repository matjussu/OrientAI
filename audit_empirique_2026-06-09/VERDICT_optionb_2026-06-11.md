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
