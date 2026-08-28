"""Sprint 12 axe 2 — Judge Claude Sonnet rubric pour bench α-comparatif.

Référence ordre : 2026-05-01-1820 Option α-comparatif GO Matteo 17:09 CEST.

## Stratégie

Charge `responses_triangulaire.jsonl` (10q × 3 systèmes) → blinde les
labels par question (seed-déterministe, A/B/C randomisés) → appelle
`judge_question` Claude Sonnet 4.5 (rubric 6 critères 0-3 = 18 max,
cf `src/eval/judge.py`) → maps labels → systèmes → aggrège scores.

## Output

`results/sprint12-axe-2-agent-pipeline-bench/judge_scores.json` avec :
- per_question_blinded : labels randomisés + scores judge bruts
- per_question_mapped : assignation label→system + scores
- per_system_aggregated : avg total, avg per-criterion, win count
- deltas : Δ(agent − rag_enriched), Δ(agent − baseline), Δ(rag_enriched − baseline)

## Coût estimé

10 questions × 1 judge call (3 réponses dans 1 call) × ~$0.10/call = ~$1.00.
Sous budget bench α-comparatif <$15.

## Critères mesurables Phase 1

- **GO α-vintage** : Δ(agent − rag_enriched) ≥ 0 → agentic vintage suffit
- **NO-GO α-vintage** : Δ < 0 → rag_enriched supérieur, justification
    chiffrée pour migration α-enrichi (Sprint 12+ effort 1-2j)

Usage :
    PYTHONPATH=. python3 scripts/judge_axe2_alpha_comparatif_2026-05-01.py
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from anthropic import Anthropic  # noqa: E402

from src.config import load_config  # noqa: E402
from src.eval.judge import judge_question  # noqa: E402


RESPONSES_PATH = REPO_ROOT / "results" / "sprint12-axe-2-agent-pipeline-bench" / "responses_triangulaire.jsonl"
OUT_PATH = REPO_ROOT / "results" / "sprint12-axe-2-agent-pipeline-bench" / "judge_scores.json"
SEED = 42
SYSTEM_KEYS = ("agent_pipeline_v3_2", "our_rag_enriched", "mistral_v3_2_no_rag")


def main() -> int:
    print(f"[judge-α] Loading config + Anthropic client...")
    cfg = load_config()
    client = Anthropic(api_key=cfg.anthropic_api_key, timeout=120.0)

    print(f"[judge-α] Loading responses : {RESPONSES_PATH}")
    with RESPONSES_PATH.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    print(f"[judge-α]   {len(records)} questions")

    rng = random.Random(SEED)
    per_question_blinded = []
    per_question_mapped = []

    print(f"\n[judge-α] === RUN judge ({len(records)} calls Claude Sonnet 4.5) ===")
    for i, rec in enumerate(records, 1):
        qid = rec["qid"]
        question = rec["question"]

        # Construct answers dict + randomize labels
        sys_to_text = {
            sys_key: rec[sys_key]["answer_text"]
            for sys_key in SYSTEM_KEYS
        }
        # Randomize label assignment per question for blinding
        keys_shuffled = list(sys_to_text.keys())
        rng.shuffle(keys_shuffled)
        labels = ["A", "B", "C"]
        label_to_system = dict(zip(labels, keys_shuffled))
        answers_blinded = {
            label: sys_to_text[label_to_system[label]]
            for label in labels
        }

        print(f"\n[judge-α] Q{i}/{len(records)} {qid} (label_to_system={label_to_system})")
        try:
            t0 = time.time()
            scores = judge_question(client, question, answers_blinded, model="claude-sonnet-4-5")
            elapsed = time.time() - t0
            for label in labels:
                if label in scores:
                    print(f"  {label} ({label_to_system[label]:25s}) total={scores[label].get('total', 0)}")
            print(f"  judge elapsed: {elapsed:.1f}s")
        except Exception as e:
            print(f"  ⚠️  judge error: {e}")
            scores = {label: {"total": 0, "error": str(e)} for label in labels}

        per_question_blinded.append({
            "qid": qid,
            "category": rec.get("category"),
            "label_to_system": label_to_system,
            "scores": scores,
        })

        # Map back to system names for aggregation
        scores_mapped = {
            label_to_system[label]: scores.get(label, {})
            for label in labels
        }
        per_question_mapped.append({
            "qid": qid,
            "category": rec.get("category"),
            "scores_per_system": scores_mapped,
        })

    # Aggregate per-system stats
    per_system_aggregated = {}
    for sys_key in SYSTEM_KEYS:
        totals = [
            q["scores_per_system"][sys_key].get("total", 0)
            for q in per_question_mapped
            if sys_key in q["scores_per_system"]
        ]
        # Per-criterion averages
        criteria = ("neutralite", "realisme", "sourcage", "diversite_geo", "agentivite", "decouverte")
        crit_avgs = {}
        for crit in criteria:
            vals = [
                q["scores_per_system"][sys_key].get(crit, 0)
                for q in per_question_mapped
                if sys_key in q["scores_per_system"]
            ]
            crit_avgs[crit] = round(sum(vals) / len(vals), 2) if vals else 0.0
        per_system_aggregated[sys_key] = {
            "n": len(totals),
            "total_avg": round(sum(totals) / len(totals), 2) if totals else 0.0,
            "total_min": min(totals) if totals else 0,
            "total_max": max(totals) if totals else 0,
            "criteria_avg": crit_avgs,
        }

    # Win counts (best-of-3 per question, ties OK)
    win_counts = {sys_key: 0 for sys_key in SYSTEM_KEYS}
    tie_count = 0
    for q in per_question_mapped:
        totals = {sys_key: q["scores_per_system"][sys_key].get("total", 0) for sys_key in SYSTEM_KEYS}
        max_total = max(totals.values())
        winners = [sys_key for sys_key, t in totals.items() if t == max_total]
        if len(winners) == 1:
            win_counts[winners[0]] += 1
        else:
            tie_count += 1

    # Compute deltas (key Phase 1 question)
    deltas = {
        "agent_minus_rag_enriched": round(
            per_system_aggregated["agent_pipeline_v3_2"]["total_avg"]
            - per_system_aggregated["our_rag_enriched"]["total_avg"],
            2,
        ),
        "agent_minus_baseline": round(
            per_system_aggregated["agent_pipeline_v3_2"]["total_avg"]
            - per_system_aggregated["mistral_v3_2_no_rag"]["total_avg"],
            2,
        ),
        "rag_enriched_minus_baseline": round(
            per_system_aggregated["our_rag_enriched"]["total_avg"]
            - per_system_aggregated["mistral_v3_2_no_rag"]["total_avg"],
            2,
        ),
    }

    # Save full results
    summary = {
        "n_questions": len(records),
        "seed": SEED,
        "model_judge": "claude-sonnet-4-5",
        "per_system_aggregated": per_system_aggregated,
        "win_counts": win_counts,
        "tie_count": tie_count,
        "deltas": deltas,
        "per_question_blinded": per_question_blinded,
        "per_question_mapped": per_question_mapped,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[judge-α] saved : {OUT_PATH}")

    # Print summary
    print("\n========== JUDGE SUMMARY ==========")
    print(f"Per-system avg total (max=18) :")
    for sys_key, stats in per_system_aggregated.items():
        print(f"  {sys_key:25s} : avg={stats['total_avg']:5.2f} (min={stats['total_min']}, max={stats['total_max']})")
    print(f"\nWin counts (best-of-3, ties=...) :")
    for sys_key, n in win_counts.items():
        print(f"  {sys_key:25s} : {n}/{len(records)} wins")
    print(f"  ties                      : {tie_count}/{len(records)}")
    print(f"\nDELTAS :")
    print(f"  agent − rag_enriched      = {deltas['agent_minus_rag_enriched']:+.2f}")
    print(f"  agent − baseline          = {deltas['agent_minus_baseline']:+.2f}")
    print(f"  rag_enriched − baseline   = {deltas['rag_enriched_minus_baseline']:+.2f}")
    print("====================================\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
