"""Sprint 5 — Bench agent pipeline apples-to-apples vs baseline figée.

Triple-run IC95 sur 24 queries balanced subset. Pipeline agentique
(disable FetchStat — économie budget+temps) + StatFactChecker post-hoc
sur les outputs (apples-to-apples avec baseline PR #75 qui utilise
StatFactChecker `src/experimental/fact_checker.py`).

## Subset balanced 24 queries

- 6 personas v4 (idx 1,4,7,10,13,16 = lila_q1, theo_q1, emma_q1,
  mohamed_q1, valerie_q1, psy_en_q1 — couvre 6 personas distincts)
- 6 DARES dédiées (idx 1-6 = q01-q06 prospective core)
- 6 blocs dédiées (idx 1-6 = q01-q06 compétences core)
- 6 user-naturel (idx 1-6 = q11-q16 multi-domain core)

## Fact-check apples-to-apples

`StatFactChecker.verify(answer, sources_aggregated)` post-hoc sur
chaque query × run. Identique à `src/experimental/fact_checker.py` utilisé
par baseline `bench_persona_complet_2026-04-26`.

## Output

`results/sprint5_bench_apples_2026-04-26/run{1,2,3}/` + `_ALL_QUERIES.json`
+ `_AGGREGATE.json` avec IC95.

## Coût

24 queries × 3 runs × ~30s pipeline + ~3s fact-check = ~50 min
wall-clock.
Mistral : ~$0.05 par run (clarify+reformule+gen+fact-check) × 24q × 3 = ~$3.60.

⚠️ Coût supérieur à $0.36 estimé initialement — gen Mistral Medium plus cher
que prévu (~$0.04 par query rien que pour gen). Ping order-info si
explosion budget post-quick-check.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean, stdev


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import faiss  # noqa: E402
from mistralai.client import Mistral  # noqa: E402

from src.agent.cache import LRUCache  # noqa: E402
from src.agent.pipeline_agent import AgentPipeline  # noqa: E402
from src.config import load_config  # noqa: E402
from src.experimental.fact_checker import StatFactChecker  # noqa: E402

from scripts.run_bench_persona_complet import _build_unified_queries  # noqa: E402


PHASED_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseD.json"
PHASED_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseD.index"

OUT_DIR = REPO_ROOT / "results" / "sprint5_bench_apples_2026-04-26"


def _select_balanced_subset(all_queries: list) -> list:
    """Sélectionne 24 queries balanced (6 par sous-suite)."""
    by_suite = {}
    for q in all_queries:
        s = q["suite"]
        by_suite.setdefault(s, []).append(q)

    # 6 personas v4 : un par persona (q1) — couvre 6 personas distincts
    personas_subset = [q for q in by_suite.get("personas_v4", [])
                       if q["id"].endswith("_q1")][:6]

    # 6 DARES : q01-q06
    dares_subset = by_suite.get("dares_dedie", [])[:6]
    blocs_subset = by_suite.get("blocs_dedie", [])[:6]
    user_subset = by_suite.get("user_naturel", [])[:6]

    return personas_subset + dares_subset + blocs_subset + user_subset


def _run_one_run(
    run_label: str,
    queries: list,
    pipeline: AgentPipeline,
    checker: StatFactChecker,
    out_subdir: Path,
) -> dict:
    """Exécute un run complet : pipeline + StatFactChecker post-hoc."""
    out_subdir.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*60}\n=== Run {run_label} ({len(queries)} queries) ===\n{'='*60}")

    results = []
    for i, q in enumerate(queries, 1):
        if i > 1:
            time.sleep(2)

        suite = q["suite"]
        qid = q["id"]
        print(f"\n[{i:2d}/{len(queries)}] [{suite:<13}] {qid}")
        print(f"    \"{q['text'][:80]}{'...' if len(q['text']) > 80 else ''}\"")

        # Pipeline
        result = pipeline.answer(q["text"])
        if result.error:
            print(f"    ❌ pipeline error : {result.error[:120]}")
            entry = {
                "suite": suite, "query_id": qid, "query_text": q["text"],
                "elapsed_pipeline_s": result.elapsed_total_s,
                "error": result.error,
            }
            results.append(entry)
            continue

        # StatFactChecker post-hoc apples-to-apples
        t_fc_0 = time.time()
        fc_input_sources = [
            {"score": s.get("score", 0), "fiche": s.get("fiche", {})}
            for s in result.sources_aggregated
        ]
        try:
            fc_report = checker.verify(result.answer_text, fc_input_sources)
            fc_summary = fc_report.summary if fc_report else None
            fc_stats = [
                {
                    "stat_text": s.stat_text,
                    "stat_value": s.stat_value,
                    "stat_unit": s.stat_unit,
                    "context": s.context_in_response,
                    "verdict": s.verdict,
                    "source_excerpt": s.source_fiche_excerpt,
                }
                for s in (fc_report.stats_extracted if fc_report else [])
            ]
            fc_elapsed = round(time.time() - t_fc_0, 2)
            fc_error = None
        except Exception as e:
            fc_summary = None
            fc_stats = []
            fc_error = f"{type(e).__name__}: {e}"
            fc_elapsed = round(time.time() - t_fc_0, 2)

        if fc_summary:
            print(f"    ✅ pipeline {result.elapsed_total_s}s + fc post-hoc {fc_elapsed}s")
            print(f"       fact-check: {fc_summary.get('n_stats_total',0)} stats → "
                  f"{fc_summary.get('n_verified',0)}✅ / "
                  f"{fc_summary.get('n_with_disclaimer',0)}🟡 / "
                  f"{fc_summary.get('n_hallucinated',0)}🔴")
        else:
            print(f"    ⚠️ fc error : {fc_error}")

        entry = {
            "suite": suite,
            "query_id": qid,
            "query_text": q["text"],
            "answer_text": result.answer_text,
            "elapsed_pipeline_s": result.elapsed_total_s,
            "elapsed_fact_check_post_hoc_s": fc_elapsed,
            "elapsed_clarify_s": result.elapsed_clarify_s,
            "elapsed_reformulate_s": result.elapsed_reformulate_s,
            "elapsed_retrieve_s": result.elapsed_retrieve_s,
            "elapsed_generate_s": result.elapsed_generate_s,
            "fact_check_summary": fc_summary,
            "fact_check_stats": fc_stats,
            "fact_check_error": fc_error,
            "n_sources_aggregated": len(result.sources_aggregated),
            "domains_top_k": sorted({s.get("fiche", {}).get("domain", "formation")
                                     for s in result.sources_aggregated}),
            "sub_queries": [sq.to_dict() for sq in result.plan.sub_queries] if result.plan else [],
        }
        # Save per-query
        out_path = out_subdir / f"query_{i:02d}_{suite}_{qid}.json"
        out_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(entry)

    # Aggregate run
    n_total = sum((r.get("fact_check_summary") or {}).get("n_stats_total", 0) for r in results)
    n_verified = sum((r.get("fact_check_summary") or {}).get("n_verified", 0) for r in results)
    n_halluc = sum((r.get("fact_check_summary") or {}).get("n_hallucinated", 0) for r in results)
    n_disc = sum((r.get("fact_check_summary") or {}).get("n_with_disclaimer", 0) for r in results)
    avg_pipeline = mean([r.get("elapsed_pipeline_s", 0) for r in results if not r.get("error")])
    avg_fc = mean([r.get("elapsed_fact_check_post_hoc_s", 0) for r in results if not r.get("error")])

    summary = {
        "run": run_label,
        "n_queries": len(queries),
        "n_success": sum(1 for r in results if not r.get("error")),
        "n_total_stats": n_total,
        "n_verified": n_verified,
        "n_hallucinated": n_halluc,
        "n_with_disclaimer": n_disc,
        "pct_verified": round(100 * n_verified / max(1, n_total), 1),
        "pct_hallucinated": round(100 * n_halluc / max(1, n_total), 1),
        "pct_disclaimer": round(100 * n_disc / max(1, n_total), 1),
        "avg_pipeline_s": round(avg_pipeline, 2),
        "avg_fact_check_s": round(avg_fc, 2),
    }

    all_path = out_subdir / "_ALL_QUERIES.json"
    all_path.write_text(json.dumps({"summary": summary, "queries": results},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRun {run_label} summary :")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return summary


def main() -> int:
    if not PHASED_FICHES_PATH.exists() or not PHASED_INDEX_PATH.exists():
        print("❌ Phase D index/fiches absent.")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print("Loading Phase D...")
    fiches = json.loads(PHASED_FICHES_PATH.read_text(encoding="utf-8"))
    index = faiss.read_index(str(PHASED_INDEX_PATH))
    print(f"  {len(fiches):,} fiches, ntotal={index.ntotal:,}")

    cache = LRUCache(maxsize=128)
    pipeline = AgentPipeline(
        client=client,
        fiches=fiches,
        index=index,
        profile_cache=cache,
        aggregated_top_n=8,
        enable_fact_check=False,  # Sprint 5 : skip FetchStat (économie)
    )
    checker = StatFactChecker(client)

    all_queries = _build_unified_queries()
    subset = _select_balanced_subset(all_queries)
    print(f"\nSubset balanced : {len(subset)} queries (6 personas + 6 DARES + 6 blocs + 6 user-naturel)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    runs_summaries = []
    t0_global = time.time()

    for run_label in ["run1", "run2", "run3"]:
        # Cache reset entre runs (mesure fair)
        cache.clear()
        run_summary = _run_one_run(
            run_label, subset, pipeline, checker,
            OUT_DIR / run_label,
        )
        runs_summaries.append(run_summary)
        if run_label != "run3":
            print(f"\n[pause 10s avant {run_label} suivant]")
            time.sleep(10)

    total_elapsed = round(time.time() - t0_global, 2)

    # Aggregate IC95 (n=3, t=4.303 df=2)
    def ic95(values):
        if len(values) < 2:
            return 0.0
        return round(4.303 * stdev(values) / (len(values) ** 0.5), 2)

    pct_verified_runs = [s["pct_verified"] for s in runs_summaries]
    pct_halluc_runs = [s["pct_hallucinated"] for s in runs_summaries]
    avg_pipeline_runs = [s["avg_pipeline_s"] for s in runs_summaries]

    aggregate = {
        "n_runs": len(runs_summaries),
        "n_queries_per_run": len(subset),
        "pct_verified": {
            "mean": round(mean(pct_verified_runs), 1),
            "std": round(stdev(pct_verified_runs) if len(pct_verified_runs) > 1 else 0, 2),
            "ic95": ic95(pct_verified_runs),
            "per_run": pct_verified_runs,
        },
        "pct_hallucinated": {
            "mean": round(mean(pct_halluc_runs), 1),
            "std": round(stdev(pct_halluc_runs) if len(pct_halluc_runs) > 1 else 0, 2),
            "ic95": ic95(pct_halluc_runs),
            "per_run": pct_halluc_runs,
        },
        "avg_pipeline_s": {
            "mean": round(mean(avg_pipeline_runs), 2),
            "std": round(stdev(avg_pipeline_runs) if len(avg_pipeline_runs) > 1 else 0, 2),
            "ic95": ic95(avg_pipeline_runs),
        },
        "total_elapsed_s": total_elapsed,
        "runs": runs_summaries,
    }

    aggregate_path = OUT_DIR / "_AGGREGATE.json"
    aggregate_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2),
                               encoding="utf-8")

    print("\n" + "=" * 60)
    print("=== AGGREGATE IC95 (n=3 runs, 24 queries balanced) ===")
    print(f"  pct_verified : mean={aggregate['pct_verified']['mean']}% ± IC95 {aggregate['pct_verified']['ic95']}pp (per_run {pct_verified_runs})")
    print(f"  pct_halluc   : mean={aggregate['pct_hallucinated']['mean']}% ± IC95 {aggregate['pct_hallucinated']['ic95']}pp (per_run {pct_halluc_runs})")
    print(f"  avg_pipeline : mean={aggregate['avg_pipeline_s']['mean']}s ± IC95 {aggregate['avg_pipeline_s']['ic95']}s")
    print(f"  total elapsed : {total_elapsed}s ({total_elapsed/60:.1f} min)")
    print(f"\n  vs baseline figée (PR #75, n=3, 48q) : 39.4% verified IC95 ±3.66 / 17.9% halluc IC95 ±3.90")
    print(f"\n✅ Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
