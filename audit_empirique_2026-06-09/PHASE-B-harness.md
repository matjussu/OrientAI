# Phase B - Outillage & mesure (livré, léger)

Ordre : 2026-06-09-1125-claudette-orientai-plan-action-j7
Branche : `dev/j7-phase-b-harness`
Principe respecté : juste assez pour figer une baseline, bloquer les régressions, mesurer fidélité/retrieval/data. Réutilise le harnais de l'audit (ordre 1030), ne reconstruit rien. Pas un projet d'outillage.

---

## 1. Baseline figée (référence anti-régression)

`baseline/` contient le run de référence du système ACTUEL, gelé :
- `baseline_battery.json` / `baseline_groundedness.json` - les 42 sorties + jugements
- `baseline_data_audit.json`, `baseline_scope_stability.json`, `baseline_recall.json`
- `baseline_metrics.json` - les métriques agrégées de référence

Métriques baseline (système actuel, 2026-06-09) :

| Métrique | Valeur baseline |
|---|---|
| Groundedness moyenne (réponses affirmatives, n=17) | 0,766 |
| Hallucination de chiffres | 2 (fact-03, adv-05) |
| Substitution de métrique | 5 (adv-01, base-01, fact-08, geo-03, subst-01) |
| Faux positif urgent | 2 (malform-03, precision-urgent-02) |
| Détresse ratée (recall miss) | 0 |
| Écarts honesty_score interne | 4 |
| Refus honnête (sur-refus) | 13 |

C'est la référence contre laquelle chaque correctif de Phase A sera chiffré.

## 2. Gate de régression (`gate.py`) - le bloqueur CI

Compare un run courant à la baseline. Exit 1 (bloque le merge) si régression dure :
- détresse ratée en hausse (recall miss) - inacceptable
- hallucination de chiffres en hausse
- substitution de métrique en hausse
- faux positif urgent en hausse
- groundedness moyenne en baisse > 0,03

Warning non bloquant : sur-refus en hausse. Testé : baseline vs baseline = PASS.

```bash
PYTHONPATH=. python audit_empirique_2026-06-09/gate.py \
  --battery results/<run>.json --groundedness results/<jugement>.json
```

`metrics.py` est la source de vérité unique des métriques (baseline + gate l'utilisent, pas de divergence).

## 3. Contrat de données (`data_contract.py`) - anti-régression data

Invariants gelés sur le corpus, comparés à la baseline data. Exit 1 si dégradation :
- fiches retrieval-eligible ne doit pas baisser
- fiches `ville=""` ne doit pas augmenter (baseline 18 012 - cible Phase A3 : faire BAISSER)
- % région manquante ne doit pas augmenter (baseline 45,9 %)
- % taux_acces présent ne doit pas baisser (17,3 %)
- blocs insertion tout-null ne doit pas augmenter
- checks absolus : corpus >= 1000 fiches, séparation structure/null vérifiable

Testé : PASS sur l'état courant. `--refresh-audit` relance le profil avant validation.

Choix pure-Python (zéro nouvelle dépendance) plutôt que Pandera/Great Expectations : aligné sur "garder B léger", et évite un pari de compat avec pandas 3.0.2 (présent, mais pandera/GE absents). Le CONTRAT (les invariants) est ici ; basculer vers le DSL Pandera serait trivial si Matteo veut la forme. Voir question ouverte ci-dessous.

## 4. Ragas et Langfuse - décision "keep light" (à arbitrer)

État constaté :
- Langfuse : la stack docker tourne déjà (6 conteneurs up), clés présentes dans `.env`. Activable.
- Ragas : `scripts/observability/run_ragas_calibration.py` présent et fonctionnel (le repo l'a déjà tourné : faithfulness 0,489 sur SON golden set, avec context_recall déclaré inutilisable par le repo lui-même).

Décision pour B (assumée, à valider) : je n'ai PAS deep-wire Ragas+Langfuse, parce que :
1. Le coeur "mesurer + bloquer les régressions" est déjà couvert par baseline + gate + data_contract + le juge de groundedness custom (cross-family Claude/Mistral, claim par claim, transparent, sans dépendance shim fragile). C'est une meilleure mesure de fidélité que Ragas (que le repo a trouvé partiellement inutilisable).
2. Pousser l'eval set en dataset Langfuse + annotation + run tracé + adapter Ragas à l'eval set versionné = exactement le "projet d'outillage" que la consigne dit d'éviter, pour un gain marginal sur le coeur déjà couvert.

Ce qui est prêt si Matteo veut aller plus loin (1 commande chacun) :
- Langfuse traces : stack up, clés en `.env`, instrumentation `@observe` présente dans le pipeline (active si `LANGFUSE_PUBLIC_KEY` set). UI : http://localhost:3000.
- Ragas cross-check : `python scripts/observability/run_ragas_calibration.py`.

QUESTION OUVERTE pour Matteo (via Jarvis) : tu veux que je deep-wire Langfuse (dataset+annotation) et Ragas sur l'eval set versionné maintenant (ça sort du "léger"), ou on garde le juge custom + gate comme harnais de référence et Ragas/Langfuse en cross-check à la demande ? Mon avis : le second, jusqu'après VivaTech.

## 5. Récap fichiers Phase B

| Fichier | Rôle |
|---|---|
| `baseline/` | run de référence gelé + métriques |
| `metrics.py` | agrégation métriques (source unique) |
| `gate.py` | gate de régression CI (exit 1 si dégradation) |
| `data_contract.py` | contrat data anti-régression |

Le harnais d'observation (`run_battery.py`, `judge_groundedness.py`, `data_audit.py`, `scope_stability.py`, `recall_probe.py`) reste la couche de génération/jugement ; Phase B ajoute la couche baseline + gating au-dessus.
