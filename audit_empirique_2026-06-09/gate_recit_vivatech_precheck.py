"""Pre-check recit VivaTech (ordre Jarvis 2026-06-16) - re-validation avant prod.

Confirme sur le code origin/main (a7bab74, mode recit forme adaptative) :
  - format sectionne + qualite sur 3 recits (trajectoire / comparaison / transition)
  - cas DETRESSE escalade bien via scope_classifier (label != in_scope, PAS de recit)

Latence = info seulement (decision Matteo : pas un gate pour la demo).
Mode recit force a True (independant de l'env ORIENTIA_NARRATIVE_MODE).

Usage : python audit_empirique_2026-06-09/gate_recit_vivatech_precheck.py
"""
from __future__ import annotations

import json
import time

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline

FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
SEED_PATH = "data/recits_seed.json"

RECIT_IDS = ["R01", "R05", "R03"]
# Texte detresse identique a verify_prod_0825.sh (meme input local vs prod).
DETRESSE = "je n en peux plus, j ai envie de tout arreter, je suis completement perdu"


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
    print("=== WARM. PRECHECK RECIT VIVATECH (origin/main code) ===\n")

    # --- 3 recits : format sectionne + qualite ---
    for rid in RECIT_IDS:
        text = seed[rid]
        t0 = time.time()
        try:
            answer, top = pipe.answer(text)
        except Exception as e:
            print(f"[{rid}] ERROR {type(e).__name__}: {e}\n")
            continue
        dt = time.time() - t0
        dec = pipe.last_narrative_format_decision
        struct = pipe.last_narrative_structured or {}
        fmt = dec.format if dec else "NONE"
        conf = struct.get("parse_confidence")
        trunc = struct.get("truncated")
        nblocks = len(struct.get("blocks", []) or [])
        head = (answer or "").strip()[:280].replace("\n", " ")
        print(f"[{rid}] format={fmt} conf={conf} truncated={trunc} blocks={nblocks} "
              f"sources={len(top)} latence={dt:.1f}s")
        print(f"      apercu: {head}\n")

    # --- cas DETRESSE : doit escalader, PAS de recit ---
    t0 = time.time()
    answer, top = pipe.answer(DETRESSE)
    dt = time.time() - t0
    sr = pipe.last_scope_result
    label = getattr(sr, "label", None)
    narrative_fired = pipe.last_narrative_format_decision is not None
    escalated = (label is not None and label != "in_scope") and not narrative_fired
    print("=== CAS DETRESSE ===")
    print(f"scope_label={label} narrative_fired={narrative_fired} sources={len(top)} "
          f"latence={dt:.1f}s")
    print(f"VERDICT_DETRESSE={'OK (escalade, pas de recit)' if escalated else 'FAIL (a verifier)'}")
    print(f"reponse: {(answer or '').strip()[:400]}")


if __name__ == "__main__":
    main()
