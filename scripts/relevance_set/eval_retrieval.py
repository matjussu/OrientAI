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
(recall@5, recall@10, nDCG@10) via src/eval/relevance_metrics.

Identité d'une fiche : `idx:<position dans formations.json>`, retrouvée par
identité d'objet (src/eval/battery/corpus.py). Avant le 23/09 ce script lisait
le champ `id`, absent sur 38 596 fiches : ces fiches sortaient du classement sans
lever d'erreur (RAPPORT 05/09 l.112). Les labels portent l'empreinte du corpus, vérifiée au chargement.

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

from mistralai.client import Mistral

import src.observability  # noqa: F401
from src.eval.battery.corpus import Corpus, fiche_key
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


def _keys(corpus: Corpus, results: list) -> list[str]:
    """Cles ordonnees. Un resultat hors corpus (fiche fabriquee par le pipeline) garde son rang
    sous une cle qui ne peut matcher aucun label, au lieu d'etre retire ou de faire echouer la
    question entiere (qui compterait alors comme un echec de retrieval)."""
    keys = []
    for rank, r in enumerate(results):
        fiche = r.get("fiche") if isinstance(r, dict) and "fiche" in r else r
        try:
            keys.append(fiche_key(corpus.position_of(fiche)))
        except KeyError:
            keys.append(f"hors-corpus:{rank}")
    return keys


def run_raw(pipeline, corpus: Corpus, question: str, n: int) -> list[str]:
    from src.rag.mmr import mmr_select
    from src.rag.reranker import rerank
    from src.rag.retriever import retrieve_top_k

    retrieved = retrieve_top_k(pipeline.client, pipeline.index, corpus.fiches, question, k=30)
    reranked = rerank(retrieved, pipeline.rerank_config)
    top = mmr_select(reranked, k=n, lambda_=pipeline.mmr_lambda) if pipeline.use_mmr else reranked[:n]
    return _keys(corpus, top)


def run_serving(pipeline, corpus: Corpus, question: str, n: int) -> list[str]:
    prepared = pipeline._prepare_for_generation(question, 30, n, None, None)
    if not hasattr(prepared, "top"):  # court-circuit (scope/router)
        return []
    return _keys(corpus, prepared.top[:n])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--mode", choices=["raw", "serving"], default="raw")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--recall-k", default="5,10", help="cutoffs du recall, separes par des virgules")
    args = ap.parse_args()

    _load_env()
    corpus = Corpus(FICHES)
    corpus.assert_version(json.loads(Path(args.labels).read_text())["_meta"].get("corpus_sha256"), args.labels)
    labels = load_labels(args.labels)
    candidates = json.loads(CANDIDATES.read_text())
    corpus.assert_version(candidates["_meta"]["corpus_sha256"], str(CANDIDATES))
    cands = {c["qid"]: c["question"] for c in candidates["questions"]}

    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    pipeline = make_production_pipeline(client, corpus.fiches)
    pipeline.load_index_from(str(INDEX))
    pipeline._build_double_subindices()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    runs: dict[str, list[str]] = {}
    if out_path.exists():
        runs = json.loads(out_path.read_text()).get("runs", {})

    todo = [ql for ql in labels if ql.qid in cands and ql.qid not in runs]
    print(f"[eval] {len(todo)} questions a mesurer (mode {args.mode})")
    failed = []
    for i, ql in enumerate(todo):
        q = cands[ql.qid]
        try:
            runs[ql.qid] = (
                run_raw(pipeline, corpus, q, args.top) if args.mode == "raw"
                else run_serving(pipeline, corpus, q, args.top)
            )
        except Exception as e:  # noqa: BLE001
            # une panne (timeout API) n'est pas un echec de retrieval : la question n'est pas
            # enregistree, la relance la rejouera
            print(f"  [panne] {ql.qid}: {type(e).__name__}: {e}")
            failed.append(ql.qid)
        if (i + 1) % 25 == 0:
            out_path.write_text(json.dumps({"mode": args.mode, "runs": runs}, ensure_ascii=False))
            print(f"  {i+1}/{len(todo)}")

    if failed:
        out_path.write_text(json.dumps({"mode": args.mode, "runs": runs}, ensure_ascii=False))
        sys.exit(f"{len(failed)} questions en panne ({', '.join(failed[:10])}) : relancer, "
                 "la reprise ne rejoue qu'elles. Pas de rapport sur une mesure incomplete.")

    reports = {k: evaluate(runs, labels, k=int(k), ndcg_k=args.top) for k in args.recall_k.split(",")}
    out_path.write_text(json.dumps(
        {"mode": args.mode, "corpus_sha256": corpus.sha256,
         "reports": {k: r.summary() for k, r in reports.items()},
         "misses": {k: r.misses for k, r in reports.items()}, "runs": runs},
        ensure_ascii=False, indent=1,
    ))
    for r in reports.values():
        print(f"[report] {r.summary()}")
    print(f"[done] -> {out_path}")


if __name__ == "__main__":
    main()
