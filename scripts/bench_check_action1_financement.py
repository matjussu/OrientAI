"""Sprint 7 — Bench-check intermédiaire Action 1 (unmute axe 4 financement).

Single-run sur les 4 queries FINANCEMENT_QUERIES Sprint 7 (curées Action 2).
Objectif : valider que l'Action 1 (`verified_by_official_source` verdict)
débloque effectivement l'axe 4 financement qui était muet (0,0pp) au
verdict Sprint 6 §4.

## Méthodologie

- 4 queries Sprint 7 financement-dédiées (CPF reconversion, bourse
  CROUS échelons, AGEFIPH RQTH, PTP)
- Single-run (le full triple-run vient ensuite avec budget validé Matteo)
- Pipeline : AgentPipeline standard (Phase E pre-Action-4) + StatFactChecker
  POST-Action-1 (nouveau verdict `verified_by_official_source`)
- Métrique cible : si **n_verified_by_source > 0** sur ces 4 queries,
  l'unmute axe 4 est confirmé empiriquement (Sprint 6 mesurait 0/23 stats
  verified sur axe 4)

Coût : ~4 queries × $0.05 = ~$0.20, ~3-4 min wall-clock.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections import Counter


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import faiss  # noqa: E402
from mistralai.client import Mistral  # noqa: E402

from src.agent.cache import LRUCache  # noqa: E402
from src.agent.pipeline_agent import AgentPipeline  # noqa: E402
from src.config import load_config  # noqa: E402
from src.experimental.fact_checker import StatFactChecker  # noqa: E402
from scripts.sprint7_queries import FINANCEMENT_QUERIES  # noqa: E402


PHASEE_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseE.json"
PHASEE_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseE.index"

OUT_DIR = REPO_ROOT / "results" / "sprint7_bench_check_action1_financement"


def main() -> int:
    if not PHASEE_FICHES_PATH.exists() or not PHASEE_INDEX_PATH.exists():
        print("❌ Phase E index/fiches absent. Lance build_index_phaseE.py d'abord.")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print("Loading Phase E (post-Action-1 fact-checker)...")
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
        enable_fact_check=False,
    )
    checker = StatFactChecker(client)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Bench-check Action 1 — 4 queries financement Sprint 7")
    print(f"{'='*60}")

    results = []
    for i, q in enumerate(FINANCEMENT_QUERIES, 1):
        print(f"\n[{i}/4] {q['id']}")
        print(f"    \"{q['text'][:100]}...\"")

        result = pipeline.answer(q["text"])
        if result.error:
            print(f"    ❌ pipeline error : {result.error[:120]}")
            continue

        # Fact-check post-hoc avec le nouveau verdict
        fc_input = [
            {"score": s.get("score", 0), "fiche": s.get("fiche", {})}
            for s in result.sources_aggregated
        ]
        try:
            fc_report = checker.verify(result.answer_text, fc_input)
            fc_summary = fc_report.summary if fc_report else None
        except Exception as e:
            print(f"    ⚠️ fc error : {type(e).__name__}: {e}")
            continue

        if fc_summary:
            print(f"    ✅ {fc_summary['n_stats_total']} stats → "
                  f"verified={fc_summary['n_verified']} "
                  f"(strict={fc_summary['n_verified_strict']} + "
                  f"by_source={fc_summary['n_verified_by_source']}) | "
                  f"disclaimer={fc_summary['n_with_disclaimer']} | "
                  f"halluc={fc_summary['n_hallucinated']}")

        # Granularités présentes dans le top-K
        granularities = Counter()
        for s in result.sources_aggregated:
            fiche = s.get("fiche", {})
            gran = fiche.get("granularity")
            if gran:
                granularities[gran] += 1

        entry = {
            "query_id": q["id"],
            "axe_target": q["axe_target"],
            "query_text": q["text"],
            "answer_text": result.answer_text,
            "elapsed_pipeline_s": result.elapsed_total_s,
            "fact_check_summary": fc_summary,
            "granularities_top_k": dict(granularities),
        }
        out_path = OUT_DIR / f"{q['id']}.json"
        out_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(entry)

    # Aggregate
    n_total = sum((r.get("fact_check_summary") or {}).get("n_stats_total", 0) for r in results)
    n_verified = sum((r.get("fact_check_summary") or {}).get("n_verified", 0) for r in results)
    n_strict = sum((r.get("fact_check_summary") or {}).get("n_verified_strict", 0) for r in results)
    n_by_source = sum((r.get("fact_check_summary") or {}).get("n_verified_by_source", 0) for r in results)
    n_disc = sum((r.get("fact_check_summary") or {}).get("n_with_disclaimer", 0) for r in results)
    n_halluc = sum((r.get("fact_check_summary") or {}).get("n_hallucinated", 0) for r in results)

    summary = {
        "n_queries": len(results),
        "n_stats_total": n_total,
        "n_verified": n_verified,
        "n_verified_strict": n_strict,
        "n_verified_by_source": n_by_source,
        "n_with_disclaimer": n_disc,
        "n_hallucinated": n_halluc,
        "pct_verified": round(100 * n_verified / max(1, n_total), 1),
        "pct_verified_by_source_share": round(100 * n_by_source / max(1, n_verified), 1) if n_verified else 0.0,
        "pct_hallucinated": round(100 * n_halluc / max(1, n_total), 1),
        "verdict_unmute_axe4": "OUI" if n_by_source > 0 else "NON (axe 4 toujours muet)",
    }

    print(f"\n{'='*60}")
    print(f"=== Aggregate Action 1 unmute check ===")
    print(f"{'='*60}")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    aggregate_path = OUT_DIR / "_AGGREGATE.json"
    aggregate_path.write_text(json.dumps({"summary": summary, "queries": results},
                                          ensure_ascii=False, indent=2),
                              encoding="utf-8")

    print(f"\n✅ Output → {OUT_DIR}")
    print(f"\nVerdict empirique :")
    if summary["n_verified_by_source"] > 0:
        print(f"  ⭐ Action 1 UNMUTE confirmé : {summary['n_verified_by_source']} stat(s) "
              f"verified_by_official_source détectée(s) (vs 0/23 Sprint 6 axe 4 muet)")
    else:
        print(f"  ⚠️ Action 1 unmute NON CONFIRMÉ sur ce subset 4 queries")
        print(f"     Possible que le bench full triple-run capture mieux l'effet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
