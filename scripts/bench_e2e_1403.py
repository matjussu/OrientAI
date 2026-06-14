"""Bench e2e ordre 1403 — réponses modèle sur un (corpus, index) donné.

Lance les questions curées (bench_e2e_questions_1403.json) via le pipeline production
et sauve les réponses. À exécuter 2× (ancien vs nouveau) via env vars :

  ORIENTIA_CORPUS_PATH=data/processed/formations.json.bak-pre-derive-20260614 \\
  ORIENTIA_INDEX_PATH=data/embeddings/formations.index.before-fills-20260614 \\
  BENCH_OUT=audit_empirique_2026-06-09/bench_e2e_AVANT.json \\
  PYTHONPATH=. python scripts/bench_e2e_1403.py

  ORIENTIA_CORPUS_PATH=data/processed/formations.json \\
  ORIENTIA_INDEX_PATH=data/embeddings/formations.index \\
  BENCH_OUT=audit_empirique_2026-06-09/bench_e2e_APRES.json \\
  PYTHONPATH=. python scripts/bench_e2e_1403.py

ORIENTIA_BENCH_ROUTER=0 désactive le RouterLLM (retrieval flat pur) si besoin.
"""
import json
import os
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline

CORPUS = os.environ.get("ORIENTIA_CORPUS_PATH", "data/processed/formations.json")
INDEX = os.environ.get("ORIENTIA_INDEX_PATH", "data/embeddings/formations.index")
OUT = os.environ.get("BENCH_OUT", "audit_empirique_2026-06-09/bench_e2e_out.json")
QUESTIONS = os.environ.get("BENCH_QUESTIONS", "audit_empirique_2026-06-09/bench_e2e_questions_1403.json")
ROUTER = os.environ.get("ORIENTIA_BENCH_ROUTER", "1") != "0"


def _src_summary(sources):
    out = []
    for s in (sources or [])[:5]:
        f = s.get("fiche") if isinstance(s, dict) and isinstance(s.get("fiche"), dict) else (s if isinstance(s, dict) else {})
        out.append({
            "nom": f.get("nom") or f.get("libelle_metier") or f.get("libelle") or f.get("libelle_formation"),
            "source": f.get("source"),
            "type_diplome": f.get("type_diplome"),
        })
    return out


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(Path(CORPUS).read_text(encoding="utf-8"))
    print(f"Corpus : {CORPUS} ({len(fiches)} fiches) | Index : {INDEX} | router={ROUTER}")
    pipeline = make_production_pipeline(client, fiches, enable_router_llm=ROUTER)
    pipeline.load_index_from(INDEX)
    questions = json.loads(Path(QUESTIONS).read_text(encoding="utf-8"))
    out = []
    for item in questions:
        try:
            ans, sources = pipeline.answer(item["q"], temperature=0.0)
        except Exception as e:
            ans, sources = f"[ERREUR: {type(e).__name__}: {e}]", []
        out.append({
            "id": item["id"], "cat": item["cat"], "q": item["q"],
            "answer": ans, "n_sources": len(sources or []),
            "top_sources": _src_summary(sources),
        })
        print(f"[{item['id']}] {item['cat']} — {len(ans)} chars, {len(sources or [])} sources")
    Path(OUT).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"==> saved {OUT}")


if __name__ == "__main__":
    main()
