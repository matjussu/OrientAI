"""Fetch les 13 traces du spot-check via Langfuse API et calcule stats par étape.

Lit le session_id dans le JSON consolidé (output de run_spot_check_traced.py)
ou prend le plus récent session "spot_check_baseline*" via API.

Output :
  - markdown docs/OBSERVABILITY_BASELINE_2026-05-13.md avec tableaux
  - JSON results/observability_baseline_2026-05-13/aggregated_stats.json

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/observability/analyze_spot_check_traces.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from langfuse import Langfuse  # noqa: E402


OUT_DIR = REPO_ROOT / "results" / "observability_baseline_2026-05-13"
RESULTS_JSON = OUT_DIR / "spot_check_traced_results.json"
REPORT_MD = REPO_ROOT / "docs" / "OBSERVABILITY_BASELINE_2026-05-13.md"
STATS_JSON = OUT_DIR / "aggregated_stats.json"


def _duration_s(o) -> float:
    if o.end_time and o.start_time:
        return (o.end_time - o.start_time).total_seconds()
    return 0.0


def main() -> int:
    if not RESULTS_JSON.exists():
        print(f"❌ Manquant : {RESULTS_JSON}. Lance d'abord run_spot_check_traced.py")
        return 1

    consolidated = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    session_id = consolidated["session_id"]
    print(f"→ Session : {session_id}")
    print(f"→ {consolidated['n_questions']} questions")
    print()

    lf = Langfuse()
    # Workaround : update_current_trace n'existe pas en Langfuse v4 → les tags
    # n'ont pas été attachés. On matche les 13 traces les plus récentes
    # avec name='orientia.answer' par ordre temporel descendant aux
    # 13 questions du JSON consolidé (ordre Q13→Q01 dans Langfuse).
    n_q = len(consolidated["results"])
    traces = lf.api.trace.list(name="orientia.answer", limit=n_q + 5)
    # On ignore la 1ère trace si c'est le smoke test (pas dans le batch)
    # → on garde les n_q plus récentes
    recent = traces.data[:n_q]
    # Langfuse API renvoie ordre desc (plus récente en 1er) → reverse pour
    # avoir Q01 en premier (chronologique)
    recent.reverse()
    print(f"→ Récupéré {len(recent)} traces récentes via API (matchées par ordre temporel)")

    # Map q_id → trace par position
    trace_by_q: dict[str, dict] = {}
    for i, t in enumerate(recent, 1):
        q_id = f"Q{i:02d}"
        detail = lf.api.trace.get(t.id)
        trace_by_q[q_id] = detail

    print(f"→ Trace mapping : {sorted(trace_by_q.keys())}")
    print()

    # Pour chaque trace, extraire le timing par step et le rattacher
    # aux infos consolidées (expected_domain, n_match, etc.)
    enriched = []
    step_timings: dict[str, list[float]] = defaultdict(list)
    for r in consolidated["results"]:
        q_id = r["q_id"]
        t = trace_by_q.get(q_id)
        if t is None:
            print(f"⚠ Trace manquante pour {q_id}")
            continue

        # Map step name → durée
        step_durs = {}
        for o in (t.observations or []):
            step_durs[o.name] = _duration_s(o)
            step_timings[o.name].append(_duration_s(o))

        enriched.append({
            **r,
            "trace_id": t.id,
            "trace_total_s": step_durs.get("orientia.answer", 0.0),
            "step_durs": step_durs,
            "metadata": t.metadata,
        })

    # Stats agrégées par step
    step_stats: dict[str, dict] = {}
    for step, durs in step_timings.items():
        if not durs:
            continue
        step_stats[step] = {
            "n_observations": len(durs),
            "avg_s": round(statistics.mean(durs), 3),
            "median_s": round(statistics.median(durs), 3),
            "min_s": round(min(durs), 3),
            "max_s": round(max(durs), 3),
            "p95_s": round(sorted(durs)[max(0, int(len(durs) * 0.95) - 1)], 3) if len(durs) > 1 else durs[0],
            "total_s": round(sum(durs), 3),
        }

    # Split pass/fail
    pass_q = [e for e in enriched if e["n_domain_match_top5"] >= 1]
    fail_q = [e for e in enriched if e["n_domain_match_top5"] < 1]

    def _mean_step_dur(qlist, step):
        vals = [e["step_durs"].get(step, 0.0) for e in qlist if step in e["step_durs"]]
        return round(statistics.mean(vals), 3) if vals else 0.0

    # Compare key steps pass vs fail
    key_steps = [
        "orientia.answer",
        "step_1_scope_classify",
        "step_2_router_llm",
        "step_5_retrieve_filter",
        "step_8_generate_with_retry",
    ]
    pass_fail_compare = {}
    for s in key_steps:
        pass_fail_compare[s] = {
            "pass_avg_s": _mean_step_dur(pass_q, s),
            "fail_avg_s": _mean_step_dur(fail_q, s),
            "n_pass": len([e for e in pass_q if s in e["step_durs"]]),
            "n_fail": len([e for e in fail_q if s in e["step_durs"]]),
        }

    # Save aggregated
    agg = {
        "session_id": session_id,
        "n_questions": len(enriched),
        "n_pass": len(pass_q),
        "n_fail": len(fail_q),
        "step_stats_global": step_stats,
        "pass_vs_fail_compare": pass_fail_compare,
        "questions_detail": [
            {k: v for k, v in e.items() if k != "metadata"}
            for e in enriched
        ],
    }
    STATS_JSON.write_text(json.dumps(agg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"→ Stats agrégées : {STATS_JSON}")

    # --- Render markdown report ---
    md = []
    md.append("# Observability Baseline — Spot-Check Gate 3 sous Langfuse")
    md.append("")
    md.append(f"**Date** : {consolidated['timestamp']}  ")
    md.append(f"**Session Langfuse** : `{session_id}`  ")
    md.append(f"**Corpus** : `{consolidated['corpus']}`  ")
    md.append(f"**Index** : `{consolidated['index']}`  ")
    md.append("")
    md.append(f"**Résultat global** : {len(pass_q)}/{len(enriched)} questions avec domain match ≥1 dans top-5 — **baseline pré-fix `fiche_to_text`**")
    md.append("")
    md.append("## 1. Timing global par étape (toutes questions)")
    md.append("")
    md.append("| Étape | n obs | avg | médiane | p95 | min | max | total cumulé |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name in sorted(step_stats.keys(), key=lambda s: -step_stats[s]["avg_s"]):
        s = step_stats[name]
        md.append(f"| `{name}` | {s['n_observations']} | {s['avg_s']}s | {s['median_s']}s | {s['p95_s']}s | {s['min_s']}s | {s['max_s']}s | {s['total_s']}s |")
    md.append("")

    md.append("## 2. Comparaison Pass (domain match ≥1) vs Fail (0/5)")
    md.append("")
    md.append("| Étape | Pass avg | Fail avg | Δ (fail-pass) |")
    md.append("|---|---:|---:|---:|")
    for s, comp in pass_fail_compare.items():
        delta = round(comp["fail_avg_s"] - comp["pass_avg_s"], 3)
        sign = "+" if delta >= 0 else ""
        md.append(f"| `{s}` | {comp['pass_avg_s']}s (n={comp['n_pass']}) | {comp['fail_avg_s']}s (n={comp['n_fail']}) | {sign}{delta}s |")
    md.append("")

    md.append("## 3. Détail par question")
    md.append("")
    md.append("| Q | expected_domain | match top-5 | total | retrieve | generate | scope | router |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for e in enriched:
        sd = e["step_durs"]
        md.append(
            f"| **{e['q_id']}** {e['expected_domain']} | "
            f"`{e['expected_domain']}` | "
            f"{e['n_domain_match_top5']}/5 | "
            f"{sd.get('orientia.answer', 0):.2f}s | "
            f"{sd.get('step_5_retrieve_filter', 0):.2f}s | "
            f"{sd.get('step_8_generate_with_retry', 0):.2f}s | "
            f"{sd.get('step_1_scope_classify', 0):.2f}s | "
            f"{sd.get('step_2_router_llm', 0):.2f}s |"
        )
    md.append("")
    md.append("## 4. Lien Langfuse UI")
    md.append("")
    md.append(f"Filter dashboard : `session_id = {session_id}` → 13 traces grouped")
    md.append("")

    REPORT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"→ Rapport markdown : {REPORT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
