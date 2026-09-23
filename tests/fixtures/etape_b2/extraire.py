"""Extrait des fiches RÉELLES du corpus B-1 et le texte de deux documents sources, pour les tests
de l'étape B-2 (aucune fiche ni ligne inventée).

Garde, par cas de rattachement, la première fiche PASS/LAS du corpus B-1 dont l'établissement
correspond ; et le texte `pdftotext -layout` du PDF SIES et du PDF de Lille (documents publics,
verrouillés), pour tester l'audit sans les bruts.

Rejouer (depuis la racine du dépôt, bruts présents et verrouillés) :
    python tests/fixtures/etape_b2/extraire.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RACINE))

from src.collect.sources_officielles import chemin_verifie  # noqa: E402

ICI = Path(__file__).parent
# cas -> (filière, motif dans l'établissement)
CAS = {
    "pass_lille": ("PASS", "Université de Lille"),
    "las_lille": ("Licence_Las", "Université de Lille"),
    "las_nanterre": ("Licence_Las", "Paris Nanterre"),
    "pass_grenoble": ("PASS", "Grenoble Alpes"),
    "pass_orsay": ("PASS", "Campus d'Orsay Université Paris-Saclay"),
    "pass_nimes": ("PASS", "Antenne de Nîmes"),
    "las_guyancourt": ("Licence_Las", "Campus de Guyancourt"),
    "pass_aubenas": ("PASS", "PASS Aubenas"),
    "las_agen": ("Licence_Las", "Antenne d'Agen"),
    "pass_toulouse": ("PASS", "Toulouse III"),
    "las_nantes": ("Licence_Las", "Nantes Université"),
}


def main() -> None:
    corpus = json.loads((RACINE / "data/processed/formations_etape_b1.json").read_text(encoding="utf-8"))
    fiches = {}
    for cas, (fili, motif) in CAS.items():
        fiches[cas] = next(f for f in corpus if f.get("source") == "parcoursup" and f.get("fili_code") == fili
                           and motif in (f.get("etablissement") or ""))
    (ICI / "fiches.json").write_text(json.dumps(fiches, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for source_id, nom in (("sies_nf_2025_31", "sies_nf31.txt"), ("univ_lille_mmopk_2026", "lille_2026.txt")):
        texte = subprocess.run(["pdftotext", "-layout", str(chemin_verifie(source_id)), "-"],
                               capture_output=True, check=True).stdout.decode("utf-8")
        (ICI / nom).write_text(texte, encoding="utf-8")


if __name__ == "__main__":
    main()
