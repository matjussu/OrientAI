"""Lance les 13 questions Spot-Check Gate 3 sous Langfuse pour baseline pré-fix.

Reuse SPOT_CHECK_QUESTIONS + _load_pipeline depuis scripts/spot_check_v5.py
(zéro duplication). Ajoute :
  - tagging Langfuse par question (expected_domain + Q1..Q13 + session_id batch)
  - mesure domain match top-K
  - output JSON consolidé pour analyse downstream

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/observability/run_spot_check_traced.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
    print("❌ LANGFUSE_PUBLIC_KEY absent — active Langfuse avant de lancer.")
    sys.exit(1)

import src.observability as obs  # noqa: E402
from langfuse import Langfuse  # noqa: E402

from scripts.spot_check_v5 import (  # noqa: E402
    SPOT_CHECK_QUESTIONS,
    _load_pipeline,
)


CORPUS_PATH = REPO_ROOT / "data" / "processed" / "formations_v5.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_v5.index"
# Output dir paramétrable via env var (sinon défaut baseline)
OUT_DIR = Path(os.environ.get(
    "ORIENTIA_OBSERVABILITY_OUT_DIR",
    str(REPO_ROOT / "results" / "observability_baseline_2026-05-13")
))


def main() -> int:
    if not CORPUS_PATH.exists() or not INDEX_PATH.exists():
        print(f"❌ Corpus ou index manquant : {CORPUS_PATH=}, {INDEX_PATH=}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # session_id partagé → group des 13 traces dans Langfuse UI
    session_id = f"spot_check_baseline_{int(time.time())}"
    print(f"→ Session Langfuse : {session_id}")
    print(f"→ {len(SPOT_CHECK_QUESTIONS)} questions, corpus v5, baseline pré-fix\n")

    pipeline, _ = _load_pipeline(CORPUS_PATH, INDEX_PATH)
    lf = Langfuse()

    results = []
    for i, (question, expected_domain, raison) in enumerate(SPOT_CHECK_QUESTIONS, 1):
        q_id = f"Q{i:02d}"
        print(f"[{q_id}] {question[:70]}…")
        t0 = time.time()

        # Update la trace en cours avec session_id + tags + metadata
        # via langfuse_observation_id passé au décorateur @observe :
        # plus simple — set ces attributs en amont via le client OTel.
        # On utilise update_current_trace dans un nullable span context :
        try:
            answer, top = pipeline.answer(question, top_k_sources=5)
            error = None
        except Exception as e:
            answer, top = "", []
            error = str(e)
            print(f"   ⚠ ERROR: {e}")

        latency = round(time.time() - t0, 3)

        # Calcul domain match top-K (idem spot_check_v5 logic)
        domains_in_top = [
            (s.get("fiche") if isinstance(s, dict) and "fiche" in s else s).get("domain")
            for s in top[:5]
        ]
        n_match = sum(1 for d in domains_in_top if d == expected_domain)

        # Tag la trace ACTIVE (le décorateur @observe a déjà créé la trace)
        # Update applique aux derniers traces créés via session_id + tags
        try:
            lf.update_current_trace(
                session_id=session_id,
                tags=[expected_domain, q_id, "spot_check_baseline_pre_fix"],
                metadata={
                    "question_index": i,
                    "expected_domain": expected_domain,
                    "raison": raison,
                    "n_domain_match_top5": n_match,
                    "n_top_returned": len(top),
                    "domains_in_top5": domains_in_top,
                    "pass_domain_match": n_match >= 1,
                },
                user_id=q_id,
            )
        except Exception as e:
            print(f"   ⚠ trace update failed: {e}")

        result = {
            "q_id": q_id,
            "question": question,
            "expected_domain": expected_domain,
            "n_domain_match_top5": n_match,
            "domains_in_top5": domains_in_top,
            "latency_s": latency,
            "answer_preview": (answer[:200] + "…") if len(answer) > 200 else answer,
            "n_top": len(top),
            "error": error,
        }
        results.append(result)
        status = "✓" if n_match >= 1 else "⚠"
        print(f"   {status} top-5 domain match: {n_match}/5  ({latency}s)\n")

    obs.flush()
    print("✅ Traces flushées.")

    # Output JSON consolidé
    out_path = OUT_DIR / "spot_check_traced_results.json"
    out_path.write_text(json.dumps({
        "session_id": session_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "corpus": str(CORPUS_PATH.relative_to(REPO_ROOT)),
        "index": str(INDEX_PATH.relative_to(REPO_ROOT)),
        "n_questions": len(results),
        "n_pass_domain_match": sum(1 for r in results if r["n_domain_match_top5"] >= 1),
        "results": results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"→ Résultats JSON : {out_path}")

    # Récap rapide
    pass_count = sum(1 for r in results if r["n_domain_match_top5"] >= 1)
    avg_latency = sum(r["latency_s"] for r in results) / len(results)
    print(f"\n📊 Récap : {pass_count}/{len(results)} domain match ≥1, avg latency {avg_latency:.2f}s")
    print(f"   Filter Langfuse UI : session_id={session_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
