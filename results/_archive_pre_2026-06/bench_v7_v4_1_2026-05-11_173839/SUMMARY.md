# Bench summary — `bench_v7_v4_1_2026-05-11_173839`

**Verdict global** : ❌ NO-GO — gates au rouge : Gate 1 — Retrieval golden_60, Gate 5 — Rubric LLM-judge externe

Gates appliquées par référence à `docs/BENCH_GATES.md` (Phase D du plan verrouillage-bench-multi-tour).

---

## Gate 1 — Retrieval golden_60 — ❌ FAIL

- recall@5 global : 64.8% (cible ≥75%) ❌ FAIL
- MRR global : 0.723 (cible ≥0.55) ✅ PASS
- nDCG@10 global : 0.725 (cible ≥0.65) ✅ PASS
- Catégories <60% : live=50.0%, reorientation=50.0% ❌

## Gate 2 — Honesty mini-bench v4.1 — ⏭ SKIPPED


## Gate 3 — Latency p95 — ✅ PASS

- p50 : 5.75s (cible ≤8s) ✅ PASS
- p95 : 11.24s (cible ≤12s) ✅ PASS
- Aucun timeout >30s : max=15.48s ✅ PASS

## Gate 4 — Robustesse adversariale — ✅ PASS

- refusal adversarial : 90.0% (cible ≥80%) ✅ PASS
- refusal cross_domain : 100.0% (cible 100%) ✅ PASS
- Hallucinations Haiku confidence ≥0.8 : 0 (cible 0) ✅ PASS

## Gate 5 — Rubric LLM-judge externe — ❌ FAIL

- Claude our_rag /18 : 10.75 (cible ≥12) ❌ FAIL
-   Δ vs neutral baselines : +1.30 pts (cible ≥+1.0) ✅ PASS
- GPT-4o our_rag /18 : 8.18 (cible ≥12) ❌ FAIL
-   Δ vs neutral baselines : -3.63 pts (cible ≥+1.0) ❌ FAIL

## Gate 6 — Honesty Haiku factcheck — ⏭ SKIPPED

- Haiku format inattendu, parse impossible

---

## Annexe : artefacts présents

- `audit_v7.md` (3,265 bytes)
- `eval_recall_v7.json` (102,328 bytes)
- `factcheck/scores_haiku.json` (1,511,349 bytes)
- `generation/label_mapping.json` (14,841 bytes)
- `generation/responses_blind.json` (1,408,823 bytes)
- `generation/seed.txt` (2 bytes)
- `judges/scores_claude.json` (176,380 bytes)
- `judges/scores_gpt4o.json` (154,603 bytes)
- `mini_bench.json` (70,483 bytes)
- `spot_check.txt` (2,366 bytes)