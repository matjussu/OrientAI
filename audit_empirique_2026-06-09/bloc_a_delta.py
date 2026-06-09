"""Bloc A — analyse AVANT/APRÈS par question (au-delà du gate agrégé).

Liste les bascules d'outcome (surtout honest_refusal -> answered_grounded = la
correction de faux-refus visée), et flague toute régression (grounded -> autre).
Lecture seule sur les artefacts déjà produits.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"


def load_outcomes(ground_path):
    out = {}
    for r in json.loads(Path(ground_path).read_text()):
        out[r["id"]] = {
            "outcome": (r.get("judgment") or {}).get("outcome"),
            "ground": (r.get("judgment") or {}).get("groundedness"),
            "cat": r.get("category"),
        }
    return out


av = load_outcomes(RES / "bloc_a_groundedness_avant.json")
ap = load_outcomes(RES / "bloc_a_groundedness_apres.json")

flips = []
for qid in sorted(set(av) & set(ap)):
    a, b = av[qid], ap[qid]
    if a["outcome"] != b["outcome"]:
        flips.append((qid, a["cat"], a["outcome"], b["outcome"]))

WIN = {"honest_refusal", "off_topic", "answered_unsupported"}
wins = [f for f in flips if f[2] in WIN and f[3] == "answered_grounded"]
regr = [f for f in flips if f[2] == "answered_grounded" and f[3] != "answered_grounded"]
refus_to_ans = [f for f in flips if f[2] == "honest_refusal" and f[3] != "honest_refusal"]

print(f"Bascules d'outcome AVANT->APRÈS : {len(flips)}")
print(f"  refus -> répond (toutes)      : {len(refus_to_ans)}")
print(f"  -> answered_grounded (gains)  : {len(wins)}")
print(f"  grounded -> autre (régress.)  : {len(regr)}")

print("\n--- GAINS (refus/unsupported -> grounded) ---")
for qid, cat, o1, o2 in wins:
    print(f"  {qid} [{cat}] {o1} -> {o2}")
print("\n--- RÉGRESSIONS (grounded -> autre) ---")
for qid, cat, o1, o2 in regr:
    print(f"  {qid} [{cat}] {o1} -> {o2}")
print("\n--- AUTRES BASCULES ---")
for qid, cat, o1, o2 in flips:
    if (qid, cat, o1, o2) not in wins and (qid, cat, o1, o2) not in regr:
        print(f"  {qid} [{cat}] {o1} -> {o2}")
