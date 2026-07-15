"""Vérif backend (ordre 1738) : answer_stream émet bien un event `structured`
(NarrativeResponse typé) après les tokens, avant `done`, en mode récit.

Usage : PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/verify_structured_emit.py
"""
from __future__ import annotations

import asyncio
import json

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline


async def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)
    fiches = json.load(open("data/processed/formations.json", encoding="utf-8"))
    seed = {r["id"]: r["text"]
            for r in json.load(open("data/recits_seed.json", encoding="utf-8"))["recits"]}
    pipe = make_production_pipeline(
        client, fiches, enable_narrative_mode=True,
        enable_validator=False, enable_golden_qa=False, enable_post_process=False,
    )
    pipe.load_index_from("data/embeddings/formations.index")
    try:
        pipe._build_double_subindices()
    except Exception as e:
        print("warmup retrieval skip:", e)
    pipe.warmup_generation()

    # RECIT (doit émettre structured)
    seen, structured = [], None
    async for ev in pipe.answer_stream(seed["R01"]):
        t = ev.get("type")
        if t != "token":
            seen.append(t)
        if t == "structured":
            structured = ev["structured"]
    print("RECIT R01 non-token events:", seen)
    ok_order = "structured" in seen and "done" in seen and seen.index("structured") < seen.index("done")
    print("  structured émis AVANT done:", ok_order)
    if structured:
        print("  format:", structured.get("format"), "conf:", structured.get("parse_confidence"),
              "roles:", [b.get("role") for b in structured.get("blocks", [])])
        json.dumps(structured)  # doit passer (déjà coercé numpy côté producer en prod)
        print("  json.dumps(structured) OK")

    # DETRESSE (NE doit PAS émettre structured — scope court-circuite)
    seen_d = []
    async for ev in pipe.answer_stream("je n en peux plus, j ai envie de tout arreter, je suis completement perdu"):
        t = ev.get("type")
        if t != "token":
            seen_d.append(t)
    print("DETRESSE non-token events:", seen_d)
    print("  PAS de structured sur détresse:", "structured" not in seen_d)


if __name__ == "__main__":
    asyncio.run(main())
