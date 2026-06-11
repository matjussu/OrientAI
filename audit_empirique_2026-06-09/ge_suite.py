"""Suite Great Expectations sur le corpus OrientAI (B-complet).

Vraie suite de validation data (GE 1.x). Aplatit le corpus en DataFrame et
applique deux tiers d'attentes :
- HARD (bloquantes) : invariants qui doivent tenir MAINTENANT (types, bornes,
  source non nulle). Une violation = exit 1 (regression data).
- TARGET (dette data, non bloquantes) : la cible que Phase A3 doit atteindre
  (ville non vide, region presente). Actuellement violees -> rapportees comme
  dette mesuree, pas un echec de gate.

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/ge_suite.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import great_expectations as gx
from great_expectations import expectations as gxe

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"
OUT = REPO / "audit_empirique_2026-06-09/results/ge_validation.json"

KNOWN_SOURCES = {
    "parcoursup", "monmaster", "rncp", "rncp_blocs", "onisep", "inserjeunes_cfa",
    "labonnealternance", "inserjeunes_lycee_pro", "rome_api_v4", "dares_metiers_2030",
    "onisep_ideo_fiches", "onisep_metiers", "insersup_mesr", "ip_doc_doctorat",
    "mesri_parcours_bacheliers_licence", "insee_salaan_2023",
    "crous_combine_logements_restos", "financement_dispositifs_curated",
    "onisep_formations_extended", "domtom_curated", "apec_observatoire_emploi_cadre_2026",
    "parcoursup_calendrier_officiel", "monmaster_calendrier_officiel",
    "dse_calendrier_officiel", "corrections_factuelles_curated",
}


def build_df() -> pd.DataFrame:
    fiches = json.loads(FICHES.read_text())
    rows = []
    for f in fiches:
        if not isinstance(f, dict):
            continue
        ville = f.get("ville")
        rows.append({
            "source": f.get("source"),
            "retrieval_eligible": bool(f.get("retrieval_eligible")),
            "nom": f.get("nom"),
            "ville_nonempty": isinstance(ville, str) and ville.strip() != "",
            "region_present": bool(f.get("region")),
            "taux_acces": f.get("taux_acces_parcoursup_2025"),
            "is_parcoursup": f.get("source") == "parcoursup",
        })
    return pd.DataFrame(rows)


def main():
    df = build_df()
    batch = (gx.get_context()
             .data_sources.add_pandas("corpus")
             .add_dataframe_asset("fiches")
             .add_batch_definition_whole_dataframe("batch")
             .get_batch(batch_parameters={"dataframe": df}))

    # (expectation, tier) - tier "hard" bloquant, "target" dette mesuree
    checks = [
        (gxe.ExpectColumnValuesToNotBeNull(column="source"), "hard"),
        (gxe.ExpectColumnValuesToBeInSet(column="source", value_set=sorted(KNOWN_SOURCES)), "hard"),
        (gxe.ExpectColumnValuesToBeInSet(column="retrieval_eligible", value_set=[True, False]), "hard"),
        (gxe.ExpectColumnValuesToBeBetween(column="taux_acces", min_value=0, max_value=100), "hard"),
        (gxe.ExpectColumnValuesToBeInSet(column="ville_nonempty", value_set=[True], mostly=0.95), "target"),
        (gxe.ExpectColumnValuesToBeInSet(column="region_present", value_set=[True], mostly=0.90), "target"),
    ]

    results = []
    hard_fail = 0
    print(f"=== GE SUITE corpus ({len(df)} fiches) ===")
    for exp, tier in checks:
        res = batch.validate(exp)
        ok = bool(res.success)
        meta = res.result or {}
        pct = meta.get("unexpected_percent")
        line = {"expectation": type(exp).__name__, "column": getattr(exp, "column", None),
                "tier": tier, "success": ok, "unexpected_percent": pct}
        results.append(line)
        flag = "ok " if ok else ("XX " if tier == "hard" else "~~ ")
        extra = f" (unexpected {pct:.1f}%)" if isinstance(pct, (int, float)) else ""
        print(f"  [{flag}] {tier:<6} {type(exp).__name__}({getattr(exp,'column','')}){extra}")
        if tier == "hard" and not ok:
            hard_fail += 1

    OUT.write_text(json.dumps({"n_fiches": len(df), "results": results,
                               "hard_failures": hard_fail}, ensure_ascii=False, indent=2))
    print(f"\nHARD failures: {hard_fail} | TARGET (dette A3) violations attendues sur ville/region")
    if hard_fail:
        print("GE SUITE: FAIL (regression data dure)")
        sys.exit(1)
    print("GE SUITE: PASS (invariants durs OK ; cibles A3 documentees)")
    sys.exit(0)


if __name__ == "__main__":
    main()
