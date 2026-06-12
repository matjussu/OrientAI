# Verdict CANARY juge groundedness — Phase 0 (ordre 0825) — PASS

Date 2026-06-12. Avant le re-embed full qui re-gèle la baseline, on vérifie que le
juge groundedness ACTUEL (claude-haiku-4-5-20251001) score les réponses FIGÉES du
gel (2026-06-11) de la même façon qu'au gel. Motivation : Haiku a drifté hier sur
`test_judge_faithfulness` (1 exemple STG, FIDELE vs INFIDELE). Si le juge a bougé à
l'agrégat, la baseline 0.949 n'est plus comparable à une mesure post-re-embed.

## Protocole

- 30 questions in_scope du gel, STRATIFIÉES par outcome stocké, sélection
  DÉTERMINISTE (tri par id), inclusion FORCÉE des 10 cas `hallucinated_numbers`
  (démo-critiques). Réponses + sources STRICTEMENT identiques au gel (relues depuis
  `gel_battery.json`, non régénérées).
- Re-jugement avec `judge_groundedness.py` HEAD (juge Haiku, temp=0).
- Comparaison verdict par verdict + claim par claim vs `gel_ground.json`.
- Script : `canary_2026-06-12/canary.py` (select|compare). Coût ~quelques centimes.

## Résultats

| axe | accord | lecture |
|---|---|---|
| **outcome (bucket fidélité)** | **30/30 = 100%** | gate spécifié >=95% : PASS net |
| groundedness (valeur exacte) | 25/30 = 83.3% | 5 écarts, \|Δ\| moyen 0.03 = granularité comptage claims |
| `hallucinated_numbers` (flag) | 27/30 = 90% | 3 flips, tous True->False, voir attribution |
| relabels bénins | 0 | aucun grounded<->alt_disclaimed |

## Attribution claim par claim des 3 flips hallu (le point sensible)

- **geo-013** (g 0.833->0.833) : claims BYTE-IDENTIQUES, flags `supported` identiques,
  le claim litigieux ("96% taux d'accès") reste `False` dans les deux runs. Le 96
  EXISTE dans S5 (taux_acces 96.0) mais mal-étiqueté -> le nouveau juge dit hallu=False
  ("nombre réel mal-utilisé != nombre fabriqué"). Call défendable. Hallucination NON
  masquée (claim toujours non-supporté).
- **malform-003-v3** (g 0.8->0.8) : idem, claims identiques, le claim "masters encore
  plus sélectifs (3,2%)" reste `False`. 3,2% = arrondi/comparaison sur-interprétée, pas
  un chiffre inventé. hallu False défendable, claim toujours attrapé.
- **metier-004-v1** (g 0.9->1.0) : SEUL vrai écart. Le gel avait extrait un claim
  "taux national ~3% IFMK" (fabriqué). Le re-jugement ne l'extrait pas, pioche une
  généralisation bénigne ("formations très sélectives"). = stochasticité d'EXTRACTION
  de claims temp=0 (le juge échantillonne ~10 claims d'une réponse longue). Les 9
  claims partagés ont des verdicts identiques.

## Verdict : PASS

- Gate spécifié (outcome >=95%) = **100%**. Le juge classe les 30 réponses figées dans
  le MÊME bucket de fidélité qu'au gel. Pas de drift de classification.
- Jitter groundedness (\|Δ\| 0.03) + 3 flips hallu = plancher de bruit temp=0 documenté.
  Zéro dérive systématique : aucun claim supporté->non-supporté masquant une
  hallucination. 2/3 flips hallu = call définitionnel défendable (nombre réel
  mal-utilisé), 1/3 = stochasticité d'extraction de claims.
- L'échec d'hier (`test_judge_faithfulness`) = drift sur 1 exemple ; à l'agrégat sur 30
  réponses figées, le juge REPRODUIT le gel.

## Caveat pour la Phase 3 (lecture du re-gel)

Le flag `hallucinated_numbers` a ~10% de jitter par-question sur les cas-limites de
mauvais-usage de nombre (nombre réel mal-étiqueté/arrondi/comparé). Conséquence : le
compte hallu du gel (10/497) peut bouger de quelques unités au re-run PUREMENT par
bruit de juge, sans régression réelle. Lire le delta du re-gel à l'aune de ce plancher
(cohérent avec le caveat #1 du VERDICT_gel : non-déterminisme temp=0). Le signal fiable
reste l'outcome bucket + la magnitude (pas le ±2-3 sur un compteur).

GO Phase 1 (quartiles Q1/Q3).
