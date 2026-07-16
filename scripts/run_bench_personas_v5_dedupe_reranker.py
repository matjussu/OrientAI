"""Bench v5 — pipeline + multi-corpus retrievable (formations + metiers + parcours + apec).

Clone de `run_bench_personas_v4.py` avec :
- Inputs : `formations_multi_corpus_dedupe.json` + `formations_multi_corpus_dedupe.index`
  (50 153 records vs 48 914 v4) — cf ADR-048 RAG multi-corpus
- Mistral client : `timeout_ms=180000` (ADR-047 PR #58 — fix Q12 timeout)
- Output : `results/bench_personas_v5_dedupe_reranker_2026-04-25/`

Reste identique à v4 :
- Mêmes 18 queries (6 personas × 3) — comparabilité directe baseline 4.53
- Même fact-checker StatFactChecker Mistral Small aval
- Même format de sortie (JSON par query + _ALL_QUERIES.json)

Verdict scientifique attendu : isolation de UNE seule variable (le pivot
multi-corpus, +1 239 records additifs sans modif fiche_to_text v3).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mistralai.client import Mistral  # noqa: E402
from src.config import load_config  # noqa: E402
from src.experimental.fact_checker import StatFactChecker  # noqa: E402
from src.rag.pipeline import OrientIAPipeline  # noqa: E402
from scripts.run_bench_personas_v3 import PERSONAS  # noqa: E402


FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_dedupe.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_dedupe.index"
OUT_DIR = REPO_ROOT / "results" / "bench_personas_v5_dedupe_reranker_2026-04-25"


def _run_one_query(pipeline, checker, persona, query, idx):
    t0 = time.time()
    try:
        answer, sources = pipeline.answer(query["text"])
        elapsed_gen = round(time.time() - t0, 2)
    except Exception as e:
        return {
            "idx_global": idx,
            "persona_id": persona["id"],
            "query_id": query["id"],
            "query_text": query["text"],
            "error_pipeline": f"{type(e).__name__}: {e}",
        }

    t1 = time.time()
    try:
        report = checker.verify(answer, sources)
    except Exception as e:
        report = None
        fact_check_error = f"{type(e).__name__}: {e}"
    else:
        fact_check_error = None
    elapsed_fc = round(time.time() - t1, 2)

    if report and report.stats_hallucinated:
        answer_annotated = checker.annotate(answer, report)
    else:
        answer_annotated = answer

    return {
        "idx_global": idx,
        "persona_id": persona["id"],
        "persona_description": persona["description"],
        "scope": persona["scope"],
        "query_id": query["id"],
        "query_type": query["type"],
        "query_text": query["text"],
        "elapsed_gen_s": elapsed_gen,
        "elapsed_fact_check_s": elapsed_fc,
        "answer_raw": answer,
        "answer_annotated": answer_annotated,
        "annotated_differs": answer != answer_annotated,
        "n_sources": len(sources),
        "fact_check_error": fact_check_error,
        "fact_check_summary": report.summary if report else None,
        "fact_check_stats": [
            {
                "stat_text": s.stat_text,
                "stat_value": s.stat_value,
                "stat_unit": s.stat_unit,
                "context_in_response": s.context_in_response,
                "verdict": s.verdict,
                "source_fiche_excerpt": s.source_fiche_excerpt,
            }
            for s in (report.stats_extracted if report else [])
        ],
        "sources_top10": [
            {
                "score": round(float(s.get("score", 0)), 4),
                "nom": s["fiche"].get("nom", "")[:100] or s["fiche"].get("text", "")[:100],
                "etablissement": s["fiche"].get("etablissement", ""),
                "niveau": s["fiche"].get("niveau"),
                "phase": s["fiche"].get("phase"),
                "source": s["fiche"].get("source"),
                "domaine": s["fiche"].get("domaine"),
                "domain": s["fiche"].get("domain", "formation"),
            }
            for s in sources[:10]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", type=str, default=None)
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument(
        "--out-suffix",
        type=str,
        default="",
        help="Suffix appended to OUT_DIR (e.g., '_run2' for triple-run).",
    )
    args = parser.parse_args()

    global OUT_DIR
    if args.out_suffix:
        OUT_DIR = OUT_DIR.parent / f"{OUT_DIR.name}{args.out_suffix}"

    if not FICHES_PATH.exists() or not INDEX_PATH.exists():
        print("❌ formations_multi_corpus_dedupe.json ou index FAISS multi-corpus absent.")
        print("   → Exécute d'abord : python scripts/rebuild_index_dedupe_reuse.py")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)  # ADR-047
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches):,} fiches multi-corpus")

    pipeline = OrientIAPipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))
    checker = StatFactChecker(client)

    personas_to_run = PERSONAS
    if args.persona:
        personas_to_run = [p for p in PERSONAS if p["id"] == args.persona]
    if args.max:
        personas_to_run = personas_to_run[: args.max]

    print(f"Bench v5 : {len(personas_to_run)} persona(s) × 3 queries (multi-corpus)")
    print("=" * 60)

    idx = 0
    all_results = []
    for persona in personas_to_run:
        print(f"\n▶ Persona {persona['id']}")
        for query in persona["queries"]:
            idx += 1
            print(f"  [{idx:2d}/{len(personas_to_run)*3}] {query['id']} — \"{query['text'][:60]}…\"")
            res = _run_one_query(pipeline, checker, persona, query, idx)
            out_path = OUT_DIR / f"query_{idx:02d}_{persona['id']}_{query['id']}.json"
            out_path.write_text(
                json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            all_results.append(res)
            if "error_pipeline" in res:
                print(f"      ❌ pipeline error : {res['error_pipeline'][:80]}")
            else:
                fc = res.get("fact_check_summary") or {}
                domains_in_top = sorted({s["domain"] for s in res["sources_top10"]})
                print(
                    f"      gen {res['elapsed_gen_s']}s + fc {res['elapsed_fact_check_s']}s"
                    f" | stats {fc.get('n_stats_total',0)} → {fc.get('n_verified',0)}✅"
                    f" / {fc.get('n_with_disclaimer',0)}🟡 / {fc.get('n_hallucinated',0)}🔴"
                    f" | domains {domains_in_top}"
                )

    all_path = OUT_DIR / "_ALL_QUERIES.json"
    all_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✅ Bench v5 fini. Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
