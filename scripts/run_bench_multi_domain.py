"""Bench multi-domain — 8 queries non-formation-centric pour mesurer le pivot ADR-048.

Contexte : le bench v5 sur les 18 queries v4 a montré que multi-corpus
n'est activé que sur 1/18 (Q4 Théo droit). Les queries v4 sont
formation-centric par construction. Ce bench vise à exercer les 3
nouveaux corpora :

- `metier` (1 075 fiches éditoriales ONISEP)
- `parcours_bacheliers` (151 cellules MESRI L1→L2 / Licence)
- `apec_region` (13 régions APEC observatoire 2026)

8 queries, gradient simple → contextuel → ambigu, équilibrées sur les
3 domaines.

Run sur deux systèmes :
- **v4 baseline** : `formations.json` + `formations.index` (48 914 records, sans multi-corpus)
- **v5 multi-corpus** : `formations_multi_corpus.json` + `formations_multi_corpus.index` (50 153 records)

Output : `results/bench_multi_domain_2026-04-25/{system}/query_XX.json` +
`_SYNTHESIS.md` post-notation humaine.

Coût Mistral estimé : 8 queries × 2 systèmes = 16 réponses + fact-check
= ~$0.10-0.20 (sous le budget Matteo).
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


# Inputs v4 baseline (sans multi-corpus)
V4_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations.json"
V4_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations.index"

# Inputs v5 multi-corpus
V5_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus.json"
V5_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus.index"

OUT_DIR = REPO_ROOT / "results" / "bench_multi_domain_2026-04-25"


# 8 queries multi-domain — design pour exercer chaque corpus + gradient difficulté
QUERIES: list[dict[str, str]] = [
    # ---- Métier (3 queries → corpus metier 1 075) ----
    {
        "id": "m1",
        "domain_target": "metier",
        "difficulty": "simple",
        "text": "Je veux devenir développeur en cybersécurité, par où commencer après le bac ?",
    },
    {
        "id": "m2",
        "domain_target": "metier",
        "difficulty": "contextuel",
        "text": "Je rêve d'un métier artistique qui me permette de travailler de mes mains. Quels métiers existent et quelles formations y mènent ?",
    },
    {
        "id": "m3",
        "domain_target": "metier",
        "difficulty": "ambigu",
        "text": "Quelle est la différence concrète entre le métier d'ingénieur mathématicien et celui d'actuaire ?",
    },
    # ---- Parcours bacheliers (3 queries → corpus parcours 151) ----
    {
        "id": "p1",
        "domain_target": "parcours_bacheliers",
        "difficulty": "simple",
        "text": "Quel est le taux de réussite en licence de droit pour un BAC L mention Bien ?",
    },
    {
        "id": "p2",
        "domain_target": "parcours_bacheliers",
        "difficulty": "contextuel",
        "text": "Mon fils a un BAC ES mention Assez bien. Il hésite entre licence éco et licence droit. Laquelle a le meilleur taux de passage L1 → L2 ?",
    },
    {
        "id": "p3",
        "domain_target": "parcours_bacheliers",
        "difficulty": "ambigu",
        "text": "Je suis en STAPS depuis 1 an et je galère. Si je redouble vs si je me réoriente en DUT, qu'est-ce que les stats disent sur la suite du parcours ?",
    },
    # ---- APEC régional (2 queries → corpus apec_region 13) ----
    {
        "id": "a1",
        "domain_target": "apec_region",
        "difficulty": "simple",
        "text": "Quel est le marché du travail des cadres en Bretagne en 2026 ?",
    },
    {
        "id": "a2",
        "domain_target": "apec_region",
        "difficulty": "contextuel",
        "text": "Pour un jeune diplômé bac+5 informatique, dans quelle région française métropolitaine les recrutements cadres 2026 sont-ils les plus dynamiques ?",
    },
]


def _run_one(pipeline: OrientIAPipeline, checker: StatFactChecker, query: dict) -> dict:
    t0 = time.time()
    try:
        answer, sources = pipeline.answer(query["text"])
        elapsed_gen = round(time.time() - t0, 2)
    except Exception as e:
        return {
            "id": query["id"],
            "domain_target": query["domain_target"],
            "difficulty": query["difficulty"],
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
        "id": query["id"],
        "domain_target": query["domain_target"],
        "difficulty": query["difficulty"],
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
                "verdict": s.verdict,
                "source_fiche_excerpt": s.source_fiche_excerpt,
            }
            for s in (report.stats_extracted if report else [])
        ],
        "sources_top10": [
            {
                "score": round(float(s.get("score", 0)), 4),
                "nom": (s["fiche"].get("nom") or "")[:100]
                or (s["fiche"].get("text") or "")[:100],
                "etablissement": s["fiche"].get("etablissement", ""),
                "domain": s["fiche"].get("domain", "formation"),
                "id": s["fiche"].get("id"),
            }
            for s in sources[:10]
        ],
    }


def _run_system(system: str, fiches_path: Path, index_path: Path):
    """Run les 8 queries sur un système (v4 baseline ou v5 multi-corpus)."""
    out_dir = OUT_DIR / system
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)

    print(f"\n=== {system} ===")
    print(f"Loading {fiches_path}…")
    fiches = json.loads(fiches_path.read_text(encoding="utf-8"))
    print(f"  {len(fiches):,} fiches")

    pipeline = OrientIAPipeline(client, fiches)
    pipeline.load_index_from(str(index_path))
    checker = StatFactChecker(client)

    all_results = []
    for query in QUERIES:
        print(f"  [{query['id']}] ({query['domain_target']}, {query['difficulty']}) "
              f"\"{query['text'][:60]}…\"")
        res = _run_one(pipeline, checker, query)
        out_path = out_dir / f"query_{query['id']}.json"
        out_path.write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        all_results.append(res)
        if "error_pipeline" in res:
            print(f"      ❌ {res['error_pipeline'][:80]}")
        else:
            domains = sorted({s["domain"] for s in res["sources_top10"]})
            fc = res.get("fact_check_summary") or {}
            print(
                f"      gen {res['elapsed_gen_s']}s + fc {res['elapsed_fact_check_s']}s"
                f" | stats {fc.get('n_stats_total',0)}: {fc.get('n_verified',0)}✅"
                f"/{fc.get('n_with_disclaimer',0)}🟡/{fc.get('n_hallucinated',0)}🔴"
                f" | domains {domains}"
            )

    all_path = out_dir / "_ALL_QUERIES.json"
    all_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--system",
        choices=["v4", "v5", "both"],
        default="both",
        help="Quel système exécuter (défaut: both)",
    )
    args = parser.parse_args()

    if args.system in ("v4", "both"):
        if not V4_FICHES_PATH.exists() or not V4_INDEX_PATH.exists():
            print(f"❌ V4 inputs absents : {V4_FICHES_PATH} / {V4_INDEX_PATH}")
            return 1
        _run_system("v4_baseline", V4_FICHES_PATH, V4_INDEX_PATH)

    if args.system in ("v5", "both"):
        if not V5_FICHES_PATH.exists() or not V5_INDEX_PATH.exists():
            print(f"❌ V5 inputs absents : {V5_FICHES_PATH} / {V5_INDEX_PATH}")
            print("   → exécute d'abord : python scripts/build_multi_corpus_index.py")
            return 1
        _run_system("v5_multi_corpus", V5_FICHES_PATH, V5_INDEX_PATH)

    print(f"\n✅ Bench multi-domain fini. Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
