"""CI minimale golden 50q (Phase 4, order 0825).

Gate de NON-RÉGRESSION retrieval, déterministe et rapide (hors juge), à lancer
pendant/après un re-embed pour détecter qu'on n'a pas cassé le retrieval.

Deux volets :
  1. RETRIEVAL RECALL (BLOQUANT, déterministe, ~secondes hors embed API) : pour
     chaque question golden ayant un expected_source, on vérifie que le top-k
     retrieval (retrieve + rerank + MMR, SANS génération LLM) surface au moins une
     fiche de la source attendue. Recall source comparé à un plancher de
     non-régression. Le recall domain est mesuré mais REPORTÉ seulement (instrument
     ambigu, cf docstring du seuil).
  2. JUGE (ALERTE NON BLOQUANTE) : `golden_ci.sh` enchaîne une passe génération +
     groundedness et imprime la moyenne en alerte, sans jamais faire échouer le gate.

Usage :
    PYTHONPATH=. .venv/bin/python -m src.eval.golden_ci            # gate (exit 2 si sous plancher)
    PYTHONPATH=. .venv/bin/python -m src.eval.golden_ci --report   # mesure seule, exit 0 (calibration)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "data/golden_eval/golden_50.json"
INDEX_PATH = REPO / "data/embeddings/formations.index"
FICHES_PATH = REPO / "data/processed/formations.json"

# Seuil plancher de NON-RÉGRESSION du recall SOURCE (parcoursup/monmaster).
# Signal PROPRE et non ambigu : ces questions DOIVENT retrouver une fiche de la
# source attendue. Observé 17/17 = 100% -> plancher 0.90 (marge anti-bruit).
# Un re-embed qui passe SOUS ce seuil a cassé le retrieval -> gate ROUGE.
RECALL_SOURCE_FLOOR = 0.90
# Le recall DOMAIN n'est PAS un gate : expected_domain encode souvent le TYPE de
# donnée attendu (ex insertion_pro = sous-dict salaire porté par une fiche
# droit/metier), pas un tag de fiche à retrouver. Mesuré et reporté pour triage
# humain (détail des misses), mais ne fait pas échouer le build (instrument ambigu,
# cf [[feedback-validate-measurement-instrument]]).


def _load_env():
    if os.environ.get("MISTRAL_API_KEY"):
        return
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def index_available() -> bool:
    """Le gate retrieval est exécutable (index FAISS + clé Mistral présents) ?"""
    _load_env()
    return INDEX_PATH.exists() and bool(os.environ.get("MISTRAL_API_KEY"))


def _retrieve_only(pipeline, question: str) -> list[dict]:
    """Retrieve + rerank (+ MMR + intent) SANS génération LLM. Calque
    src/eval/inspect_retrieval._retrieve_only sur la pipeline production."""
    from src.rag.retriever import retrieve_top_k
    from src.rag.reranker import rerank
    from src.rag.mmr import mmr_select
    from src.rag.intent import intent_to_config, classify_intent

    top_k_sources = 10
    mmr_lambda = pipeline.mmr_lambda
    if pipeline.use_intent:
        cfg = intent_to_config(classify_intent(question))
        top_k_sources = cfg.top_k_sources
        mmr_lambda = cfg.mmr_lambda
    retrieved = retrieve_top_k(pipeline.client, pipeline.index, pipeline.fiches, question, k=30)
    reranked = rerank(retrieved, pipeline.rerank_config)
    if pipeline.use_mmr:
        return mmr_select(reranked, k=top_k_sources, lambda_=mmr_lambda)
    return reranked[:top_k_sources]


def _fiche_source(f: dict) -> str:
    return (f.get("source") or "").lower()


def _fiche_domain(f: dict) -> str:
    return (f.get("domain") or f.get("domaine") or "").lower()


def _hits_source(sources: list[dict], expected: str) -> bool:
    exp = expected.lower()
    return any(exp in _fiche_source(s.get("fiche", {})) for s in sources)


def _hits_domain(sources: list[dict], expected: str) -> bool:
    exp = expected.lower()
    return any(exp == _fiche_domain(s.get("fiche", {})) for s in sources)


def run_recall_gate() -> dict:
    """Mesure le recall retrieval sur les 50q golden. Retourne un dict de métriques
    (ne lève pas sur le résultat : la décision gate est prise par l'appelant via les
    seuils). Lève SystemExit si l'environnement (clé/index) est absent."""
    import src.observability  # noqa: F401  (shim mistralai avant tout import lourd)
    from mistralai.client import Mistral
    from src.rag.factory import make_production_pipeline

    _load_env()
    if not os.environ.get("MISTRAL_API_KEY"):
        raise SystemExit("MISTRAL_API_KEY manquant (ni env ni .env)")
    if not INDEX_PATH.exists():
        raise SystemExit(f"index FAISS absent : {INDEX_PATH} (re-embed d'abord)")

    questions = json.loads(GOLDEN.read_text())["questions"]
    fiches = json.loads(FICHES_PATH.read_text())
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))

    src_total = src_hit = dom_total = dom_hit = 0
    misses: list[dict] = []
    for q in questions:
        sources = _retrieve_only(pipeline, q["question"])
        exp_src = q.get("expected_source")
        exp_dom = q.get("expected_domain")
        if exp_src:
            src_total += 1
            ok = _hits_source(sources, exp_src)
            src_hit += ok
            if not ok:
                misses.append({"id": q["id"], "type": "source", "expected": exp_src})
        if exp_dom:
            dom_total += 1
            ok = _hits_domain(sources, exp_dom)
            dom_hit += ok
            if not ok:
                misses.append({"id": q["id"], "type": "domain", "expected": exp_dom})
    return {
        "n_questions": len(questions),
        "recall_source": src_hit / src_total if src_total else None,
        "recall_source_n": f"{src_hit}/{src_total}",
        "recall_domain": dom_hit / dom_total if dom_total else None,
        "recall_domain_n": f"{dom_hit}/{dom_total}",
        "misses": misses,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="mesure seule, exit 0 (calibration des seuils)")
    args = ap.parse_args()

    m = run_recall_gate()
    print(f"[golden-ci] {m['n_questions']}q | recall source {m['recall_source_n']} "
          f"({m['recall_source']:.1%}) | recall domain {m['recall_domain_n']} "
          f"({m['recall_domain']:.1%})")
    if m["misses"]:
        print("[golden-ci] misses :")
        for x in m["misses"]:
            print(f"    {x['id']} {x['type']}={x['expected']}")
    print("[golden-ci] (recall domain = report non bloquant, instrument ambigu)")

    if args.report:
        return 0

    # Gate sur le recall SOURCE uniquement (signal propre).
    if m["recall_source"] is not None and m["recall_source"] < RECALL_SOURCE_FLOOR:
        print(f"[golden-ci] GATE ROUGE : recall source {m['recall_source']:.1%} "
              f"< plancher {RECALL_SOURCE_FLOOR:.0%} -> retrieval régressé.")
        return 2
    print("[golden-ci] GATE VERT : recall source non régressé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
