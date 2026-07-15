"""Capture le markdown RÉEL de la section 3 (chemin concret / options) en local,
pour voir la structure d'indentation des sous-puces avant de coder le grouping
(_parse_pistes). Ordre 1902.

Usage : PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/dump_section3_markdown.py
"""
from __future__ import annotations

import json

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline

FICHES = "data/processed/formations.json"
INDEX = "data/embeddings/formations.index"
SEED = "data/recits_seed.json"


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)
    fiches = json.load(open(FICHES, encoding="utf-8"))
    seed = {r["id"]: r["text"] for r in json.load(open(SEED, encoding="utf-8"))["recits"]}
    pipe = make_production_pipeline(
        client, fiches, enable_narrative_mode=True,
        enable_validator=False, enable_golden_qa=False, enable_post_process=False,
    )
    pipe.load_index_from(INDEX)
    try:
        pipe._build_double_subindices()
    except Exception as e:
        print("warmup skip:", e)
    pipe.warmup_generation()

    for rid in ("R01", "R03"):
        pipe.answer(seed[rid])
        ns = pipe.last_narrative_structured or {}
        opt = next((b for b in ns.get("blocks", []) if b.get("role") == "options"), None)
        print(f"\n######## {rid} — bloc options (chemin concret) RAW MARKDOWN (repr par ligne) ########")
        if not opt:
            print("  pas de bloc options")
            continue
        for ln in (opt.get("markdown", "")).splitlines():
            print(repr(ln))
        print(f"  -> items actuels parsés: {len(opt.get('items', []))}")


if __name__ == "__main__":
    main()
