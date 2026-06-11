"""Gate Option B (J2 U1) : SELECT bypass-vers-refus -> fall-through RAG gardé.

A/B temp=0 sur 48q SELECT-eligibles. Gate (Jarvis cond. 3) :
  honest_refusal en BAISSE ET hallucinated_numbers + metric_substitution NE
  montent PAS. Sinon -> revert le fall-through (pool filter conservé).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import compute_metrics

RES = Path(__file__).resolve().parent / "results"
BB, BA = RES / "ob_battery_before.json", RES / "ob_battery_after.json"
GB, GA = RES / "ob_ground_before.json", RES / "ob_ground_after.json"


def main():
    for p in (BB, BA, GB, GA):
        if not p.exists():
            raise SystemExit(f"manque {p}")
    mb = compute_metrics(str(BB), str(GB))
    ma = compute_metrics(str(BA), str(GA))

    print("=" * 68)
    print("GATE OPTION B — fall-through SELECT->RAG, A/B temp=0, 48q SELECT-eligibles")
    print("=" * 68)
    def line(k, label):
        print(f"  {label:32s} {mb[k]} -> {ma[k]}  ({ma[k]-mb[k]:+d})")
    line("n_honest_refusal", "honest_refusal")
    line("n_hallucinated_numbers", "hallucinated_numbers")
    line("n_metric_substitution", "metric_substitution")
    print(f"  {'answered_grounded':32s} "
          f"{mb['outcomes'].get('answered_grounded',0)} -> {ma['outcomes'].get('answered_grounded',0)}")
    print(f"  {'answered_unsupported':32s} "
          f"{mb['outcomes'].get('answered_unsupported',0)} -> {ma['outcomes'].get('answered_unsupported',0)}")
    print(f"  {'mean_groundedness':32s} {mb['mean_groundedness_asserting']} -> {ma['mean_groundedness_asserting']}")
    print(f"  outcomes before: {mb['outcomes']}")
    print(f"  outcomes after : {ma['outcomes']}")

    # tag fall-through (attribution)
    Ba = json.loads(BA.read_text())
    ft = sum(1 for r in Ba if r.get("select_fallthrough"))
    print(f"\n  réponses servies par fall-through RAG (AFTER) : {ft}/{len(Ba)}")

    # GATE
    refus_down = ma["n_honest_refusal"] < mb["n_honest_refusal"]
    hallu_ok = ma["n_hallucinated_numbers"] <= mb["n_hallucinated_numbers"]
    subst_ok = ma["n_metric_substitution"] <= mb["n_metric_substitution"]
    gate = refus_down and hallu_ok and subst_ok
    print("\n" + "=" * 68)
    print(f"  honest_refusal en baisse        : {'OK' if refus_down else 'NON'} "
          f"({mb['n_honest_refusal']}->{ma['n_honest_refusal']})")
    print(f"  hallucinated_numbers ne monte pas: {'OK' if hallu_ok else 'FAIL'} "
          f"({mb['n_hallucinated_numbers']}->{ma['n_hallucinated_numbers']})")
    print(f"  metric_substitution ne monte pas : {'OK' if subst_ok else 'FAIL'} "
          f"({mb['n_metric_substitution']}->{ma['n_metric_substitution']})")
    print(f"  GATE OPTION B : {'PASS' if gate else 'FAIL -> REVERT le fall-through'}")
    print("=" * 68)


if __name__ == "__main__":
    main()
