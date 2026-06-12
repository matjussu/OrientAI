"""Canary juge groundedness (Phase 0, ordre 2026-06-12-0825).

But : avant le re-embed full qui re-gèle la baseline, vérifier que le juge
groundedness ACTUEL (claude-haiku-4-5-20251001) score les réponses FIGÉES du gel
de la MÊME façon qu'au moment du gel (2026-06-11). Motivation : Haiku a drifté
hier sur test_judge_faithfulness (FIDELE vs INFIDELE). Si le juge a bougé, la
baseline 0.949 figée n'est plus comparable à une mesure post-re-embed.

Méthode :
  - on NE régénère PAS les réponses : on relit gel_battery.json (réponses+sources
    strictement identiques au gel) et on les re-juge avec judge_groundedness.py.
  - on compare verdict par verdict aux scores stockés (gel_ground.json).
  - PASS = >=95% verdicts identiques (outcome). FAIL = drift confirmé -> order-blocked.

Échantillon : 30 questions in_scope (LLM-jugées), STRATIFIÉES par outcome stocké,
sélection DÉTERMINISTE (tri par id), avec inclusion FORCÉE des 10 cas
hallucinated_numbers (démo-critiques : détection de chiffres fabriqués).

Usage :
  # 1. sélection (écrit canary_input.json au format battery + canary_expected.json)
  PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/canary_2026-06-12/canary.py select
  # 2. re-jugement (juge Haiku actuel sur réponses figées)
  PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/judge_groundedness.py \
      --in  audit_empirique_2026-06-09/canary_2026-06-12/canary_input.json \
      --out audit_empirique_2026-06-09/canary_2026-06-12/canary_ground.json
  # 3. comparaison + verdict
  PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/canary_2026-06-12/canary.py compare
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
GEL_BATTERY = RESULTS / "gel_battery.json"
GEL_GROUND = RESULTS / "gel_ground.json"
CANARY_INPUT = HERE / "canary_input.json"
CANARY_EXPECTED = HERE / "canary_expected.json"
CANARY_GROUND = HERE / "canary_ground.json"
CANARY_REPORT = HERE / "canary_report.md"

# Cibles par bucket d'outcome stocké (total 30). On sur-échantillonne les buckets
# discriminants (unsupported, metric_substitution) où un drift se verrait.
TARGETS = {
    "answered_grounded": 8,
    "answered_alternative_disclaimed": 8,
    "answered_unsupported": 6,
    "metric_substitution": 4,
    "honest_refusal": 4,
}
PASS_THRESHOLD = 0.95


def _load(p: Path):
    return json.loads(p.read_text())


def select():
    battery = {r["id"]: r for r in _load(GEL_BATTERY)}
    ground = _load(GEL_GROUND)
    # in_scope = jugés par LLM (les court-circuits urgent/oos/greeting sont triviaux)
    llm = [r for r in ground if r.get("scope") == "in_scope"]

    # inclusion forcée : tous les cas hallucinated_numbers (démo-critiques)
    forced = [r["id"] for r in llm if r["judgment"].get("hallucinated_numbers")]
    forced_set = set(forced)

    by_outcome: dict[str, list[str]] = {}
    for r in sorted(llm, key=lambda x: x["id"]):  # tri déterministe
        by_outcome.setdefault(r["judgment"].get("outcome"), []).append(r["id"])

    chosen: list[str] = list(forced)  # garde l'ordre, dédup plus bas
    for outcome, target in TARGETS.items():
        ids = by_outcome.get(outcome, [])
        already = sum(1 for i in chosen if i in ids)
        for i in ids:
            if len([c for c in chosen if c in ids]) >= target:
                break
            if i not in chosen:
                chosen.append(i)
    # dédup en conservant l'ordre
    seen = set()
    chosen = [i for i in chosen if not (i in seen or seen.add(i))]

    # écrit l'input au format battery (réponses+sources FIGÉES, inchangées)
    input_records = [battery[i] for i in chosen]
    CANARY_INPUT.write_text(json.dumps(input_records, ensure_ascii=False, indent=2))
    # écrit les verdicts attendus (extraits du gel) pour la comparaison
    expected = [r for r in ground if r["id"] in set(chosen)]
    CANARY_EXPECTED.write_text(json.dumps(expected, ensure_ascii=False, indent=2))

    from collections import Counter
    dist = Counter(r["judgment"].get("outcome") for r in expected)
    print(f"[select] {len(chosen)} questions figées -> {CANARY_INPUT.name}")
    print(f"[select] dont {len(forced_set)} cas hallucinated_numbers inclus de force")
    print("[select] distribution outcome (stocké) :")
    for o, c in dist.most_common():
        print(f"           {o}: {c}")


def _benign_relabel(exp: dict, got: dict) -> bool:
    """Relabel bénin = grounded <-> alternative_disclaimed avec groundedness
    identique (1.0). Les deux sont FIDELES (g=1.0), c'est du bruit de bucketing,
    pas un drift de fidélité. Tout le reste est substantiel."""
    pair = {exp.get("outcome"), got.get("outcome")}
    if pair == {"answered_grounded", "answered_alternative_disclaimed"}:
        return exp.get("groundedness") == got.get("groundedness")
    return False


def compare():
    expected = {r["id"]: r["judgment"] for r in _load(CANARY_EXPECTED)}
    got = {r["id"]: r["judgment"] for r in _load(CANARY_GROUND)}
    ids = [r["id"] for r in _load(CANARY_INPUT)]

    rows = []
    n_outcome_match = 0
    n_ground_match = 0
    n_hallu_match = 0
    n_benign = 0
    substantive = []
    abs_deltas = []

    for i in ids:
        e, g = expected[i], got.get(i, {})
        eo, go = e.get("outcome"), g.get("outcome")
        eg, gg = e.get("groundedness"), g.get("groundedness")
        eh, gh = bool(e.get("hallucinated_numbers")), bool(g.get("hallucinated_numbers"))
        outcome_ok = eo == go
        ground_ok = eg == gg
        hallu_ok = eh == gh
        n_outcome_match += outcome_ok
        n_ground_match += ground_ok
        n_hallu_match += hallu_ok
        if eg is not None and gg is not None:
            abs_deltas.append(abs(eg - gg))
        benign = (not outcome_ok) and _benign_relabel(e, g)
        if benign:
            n_benign += 1
        # substantiel = drift de fidélité : groundedness bouge, hallu flip,
        # ou relabel non-bénin (ex: grounded -> unsupported)
        is_substantive = (not ground_ok) or (not hallu_ok) or (
            (not outcome_ok) and not benign)
        if is_substantive:
            substantive.append((i, eo, go, eg, gg, eh, gh))
        rows.append((i, eo, go, eg, gg, eh, gh, outcome_ok, ground_ok, hallu_ok, benign))

    n = len(ids)
    outcome_rate = n_outcome_match / n
    ground_rate = n_ground_match / n
    hallu_rate = n_hallu_match / n
    mean_abs_delta = sum(abs_deltas) / len(abs_deltas) if abs_deltas else 0.0

    gate_pass = outcome_rate >= PASS_THRESHOLD
    # verdict substantiel : aucun drift de fidélité (groundedness/hallu stables)
    no_substantive_drift = len(substantive) == 0

    lines = []
    lines.append(f"# Canary juge groundedness — {n} réponses figées du gel\n")
    lines.append(f"Re-jugement avec le juge ACTUEL (claude-haiku-4-5-20251001) "
                 f"des réponses+sources STRICTEMENT identiques au gel 2026-06-11.\n")
    lines.append("## Accords verdict par verdict\n")
    lines.append(f"- **outcome identique : {n_outcome_match}/{n} = {outcome_rate:.1%}** "
                 f"(seuil PASS {PASS_THRESHOLD:.0%})")
    lines.append(f"- groundedness identique (exact) : {n_ground_match}/{n} = {ground_rate:.1%}")
    lines.append(f"- hallucinated_numbers flag identique : {n_hallu_match}/{n} = {hallu_rate:.1%}")
    lines.append(f"- |Δ groundedness| moyen (cas chiffrés) : {mean_abs_delta:.4f}")
    lines.append(f"- relabels bénins (grounded<->alt_disclaimed à g=1.0) : {n_benign}")
    lines.append(f"- mismatches SUBSTANTIELS (fidélité) : {len(substantive)}\n")

    lines.append("## Verdict\n")
    if gate_pass and no_substantive_drift:
        verdict = "PASS"
        lines.append(f"**{verdict}** — outcome {outcome_rate:.1%} >= {PASS_THRESHOLD:.0%} "
                     f"ET zéro drift de fidélité. Le juge est stable, baseline comparable. "
                     f"GO pour les phases de mesure.")
    elif gate_pass and not no_substantive_drift:
        verdict = "PASS-AVEC-RESERVE"
        lines.append(f"**{verdict}** — outcome {outcome_rate:.1%} >= seuil MAIS "
                     f"{len(substantive)} mismatch(es) substantiel(s) sur l'axe fidélité. "
                     f"À arbitrer : noise isolé ou début de drift ? Voir détail ci-dessous.")
    elif (not gate_pass) and no_substantive_drift:
        verdict = "BORDERLINE"
        lines.append(f"**{verdict}** — outcome {outcome_rate:.1%} < {PASS_THRESHOLD:.0%} MAIS "
                     f"les mismatches sont des relabels bénins (g inchangé), pas un drift de "
                     f"fidélité. Probablement du bruit de bucketing temp=0, pas Haiku qui drifte. "
                     f"Recommandation : ne PAS bloquer mécaniquement, attribuer chaque flip.")
    else:
        verdict = "FAIL"
        lines.append(f"**{verdict}** — outcome {outcome_rate:.1%} < {PASS_THRESHOLD:.0%} "
                     f"ET {len(substantive)} drift(s) de fidélité. Drift Haiku confirmé. "
                     f"STOP : order-blocked, re-ancrer la baseline avant toute mesure.")

    if substantive:
        lines.append("\n## Mismatches substantiels (détail)\n")
        lines.append("| id | outcome stocké | outcome re-jugé | g stocké | g re-jugé | hallu stocké | hallu re-jugé |")
        lines.append("|---|---|---|---|---|---|---|")
        for i, eo, go, eg, gg, eh, gh in substantive:
            lines.append(f"| {i} | {eo} | {go} | {eg} | {gg} | {eh} | {gh} |")

    report = "\n".join(lines) + "\n"
    CANARY_REPORT.write_text(report)
    print(report)
    print(f"[compare] rapport écrit -> {CANARY_REPORT}")
    # code retour exploitable : 0 si stable, 2 si drift substantiel
    return 0 if (gate_pass and no_substantive_drift) else (1 if verdict in ("PASS-AVEC-RESERVE", "BORDERLINE") else 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["select", "compare"])
    args = ap.parse_args()
    if args.mode == "select":
        select()
    else:
        raise SystemExit(compare())


if __name__ == "__main__":
    main()
