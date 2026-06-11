"""Analyse avant/apres garde-fou, par subset disjoint (voie C2a / salaire).

- metriques via compute_metrics() (source de verite) restreintes a chaque subset
- volet (b) : compteur brut/net deterministe (salary_qualifier_check)
- gate par subset (def Jarvis 2026-06-11) :
    voie C2a : honest_refusal NE remonte PAS
    salaire  : metric_substitution en baisse nette ET answered_grounded ne baisse
               pas ; remontee honest_refusal OK ssi elle remplace des substitutions
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import compute_metrics
from salary_qualifier_check import check_salary_qualifier

DIR = Path(__file__).resolve().parent
RES = DIR / "results"
SUB = json.loads((DIR / "subset_gardefou.json").read_text())
VOIE_IDS = {q["id"] for q in SUB["items"] if q.get("_subset") == "voie_c2a"}
SAL_IDS = {q["id"] for q in SUB["items"] if q.get("_subset") == "salaire"}

BB, BA = RES / "gf_battery_before.json", RES / "gf_battery_after.json"
GB, GA = RES / "gf_ground_before.json", RES / "gf_ground_after.json"


def subset_metrics(battery, ground, ids):
    B = [r for r in json.loads(Path(battery).read_text()) if r["id"] in ids]
    J = [r for r in json.loads(Path(ground).read_text()) if r["id"] in ids]
    tb, tj = RES / "_t_b.json", RES / "_t_j.json"
    tb.write_text(json.dumps(B)); tj.write_text(json.dumps(J))
    m = compute_metrics(str(tb), str(tj)); tb.unlink(); tj.unlink()
    return m


def brutnet(battery, ids):
    B = {r["id"]: r for r in json.loads(Path(battery).read_text()) if r["id"] in ids}
    total, per = 0, {}
    for qid, r in B.items():
        v = check_salary_qualifier(r.get("answer", ""), r.get("sources"))
        if v:
            per[qid] = v; total += len(v)
    return total, per


def outcomes_by_id(ground, ids):
    J = json.loads(Path(ground).read_text())
    return {r["id"]: (r.get("judgment") or {}).get("outcome", "?") for r in J if r["id"] in ids}


def show(title, mb, ma):
    print(f"\n### {title}")
    def d(k): return f"{ma[k]-mb[k]:+d}"
    print(f"  answered_grounded     : {mb['outcomes'].get('answered_grounded',0)} -> {ma['outcomes'].get('answered_grounded',0)}")
    print(f"  answered_unsupported  : {mb['outcomes'].get('answered_unsupported',0)} -> {ma['outcomes'].get('answered_unsupported',0)}")
    print(f"  metric_substitution   : {mb['n_metric_substitution']} -> {ma['n_metric_substitution']}  ({d('n_metric_substitution')})")
    print(f"  honest_refusal        : {mb['n_honest_refusal']} -> {ma['n_honest_refusal']}  ({d('n_honest_refusal')})")
    print(f"  hallucinated_numbers  : {mb['n_hallucinated_numbers']} -> {ma['n_hallucinated_numbers']}  ({d('n_hallucinated_numbers')})")
    print(f"  mean_groundedness     : {mb['mean_groundedness_asserting']} -> {ma['mean_groundedness_asserting']}")
    print(f"  outcomes before: {mb['outcomes']}")
    print(f"  outcomes after : {ma['outcomes']}")


def main():
    for p in (BB, BA, GB, GA):
        if not p.exists():
            raise SystemExit(f"manque {p}")

    print("=" * 70)
    print("DELTA GARDE-FOU (avant/apres), instrument _FICHE_KEEP fixe constant")
    print("=" * 70)

    # --- SUBSET VOIE C2a (16q) : gate honest_refusal ne remonte pas ---
    mvb = subset_metrics(BB, GB, VOIE_IDS)
    mva = subset_metrics(BA, GA, VOIE_IDS)
    show("VOIE C2a 16q (garde-fou RÈGLE 7 anti-elaboration reconversion)", mvb, mva)
    ob, oa = outcomes_by_id(GB, VOIE_IDS), outcomes_by_id(GA, VOIE_IDS)
    print("  changements d'outcome :")
    for qid in sorted(VOIE_IDS):
        if ob.get(qid) != oa.get(qid):
            print(f"    {qid:16s} {ob.get(qid)} -> {oa.get(qid)}")
    voie_gate = mva['n_honest_refusal'] <= mvb['n_honest_refusal']
    print(f"  GATE voie (honest_refusal ne remonte pas) : {'PASS' if voie_gate else 'FAIL'} "
          f"({mvb['n_honest_refusal']} -> {mva['n_honest_refusal']})")

    # --- SUBSET SALAIRE (60q) : gate substitution down + answered_grounded ne baisse pas ---
    msb = subset_metrics(BB, GB, SAL_IDS)
    msa = subset_metrics(BA, GA, SAL_IDS)
    show("SALAIRE 60q (garde-fou RÈGLE 6 substitution + brut/net)", msb, msa)
    bnb, bnb_per = brutnet(BB, SAL_IDS)
    bna, bna_per = brutnet(BA, SAL_IDS)
    print(f"  volet (b) brut/net deterministe (checker) : {bnb} -> {bna} violations  ({bna-bnb:+d})")
    if bnb_per:
        print(f"    before violations : {list(bnb_per.keys())}")
    if bna_per:
        print(f"    after  violations : {list(bna_per.keys())}")
    osb, osa = outcomes_by_id(GB, SAL_IDS), outcomes_by_id(GA, SAL_IDS)
    print("  changements d'outcome (salaire) :")
    for qid in sorted(SAL_IDS):
        if osb.get(qid) != osa.get(qid):
            print(f"    {qid:16s} {osb.get(qid)} -> {osa.get(qid)}")
    sub_down = msa['n_metric_substitution'] < msb['n_metric_substitution']
    grounded_ok = msa['outcomes'].get('answered_grounded', 0) >= msb['outcomes'].get('answered_grounded', 0)
    sal_gate = sub_down and grounded_ok
    print(f"  GATE salaire (substitution down ET answered_grounded ne baisse pas) : "
          f"{'PASS' if sal_gate else 'FAIL'} "
          f"[subst {msb['n_metric_substitution']}->{msa['n_metric_substitution']}, "
          f"grounded {msb['outcomes'].get('answered_grounded',0)}->{msa['outcomes'].get('answered_grounded',0)}]")

    print("\n" + "=" * 70)
    print(f"GATE GLOBAL : voie={'PASS' if voie_gate else 'FAIL'} | salaire={'PASS' if sal_gate else 'FAIL'} | "
          f"brut/net {bnb}->{bna}")
    print("=" * 70)


if __name__ == "__main__":
    main()
