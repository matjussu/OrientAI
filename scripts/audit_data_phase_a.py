"""Phase A audit data — pour chaque hallu Layer3 détectée, identifier si :

- Type A : info correcte ÉTAIT dans les fiches retrievées → bug LLM
- Type B : info absente du corpus → LLM comble avec son training (= bug DATA)
- Type C : info partielle dans corpus → LLM extrapole

Approche :
1. Charge phase_a_with_sources.json (responses + top_sources retrievées)
2. Charge phase2_layer3_audit.json (claims Layer3 suspects)
3. Pour chaque réponse, appelle StatFactChecker (Mistral Small) qui vérifie
   chaque chiffre/statistique vs sources retrievées → verdict 4 niveaux
4. Croise : claims Layer3 suspects ⊃ unsourced_unsafe StatFactChecker ?
5. Classifie réponse en A/B/C selon ratios.

Output : JSON + tableau récap pour décider data corpus elargissement vs LLM tuning.

Usage :
    python scripts/audit_data_phase_a.py \\
        --bench results/mini_bench/phase_a_with_sources.json \\
        --layer3 results/mini_bench/phase2_layer3_audit.json \\
        --out results/mini_bench/phase_a_data_audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mistralai.client import Mistral  # noqa: E402

from src.config import load_config  # noqa: E402
from src.experimental.fact_checker import StatFactChecker  # noqa: E402
from src.rag.pipeline import OrientIAPipeline  # noqa: E402
from src.rag.factory import make_production_pipeline  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations.index"


def classify_record(stat_summary: dict, n_layer3_warnings: int) -> str:
    """Classifie une réponse en type A/B/C/clean.

    - clean         : 0 hallu détectée par aucun outil
    - type_A_llm    : Layer3 flag MAIS StatFactChecker dit majoritairement verified
                     (info était là, LLM a foiré)
    - type_B_data   : Layer3 flag ET StatFactChecker dit majoritairement unsourced_unsafe
                     (info absente du corpus)
    - type_C_mixte  : Layer3 flag ET mix verified + unsourced
    - type_layer3_only : Layer3 flag mais aucun chiffre testable par StatFactChecker
                        (claim qualitatif type "label garantit qualité")
    """
    n_total = stat_summary.get("n_stats_total", 0)
    n_verified = stat_summary.get("n_verified", 0)
    n_unsafe = stat_summary.get("n_hallucinated", 0)
    n_disclaimer = stat_summary.get("n_with_disclaimer", 0)

    if n_layer3_warnings == 0 and n_unsafe == 0:
        return "clean"
    if n_layer3_warnings > 0 and n_total == 0:
        return "type_layer3_only"  # Layer3 a flagué du qualitatif non chiffré
    if n_unsafe > 0 and n_verified == 0:
        return "type_B_data"  # tout est non sourcé
    if n_unsafe == 0 and n_verified > 0:
        return "type_A_llm"  # tout vérifié mais Layer3 flag — LLM a peut-être contexte mal
    if n_unsafe > 0 and n_verified > 0:
        return "type_C_mixte"
    return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path, required=True,
                        help="Mini-bench JSON avec --store-sources")
    parser.add_argument("--layer3", type=Path, required=True,
                        help="Layer3 audit JSON")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output audit JSON")
    args = parser.parse_args()

    # Setup
    cfg = load_config()
    if not cfg.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY missing")
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fact_checker = StatFactChecker(client)

    # Pour faire du retrieve à la volée si bench n'a pas de top_sources, on
    # charge le pipeline production avec son index FAISS.
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))

    bench = json.loads(args.bench.read_text(encoding="utf-8"))
    layer3_data = json.loads(args.layer3.read_text(encoding="utf-8"))
    layer3_by_id = {r["id"]: r for r in layer3_data["audit_records"]}

    print(f"[audit-data] processing {len(bench['unimodal_results'])} responses")

    audit_records = []
    type_counts = {"clean": 0, "type_A_llm": 0, "type_B_data": 0,
                   "type_C_mixte": 0, "type_layer3_only": 0, "unknown": 0}

    for i, rec in enumerate(bench["unimodal_results"], 1):
        qid = rec["id"]
        question = rec["question"]
        response = rec.get("response") or ""
        if not response:
            print(f"  [{i}] {qid}: SKIP (no response)")
            continue

        # Récupérer top_sources : soit dans le bench (--store-sources), soit
        # refaire le retrieve si absentes.
        if rec.get("top_sources"):
            # Reconstruire le format attendu par StatFactChecker (list[dict] avec
            # key "fiche"). On a les summaries — pour StatFactChecker on a besoin
            # de fiches plus riches → refaire le retrieve.
            from src.rag.retriever import retrieve_top_k
            from src.rag.reranker import rerank
            from src.rag.intent import classify_domain_hint
            domain_hint = classify_domain_hint(question)
            retrieved = retrieve_top_k(client, pipeline.index, fiches, question, k=30)
            sources = rerank(retrieved, pipeline.rerank_config, domain_hint=domain_hint)[:10]
        else:
            from src.rag.retriever import retrieve_top_k
            from src.rag.reranker import rerank
            from src.rag.intent import classify_domain_hint
            domain_hint = classify_domain_hint(question)
            retrieved = retrieve_top_k(client, pipeline.index, fiches, question, k=30)
            sources = rerank(retrieved, pipeline.rerank_config, domain_hint=domain_hint)[:10]

        # StatFactChecker
        t0 = time.time()
        report = fact_checker.verify(response, sources)
        elapsed = round(time.time() - t0, 2)
        stat_summary = report.summary

        # Layer3 warnings pour cette question
        layer3_rec = layer3_by_id.get(qid, {})
        n_layer3 = layer3_rec.get("n_layer3_warnings", 0)
        layer3_warnings = layer3_rec.get("layer3_warnings", [])

        # Classification
        verdict = classify_record(stat_summary, n_layer3)
        type_counts[verdict] = type_counts.get(verdict, 0) + 1

        print(f"  [{i}/{len(bench['unimodal_results'])}] {qid}: verdict={verdict} "
              f"| Layer3={n_layer3} | StatFactChecker={stat_summary.get('n_verified', 0)}V/"
              f"{stat_summary.get('n_with_disclaimer', 0)}D/"
              f"{stat_summary.get('n_hallucinated', 0)}U "
              f"({elapsed}s)")

        audit_records.append({
            "id": qid,
            "category": rec.get("category"),
            "intent_target": rec.get("intent_target"),
            "chemin_target": rec.get("chemin_target"),
            "question": question,
            "verdict": verdict,
            "layer3": {
                "n_warnings": n_layer3,
                "warnings": layer3_warnings,
            },
            "stat_fact_checker": {
                "summary": stat_summary,
                "stats_extracted": [
                    {
                        "stat_text": s.stat_text,
                        "verdict": s.verdict,
                        "source_excerpt": (s.source_fiche_excerpt or "")[:200],
                    }
                    for s in report.stats_extracted
                ],
            },
            "elapsed_factcheck_s": elapsed,
        })

    out_payload = {
        "metadata": {
            "source_bench": str(args.bench),
            "source_layer3": str(args.layer3),
            "n_processed": len(audit_records),
            "type_counts": type_counts,
            "model_factchecker": fact_checker.model,
        },
        "audit_records": audit_records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[audit-data] Saved to {args.out}")
    print(f"[audit-data] Verdicts: {type_counts}")


if __name__ == "__main__":
    main()
