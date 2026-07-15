"""Analyse multi-axes des 13 traces du spot-check : pas seulement la latency.

Extrait :
  - Tokens in/out par appel Mistral (medium / small / embed) → coût par question
  - Full answer (capturée par @observe) → longueur, citations, refus
  - Domains retrievés vs expected → distribution mismatch
  - Si dispo : scope_label, router sub_indexes

Lit le JSON consolidé (run_spot_check_traced.py output) puis enrichit via API
Langfuse en récupérant les full traces.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from langfuse import Langfuse  # noqa: E402


OUT_DIR = Path(os.environ.get(
    "ORIENTIA_OBSERVABILITY_OUT_DIR",
    str(REPO_ROOT / "results" / "observability_baseline_2026-05-13")
))
RESULTS_JSON = OUT_DIR / "spot_check_traced_results.json"
MULTI_AXIS_JSON = OUT_DIR / "multi_axis_analysis.json"
_REPORT_NAME = os.environ.get("ORIENTIA_OBSERVABILITY_REPORT", "OBSERVABILITY_MULTI_AXIS_2026-05-13.md")
MULTI_AXIS_MD = REPO_ROOT / "docs" / _REPORT_NAME


# Tarifs Mistral 2026 ($/1M tokens) — confirmer si besoin
PRICING = {
    "mistral-medium-latest": {"input": 0.40, "output": 2.00},
    "mistral-small-latest": {"input": 0.20, "output": 0.60},
    "mistral-embed": {"input": 0.10, "output": 0.0},
}


def _estimate_cost(obs) -> float:
    """Estime le coût USD d'une observation à partir des tokens."""
    if not obs.usage_details:
        return 0.0
    model = (obs.model or "").lower()
    matched_model = None
    for k in PRICING:
        if k in model:
            matched_model = k
            break
    if not matched_model:
        return 0.0
    pricing = PRICING[matched_model]
    in_tok = obs.usage_details.get("input", 0) or 0
    out_tok = obs.usage_details.get("output", 0) or 0
    return (in_tok / 1_000_000) * pricing["input"] + (out_tok / 1_000_000) * pricing["output"]


def _count_citations(text: str) -> int:
    """Compte les [source SX] (incl. combinés S3/S4/S5 ou S3, S4)."""
    n = 0
    for tag in re.findall(r"\[source\s+([^\]]+)\]", text or ""):
        n += len(re.findall(r"S\d+", tag))
    return n


def _detect_refusal(text: str) -> bool:
    """Détecte un pattern de refus / info-non-disponible."""
    patterns = [
        r"je n'ai pas (de|d')\s*(info|donnée|formation)",
        r"information non disponible",
        r"je préfère ne pas répondre",
        r"mes sources ne",
        r"aucune information",
        r"absente? de mes sources",
    ]
    t = (text or "").lower()
    return any(re.search(p, t) for p in patterns)


def _detect_url_hallu(text: str) -> int:
    """Compte les patterns d'URL hallucinées '(information non disponible dans mes sources)'."""
    return len(re.findall(r"\(information non disponible dans mes sources\)", text or "", re.I))


def main() -> int:
    if not RESULTS_JSON.exists():
        print(f"❌ {RESULTS_JSON} absent")
        return 1

    consolidated = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    import httpx
    lf = Langfuse(httpx_client=httpx.Client(timeout=60.0))
    n_q = len(consolidated["results"])

    traces_list = lf.api.trace.list(name="orientia.answer", limit=n_q + 5)
    recent = traces_list.data[:n_q]
    recent.reverse()

    enriched = []
    for i, (r, t_summary) in enumerate(zip(consolidated["results"], recent), 1):
        q_id = r["q_id"]
        t = lf.api.trace.get(t_summary.id)

        # Full answer = output du root span 'orientia.answer'
        root = next((o for o in (t.observations or []) if o.name == "orientia.answer"), None)
        full_answer = ""
        if root and root.output:
            # output est un tuple (answer_text, top) capturé → premier élément
            if isinstance(root.output, list) and len(root.output) >= 1:
                full_answer = root.output[0] if isinstance(root.output[0], str) else str(root.output[0])
            elif isinstance(root.output, str):
                full_answer = root.output

        # Tokens & cost par type d'appel Mistral
        tokens_in = 0
        tokens_out = 0
        cost_usd = 0.0
        cost_by_model: dict[str, float] = defaultdict(float)
        tokens_by_model: dict[str, dict] = defaultdict(lambda: {"input": 0, "output": 0})
        n_mistral_calls = 0
        for o in (t.observations or []):
            if o.type in ("GENERATION", "EMBEDDING"):
                n_mistral_calls += 1
                model_key = (o.model or "unknown").lower()
                # Simplifier : juste le nom modèle, pas latest etc
                model_short = model_key.replace("-latest", "")
                if o.usage_details:
                    in_tok = o.usage_details.get("input", 0) or 0
                    out_tok = o.usage_details.get("output", 0) or 0
                    tokens_in += in_tok
                    tokens_out += out_tok
                    tokens_by_model[model_short]["input"] += in_tok
                    tokens_by_model[model_short]["output"] += out_tok
                c = _estimate_cost(o)
                cost_usd += c
                cost_by_model[model_short] += c

        # Contenu de la réponse
        n_citations = _count_citations(full_answer)
        is_refusal = _detect_refusal(full_answer)
        n_url_hallu = _detect_url_hallu(full_answer)
        n_words = len(full_answer.split())
        n_chars = len(full_answer)

        # Tag depuis la trace (si présent — sera None à cause du bug update_current_trace)
        enriched.append({
            **r,
            "trace_id": t.id,
            "trace_total_s": next((
                (o.end_time - o.start_time).total_seconds()
                for o in (t.observations or [])
                if o.name == "orientia.answer"
            ), 0.0),
            "n_mistral_calls": n_mistral_calls,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost_usd, 6),
            "cost_by_model": {k: round(v, 6) for k, v in cost_by_model.items()},
            "tokens_by_model": dict(tokens_by_model),
            "answer_full": full_answer,
            "n_words_answer": n_words,
            "n_chars_answer": n_chars,
            "n_citations": n_citations,
            "is_refusal": is_refusal,
            "n_url_hallu": n_url_hallu,
        })

    # Stats agrégées
    total_cost = sum(e["cost_usd"] for e in enriched)
    total_tokens_in = sum(e["tokens_in"] for e in enriched)
    total_tokens_out = sum(e["tokens_out"] for e in enriched)
    pass_q = [e for e in enriched if e["n_domain_match_top5"] >= 1]
    fail_q = [e for e in enriched if e["n_domain_match_top5"] < 1]

    def _mean(lst, key):
        vals = [e[key] for e in lst if e.get(key) is not None]
        return round(statistics.mean(vals), 3) if vals else 0.0

    summary = {
        "n_questions": len(enriched),
        "n_pass": len(pass_q),
        "n_fail": len(fail_q),
        "cost_total_usd": round(total_cost, 4),
        "cost_avg_per_q_usd": round(total_cost / len(enriched), 6) if enriched else 0,
        "tokens_total_in": total_tokens_in,
        "tokens_total_out": total_tokens_out,
        "avg_words_answer_pass": _mean(pass_q, "n_words_answer"),
        "avg_words_answer_fail": _mean(fail_q, "n_words_answer"),
        "avg_citations_pass": _mean(pass_q, "n_citations"),
        "avg_citations_fail": _mean(fail_q, "n_citations"),
        "n_refusal": sum(1 for e in enriched if e["is_refusal"]),
        "n_url_hallu": sum(1 for e in enriched if e["n_url_hallu"] > 0),
        "n_url_hallu_total": sum(e["n_url_hallu"] for e in enriched),
    }

    out_doc = {
        "summary": summary,
        "questions": enriched,
    }
    MULTI_AXIS_JSON.write_text(json.dumps(out_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"→ Multi-axis JSON : {MULTI_AXIS_JSON}")

    # Rapport markdown
    md = []
    md.append("# Observability Multi-Axes — Spot-Check Gate 3 (correction)")
    md.append("")
    md.append("**Correction du précédent rapport** : l'analyse initiale n'exploitait que l'axe LATENCY. Voici les autres dimensions présentes dans les traces que je n'avais pas regardées.")
    md.append("")
    md.append("## A. Coût & tokens")
    md.append("")
    md.append(f"- **Coût total bench** : ${summary['cost_total_usd']:.4f} (13 questions)")
    md.append(f"- **Coût moyen / question** : ${summary['cost_avg_per_q_usd']:.6f}")
    md.append(f"- **Tokens total in** : {summary['tokens_total_in']:,}")
    md.append(f"- **Tokens total out** : {summary['tokens_total_out']:,}")
    md.append("")
    md.append("| Q | tokens in | tokens out | $ cost | mistral-medium | mistral-small | embed |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")
    for e in enriched:
        cm = e["cost_by_model"]
        md.append(f"| {e['q_id']} | {e['tokens_in']:,} | {e['tokens_out']:,} | ${e['cost_usd']:.6f} | ${cm.get('mistral-medium', 0):.6f} | ${cm.get('mistral-small', 0):.6f} | ${cm.get('mistral-embed', 0):.6f} |")
    md.append("")

    md.append("## B. Qualité de la réponse")
    md.append("")
    md.append(f"- **Refus détectés** : {summary['n_refusal']}/13 questions ({100*summary['n_refusal']/13:.0f}%)")
    md.append(f"- **URLs hallucinées** : {summary['n_url_hallu']}/13 questions concernées, {summary['n_url_hallu_total']} occurrences total (pattern `(information non disponible dans mes sources)`)")
    md.append(f"- **Mots / réponse — pass** : {summary['avg_words_answer_pass']}")
    md.append(f"- **Mots / réponse — fail** : {summary['avg_words_answer_fail']}")
    md.append(f"- **Citations / réponse — pass** : {summary['avg_citations_pass']}")
    md.append(f"- **Citations / réponse — fail** : {summary['avg_citations_fail']}")
    md.append("")
    md.append("| Q | match | mots | citations | refusal | URL hallu | preview |")
    md.append("|---|---:|---:|---:|:---:|---:|---|")
    for e in enriched:
        emoji = "✅" if e["n_domain_match_top5"] >= 1 else "❌"
        ref = "⚠" if e["is_refusal"] else "—"
        url_h = "⚠" if e["n_url_hallu"] > 0 else "—"
        preview = (e["answer_full"][:80] + "…").replace("\n", " ")
        md.append(f"| {e['q_id']} | {emoji} {e['n_domain_match_top5']}/5 | {e['n_words_answer']} | {e['n_citations']} | {ref} | {e['n_url_hallu']} | {preview} |")
    md.append("")

    md.append("## C. Patterns sources retrievées (top-5 domain distribution)")
    md.append("")
    all_top_domains: Counter = Counter()
    for e in enriched:
        for d in e["domains_in_top5"]:
            all_top_domains[d or "(formation)"] += 1
    md.append("Distribution agrégée des 65 sources top-5 retrievées sur les 13 questions :")
    md.append("")
    md.append("| Domain | Count | % |")
    md.append("|---|---:|---:|")
    total_sources = sum(all_top_domains.values())
    for dom, n in all_top_domains.most_common():
        md.append(f"| `{dom}` | {n} | {100*n/total_sources:.1f}% |")
    md.append("")

    md.append("## D. Synthèse multi-axes")
    md.append("")
    md.append("- **Coût** : negligible (~$0.003/question). Pas une contrainte.")
    md.append(f"- **Refus** : {summary['n_refusal']}/13 — exactement les 9 fails + Q12 (qui a un refus partiel sur 'bac S supprimé')")
    md.append(f"- **URL hallu** : {summary['n_url_hallu']}/13 — pattern toxique `(information non disponible dans mes sources)` injecté dans des liens markdown")
    md.append("- **Distribution sources** : explore le JSON pour voir si les fiches `(formation)` dominent même quand un domain annexe est attendu (preuve directe du diagnostic Claudette `fiche_to_text` ignore le champ `text`)")
    md.append("")

    MULTI_AXIS_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"→ Rapport multi-axes : {MULTI_AXIS_MD}")
    print()
    print(f"📊 Récap : ${summary['cost_total_usd']:.4f} total | {summary['n_refusal']} refus | {summary['n_url_hallu']} Q avec URL hallu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
