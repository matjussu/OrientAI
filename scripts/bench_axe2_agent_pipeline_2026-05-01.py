"""Sprint 12 axe 2 — bench Option α-comparatif TRIANGULAIRE 3 systèmes.

Référence ordre : 2026-05-01-1820 Option α GO Matteo 16:54 CEST.

## Stratégie

Bench 10 questions hold-out (subset reproductible seed=42 depuis test
split de `src/eval/questions.json` 68q hold-out) sur 2 systèmes :
- `AgentPipelineSystem` (Sprint 1-4 axe B mergé main, Mistral Large
    function-calling souverain + génération Mistral medium, fact_check
    désactivé pour apples-to-apples)
- `MistralWithCustomPromptSystem` configuré comme `mistral_v3_2_no_rag`
    (single-shot Mistral medium v3.2 prompt sans RAG)

Sortie : JSONL des réponses pour judge S4 (Claude Sonnet rubric).

## Critère GO/NO-GO empirique

Δ Claude rubric mean (`agent_pipeline_v3_2` - `mistral_v3_2_no_rag`)
> +0.5 → GO Sprint 12 axe 2 confirmé.

## Coût estimé

- AgentPipeline : 10q × ~25-40s × ~$0.02-0.05 = ~$0.50-1.00
- mistral_v3_2_no_rag : 10q × ~10s × ~$0.005 = ~$0.05
- Total bench responses : ~$0.55-1.05

Judge S4 séparé : ~$1-2 (Claude Sonnet rubric ~$0.15/q × 20).

## Corpus AgentPipeline

Note design : phaseD/phaseE corpus JSON manquant localement (post
Sprint 9 mergé sur main). Fallback `phaseC_blocs` (Sprint 6, 54 186
cells, json+index présents). Documenté dans verdict S5.

Usage :
    PYTHONPATH=. python3 scripts/bench_axe2_agent_pipeline_2026-05-01.py
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import faiss  # noqa: E402
from mistralai.client import Mistral  # noqa: E402

from src.agent.cache import LRUCache  # noqa: E402
from src.agent.pipeline_agent import AgentPipeline  # noqa: E402
from src.config import load_config  # noqa: E402
from src.eval.systems import (  # noqa: E402
    AgentPipelineSystem,
    MistralWithCustomPromptSystem,
    OurRagSystem,
)
from src.rag.pipeline import OrientIAPipeline  # noqa: E402
from src.prompt.system import SYSTEM_PROMPT  # noqa: E402


QUESTIONS_PATH = REPO_ROOT / "src" / "eval" / "questions.json"
# Pipeline A AgentPipeline — corpus phaseC_blocs (Sprint 6 fallback, phaseD JSON missing)
AGENT_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseC_blocs.json"
AGENT_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseC_blocs.index"
# Pipeline B OurRagSystem enrichi — corpus formations_unified post-D1 (Sprint 12)
RAG_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_unified.json"
RAG_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_unified.index"
GOLDEN_QA_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "golden_qa.index"
GOLDEN_QA_META_PATH = REPO_ROOT / "data" / "processed" / "golden_qa_meta.json"
OUT_PATH = REPO_ROOT / "results" / "sprint12-axe-2-agent-pipeline-bench" / "responses_triangulaire.jsonl"
SEED = 42
N_HOLD_OUT = 10


def _select_holdout_questions() -> list[dict]:
    """Sélection reproductible 10q depuis test split (68q hold-out)."""
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    test_questions = [q for q in data["questions"] if q.get("split") == "test"]
    rng = random.Random(SEED)
    sample = rng.sample(test_questions, k=N_HOLD_OUT)
    return sorted(sample, key=lambda q: q["id"])


def main() -> int:
    print(f"[bench-α] Loading config + Mistral client...")
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    # Pipeline A — AgentPipeline vintage (phaseC_blocs corpus, Sprint 6 fallback)
    print(f"[bench-α] Loading phaseC_blocs corpus + index for AgentPipeline...")
    agent_fiches = json.loads(AGENT_FICHES_PATH.read_text(encoding="utf-8"))
    agent_index = faiss.read_index(str(AGENT_INDEX_PATH))
    print(f"[bench-α]   {len(agent_fiches):,} fiches, index ntotal={agent_index.ntotal:,}")

    # Pipeline B — OurRag enrichi (formations_unified Sprint 12 D1 + Q&A Golden +
    # metadata filter activé par défaut)
    print(f"[bench-α] Loading formations_unified corpus + index for OurRag enrichi...")
    rag_fiches = json.loads(RAG_FICHES_PATH.read_text(encoding="utf-8"))
    rag_index = faiss.read_index(str(RAG_INDEX_PATH))
    print(f"[bench-α]   {len(rag_fiches):,} fiches, index ntotal={rag_index.ntotal:,}")

    print(f"[bench-α] Building 3 systems triangulaire α-comparatif...")
    # 1. agent_pipeline_v3_2 (vintage Sprint 4)
    agent_pipeline = AgentPipeline(
        client=client,
        fiches=agent_fiches,
        index=agent_index,
        profile_cache=LRUCache(maxsize=128),
        aggregated_top_n=8,
        parallel_max_workers=3,
        enable_fact_check=False,
    )
    sys_agent = AgentPipelineSystem(pipeline=agent_pipeline)

    # 2. our_rag_enriched (acquis Sprint 9-12 empilés)
    rag_pipeline = OrientIAPipeline(
        client=client,
        fiches=rag_fiches,
        use_mmr=True,
        use_intent=True,
        use_metadata_filter=True,  # Sprint 10 chantier C activated
        use_golden_qa=True,  # Sprint 10 chantier D
        golden_qa_index_path=str(GOLDEN_QA_INDEX_PATH),
        golden_qa_meta_path=str(GOLDEN_QA_META_PATH),
    )
    rag_pipeline.load_index_from(str(RAG_INDEX_PATH))
    sys_rag_enriched = OurRagSystem(pipeline=rag_pipeline)
    sys_rag_enriched.name = "our_rag_enriched"  # rename pour clarté α-comparatif

    # 3. mistral_v3_2_no_rag (no-RAG baseline)
    sys_baseline = MistralWithCustomPromptSystem(
        client=client,
        system_prompt=SYSTEM_PROMPT,
        name="mistral_v3_2_no_rag",
    )
    print(f"[bench-α]   {sys_agent.name} + {sys_rag_enriched.name} + {sys_baseline.name}")

    questions = _select_holdout_questions()
    print(f"[bench-α] {len(questions)} hold-out questions (seed={SEED}) :")
    for q in questions:
        print(f"           - {q['id']} [{q['category']}] {q['text'][:60]}...")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    cost_estimate = {"agent": 0.0, "baseline": 0.0}

    print(f"\n[bench-α] === RUN === ({len(questions)} q × 3 systèmes = {3*len(questions)} calls)")

    def _safe_answer(system, qid, text):
        t0 = time.time()
        try:
            answer_text = system.answer(qid, text)
            return {
                "answer_text": answer_text,
                "elapsed_s": round(time.time() - t0, 2),
                "chars": len(answer_text),
                "error": None,
            }
        except Exception as e:
            return {
                "answer_text": f"[bench_error: {e}]",
                "elapsed_s": round(time.time() - t0, 2),
                "chars": 0,
                "error": str(e),
            }

    for i, q in enumerate(questions, 1):
        qid, text = q["id"], q["text"]
        print(f"\n[bench-α] Q{i}/{len(questions)} {qid} [{q['category']}]")

        agent_result = _safe_answer(sys_agent, qid, text)
        print(f"  agent_vintage   : {agent_result['elapsed_s']:.1f}s, {agent_result['chars']} chars")

        rag_enriched_result = _safe_answer(sys_rag_enriched, qid, text)
        print(f"  rag_enriched    : {rag_enriched_result['elapsed_s']:.1f}s, {rag_enriched_result['chars']} chars")

        baseline_result = _safe_answer(sys_baseline, qid, text)
        print(f"  baseline_no_rag : {baseline_result['elapsed_s']:.1f}s, {baseline_result['chars']} chars")

        results.append({
            "qid": qid,
            "category": q["category"],
            "split": q.get("split"),
            "question": text,
            "agent_pipeline_v3_2": agent_result,
            "our_rag_enriched": rag_enriched_result,
            "mistral_v3_2_no_rag": baseline_result,
        })

    # Save raw JSONL
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[bench-α] raw saved : {OUT_PATH}")

    # Aggregated stats triangulaire
    print("\n========== STATS TRIANGULAIRE ==========")
    for sys_key in ("agent_pipeline_v3_2", "our_rag_enriched", "mistral_v3_2_no_rag"):
        lats = [r[sys_key]["elapsed_s"] for r in results]
        chars = [r[sys_key]["chars"] for r in results]
        errs = sum(1 for r in results if r[sys_key]["error"])
        print(f"{sys_key:25s} : avg latency {sum(lats)/len(lats):5.1f}s, "
              f"avg chars {sum(chars)//len(chars):5d}, errors {errs}/{len(results)}")
    print("========================================\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
