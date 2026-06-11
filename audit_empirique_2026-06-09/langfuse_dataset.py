"""Pousse l'eval set versionne en dataset Langfuse (B-complet, deep-wiring).

La stack Langfuse tourne deja (self-hostee). Ce script cree/peuple un dataset
annotable a partir de eval_set_full.json -> permet l'annotation manuelle et
l'eval en ligne sur echantillon depuis l'UI Langfuse (http://localhost:3000).

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/langfuse_dataset.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from langfuse import Langfuse

REPO = Path(__file__).resolve().parent.parent
EVAL = REPO / "audit_empirique_2026-06-09/eval_set_full.json"
DATASET = "orientai-eval-2026-06-09-full"


def _load_env():
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main():
    _load_env()
    data = json.loads(EVAL.read_text())
    items = data["items"]
    lf = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
    )
    lf.create_dataset(name=DATASET,
                      description=f"OrientAI eval set {data['version']} ({len(items)} q)",
                      metadata={"version": data["version"], "n": len(items)})
    n = 0
    for it in items:
        lf.create_dataset_item(
            dataset_name=DATASET,
            input={"question": it["question"]},
            expected_output={"expectation": it.get("expectation")},
            metadata={"id": it["id"], "category": it["category"],
                      "pair_id": it.get("pair_id"), "variant": it.get("variant")},
        )
        n += 1
    lf.flush()
    print(f"dataset '{DATASET}' : {n} items pousses vers {os.environ.get('LANGFUSE_HOST','http://localhost:3000')}")


if __name__ == "__main__":
    main()
