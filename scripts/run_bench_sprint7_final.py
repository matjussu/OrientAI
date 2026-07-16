"""Sprint 7 — Bench final 2 modes ablation (Option E budget validé).

Bench 38 queries balanced × 3 runs IC95 × 2 modes :
- **Mode Baseline** : SYSTEM_PROMPT v3.2 + critic loop OFF (= comportement Sprint 5/6)
- **Mode Both** : SYSTEM_PROMPT_V33_STRICT (R1-R6) + critic loop ON

Permet d'isoler le gain combiné des Actions 1-5 + R6 vs baseline pure.
Ablation Strict-only vs Critic-only en backlog Sprint 7.5 si gain ambigu.

## Coût estimé (Option E validée par Matteo)

- Mode Baseline : 38 q × 3 runs × ~$0.04 (gen) = $4.56
- Mode Both : 38 q × 3 runs × ~$0.06 (gen + critic ~$0.02) = $6.84
- **Total ~$11.40**

## Wall-clock estimé

- Mode Baseline : ~30s/q × 38 × 3 = ~57 min
- Mode Both : ~36s/q × 38 × 3 = ~68 min (critic loop +6s/q)
- **Total ~2h05** (sequentiel)

## Output

`results/sprint7_bench_final_2026-04-27/` :
  - `mode_baseline/run{1,2,3}/` — outputs par query baseline
  - `mode_both/run{1,2,3}/` — outputs par query Both
  - `_AGGREGATE_BASELINE.json` — IC95 mode Baseline
  - `_AGGREGATE_BOTH.json` — IC95 mode Both
  - `_VERDICT_DELTA.json` — comparaison cumul Sprint 7 vs Baseline
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
from src.experimental.critic_loop import CriticLoop  # noqa: E402
from src.experimental.system_strict import SYSTEM_PROMPT_V33_STRICT  # noqa: E402

from scripts.run_bench_persona_complet import _build_unified_queries  # noqa: E402
from scripts.sprint7_queries import (  # noqa: E402
    build_sprint7_queries,
    select_baseline_subset_24q,
)


PHASEE_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseE.json"
PHASEE_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseE.index"

OUT_DIR = REPO_ROOT / "results" / "sprint7_bench_final_2026-04-27"


def _extract_granularities(sources_aggregated: list) -> list[str]:
    """Extrait granularity de chaque source pour analyse retrieval-side."""
    granularities: list[str] = []
    for s in sources_aggregated:
        fiche = s.get("fiche", {}) or {}
        gran = fiche.get("granularity")
        if gran:
            granularities.append(gran)
        else:
            domain = fiche.get("domain", "formation")
            granularities.append(f"_{domain}")
    return granularities


def _run_one_run(
    run_label: str,
    queries: list,
    pipeline: AgentPipeline,
    checker: StatFactChecker,
    critic_loop: CriticLoop | None,
    out_subdir: Path,
) -> dict:
    """Run complet sur 38 queries pour 1 mode 1 run."""
    out_subdir.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*70}")
    print(f"=== Run {run_label} ({len(queries)} queries, "
          f"critic={'ON' if critic_loop else 'OFF'}) ===")
    print(f"{'='*70}")

    results = []
    for i, q in enumerate(queries, 1):
        if i > 1:
            time.sleep(2)

        suite = q["suite"]
        qid = q["id"]
        print(f"\n[{i:2d}/{len(queries)}] [{suite:<18}] {qid}")
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

        # Mode Both : critic loop avant fact-check
        critic_n_modifications = 0
        critic_summary = None
        critic_elapsed = 0.0
        answer_text = result.answer_text
        if critic_loop:
            t_critic_0 = time.time()
            critic_report = critic_loop.review(answer_text, result.sources_aggregated)
            critic_elapsed = round(time.time() - t_critic_0, 2)
            answer_text = critic_report.response_corrected
            critic_n_modifications = critic_report.n_modifications
            critic_summary = critic_report.modifications_summary
            print(f"    🔧 critic loop {critic_elapsed}s : "
                  f"{critic_n_modifications} modifications")

        # Fact-check post-hoc
        t_fc_0 = time.time()
        fc_input_sources = [
            {"score": s.get("score", 0), "fiche": s.get("fiche", {})}
            for s in result.sources_aggregated
        ]
        try:
            fc_report = checker.verify(answer_text, fc_input_sources)
            fc_summary = fc_report.summary if fc_report else None
            fc_elapsed = round(time.time() - t_fc_0, 2)
            fc_error = None
        except Exception as e:
            fc_summary = None
            fc_elapsed = round(time.time() - t_fc_0, 2)
            fc_error = f"{type(e).__name__}: {e}"

        if fc_summary:
            n_strict = fc_summary.get('n_verified_strict', 0)
            n_by_source = fc_summary.get('n_verified_by_source', 0)
            print(f"    ✅ pipeline {result.elapsed_total_s}s + fc {fc_elapsed}s | "
                  f"verif={fc_summary['n_verified']} (strict={n_strict} + "
                  f"by_source={n_by_source}) | halluc={fc_summary['n_hallucinated']}")
        else:
            print(f"    ⚠️ fc error : {fc_error}")

        entry = {
            "suite": suite,
            "query_id": qid,
            "query_text": q["text"],
            "answer_text": answer_text,
            "answer_text_pre_critic": result.answer_text if critic_loop else None,
            "elapsed_pipeline_s": result.elapsed_total_s,
            "elapsed_critic_loop_s": critic_elapsed,
            "elapsed_fact_check_post_hoc_s": fc_elapsed,
            "critic_n_modifications": critic_n_modifications,
            "critic_summary": critic_summary,
            "fact_check_summary": fc_summary,
            "fact_check_error": fc_error,
            "n_sources_aggregated": len(result.sources_aggregated),
            "domains_top_k": sorted({s.get("fiche", {}).get("domain", "formation")
                                     for s in result.sources_aggregated}),
            "granularities_top_k": _extract_granularities(result.sources_aggregated),
        }
        out_path = out_subdir / f"query_{i:02d}_{suite}_{qid}.json"
        out_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(entry)

    # Aggregate run
    n_total = sum((r.get("fact_check_summary") or {}).get("n_stats_total", 0) for r in results)
    n_verified = sum((r.get("fact_check_summary") or {}).get("n_verified", 0) for r in results)
    n_strict = sum((r.get("fact_check_summary") or {}).get("n_verified_strict", 0) for r in results)
    n_by_source = sum((r.get("fact_check_summary") or {}).get("n_verified_by_source", 0) for r in results)
    n_halluc = sum((r.get("fact_check_summary") or {}).get("n_hallucinated", 0) for r in results)
    n_disc = sum((r.get("fact_check_summary") or {}).get("n_with_disclaimer", 0) for r in results)
    avg_pipeline = mean([r.get("elapsed_pipeline_s", 0) for r in results if not r.get("error")] or [0])

    summary = {
        "run": run_label,
        "n_queries": len(queries),
        "n_success": sum(1 for r in results if not r.get("error")),
        "n_total_stats": n_total,
        "n_verified": n_verified,
        "n_verified_strict": n_strict,
        "n_verified_by_source": n_by_source,
        "n_hallucinated": n_halluc,
        "n_with_disclaimer": n_disc,
        "pct_verified": round(100 * n_verified / max(1, n_total), 1),
        "pct_hallucinated": round(100 * n_halluc / max(1, n_total), 1),
        "pct_disclaimer": round(100 * n_disc / max(1, n_total), 1),
        "avg_pipeline_s": round(avg_pipeline, 2),
        "total_critic_modifications": sum(r.get("critic_n_modifications", 0) for r in results),
    }

    all_path = out_subdir / "_ALL_QUERIES.json"
    all_path.write_text(json.dumps({"summary": summary, "queries": results},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRun {run_label} summary :")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return summary


def _aggregate_ic95(runs_summaries: list[dict], mode_label: str) -> dict:
    """Agrège n=3 runs avec IC95 (t=4.303 df=2)."""
    def ic95(values):
        if len(values) < 2:
            return 0.0
        return round(4.303 * stdev(values) / (len(values) ** 0.5), 2)

    pct_verified_runs = [s["pct_verified"] for s in runs_summaries]
    pct_halluc_runs = [s["pct_hallucinated"] for s in runs_summaries]
    avg_pipeline_runs = [s["avg_pipeline_s"] for s in runs_summaries]

    return {
        "mode": mode_label,
        "n_runs": len(runs_summaries),
        "n_queries_per_run": runs_summaries[0]["n_queries"] if runs_summaries else 0,
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
        },
        "total_critic_modifications": sum(s.get("total_critic_modifications", 0) for s in runs_summaries),
        "runs": runs_summaries,
    }


def _run_mode(
    mode_label: str,
    queries: list,
    pipeline: AgentPipeline,
    checker: StatFactChecker,
    critic_loop: CriticLoop | None,
    out_dir: Path,
) -> dict:
    """Triple-run pour 1 mode + aggregate IC95."""
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_summaries = []
    cache = pipeline.profile_cache
    for run_label in ["run1", "run2", "run3"]:
        if cache:
            cache.clear()
        run_summary = _run_one_run(
            run_label, queries, pipeline, checker, critic_loop,
            out_dir / run_label,
        )
        runs_summaries.append(run_summary)
        if run_label != "run3":
            print(f"\n[pause 10s avant run suivant {mode_label}]")
            time.sleep(10)
    aggregate = _aggregate_ic95(runs_summaries, mode_label)
    aggregate_path = out_dir / "_AGGREGATE.json"
    aggregate_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
    return aggregate


def main() -> int:
    if not PHASEE_FICHES_PATH.exists() or not PHASEE_INDEX_PATH.exists():
        print("❌ Phase E index/fiches absent.")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print("Loading Phase E updated (post-Action-4 inserjeunes granularité 3)...")
    fiches = json.loads(PHASEE_FICHES_PATH.read_text(encoding="utf-8"))
    index = faiss.read_index(str(PHASEE_INDEX_PATH))
    print(f"  {len(fiches):,} fiches, ntotal={index.ntotal:,}")

    cache = LRUCache(maxsize=128)

    # Mode Baseline : v3.2 + critic OFF
    pipeline_baseline = AgentPipeline(
        client=client, fiches=fiches, index=index,
        profile_cache=cache,
        aggregated_top_n=8,
        enable_fact_check=False,
        system_prompt_override=None,  # default v3.2
    )
    # Mode Both : v3.3 strict + critic ON
    pipeline_both = AgentPipeline(
        client=client, fiches=fiches, index=index,
        profile_cache=cache,
        aggregated_top_n=8,
        enable_fact_check=False,
        system_prompt_override=SYSTEM_PROMPT_V33_STRICT,
    )
    checker = StatFactChecker(client)
    critic_loop = CriticLoop(client)

    all_queries = _build_unified_queries()
    baseline_24q = select_baseline_subset_24q(all_queries)
    bench_38q = build_sprint7_queries(baseline_24q)
    print(f"\nBench 38 queries (24 baseline + 14 nouvelles Sprint 7)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0_global = time.time()

    # Mode Baseline triple-run
    print(f"\n{'#'*70}")
    print(f"### MODE BASELINE (v3.2 + critic OFF) — Sprint 5/6 baseline equivalent")
    print(f"{'#'*70}")
    aggregate_baseline = _run_mode(
        "baseline", bench_38q, pipeline_baseline, checker, None,
        OUT_DIR / "mode_baseline",
    )

    # Mode Both triple-run
    print(f"\n{'#'*70}")
    print(f"### MODE BOTH (v3.3 strict R1-R6 + critic loop ON) — Sprint 7 cumul")
    print(f"{'#'*70}")
    aggregate_both = _run_mode(
        "both", bench_38q, pipeline_both, checker, critic_loop,
        OUT_DIR / "mode_both",
    )

    total_elapsed = round(time.time() - t0_global, 2)

    # Verdict delta
    verdict_delta = {
        "baseline_aggregate": aggregate_baseline,
        "both_aggregate": aggregate_both,
        "delta_pct_verified_mean": round(
            aggregate_both["pct_verified"]["mean"] - aggregate_baseline["pct_verified"]["mean"], 1
        ),
        "delta_pct_hallucinated_mean": round(
            aggregate_both["pct_hallucinated"]["mean"] - aggregate_baseline["pct_hallucinated"]["mean"], 1
        ),
        "delta_avg_pipeline_s": round(
            aggregate_both["avg_pipeline_s"]["mean"] - aggregate_baseline["avg_pipeline_s"]["mean"], 2
        ),
        "total_elapsed_s": total_elapsed,
        "n_queries": len(bench_38q),
        "comparable_baseline_sprint56": "39.4% verified ± IC95 3.66pp / 17.9% halluc ± 3.90pp (24q figées)",
    }

    verdict_path = OUT_DIR / "_VERDICT_DELTA.json"
    verdict_path.write_text(json.dumps(verdict_delta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"=== VERDICT DELTA Sprint 7 cumul vs Baseline ===")
    print(f"{'='*70}")
    print(f"  pct_verified (Sprint 7 Both)    : {aggregate_both['pct_verified']['mean']}% "
          f"± IC95 {aggregate_both['pct_verified']['ic95']}pp")
    print(f"  pct_verified (Baseline Sprint 5/6) : {aggregate_baseline['pct_verified']['mean']}% "
          f"± IC95 {aggregate_baseline['pct_verified']['ic95']}pp")
    print(f"  Delta verified                  : {verdict_delta['delta_pct_verified_mean']:+.1f}pp")
    print(f"  pct_halluc (Both)               : {aggregate_both['pct_hallucinated']['mean']}% "
          f"± IC95 {aggregate_both['pct_hallucinated']['ic95']}pp")
    print(f"  pct_halluc (Baseline)           : {aggregate_baseline['pct_hallucinated']['mean']}% "
          f"± IC95 {aggregate_baseline['pct_hallucinated']['ic95']}pp")
    print(f"  Delta halluc                    : {verdict_delta['delta_pct_hallucinated_mean']:+.1f}pp")
    print(f"\n  Latence Both (avec critic) : {aggregate_both['avg_pipeline_s']['mean']}s "
          f"(+{verdict_delta['delta_avg_pipeline_s']:.1f}s vs Baseline)")
    print(f"  Total critic modifications : {aggregate_both['total_critic_modifications']}")
    print(f"\n  Total wall-clock : {total_elapsed}s ({total_elapsed/60:.1f} min)")
    print(f"\n✅ Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
