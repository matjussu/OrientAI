"""Génère les fixtures des tests de l'étape A à partir des données RÉELLES (pas inventées).

- `fiches.json` : fiches Parcoursup réelles, avant (corpus de référence) et après (corpus de
  l'étape A), plus le texte que produisait le `fiche_to_text` de main sur la fiche d'avant ;
- `cog_extrait.csv` : lignes du COG INSEE 2025 nécessaires aux tests des communes ;
- `intitules_but.csv` : toutes les lignes BUT du jeu Parcoursup 2025 (fili, filière, intitulés),
  pour tester la table de domaines sur la population entière, pas sur des exemples choisis.

Usage :
    python scripts/donnee/generer_fixtures_etape_a.py --reference <formations.json> \\
        --etape-a data/processed/formations_etape_a.json --revision-avant 89e0f27
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

from src.collect.corpus_etape_a import _intitule_cartographie
from src.collect.sources_officielles import chemin_verifie
from src.eval.donnee.texte import charger_fiche_to_text

SORTIE = Path("tests/fixtures/etape_a")
# BUT Informatique, PASS option sciences infirmières (Lille), BUT GEII avec InserSup, fiche
# sans taux 2025, fiches parisiennes (arrondissement), LAS majeure maths, IFSI, CPGE MP2I,
# fiche marseillaise (arrondissement, académie Aix-Marseille), PASS à distance créé en A4.
CODES = ["7596", "36433", "2139", "22946", "9517", "39316", "23244", "36000", "2623", "29180"]
COMMUNES = {"Aubière", "Lille", "Saint-Étienne", "Schœlcher", "Vandœuvre-lès-Nancy", "Borgo", "Montluçon"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--etape-a", type=Path, required=True)
    ap.add_argument("--revision-avant", default="89e0f27")
    args = ap.parse_args()
    SORTIE.mkdir(parents=True, exist_ok=True)

    ref = {str(f["cod_aff_form"]): f for f in json.loads(args.reference.read_text()) if f.get("source") == "parcoursup"}
    apres = {f["cod_aff_form"]: f for f in json.loads(args.etape_a.read_text()) if f.get("source") == "parcoursup"}
    ancien = charger_fiche_to_text(args.revision_avant)
    fixtures = {
        "provenance": {
            "reference": str(args.reference), "etape_a": str(args.etape_a),
            "revision_texte_avant": args.revision_avant,
        },
        "apres": {c: apres[c] for c in CODES},
        "avant": {c: ref[c] for c in CODES if c in ref},
        "textes_avant": {c: ancien(ref[c]) for c in CODES if c in ref},
    }
    (SORTIE / "fiches.json").write_text(json.dumps(fixtures, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    cog = pd.read_csv(chemin_verifie("insee_cog_communes_2025"), dtype=str, keep_default_na=False)
    garde = cog[
        cog["LIBELLE"].isin(COMMUNES)
        | cog["COM"].isin({"75056", "69123", "13055", "75106", "69388", "13213"})
        | (cog["COMPARENT"] == "49092")  # communes déléguées d'une commune nouvelle (Chemillé-en-Anjou)
        | (cog["COM"] == "49092")
    ]
    garde.to_csv(SORTIE / "cog_extrait.csv", index=False, quoting=csv.QUOTE_ALL)

    officiel = pd.read_csv(chemin_verifie("parcoursup_2025"), sep=";", dtype=str, keep_default_na=False)
    carto = pd.read_csv(chemin_verifie("cartographie_parcoursup_2025"), sep=";", dtype=str)
    nm = {g: _intitule_cartographie(x) or "" for g, x in zip(carto["gta"], carto["nm"])}
    but = officiel[officiel["fili"] == "BUT"]
    pd.DataFrame({
        "cod_aff_form": but["cod_aff_form"], "fili": but["fili"], "filiere": but["form_lib_voe_acc"],
        "filiere_detaillee": but["fil_lib_voe_acc"], "intitule": but["lib_for_voe_ins"],
        "intitule_complet": [nm.get(c, "") for c in but["cod_aff_form"]], "detail": but["detail_forma"],
    }).to_csv(SORTIE / "intitules_but.csv", index=False, sep=";")
    print(f"fixtures écrites dans {SORTIE}")


if __name__ == "__main__":
    main()
