"""Mesure le retrieval contre le set de pertinence labellisé (H1 lot 2.1).

Deux modes de mesure :
  --mode raw      : retrieve_top_k + rerank + MMR (déterministe hors embed,
                    AUCUN LLM). Le circuit vectoriel pur : rapide, gratuit,
                    c'est le gate CI par défaut.
  --mode serving  : pipeline._prepare_for_generation complet (router LLM,
                    sub-indexes, SELECT, hardlocks) — CE QUE LE LLM VOIT
                    réellement (prepared.top). Coûte ~2 appels mistral-small
                    par question. Pour les baselines et les gates de lot.

Sortie : runs JSON {qid: [fiche_id ordonnés]} + rapport métriques
(recall@5, nDCG@10) via src/eval/relevance_metrics.

Usage :
    PYTHONPATH=. python scripts/relevance_set/eval_retrieval.py \
        --labels scripts/relevance_set/labels.json \
        --mode raw --out results/relevance/raw_baseline.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import src.observability  # noqa: F401
from mistralai.client import Mistral

from src.eval.relevance_metrics import evaluate, load_labels
from src.rag.factory import make_production_pipeline

CANDIDATES = REPO / "scripts/relevance_set/candidates.json"
FICHES = REPO / "data/processed/formations.json"
INDEX = REPO / "data/embeddings/formations.index"


def _load_env() -> None:
    if os.environ.get("MISTRAL_API_KEY"):
        return
    for line in (REPO / ".env").read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _fiche_id(fiche: dict) -> str:
    return str(fiche.get("id") or "")


def run_raw(pipeline, fiches, question: str, n: int) -> list[str]:
    from src.rag.mmr import mmr_select
    from src.rag.reranker import rerank
    from src.rag.retriever import retrieve_top_k

    retrieved = retrieve_top_k(pipeline.client, pipeline.index, fiches, question, k=30)
    reranked = rerank(retrieved, pipeline.rerank_config)
    top = mmr_select(reranked, k=n, lambda_=pipeline.mmr_lambda) if pipeline.use_mmr else reranked[:n]
    out = []
    for s in top:
        fiche = s.get("fiche") if isinstance(s, dict) and "fiche" in s else s
        fid = _fiche_id(fiche if isinstance(fiche, dict) else {})
        if fid:
            out.append(fid)
    return out


def run_serving(pipeline, question: str, n: int) -> list[str]:
    prepared = pipeline._prepare_for_generation(question, 30, n, None, None)
    if not hasattr(prepared, "top"):  # court-circuit (scope/router)
        return []
    out = []
    for s in prepared.top[:n]:
        fiche = s.get("fiche") if isinstance(s, dict) and "fiche" in s else s
        fid = _fiche_id(fiche if isinstance(fiche, dict) else {})
        if fid:
            out.append(fid)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--mode", choices=["raw", "serving"], default="raw")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--recall-k", type=int, default=5)
    args = ap.parse_args()

    _load_env()
    labels = load_labels(args.labels)
    cands = {c["qid"]: c["question"] for c in json.loads(CANDIDATES.read_text())}

    fiches = json.loads(FICHES.read_text())
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(INDEX))
    pipeline._build_double_subindices()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    runs: dict[str, list[str]] = {}
    if out_path.exists():
        runs = json.loads(out_path.read_text()).get("runs", {})

    todo = [ql for ql in labels if ql.qid in cands and ql.qid not in runs]
    print(f"[eval] {len(todo)} questions a mesurer (mode {args.mode})")
    for i, ql in enumerate(todo):
        q = cands[ql.qid]
        try:
            runs[ql.qid] = (
                run_raw(pipeline, fiches, q, args.top) if args.mode == "raw"
                else run_serving(pipeline, q, args.top)
            )
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] {ql.qid}: {type(e).__name__}: {e}")
            runs[ql.qid] = []
        if (i + 1) % 25 == 0:
            out_path.write_text(json.dumps({"mode": args.mode, "runs": runs}, ensure_ascii=False))
            print(f"  {i+1}/{len(todo)}")

    report = evaluate(runs, labels, k=args.recall_k, ndcg_k=args.top)
    out_path.write_text(json.dumps(
        {"mode": args.mode, "report": report.summary(), "misses": report.misses, "runs": runs},
        ensure_ascii=False, indent=1,
    ))
    print(f"[report] {report.summary()}")
    print(f"[done] -> {out_path}")


if __name__ == "__main__":
    main()
