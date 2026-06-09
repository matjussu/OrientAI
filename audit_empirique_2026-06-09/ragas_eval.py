"""Ragas complet sur l'eval set versionne (B-complet, cross-check du juge custom).

Metriques reference-free (pas de ground_truth labellise sur 497q) :
- faithfulness : la reponse est-elle ancree dans les contextes recuperes
- answer_relevancy : la reponse repond-elle a la question
- context precision (sans reference) : les contextes recuperes sont-ils pertinents

Tourne sur les reponses GENEREES du battery_full.json (in_scope avec sources).
Juge : mistral-small-latest T=0 (cohérent avec le repo). Shim mistralai obligatoire.

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/ragas_eval.py \
        --battery results/battery_full.json --out results/ragas_full.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import src.observability  # noqa: F401 - shim mistralai AVANT ragas
from src.config import load_config

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings

# context precision sans reference (selon version ragas)
try:
    from ragas.metrics import LLMContextPrecisionWithoutReference
    _ctx_prec = LLMContextPrecisionWithoutReference()
except Exception:  # noqa: BLE001
    _ctx_prec = None

REPO = Path(__file__).resolve().parent.parent


def _ctx_str(s: dict) -> str:
    if not isinstance(s, dict):
        return str(s)
    return json.dumps({k: v for k, v in s.items() if k not in ("_sub_index", "_retrieval_score")},
                      ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--battery", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = json.loads(Path(args.battery).read_text())
    # gradeable : reponse generee avec contextes (pas de court-circuit)
    grad = [r for r in rows
            if (r.get("scope") or {}).get("label") == "in_scope"
            and r.get("answer") and r.get("n_sources", 0) > 0 and not r.get("error")]
    if args.limit:
        grad = grad[: args.limit]
    print(f"gradeable rows for Ragas: {len(grad)}")

    dataset = Dataset.from_dict({
        "user_input": [r["question"] for r in grad],
        "response": [r["answer"] for r in grad],
        "retrieved_contexts": [[_ctx_str(s) for s in (r.get("sources") or [])] for r in grad],
    })

    cfg = load_config()
    llm = LangchainLLMWrapper(ChatMistralAI(
        model="mistral-small-latest", temperature=0.0, mistral_api_key=cfg.mistral_api_key))
    emb = LangchainEmbeddingsWrapper(MistralAIEmbeddings(api_key=cfg.mistral_api_key))

    metrics = [faithfulness, answer_relevancy]
    if _ctx_prec is not None:
        metrics.append(_ctx_prec)

    result = evaluate(dataset, metrics=metrics, llm=llm, embeddings=emb)
    df = result.to_pandas()

    agg = {}
    for col in df.columns:
        if df[col].dtype.kind in "fi":
            try:
                agg[col] = round(float(df[col].mean()), 3)
            except Exception:  # noqa: BLE001
                pass
    out = {"n": len(grad), "aggregate": agg,
           "per_sample": json.loads(df.to_json(orient="records"))}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print("RAGAS aggregate:", json.dumps(agg, ensure_ascii=False))


if __name__ == "__main__":
    main()
