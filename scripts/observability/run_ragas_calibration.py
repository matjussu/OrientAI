"""Bench Ragas calibration — 50 entrées golden JSONL équilibrées par category × axe.

Run le pipeline OrientIA (état HEAD, donc post-fix C+ si on est sur la branche)
sur 50 questions du golden_qa_v1.jsonl, capture les contexts retrievés, puis
évalue avec Ragas faithfulness + context_recall via Mistral small (judge).

Cible Matteo : scores 0.6-0.85 = calibré. Trop haut (≥0.95) = mock-friendly,
trop bas (≤0.4) = signal cassé.

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/observability/run_ragas_calibration.py
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

# ⚠️ CRITIQUE : shim mistralai AVANT import ragas
import src.observability as obs  # noqa: F401,E402

from mistralai.client import Mistral  # noqa: E402
from src.config import load_config  # noqa: E402
from src.rag.factory import make_production_pipeline  # noqa: E402

from datasets import Dataset  # noqa: E402
from ragas import evaluate  # noqa: E402
from ragas.metrics import faithfulness, context_recall  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings  # noqa: E402


GOLDEN_PATH = REPO_ROOT / "data" / "golden_qa" / "golden_qa_v1.jsonl"
CORPUS_PATH = REPO_ROOT / "data" / "processed" / "formations_v5.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_v5.index"
OUT_DIR = REPO_ROOT / "results" / "ragas_calibration_2026-05-14"

# Distribution stratifiée 50 entrées sur 5 catégories
SAMPLES_PER_CATEGORY = {
    "lyceen_post_bac": 10,
    "etudiant_reorientation": 11,
    "actif_jeune": 10,
    "master_debouchés": 10,
    "famille_social": 9,
}
TOTAL_SAMPLES = sum(SAMPLES_PER_CATEGORY.values())  # 50
SEED = 42


def _load_jsonl() -> list[dict]:
    """Charge JSONL, filtre keep+flag, retourne list de dicts."""
    entries = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("decision") in ("keep", "flag"):
            entries.append(d)
    return entries


def _stratify_sample(entries: list[dict], samples_per_cat: dict[str, int], seed: int) -> list[dict]:
    """Échantillonnage stratifié déterministe par category."""
    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e.get("category", "?"), []).append(e)

    rng = random.Random(seed)
    sampled = []
    for cat, n in samples_per_cat.items():
        pool = by_cat.get(cat, [])
        if len(pool) < n:
            print(f"⚠ Catégorie '{cat}' a seulement {len(pool)} entrées (besoin {n}), prends tout")
            sampled.extend(pool)
        else:
            sampled.extend(rng.sample(pool, n))
    return sampled


def _fiche_to_context(fiche: dict) -> str:
    """Convertit une fiche dict en string de contexte pour Ragas.

    Inclut nom, établissement, ville, région, domain, et le champ text/detail
    si présents. Tronqué à ~600 chars pour rester gérable.
    """
    if not isinstance(fiche, dict):
        return str(fiche)[:600]
    parts = []
    for key in ("nom", "libelle_metier", "libelle", "subject"):
        if val := fiche.get(key):
            parts.append(f"Nom: {val}")
            break
    if etab := fiche.get("etablissement"):
        parts.append(f"Établissement: {etab}")
    if ville := fiche.get("ville"):
        parts.append(f"Ville: {ville}")
    if region := fiche.get("region"):
        parts.append(f"Région: {region}")
    if niveau := fiche.get("niveau"):
        parts.append(f"Niveau: {niveau}")
    if domain := fiche.get("domain"):
        parts.append(f"Type: {domain}")
    # Détail substantiel (le post-fix C+ a maintenant les annexes avec text)
    if text := fiche.get("text"):
        parts.append(f"Détail: {text[:500]}")
    elif detail := fiche.get("detail"):
        parts.append(f"Description: {detail[:400]}")
    if labels := fiche.get("labels"):
        parts.append(f"Labels: {', '.join(labels) if isinstance(labels, list) else labels}")
    return " | ".join(parts)[:1500]


def main() -> int:
    if not GOLDEN_PATH.exists():
        print(f"❌ {GOLDEN_PATH} absent")
        return 1
    if not CORPUS_PATH.exists() or not INDEX_PATH.exists():
        print(f"❌ Corpus ou index manquant")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"→ Stratification : {SAMPLES_PER_CATEGORY} ({TOTAL_SAMPLES} entrées, seed={SEED})")
    entries = _load_jsonl()
    print(f"→ JSONL : {len(entries)} entrées keep+flag")
    sampled = _stratify_sample(entries, SAMPLES_PER_CATEGORY, SEED)
    print(f"→ Sample stratifié : {len(sampled)} entrées sélectionnées")

    # Load pipeline
    print(f"\n→ Loading pipeline (corpus + index)…")
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))
    print(f"→ Pipeline ready ({len(fiches):,} fiches)")

    # Phase 1 : run pipeline sur chaque question, capture answer + contexts
    print(f"\n=== Phase 1/2 : pipeline.answer() × {TOTAL_SAMPLES} ===")
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    metadata = []

    for i, e in enumerate(sampled, 1):
        q = e.get("final_qa", {}).get("question") or e.get("question_seed", "")
        gt = e.get("final_qa", {}).get("answer_refined") or e.get("draft", {}).get("answer", "")
        if not q or not gt:
            print(f"  ⚠ {i}/{TOTAL_SAMPLES} entry skipped (missing fields)")
            continue
        t0 = time.time()
        try:
            answer, top = pipeline.answer(q, top_k_sources=5)
        except Exception as exc:
            print(f"  ❌ {i}/{TOTAL_SAMPLES} ERROR : {exc}")
            continue
        ctx = [_fiche_to_context(s.get("fiche", s) if isinstance(s, dict) else s) for s in top[:5]]
        questions.append(q)
        answers.append(answer)
        contexts.append(ctx if ctx else ["(empty retrieval)"])
        ground_truths.append(gt)
        metadata.append({
            "prompt_id": e.get("prompt_id"),
            "iteration": e.get("iteration"),
            "category": e.get("category"),
            "axe_couvert": e.get("axe_couvert"),
            "decision": e.get("decision"),
            "elapsed_s": round(time.time() - t0, 2),
        })
        print(f"  [{i:02d}/{TOTAL_SAMPLES}] {e.get('category', '?'):25s} {time.time()-t0:5.2f}s  ({len(top)} ctx)")

    print(f"\n→ Phase 1 done : {len(questions)} samples avec contexts")

    # Phase 2 : Ragas eval
    print(f"\n=== Phase 2/2 : Ragas faithfulness + context_recall ===")
    dataset = Dataset.from_dict({
        "user_input": questions,
        "response": answers,
        "retrieved_contexts": contexts,
        "reference": ground_truths,
    })

    mistral_llm = LangchainLLMWrapper(
        ChatMistralAI(
            model="mistral-small-latest",
            temperature=0.0,
            mistral_api_key=cfg.mistral_api_key,
        )
    )
    mistral_emb = LangchainEmbeddingsWrapper(
        MistralAIEmbeddings(api_key=cfg.mistral_api_key)
    )

    print(f"→ Ragas evaluate (judge: mistral-small-latest, T=0)…")
    t_eval = time.time()
    result = evaluate(
        dataset,
        metrics=[faithfulness, context_recall],
        llm=mistral_llm,
        embeddings=mistral_emb,
    )
    print(f"→ Ragas done in {time.time()-t_eval:.1f}s")
    print()
    print(f"📊 Résultats Ragas (n={len(questions)}) :")
    print(f"   {result}")

    # Per-sample scores
    df = result.to_pandas()
    # Save
    out_path = OUT_DIR / "ragas_results.json"
    rows = []
    for i, row in df.iterrows():
        md = metadata[i] if i < len(metadata) else {}
        rows.append({
            "index": int(i),
            **md,
            "user_input": row.get("user_input", ""),
            "faithfulness": float(row.get("faithfulness", 0)) if row.get("faithfulness") is not None else None,
            "context_recall": float(row.get("context_recall", 0)) if row.get("context_recall") is not None else None,
        })

    summary = {
        "n_questions": len(questions),
        "ragas_aggregate": {
            "faithfulness": float(df["faithfulness"].mean()),
            "context_recall": float(df["context_recall"].mean()),
        },
        "by_category": {},
    }
    # Per-category breakdown
    import collections
    cat_scores: dict[str, list] = collections.defaultdict(lambda: {"faith": [], "recall": []})
    for r in rows:
        cat = r.get("category", "?")
        if r["faithfulness"] is not None:
            cat_scores[cat]["faith"].append(r["faithfulness"])
        if r["context_recall"] is not None:
            cat_scores[cat]["recall"].append(r["context_recall"])
    for cat, sc in cat_scores.items():
        if sc["faith"] and sc["recall"]:
            summary["by_category"][cat] = {
                "n": len(sc["faith"]),
                "faithfulness_avg": round(sum(sc["faith"]) / len(sc["faith"]), 3),
                "context_recall_avg": round(sum(sc["recall"]) / len(sc["recall"]), 3),
            }

    out_path.write_text(json.dumps({
        "summary": summary,
        "per_sample": rows,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n→ Résultats : {out_path}")
    print(f"\n=== Récap final ===")
    print(f"  Faithfulness avg : {summary['ragas_aggregate']['faithfulness']:.3f}")
    print(f"  Context recall avg : {summary['ragas_aggregate']['context_recall']:.3f}")
    print(f"\nPar catégorie :")
    for cat, s in summary["by_category"].items():
        print(f"  {cat:25s} n={s['n']:2d}  faith={s['faithfulness_avg']:.3f}  recall={s['context_recall_avg']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
