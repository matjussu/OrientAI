"""Diagnostic C2b — couverture POTENTIELLE du join salaire InserSup (v2).

Mesure (sans plomberie) combien de fiches recevraient un salaire RÉEL (valeur
source, zéro agrégation) via le join propre contre les lignes InserSup
établissement-diplôme du CSV local à salaire net médian non-null.

v2 — corrige l'artefact v1 (parcoursup type_diplome vide + sémantique entrée-bac
≠ sortie-diplôme). Le vrai join sémantique :
- MonMaster (masters, bac+5) -> InserSup par NOM d'établissement + type master
  (+ discipline). Les masters n'ont pas d'UAI mais le nom matche InserSup.
- Parcoursup supérieur avec UAI + type dérivé du nom (BUT/LP) -> InserSup par UAI.

Gate (arbitrage Jarvis) : >=500 -> implémenter ; <500 -> parker + constat.

Usage: PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/diag_insersup_salary_coverage.py
"""
from __future__ import annotations

import collections
import csv
import json
import re
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "data/raw/insersup.csv"
FICHES = REPO / "data/processed/formations.json"

COL_ETAB = "Établissement"
COL_UAI = "Code UAI de l'établissement"
COL_TYPE = "type_diplome"
COL_DISC = "Domaine disciplinaire"
COL_GENRE, COL_NAT, COL_REGIME, COL_OBT = "Genre", "Nationalité", "Régime d'inscription", "Obtention du diplôme"
COL_SAL12 = "12-Salaire mensuel net médian en équivalent temps plein - 12 mois après le diplôme"
COL_SAL30 = "30-Salaire mensuel net médian en équivalent temps plein - 30 mois après le diplôme"


def _norm(s) -> str:
    s = str(s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)


def _is_master(type_dip: str) -> bool:
    t = _norm(type_dip)
    return "master" in t


def _derive_type_from_nom(nom: str) -> str | None:
    n = _norm(nom)
    if "master" in n:
        return "master"
    if "bachelor universitaire de technologie" in n or re.search(r"\bbut\b", n):
        return "but"
    if "licence professionnelle" in n or "licence pro" in n:
        return "licence_pro"
    if "licence" in n:
        return "licence"
    if "ingenieur" in n:
        return "ingenieur"
    return None


def main():
    fiches = json.loads(FICHES.read_text())
    print(f"corpus: {len(fiches)} fiches")

    # 1. Parse CSV : lignes ensemble avec salaire non-null -> index par nom etab + par UAI
    by_name: dict[str, set[str]] = collections.defaultdict(set)   # nom_norm -> {type_norm avec salaire}
    by_uai: dict[str, set[str]] = collections.defaultdict(set)
    name_disc: dict[str, set[str]] = collections.defaultdict(set)  # nom_norm -> {disciplines}
    n_rows_sal = 0
    with open(CSV, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            if (row.get(COL_GENRE) != "ensemble" or row.get(COL_NAT) != "ensemble"
                    or row.get(COL_REGIME) != "ensemble" or row.get(COL_OBT) != "ensemble"):
                continue
            sal = (row.get(COL_SAL12) or row.get(COL_SAL30) or "").strip()
            if not sal or sal in ("ns", "nd", ".", "secret"):
                continue
            n_rows_sal += 1
            etab = _norm(row.get(COL_ETAB))
            uai = (row.get(COL_UAI) or "").strip().upper()
            tnorm = _norm(row.get(COL_TYPE))
            disc = _norm(row.get(COL_DISC))
            if etab:
                by_name[etab].add(tnorm)
                name_disc[etab].add(disc)
            if uai:
                by_uai[uai].add(tnorm)
    print(f"InserSup lignes ensemble avec salaire: {n_rows_sal}")
    print(f"  établissements distincts (nom) avec salaire: {len(by_name)}")
    print(f"  UAI distincts avec salaire: {len(by_uai)}")

    # 2a. MonMaster -> match par nom établissement + type master (+ discipline pour le compte précis)
    # index nom -> {disciplines AVEC un master à salaire}
    name_master_disc: dict[str, set[str]] = collections.defaultdict(set)
    with open(CSV, encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            if (row.get(COL_GENRE) != "ensemble" or row.get(COL_NAT) != "ensemble"
                    or row.get(COL_REGIME) != "ensemble" or row.get(COL_OBT) != "ensemble"):
                continue
            sal = (row.get(COL_SAL12) or row.get(COL_SAL30) or "").strip()
            if not sal or sal in ("ns", "nd", ".", "secret"):
                continue
            if "master" not in _norm(row.get(COL_TYPE)):
                continue
            name_master_disc[_norm(row.get(COL_ETAB))].add(_norm(row.get(COL_DISC)))

    mm = [f for f in fiches if isinstance(f, dict) and f.get("source") == "monmaster"]
    mm_match = [f for f in mm if any("master" in t for t in by_name.get(_norm(f.get("etablissement")), set()))]
    # compte précis discipline : la discipline de la fiche est présente dans les disciplines master à salaire de l'établissement
    mm_match_disc = [
        f for f in mm
        if _norm(f.get("discipline")) and _norm(f.get("discipline")) in name_master_disc.get(_norm(f.get("etablissement")), set())
    ]
    print(f"\nMonMaster: {len(mm)} fiches")
    print(f"  -> (étab x master) à salaire [borne haute]: {len(mm_match)}")
    print(f"  -> (étab x master x DISCIPLINE) à salaire [précis]: {len(mm_match_disc)}")

    # 2b. Parcoursup supérieur avec UAI + type dérivé du nom -> match UAI
    ps = [f for f in fiches if isinstance(f, dict) and f.get("source") == "parcoursup"
          and (f.get("cod_uai") or f.get("uai"))]
    ps_match = []
    for f in ps:
        uai = str(f.get("cod_uai") or f.get("uai") or "").strip().upper()
        dtype = _derive_type_from_nom(f.get("nom"))
        if not dtype:
            continue
        types_here = by_uai.get(uai, set())
        if any(dtype in t or (dtype == "licence" and "licence" in t) for t in types_here):
            ps_match.append(f)
    print(f"\nParcoursup avec UAI: {len(ps)} fiches")
    print(f"  -> UAI + type dérivé matché InserSup avec salaire: {len(ps_match)}")

    total = len(mm_match) + len(ps_match)
    total_precis = len(mm_match_disc) + len(ps_match)
    print(f"\n=== COUVERTURE POTENTIELLE (salaire source réel, zéro agrégation) ===")
    print(f"  BORNE HAUTE (étab/UAI x type)         : {total}  (MM {len(mm_match)} + PS {len(ps_match)})")
    print(f"  PRÉCIS (MM avec match discipline)     : {total_precis}  (MM {len(mm_match_disc)} + PS {len(ps_match)})")
    # breakdown MonMaster par discipline matchable
    print(f"\n  MonMaster matchés — aperçu disciplines (top 10):")
    dd = collections.Counter(_norm(f.get("discipline")) for f in mm_match)
    for d, c in dd.most_common(10):
        print(f"    {c:4d}  {d[:50]}")

    print(f"\n=== VERDICT GATE (compte précis) : {total_precis} fiches "
          f"{'>= 500 -> IMPLÉMENTER' if total_precis >= 500 else '< 500 -> PARKER'} ===")


if __name__ == "__main__":
    main()
