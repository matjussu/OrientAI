"""Bench v4 — pipeline + fact-checker Mistral Small aval.

Clone de `run_bench_personas.py` + intégration `StatFactChecker`.
Pour chaque query :
1. `pipeline.answer(q)` produit la réponse brute (v3 pipeline, corpus 48k v2)
2. `fact_checker.verify(answer, sources)` détecte les stats hallucinées
3. `fact_checker.annotate(answer, report)` ajoute `*(non vérifié)*` sur stats unsafe
4. Sauvegarde : original answer + annotated answer + report JSON

Output : `results/bench_personas_v4_2026-04-24/` avec pour chaque query :
- `answer_raw` : sortie pipeline sans modification
- `answer_annotated` : avec marqueurs `(non vérifié dans les sources)` sur stats unsafe
- `fact_check_report` : détail par stat (verdict, source_excerpt, contexte)
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


FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations.index"
OUT_DIR = REPO_ROOT / "results" / "bench_personas_v4_2026-04-24"


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

    # Fact-check aval
    t1 = time.time()
    try:
        report = checker.verify(answer, sources)
    except Exception as e:
        report = None
        fact_check_error = f"{type(e).__name__}: {e}"
    else:
        fact_check_error = None
    elapsed_fc = round(time.time() - t1, 2)

    # Annotate answer si hallucinations détectées
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
                "nom": s["fiche"].get("nom", "")[:100],
                "etablissement": s["fiche"].get("etablissement", ""),
                "niveau": s["fiche"].get("niveau"),
                "phase": s["fiche"].get("phase"),
                "source": s["fiche"].get("source"),
                "domaine": s["fiche"].get("domaine"),
            }
            for s in sources[:10]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", type=str, default=None)
    parser.add_argument("--max", type=int, default=None)
    args = parser.parse_args()

    if not FICHES_PATH.exists() or not INDEX_PATH.exists():
        print("❌ formations.json ou index FAISS absent.")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)  # ADR-047
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))
    pipeline = OrientIAPipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))
    checker = StatFactChecker(client)

    personas_to_run = PERSONAS
    if args.persona:
        personas_to_run = [p for p in PERSONAS if p["id"] == args.persona]
    if args.max:
        personas_to_run = personas_to_run[: args.max]

    print(f"Bench v4 : {len(personas_to_run)} persona(s) × 3 queries")
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
                print(f"      ❌ pipeline error")
            else:
                fc = res.get("fact_check_summary") or {}
                print(f"      gen {res['elapsed_gen_s']}s + fc {res['elapsed_fact_check_s']}s"
                      f" | stats {fc.get('n_stats_total',0)} → {fc.get('n_verified',0)}✅"
                      f" / {fc.get('n_with_disclaimer',0)}🟡 / {fc.get('n_hallucinated',0)}🔴")

    all_path = OUT_DIR / "_ALL_QUERIES.json"
    all_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✅ Bench v4 fini. Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
