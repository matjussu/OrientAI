"""Analyse du delta C2a (avant/après) sur le sous-ensemble reconversion.

Lit les 4 artefacts (battery+ground, before+after), calcule les métriques via
la source de vérité compute_metrics(), et décompose :
  - 28q complets (contexte, avec note plafond : 12q de financement = C2b)
  - 16q "voie d'accès" (effet ATTRIBUABLE de C2a : VAE, formation continue,
    alternance) -> c'est là que se lit le verdict.
Plus le détail par question (quelles réponses passent de refus -> sourcé).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import compute_metrics

DIR = Path(__file__).resolve().parent
RES = DIR / "results"
SUBSET = json.loads((DIR / "subset_C2a_reconversion.json").read_text())
VOIE_IDS = {q["id"] for q in SUBSET["items"] if q.get("_c2a_voie_dacces")}
ALL_IDS = {q["id"] for q in SUBSET["items"]}


def subset_metrics(battery_path, ground_path, keep_ids):
    """compute_metrics restreint à un sous-ensemble d'ids (filtre les fichiers)."""
    B = [r for r in json.loads(Path(battery_path).read_text()) if r["id"] in keep_ids]
    J = [r for r in json.loads(Path(ground_path).read_text()) if r["id"] in keep_ids]
    tb, tj = RES / "_tmp_b.json", RES / "_tmp_j.json"
    tb.write_text(json.dumps(B)); tj.write_text(json.dumps(J))
    m = compute_metrics(str(tb), str(tj))
    tb.unlink(); tj.unlink()
    return m


def outcomes_by_id(ground_path, keep_ids):
    J = json.loads(Path(ground_path).read_text())
    return {r["id"]: (r.get("judgment") or {}).get("outcome", "?")
            for r in J if r["id"] in keep_ids}


def show(title, mb, ma):
    print(f"\n### {title}")
    print(f"  questions notées (asserting)   : {mb['n_gradeable_asserting']} -> {ma['n_gradeable_asserting']}")
    print(f"  honest_refusal                 : {mb['n_honest_refusal']} -> {ma['n_honest_refusal']}  ({ma['n_honest_refusal']-mb['n_honest_refusal']:+d})")
    print(f"  answered_grounded              : {mb['outcomes'].get('answered_grounded',0)} -> {ma['outcomes'].get('answered_grounded',0)}")
    print(f"  answered_unsupported (hallu)   : {mb['outcomes'].get('answered_unsupported',0)} -> {ma['outcomes'].get('answered_unsupported',0)}")
    print(f"  metric_substitution            : {mb['n_metric_substitution']} -> {ma['n_metric_substitution']}  ({ma['n_metric_substitution']-mb['n_metric_substitution']:+d})")
    print(f"  n_hallucinated_numbers         : {mb['n_hallucinated_numbers']} -> {ma['n_hallucinated_numbers']}  ({ma['n_hallucinated_numbers']-mb['n_hallucinated_numbers']:+d})")
    gb, ga = mb['mean_groundedness_asserting'], ma['mean_groundedness_asserting']
    print(f"  mean_groundedness (asserting)  : {gb} -> {ga}")
    print(f"  outcomes before: {mb['outcomes']}")
    print(f"  outcomes after : {ma['outcomes']}")


def main():
    bb, ba = RES / "c2a_battery_before.json", RES / "c2a_battery_after.json"
    gb, ga = RES / "c2a_ground_before.json", RES / "c2a_ground_after.json"
    for p in (bb, ba, gb, ga):
        if not p.exists():
            raise SystemExit(f"manque {p}")

    print("=" * 64)
    print("DELTA C2a — voies_acces -> dispositifs_reconversion")
    print("=" * 64)

    # 16q voie d'accès = effet attribuable (LE verdict)
    show("SOUS-ENSEMBLE VOIE D'ACCÈS (16q) — effet attribuable C2a",
         subset_metrics(bb, gb, VOIE_IDS), subset_metrics(ba, ga, VOIE_IDS))

    # 28q complets = contexte, avec note plafond
    show("28q COMPLETS (contexte) — plafond ~16, les 12q financement = C2b",
         subset_metrics(bb, gb, ALL_IDS), subset_metrics(ba, ga, ALL_IDS))

    # détail par question sur le sous-ensemble voie : qui change d'outcome
    ob = outcomes_by_id(gb, VOIE_IDS)
    oa = outcomes_by_id(ga, VOIE_IDS)
    print("\n### CHANGEMENTS D'OUTCOME (sous-ensemble voie 16q)")
    changed = 0
    for qid in sorted(VOIE_IDS):
        if ob.get(qid) != oa.get(qid):
            changed += 1
            print(f"  {qid:16s} : {ob.get(qid)} -> {oa.get(qid)}")
    if not changed:
        print("  (aucun changement d'outcome)")


if __name__ == "__main__":
    main()
