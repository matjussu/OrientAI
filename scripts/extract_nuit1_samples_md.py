"""Extraction lisible des Q&A keep+flag nuit 1 (28-29/04) en Markdown.

Lit `data/golden_qa/golden_qa_v1.jsonl`, filtre `decision in (keep, flag)`,
rend en Markdown structuré format v3 (cf docs/sprint9-data-dryrun-samples-2026-04-28.md
commit 6cc9492) pour démarrer le sample humain Matteo+Ella+Deo en matinée.

Usage : python3 scripts/extract_nuit1_samples_md.py
Output : docs/sprint9-data-nuit1-samples-2026-04-29.md

Spec ordre Jarvis : 2026-04-29-0656-claudette-orientia-validation-extract-nuit1.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "data" / "golden_qa" / "golden_qa_v1.jsonl"
OUTPUT_PATH = ROOT / "docs" / "sprint9-data-nuit1-samples-2026-04-29.md"

DECISION_BOUNDARIES = "score_total ≥ 85 = `keep` / 70-84 = `flag` / < 70 = `drop`"


def load_keep_flag(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("decision") in ("keep", "flag"):
                records.append(rec)
    # Tri déterministe : prompt_id puis iteration
    records.sort(key=lambda r: (r["prompt_id"], r["iteration"]))
    return records


def render_research(text: str, max_chars: int = 1200) -> str:
    """Render le research_sources_text en blockquote tronqué."""
    if not text:
        return "_(pas de research extrait)_"
    snippet = text[:max_chars]
    if len(text) > max_chars:
        snippet += "\n\n[...]"
    # Quote chaque ligne
    lines = snippet.split("\n")
    return "\n".join(f"> {ln}" if ln.strip() else ">" for ln in lines)


def render_blockquote(text: str) -> str:
    if not text:
        return "_(vide)_"
    lines = text.split("\n")
    return "\n".join(f"> {ln}" if ln.strip() else ">" for ln in lines)


def render_qa_section(
    rec: dict[str, Any], idx_global: int, n_seeds_for_prompt: int
) -> str:
    """Render une Q&A en section MD format v3 enrichi (category + prompt_id + seed_idx)."""
    pid = rec["prompt_id"]
    it = rec["iteration"]
    cat = rec["category"]
    axe = rec.get("axe_couvert")
    seed_idx = it % n_seeds_for_prompt if n_seeds_for_prompt else it
    decision = rec["decision"]
    score = rec.get("score_total", 0)
    elapsed = rec.get("elapsed_s", 0)

    final_qa = rec.get("final_qa") or {}
    critique = rec.get("critique") or {}
    scores_par_axe = critique.get("scores_par_axe") or {}

    fact = scores_par_axe.get("factuelle", "?")
    post = scores_par_axe.get("posture", "?")
    coh = scores_par_axe.get("coherence", "?")
    hall = scores_par_axe.get("hallucination", "?")

    seed_q = rec.get("question_seed", "")
    refined_q = final_qa.get("question", "")
    refined_a = final_qa.get("answer_refined", "")
    research = rec.get("research_sources_text", "")
    corrections = critique.get("corrections_suggérées", "_(non fournies)_")
    decision_recom = critique.get("decision_recommandée", decision)

    return f"""## Q&A #{idx_global} — `{pid}` iter {it} (catégorie `{cat}`, axe {axe}, seed_idx {seed_idx})

**Décision** : `{decision}` (score **{score}**, recommandée critique `{decision_recom}`)
**Latence** : {elapsed}s

**Question seed (depuis `config/diverse_prompts_50.yaml`)** :
{render_blockquote(seed_q)}

**Question (refined par Phase 4)** :
{render_blockquote(refined_q)}

**Answer (refined par Phase 4)** :

{render_blockquote(refined_a)}

**Sources research (Phase 1 WebSearch, extraits)** :

{render_research(research)}

**Critique scores Phase 3** : factuelle **{fact}/25** / posture **{post}/25** / cohérence **{coh}/25** / hallucination **{hall}/25** = **{score}/100**

**Corrections suggérées par le critique** :
{render_blockquote(corrections)}

_Décision recommandée par critique : `{decision_recom}` — décision finale : `{decision}` (boundaries : {DECISION_BOUNDARIES})_
"""


def build_synthese(records: list[dict[str, Any]], n_seeds_per_prompt: dict[str, int]) -> str:
    """Synthèse fin de doc : distribution + axes faibles + cas limites flagués."""
    # Distribution category + decision
    cat_decision = defaultdict(lambda: Counter())
    for r in records:
        cat_decision[r["category"]][r["decision"]] += 1
    prompt_count = Counter(r["prompt_id"] for r in records)

    # Axes stats
    axes = {"factuelle": [], "posture": [], "coherence": [], "hallucination": []}
    for r in records:
        spa = (r.get("critique") or {}).get("scores_par_axe") or {}
        for k in axes:
            v = spa.get(k)
            if isinstance(v, int):
                axes[k].append(v)

    # Cas limites flagués
    flagged = [r for r in records if r["decision"] == "flag"]
    flagged.sort(key=lambda r: r.get("score_total", 0))  # plus bas en premier

    # Build markdown
    out = ["## Synthèse review humaine\n"]

    out.append("### Distribution par catégorie + décision\n")
    out.append("| Catégorie | keep | flag | total |")
    out.append("|---|---|---|---|")
    for cat, counts in sorted(cat_decision.items()):
        keep = counts.get("keep", 0)
        flag = counts.get("flag", 0)
        out.append(f"| `{cat}` | {keep} | {flag} | {keep + flag} |")
    out.append("")

    out.append("### Distribution par prompt_id\n")
    out.append("| prompt_id | n Q&A keep+flag | seeds disponibles |")
    out.append("|---|---|---|")
    for pid, n in sorted(prompt_count.items()):
        n_seeds = n_seeds_per_prompt.get(pid, "?")
        out.append(f"| `{pid}` | {n} | {n_seeds} |")
    out.append("")

    out.append("### Score moyen par axe critique (45 Q&A)\n")
    out.append("| Axe | Moyenne /25 | Min | Max | Médiane |")
    out.append("|---|---|---|---|---|")
    rows = []
    for axe_name, vals in axes.items():
        if vals:
            mean = statistics.mean(vals)
            mn = min(vals)
            mx = max(vals)
            med = statistics.median(vals)
            rows.append((mean, axe_name, mn, mx, med))
    rows.sort()  # Croissant : plus faible en premier
    for mean, axe_name, mn, mx, med in rows:
        out.append(f"| `{axe_name}` | **{mean:.1f}** | {mn} | {mx} | {med:.1f} |")
    out.append("")
    weakest = rows[0][1] if rows else "?"
    out.append(f"_Axe le plus faible : `{weakest}` — focus prioritaire pour la review humaine._\n")

    out.append("### Couverture catégorielle nuit 1\n")
    out.append("Le pipeline a brûlé le quota avant d'attaquer les catégories suivantes.")
    out.append("La nuit 1 ne couvre que **1 catégorie sur 7** prévues au YAML 51 prompts :\n")
    out.append("- ✅ `lyceen_post_bac` : couvert (45/600 jobs prévus = 7.5%)")
    expected_cats = [
        "etudiant_reorientation",
        "actif_jeune",
        "master_debouches",
        "famille_social",
        "meta_question",
        "profil_non_cadre",
    ]
    for c in expected_cats:
        out.append(f"- ❌ `{c}` : non-couvert (à relancer nuit 2 post-fix)")
    out.append("")

    out.append("### Cas limites instructifs (les 9 flags)\n")
    out.append("Les Q&A flaggées (score 70-84) sont les plus instructives pour calibrer "
               "le prompt v3.2 / la pipeline 4 phases. Triées par score croissant :\n")
    out.append("| # | prompt_id | iter | score | axe le plus bas | sample |")
    out.append("|---|---|---|---|---|---|")
    for i, r in enumerate(flagged, 1):
        pid = r["prompt_id"]
        it = r["iteration"]
        score = r.get("score_total", 0)
        spa = (r.get("critique") or {}).get("scores_par_axe") or {}
        if spa:
            axe_min = min((v, k) for k, v in spa.items() if isinstance(v, int))
            axe_label = f"`{axe_min[1]}` ({axe_min[0]}/25)"
        else:
            axe_label = "?"
        seed = r.get("question_seed", "")[:80]
        out.append(f"| {i} | `{pid}` | {it} | **{score}** | {axe_label} | {seed}{'…' if len(r.get('question_seed', '')) > 80 else ''} |")
    out.append("")

    out.append("### Recommandations sample humain\n")
    out.append("1. **Focus axe `hallucination`** (score moyen le plus bas) — vérifier "
               "chaque chiffre cité, chaque URL référencée, chaque nom propre formation/école.")
    out.append("2. **Comparer keep score 85 vs 89** — y a-t-il une vraie différence "
               "qualitative entre la borne basse keep et le haut du panier ?")
    out.append("3. **Comparer flag 70 vs 84** — la frontière 84/85 est-elle bien "
               "calibrée ? Faut-il décaler boundary keep à 87 ou 90 ?")
    out.append("4. **Couvrir au moins 1 cas par seed_idx unique** dans A1, A2, A3 — "
               "vérifier que le pipeline ne fait pas de bias seed (toujours mêmes "
               "patterns de réponse selon le seed).")
    out.append("5. **Cross-check les 9 flags en priorité** — décider si keep "
               "(remontée frontière) / drop (mauvaise qualité réelle) / re-run "
               "(possibilité bug isolé non-stop-condition).")
    out.append("")

    return "\n".join(out)


def build_yaml_seed_count(yaml_path: Path) -> dict[str, int]:
    """Compte les seeds par prompt_id depuis le YAML config."""
    import yaml as yaml_mod
    if not yaml_path.exists():
        return {}
    data = yaml_mod.safe_load(yaml_path.read_text(encoding="utf-8"))
    return {p["id"]: len(p.get("questions_seed") or []) for p in data.get("prompts", [])}


def main() -> int:
    if not JSONL_PATH.exists():
        print(f"⚠️  JSONL absent : {JSONL_PATH}")
        return 1

    yaml_path = ROOT / "config" / "diverse_prompts_50.yaml"
    n_seeds_per_prompt = build_yaml_seed_count(yaml_path)

    records = load_keep_flag(JSONL_PATH)
    print(f"==> {len(records)} Q&A keep+flag chargées depuis {JSONL_PATH.name}")

    # Header
    keep_n = sum(1 for r in records if r["decision"] == "keep")
    flag_n = sum(1 for r in records if r["decision"] == "flag")
    avg_score = statistics.mean(r.get("score_total", 0) for r in records) if records else 0

    parts = [
        "# Sample Q&A keep+flag nuit 1 — Sprint 9-data 2026-04-29",
        "",
        "**Date génération doc** : 2026-04-29 (post-fix bug stop condition)",
        "**Source pipeline** : nuit 28-29/04, `data/golden_qa/golden_qa_v1.jsonl` (1020 jobs traités)",
        "**Filtre** : `decision in (keep, flag)`, soit **45 Q&A sur 1020** = 4.4% rendement utilisable",
        f"**Détail** : {keep_n} keep + {flag_n} flag, score moyen **{avg_score:.1f}/100**",
        "**Modèles** : research Haiku 4.5 + draft Opus 4.7 + critique-refine Opus 4.7 (stratégie hybride v3)",
        "**Bug nuit 1** : voir `docs/SPRINT9_DATA_VERDICT.md` §12 (root cause + fix appliqué commit 548834a)",
        "",
        "---",
        "",
        "## Stats globales",
        "",
        "| # | prompt_id | iter | category | score | décision | latence |",
        "|---|---|---|---|---|---|---|",
    ]

    for i, r in enumerate(records, 1):
        parts.append(
            f"| {i} | `{r['prompt_id']}` | {r['iteration']} | `{r['category']}` | "
            f"**{r.get('score_total', 0)}** | `{r['decision']}` | "
            f"{r.get('elapsed_s', 0)}s |"
        )

    parts.append("")
    parts.append("**Boundaries** : " + DECISION_BOUNDARIES)
    parts.append("")
    parts.append("---")
    parts.append("")

    # Sections par Q&A
    for i, r in enumerate(records, 1):
        n_seeds = n_seeds_per_prompt.get(r["prompt_id"], 6)  # fallback 6 (default YAML)
        parts.append(render_qa_section(r, i, n_seeds))
        parts.append("---")
        parts.append("")

    # Synthèse
    parts.append(build_synthese(records, n_seeds_per_prompt))

    parts.append("---")
    parts.append("")
    parts.append("*Doc généré par `scripts/extract_nuit1_samples_md.py` "
                 "sous l'ordre `2026-04-29-0656-claudette-orientia-validation-extract-nuit1`. "
                 "Format v3 référence : `docs/sprint9-data-dryrun-samples-2026-04-28.md` "
                 "(commit `6cc9492`).*")

    OUTPUT_PATH.write_text("\n".join(parts), encoding="utf-8")
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"==> Doc écrit : {OUTPUT_PATH} ({size_kb:.1f} KB, {len(parts)} blocs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
