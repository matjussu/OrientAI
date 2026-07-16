"""Sprint 6 — Bench agent pipeline apples-to-apples Phase E (5 axes corpora gaps).

Clone fidèle de `run_bench_agent_pipeline_apples.py` (Sprint 5) avec :
- Index : `formations_multi_corpus_phaseE.{json,index}` (56 089 vecteurs)
  au lieu de phaseD (54 297) — incluant les 1 792 nouvelles cells Sprint 6
- Output : `results/sprint6_bench_apples_2026-04-27/`
- Champ supplémentaire `granularities_top_k` dans chaque entry (extrait
  de `sources_aggregated`) pour permettre l'analyse retrieval-side
  per-axe Option A demandée par Jarvis (décomposition pp par axe DARES /
  inserjeunes / financement / DROM territorial / voie pré-bac)

## Méthodologie identique Sprint 5

- 24 queries balanced subset (6 personas + 6 DARES + 6 blocs + 6 user-naturel)
- Triple-run IC95 (n=3, t-distribution df=2)
- AgentPipeline avec aggregated_top_n=8, enable_fact_check=False
- StatFactChecker post-hoc sur sources_aggregated apples-to-apples baseline

## Coût estimé

24 queries × 3 runs × ~30s pipeline + ~3s fact-check = ~50 min wall-clock.
Mistral : ~$0.05/run × 24q × 3 = ~$3.60 (Sprint 5 referenciel).

## Comparaison attendue

- Baseline figée Sprint 5 (48q apples-to-apples × 3) : 39.4% verified IC95 ±3.66 / 17.9% halluc ±3.90
- Sprint 5 agent pre-Sprint-6 (24q × 3) : 23.0% verified ±19.73 / 17.7% halluc ±27.85 (avec phaseD)
- Sprint 6 cible : combler le -16.4pp verified par enrichissement corpora (5 axes)
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
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


PHASEE_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseE.json"
PHASEE_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseE.index"

OUT_DIR = REPO_ROOT / "results" / "sprint6_bench_apples_2026-04-27"


def _select_balanced_subset(all_queries: list) -> list:
    """Sélectionne 24 queries balanced (6 par sous-suite). Identique Sprint 5."""
    by_suite: dict = {}
    for q in all_queries:
        s = q["suite"]
        by_suite.setdefault(s, []).append(q)

    personas_subset = [q for q in by_suite.get("personas_v4", [])
                       if q["id"].endswith("_q1")][:6]
    dares_subset = by_suite.get("dares_dedie", [])[:6]
    blocs_subset = by_suite.get("blocs_dedie", [])[:6]
    user_subset = by_suite.get("user_naturel", [])[:6]

    return personas_subset + dares_subset + blocs_subset + user_subset


def _extract_granularities(sources_aggregated: list) -> list[str]:
    """Extrait granularity de chaque source pour analyse retrieval-side.

    Sprint 6 specific : permet de tracer la contribution per-axe
    (granularities Sprint 6 : fap_region, formation_france, region_diplome,
    dispositif, voie, territoire, synthese_cross, bac_pro_domaine,
    cap_domaine, type_diplome_synthese vs anciennes : fap, region, etc.).
    """
    granularities: list[str] = []
    for s in sources_aggregated:
        fiche = s.get("fiche", {}) or {}
        gran = fiche.get("granularity")
        if gran:
            granularities.append(gran)
        else:
            # Fallback : utiliser domain pour identifier (formation = base, etc.)
            domain = fiche.get("domain", "formation")
            granularities.append(f"_{domain}")
    return granularities


def _run_one_run(
    run_label: str,
    queries: list,
    pipeline: AgentPipeline,
    checker: StatFactChecker,
    out_subdir: Path,
) -> dict:
    """Run complet : pipeline + StatFactChecker post-hoc + extraction granularities."""
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

        # Sprint 6 : extraction granularités pour analyse retrieval-side per-axe
        granularities_top_k = _extract_granularities(result.sources_aggregated)

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
            "granularities_top_k": granularities_top_k,  # Sprint 6 specific
            "sub_queries": [sq.to_dict() for sq in result.plan.sub_queries] if result.plan else [],
        }
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
    if not PHASEE_FICHES_PATH.exists() or not PHASEE_INDEX_PATH.exists():
        print("❌ Phase E index/fiches absent.")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print("Loading Phase E (Sprint 6, 5 axes corpora gaps)...")
    fiches = json.loads(PHASEE_FICHES_PATH.read_text(encoding="utf-8"))
    index = faiss.read_index(str(PHASEE_INDEX_PATH))
    print(f"  {len(fiches):,} fiches, ntotal={index.ntotal:,}")

    cache = LRUCache(maxsize=128)
    pipeline = AgentPipeline(
        client=client,
        fiches=fiches,
        index=index,
        profile_cache=cache,
        aggregated_top_n=8,
        enable_fact_check=False,  # Sprint 5/6 : skip FetchStat (économie)
    )
    checker = StatFactChecker(client)

    all_queries = _build_unified_queries()
    subset = _select_balanced_subset(all_queries)
    print(f"\nSubset balanced : {len(subset)} queries (6 personas + 6 DARES + 6 blocs + 6 user-naturel)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    runs_summaries = []
    t0_global = time.time()

    for run_label in ["run1", "run2", "run3"]:
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
    print(f"  vs Sprint 5 (24q × 3, phaseD) : 23.0% verified IC95 ±19.73 / 17.7% halluc ±27.85")
    print(f"\n✅ Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
