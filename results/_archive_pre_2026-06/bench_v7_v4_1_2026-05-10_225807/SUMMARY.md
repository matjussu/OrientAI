# Bench summary — `bench_v7_v4_1_2026-05-10_225807`

**Verdict global** : ❌ NO-GO — gates au rouge : Gate 1 — Retrieval golden_60, Gate 4 — Robustesse adversariale, Gate 5 — Rubric LLM-judge externe

Gates appliquées par référence à `docs/BENCH_GATES.md` (Phase D du plan verrouillage-bench-multi-tour).

---

## Gate 1 — Retrieval golden_60 — ❌ FAIL

- recall@5 global : 54.5% (cible ≥75%) ❌ FAIL
- MRR global : 0.634 (cible ≥0.55) ✅ PASS
- nDCG@10 global : 0.633 (cible ≥0.65) ❌ FAIL
- Catégories <60% : live=50.0%, metier=20.0%, reorientation=40.0% ❌

## Gate 2 — Honesty mini-bench v4.1 — ⏭ SKIPPED


## Gate 3 — Latency p95 — ✅ PASS

- p50 : 6.38s (cible ≤8s) ✅ PASS
- p95 : 11.19s (cible ≤12s) ✅ PASS
- Aucun timeout >30s : max=13.25s ✅ PASS

## Gate 4 — Robustesse adversariale — ❌ FAIL

- refusal adversarial : 60.0% (cible ≥80%) ❌ FAIL
- refusal cross_domain : 0.0% (cible 100%) ❌ FAIL
- Hallucinations Haiku confidence ≥0.8 : 0 (cible 0) ✅ PASS

## Gate 5 — Rubric LLM-judge externe — ❌ FAIL

- Claude our_rag /18 : 10.73 (cible ≥12) ❌ FAIL
-   Δ vs neutral baselines : +1.39 pts (cible ≥+1.0) ✅ PASS
- GPT-4o our_rag /18 : 9.29 (cible ≥12) ❌ FAIL
-   Δ vs neutral baselines : -2.71 pts (cible ≥+1.0) ❌ FAIL

## Gate 6 — Honesty Haiku factcheck — ⏭ SKIPPED

- Haiku format inattendu, parse impossible

---

## Annexe : artefacts présents

- `SUMMARY.md` (1,742 bytes)
- `audit_v7.md` (3,265 bytes)
- `eval_recall_v7.json` (94,160 bytes)
- `factcheck/scores_haiku.json` (114,612 bytes)
- `generation/label_mapping.json` (13,796 bytes)
- `generation/responses_blind.json` (1,288,718 bytes)
- `generation/seed.txt` (2 bytes)
- `judges/scores_claude.json` (161,772 bytes)
- `judges/scores_gpt4o.json` (142,392 bytes)
- `mini_bench.json` (68,804 bytes)
- `spot_check.txt` (2,366 bytes)