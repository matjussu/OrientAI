"""Contrat de donnees anti-regression sur le corpus OrientAI.

But (Phase B, leger) : figer des invariants mesurables sur le corpus et BLOQUER
toute regression data (un rebuild qui ajouterait des villes vides, ferait
chuter la couverture region, ou casserait la separation structure/null).

Choix : pur Python, zero nouvelle dependance (vs Pandera/Great Expectations).
Aligne sur la consigne "garder B leger, pas un projet d'outillage". Si Matteo
veut le DSL Pandera, swap trivial - le contrat (les invariants) est ici.

Le contrat compare l'etat courant a la baseline data figee
(baseline/baseline_data_audit.json) et echoue (exit 1) si un invariant se
degrade au-dela de la tolerance.

Usage:
    PYTHONPATH=. python audit_empirique_2026-06-09/data_contract.py
    PYTHONPATH=. python audit_empirique_2026-06-09/data_contract.py --refresh-audit
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CUR_AUDIT = REPO / "audit_empirique_2026-06-09/results/data_audit.json"
BASE_AUDIT = HERE / "baseline" / "baseline_data_audit.json"

# Invariants du contrat. Chaque cle : (chemin dans l'audit, sens, tolerance).
# "no_increase" : la valeur ne doit pas augmenter (ex villes vides).
# "no_decrease" : la valeur ne doit pas diminuer (ex fiches eligible).
CONTRACT = [
    ("retrieval_eligible", "no_decrease", 0, "fiches retrieval-eligible"),
    (("ville_trap", "empty_string_count"), "no_increase", 0, "fiches ville=chaine vide"),
    (("region_coverage_eligible", "missing_pct"), "no_increase", 0.5, "% region manquante"),
    (("numeric_fields_pct_of_corpus", "taux_acces_parcoursup_2025"), "no_decrease", 0.5, "% taux_acces present"),
    (("insertion_block", "block_all_null"), "no_increase", 0, "blocs insertion tout-null"),
]

# Invariants ABSOLUS (independants de la baseline) - le design structurel.
def absolute_checks(audit: dict) -> list[str]:
    violations = []
    if audit.get("n_fiches", 0) < 1000:
        violations.append(f"corpus suspect : {audit.get('n_fiches')} fiches (<1000)")
    # separation structure/null : les champs chiffres doivent exister comme
    # champs types (pas du texte) - on verifie que le profil les compte.
    if "numeric_fields_nonnull" not in audit:
        violations.append("profil sans numeric_fields_nonnull (separation structure/null non verifiable)")
    return violations


def _get(d, path):
    if isinstance(path, str):
        return d.get(path)
    cur = d
    for p in path:
        cur = (cur or {}).get(p)
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-audit", action="store_true",
                    help="relance data_audit.py avant de valider")
    args = ap.parse_args()

    if args.refresh_audit or not CUR_AUDIT.exists():
        print("[contract] refresh data_audit.py ...")
        subprocess.run([sys.executable, str(HERE / "data_audit.py")],
                       cwd=str(REPO), env={**__import__("os").environ, "PYTHONPATH": str(REPO)},
                       check=True, stdout=subprocess.DEVNULL)

    cur = json.loads(CUR_AUDIT.read_text())
    base = json.loads(BASE_AUDIT.read_text())

    hard = []
    print("=== CONTRAT DE DONNEES (vs baseline data figee) ===")
    for path, rule, tol, label in CONTRACT:
        b, c = _get(base, path), _get(cur, path)
        if b is None or c is None:
            print(f"  ? {label}: champ absent (b={b} c={c})")
            continue
        if rule == "no_increase" and c > b + tol:
            hard.append(f"{label}: {b} -> {c} (hausse > {tol})")
            flag = "x"
        elif rule == "no_decrease" and c < b - tol:
            hard.append(f"{label}: {b} -> {c} (baisse > {tol})")
            flag = "x"
        else:
            flag = "ok"
        print(f"  [{flag}] {label}: baseline={b} courant={c}")

    for v in absolute_checks(cur):
        hard.append(v)
        print(f"  x ABSOLU: {v}")

    if hard:
        print("\nCONTRAT VIOLE :")
        for h in hard:
            print(f"  x {h}")
        print("\nDATA CONTRACT: FAIL")
        sys.exit(1)
    print("\nDATA CONTRACT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
