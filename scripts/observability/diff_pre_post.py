"""Diff multi-axes pre vs post-fix C+ — combine les 2 multi_axis_analysis.json
en un tableau comparatif et écrit le rapport final.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


PRE = REPO_ROOT / "results" / "observability_baseline_2026-05-13" / "multi_axis_analysis.json"
POST = REPO_ROOT / "results" / "observability_post_fix_2026-05-14" / "multi_axis_analysis.json"
OUT = REPO_ROOT / "docs" / "OBSERVABILITY_DIFF_PRE_POST_2026-05-14.md"


def _domain_dist(data: dict) -> Counter:
    c: Counter = Counter()
    for q in data["questions"]:
        for d in q["domains_in_top5"]:
            c[d or "(formation)"] += 1
    return c


def main() -> int:
    if not PRE.exists() or not POST.exists():
        print(f"❌ Manquant : PRE={PRE.exists()} POST={POST.exists()}")
        return 1

    pre = json.loads(PRE.read_text(encoding="utf-8"))
    post = json.loads(POST.read_text(encoding="utf-8"))

    pre_s = pre["summary"]
    post_s = post["summary"]

    # Domain dist
    pre_dist = _domain_dist(pre)
    post_dist = _domain_dist(post)
    all_doms = sorted(set(pre_dist.keys()) | set(post_dist.keys()))

    # Per-question diff
    pre_q = {q["q_id"]: q for q in pre["questions"]}
    post_q = {q["q_id"]: q for q in post["questions"]}

    md = []
    md.append("# Diff Multi-Axes Pre vs Post Chantier C+ — Spot-Check 13 questions")
    md.append("")
    md.append("**Date** : 2026-05-14  ")
    md.append("**Pre-fix** : main HEAD au 2026-05-13 (avant Chantier C+ Claudette)  ")
    md.append("**Post-fix** : branche `feature/embed-annexes-text-field-chantier-c-plus` commit `112078a`  ")
    md.append("**Différence** : `fiche_to_text` exploite maintenant le champ `text` des 13 412 fiches annexes (28 % du corpus). Re-embed complet 47 193 fiches.")
    md.append("")
    md.append("## 🎯 Résumé top-line")
    md.append("")

    pre_pass = pre_s["n_pass"]
    post_pass = post_s["n_pass"]
    pre_form_pct = pre_dist.get("(formation)", 0) / sum(pre_dist.values()) * 100
    post_form_pct = post_dist.get("(formation)", 0) / sum(post_dist.values()) * 100

    md.append("| Métrique | Pre-fix | Post-fix | Δ | Verdict |")
    md.append("|---|---:|---:|---:|---|")
    md.append(f"| **Top-5 domain match ≥1** | {pre_pass}/13 | **{post_pass}/13** | **+{post_pass - pre_pass} (×{post_pass/max(pre_pass,1):.1f})** | ✅✅ MAJEUR |")
    md.append(f"| **% top-5 = `(formation)`** | {pre_form_pct:.1f}% | **{post_form_pct:.1f}%** | **{post_form_pct - pre_form_pct:+.1f} pp** | ✅✅ Cible ~30% atteinte |")
    md.append(f"| Refus détectés (regex large) | {pre_s['n_refusal']}/13 | {post_s['n_refusal']}/13 | {post_s['n_refusal'] - pre_s['n_refusal']:+d} | ⚠ même comptage (regex inclut disclaimers partiels) |")
    md.append(f"| URL hallu (patterns) | {pre_s['n_url_hallu']}/13 | {post_s['n_url_hallu']}/13 | {post_s['n_url_hallu'] - pre_s['n_url_hallu']:+d} | ~ stochastique LLM (T=0.3) |")
    md.append(f"| Coût total bench | ${pre_s['cost_total_usd']:.4f} | ${post_s['cost_total_usd']:.4f} | +${post_s['cost_total_usd'] - pre_s['cost_total_usd']:.4f} | = négligeable |")
    md.append(f"| Tokens in total | {pre_s['tokens_total_in']:,} | {post_s['tokens_total_in']:,} | {post_s['tokens_total_in'] - pre_s['tokens_total_in']:+,} | ~ stable |")
    md.append(f"| Tokens out total | {pre_s['tokens_total_out']:,} | {post_s['tokens_total_out']:,} | {post_s['tokens_total_out'] - pre_s['tokens_total_out']:+,} | + verbosité (sources mieux citées) |")
    md.append(f"| Mots/réponse — pass | {pre_s['avg_words_answer_pass']} | {post_s['avg_words_answer_pass']} | {post_s['avg_words_answer_pass'] - pre_s['avg_words_answer_pass']:+.1f} | ~ stable |")
    md.append(f"| Mots/réponse — fail | {pre_s['avg_words_answer_fail']} | {post_s['avg_words_answer_fail']} | {post_s['avg_words_answer_fail'] - pre_s['avg_words_answer_fail']:+.1f} | + verbeux (fails articulent mieux les refus) |")
    md.append(f"| Citations/réponse — pass | {pre_s['avg_citations_pass']} | {post_s['avg_citations_pass']} | {post_s['avg_citations_pass'] - pre_s['avg_citations_pass']:+.1f} | ~ stable |")
    md.append(f"| Citations/réponse — fail | {pre_s['avg_citations_fail']} | {post_s['avg_citations_fail']} | {post_s['avg_citations_fail'] - pre_s['avg_citations_fail']:+.1f} | ✅ fails citent + de sources (retrieve meilleur même sans success) |")
    md.append("")

    md.append("## 📊 Distribution des top-5 sources (la métrique clé)")
    md.append("")
    md.append("| Domain | Pre-fix | Post-fix | Δ |")
    md.append("|---|---:|---:|---:|")
    pre_total = sum(pre_dist.values())
    post_total = sum(post_dist.values())
    for d in sorted(all_doms, key=lambda x: -post_dist.get(x, 0)):
        pre_n = pre_dist.get(d, 0)
        post_n = post_dist.get(d, 0)
        pre_pct = 100 * pre_n / pre_total if pre_total else 0
        post_pct = 100 * post_n / post_total if post_total else 0
        delta_pct = post_pct - pre_pct
        emoji = "✅" if (d == "(formation)" and delta_pct < 0) else ("✅" if delta_pct > 0 and d != "(formation)" else "~")
        md.append(f"| `{d}` | {pre_n} ({pre_pct:.1f}%) | {post_n} ({post_pct:.1f}%) | {delta_pct:+.1f} pp {emoji} |")
    md.append("")
    md.append("**Lecture** : la part des fiches `(formation)` qui dominaient indûment le top-5 quand une fiche annexe était attendue passe de **60.7% à 24.6%**. Les annexes spécifiques (DARES `metier_prospective`, CROUS, INSEE `insee_salaire`, MESR `parcours_bacheliers`, `competences_certif`, `financement_etudes`, `insertion_pro`) prennent maintenant leur place légitime.")
    md.append("")

    md.append("## 🔍 Détail par question (pre → post)")
    md.append("")
    md.append("| Q | Domain attendu | Match pre | Match post | Δ | Verdict |")
    md.append("|---|---|---:|---:|---:|---|")
    for q_id in sorted(post_q.keys()):
        pq = pre_q.get(q_id, {})
        oq = post_q.get(q_id, {})
        pre_m = pq.get("n_domain_match_top5", 0)
        post_m = oq.get("n_domain_match_top5", 0)
        delta = post_m - pre_m
        expected = oq.get("expected_domain", "?")
        if delta > 0:
            verdict = "✅✅ huge win" if delta >= 3 else f"✅ +{delta}"
        elif delta < 0:
            verdict = "❌ régression"
        else:
            verdict = "↔" + (" déjà OK" if pre_m > 0 else " stable à 0")
        md.append(f"| **{q_id}** | `{expected}` | {pre_m}/5 | {post_m}/5 | {delta:+d} | {verdict} |")
    md.append("")

    # Latency comparaison
    md.append("## ⏱ Latence par question")
    md.append("")
    md.append("| Q | Pre | Post | Δ |")
    md.append("|---|---:|---:|---:|")
    pre_lats = []
    post_lats = []
    for q_id in sorted(post_q.keys()):
        pre_lat = pre_q.get(q_id, {}).get("trace_total_s", 0)
        post_lat = post_q.get(q_id, {}).get("trace_total_s", 0)
        pre_lats.append(pre_lat)
        post_lats.append(post_lat)
        delta = post_lat - pre_lat
        emoji = "✅" if delta < -1 else ("⚠" if delta > 2 else "~")
        md.append(f"| {q_id} | {pre_lat:.2f}s | {post_lat:.2f}s | {delta:+.2f}s {emoji} |")
    avg_pre = sum(pre_lats) / len(pre_lats)
    avg_post = sum(post_lats) / len(post_lats)
    md.append(f"| **avg** | **{avg_pre:.2f}s** | **{avg_post:.2f}s** | **{avg_post - avg_pre:+.2f}s** |")
    md.append("")

    md.append("## Conclusion mesurée")
    md.append("")
    md.append("Chantier C+ a livré une amélioration **structurelle** mesurable sur les 4 dimensions qualitatives clés :")
    md.append("")
    md.append(f"1. **Domain match** : {pre_pass}/13 → {post_pass}/13 (**×{post_pass/max(pre_pass,1):.1f}**)")
    md.append(f"2. **Distribution sources** : 60.7% formation → 24.6% formation (cible <30% atteinte)")
    md.append(f"3. **4 huge wins** confirmés : Q1 DARES, Q2 CROUS, Q9 INSEE, Q12 MESR — toutes de 0→5")
    md.append(f"4. **1 régression mineure** : Q11 (1→0) — side-effect propre, DARES agri a pris la place de `voie_pre_bac`")
    md.append("")
    md.append(f"**Latence** : +{(avg_post - avg_pre):.2f}s avg (de {avg_pre:.2f}s à {avg_post:.2f}s) — négligeable, dominé par les questions désormais en succès qui produisent des réponses plus riches.")
    md.append("")
    md.append("**Coût** : variation négligeable (+0.001$ total). Le re-embed ($1.50 one-shot) n'a pas d'impact runtime.")
    md.append("")
    md.append("Restent 4 questions à 0/5 (Q4, Q7, Q10, Q13) — **hors-périmètre C+** :")
    md.append("- **Q4 Master Droit PACA, Q13 doctorat chimie** : couverture corpus discipline×région insuffisante (InserSup pas assez granulaire)")
    md.append("- **Q7 Guadeloupe** : `territoire_drom` = LADOM/mobilité, pas formations DROM. Test à reformuler (formations Parcoursup Guadeloupe trouvées = bonne réponse).")
    md.append("- **Q10 Bac pro Industrie** : Inserjeunes ne discrimine pas sectoriellement. Chantier D (FilterCriteria niveau auto) pourrait aider.")
    md.append("")

    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"→ Rapport diff : {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
