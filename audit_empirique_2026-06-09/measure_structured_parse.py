"""RISK CHECK (ordre Jarvis 16/06) : le parser deterministe (narrative_structured.py)
produit-il une structure AUSSI propre sur de vrais recits live que les mocks /recit ?

Pour R01/R03/R11 : dump du NarrativeResponse (format, parse_confidence, truncated,
roles des blocs, items/table/sources peuples). Si roles=prose partout / conf basse /
sections vides -> le live rendra moins riche que le showcase mock.

Usage : PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/measure_structured_parse.py
"""
from __future__ import annotations

import json

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline

FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
SEED_PATH = "data/recits_seed.json"
IDS = ["R01", "R03", "R11"]


def dump_blocks(ns: dict) -> None:
    print(f"  format={ns.get('format')} parse_confidence={ns.get('parse_confidence')} "
          f"truncated={ns.get('truncated')} n_sources={len(ns.get('sources') or [])} "
          f"overlays={ns.get('overlays')}")
    for i, b in enumerate(ns.get("blocks") or []):
        tbl = b.get("table")
        tbl_desc = (f"table(opts={len(tbl.get('options', []))},crit={len(tbl.get('criteria', []))})"
                    if tbl else "no-table")
        items = b.get("items") or []
        item_urls = sum(1 for it in items if (it.get("url") if isinstance(it, dict) else None))
        print(f"    [{i}] role={b.get('role'):<16} heading={str(b.get('heading'))[:34]!r:<36} "
              f"items={len(items)}(url={item_urls}) {tbl_desc} "
              f"block_sources={len(b.get('sources') or [])} md_len={len(b.get('markdown') or '')}")


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)
    fiches = json.load(open(FICHES_PATH, encoding="utf-8"))
    seed = {r["id"]: r["text"] for r in json.load(open(SEED_PATH, encoding="utf-8"))["recits"]}
    pipe = make_production_pipeline(
        client, fiches, enable_narrative_mode=True,
        enable_validator=False, enable_golden_qa=False, enable_post_process=False,
    )
    pipe.load_index_from(INDEX_PATH)
    try:
        pipe._build_double_subindices()
    except Exception as e:
        print("warmup retrieval skip:", e)
    pipe.warmup_generation()
    print("=== WARM. MESURE PARSE STRUCTURE (live vs mock) ===\n")

    for rid in IDS:
        try:
            pipe.answer(seed[rid])
        except Exception as e:
            print(f"[{rid}] ERROR {type(e).__name__}: {e}\n")
            continue
        ns = pipe.last_narrative_structured or {}
        dec = pipe.last_narrative_format_decision
        print(f"[{rid}] (format_decision={getattr(dec, 'format', '?')})")
        if not ns:
            print("  last_narrative_structured VIDE -> pas de NarrativeResponse")
        else:
            dump_blocks(ns)
        print()


if __name__ == "__main__":
    main()
