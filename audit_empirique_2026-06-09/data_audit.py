"""Audit data empirique du corpus OrientAI - mesure sur les DONNEES REELLES.

Profile data/processed/formations.json (le corpus servi en prod, cf
server.py ORIENTIA_FICHES_PATH). Aucune confiance a la doc : on compte tout.

Mesure : volume, distribution des sources, couverture region/voie/niveau,
taux de null sur les champs chiffres (le coeur du refus honnete), fraicheur,
separation structure/texte, couverture DOM-TOM et agricole, pieges
(chaines vides comptees comme presentes).

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/data_audit.py
"""
from __future__ import annotations

import json
import collections
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"
OUT = REPO / "audit_empirique_2026-06-09/results/data_audit.json"

DOMTOM = {"Guadeloupe", "Martinique", "Guyane", "La Réunion", "Mayotte",
          "Saint-Pierre-et-Miquelon", "Nouvelle-Calédonie", "Polynésie française",
          "Wallis-et-Futuna", "Saint-Martin", "Saint-Barthélemy"}


def nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def deep_get(f, *path):
    cur = f
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def main():
    fiches = json.loads(FICHES.read_text())
    n = len(fiches)
    rep: dict = {"n_fiches": n, "file": str(FICHES)}

    # 1. retrieval-eligible
    eligible = [f for f in fiches if isinstance(f, dict) and f.get("retrieval_eligible")]
    rep["retrieval_eligible"] = len(eligible)

    # 2. source distribution
    src = collections.Counter(f.get("source", "?") for f in fiches if isinstance(f, dict))
    rep["sources"] = dict(src.most_common())

    # 3. region coverage (sur eligible)
    region_present = sum(1 for f in eligible if nonempty(f.get("region")))
    rep["region_coverage_eligible"] = {
        "present": region_present, "total": len(eligible),
        "pct": round(100 * region_present / max(1, len(eligible)), 1),
        "missing_pct": round(100 * (len(eligible) - region_present) / max(1, len(eligible)), 1),
    }
    rep["region_distribution"] = dict(collections.Counter(
        (f.get("region") or "(vide)") for f in eligible).most_common(25))

    # 4. ville : piege chaine vide
    ville_key_present = sum(1 for f in fiches if isinstance(f, dict) and "ville" in f)
    ville_nonempty = sum(1 for f in fiches if isinstance(f, dict) and nonempty(f.get("ville")))
    rep["ville_trap"] = {
        "key_present": ville_key_present, "nonempty": ville_nonempty,
        "empty_string_count": ville_key_present - ville_nonempty,
    }

    # 5. niveau / type_diplome / statut coverage
    for field in ("niveau", "type_diplome", "statut", "domaine", "nom", "etablissement"):
        c = sum(1 for f in fiches if isinstance(f, dict) and nonempty(f.get(field)))
        rep.setdefault("field_coverage", {})[field] = {
            "present": c, "pct": round(100 * c / n, 1)}

    # 6. champs chiffres : present ET non-null (le coeur du refus honnete)
    # taux_acces_parcoursup_2025 (top-level), insertion taux_emploi_6m,
    # nombre_places, salaire (cherche plusieurs cles plausibles)
    def count_numeric(getter):
        present = 0  # cle existe
        nonnull = 0  # valeur non-null
        for f in fiches:
            if not isinstance(f, dict):
                continue
            v = getter(f)
            if v is not None:
                nonnull += 1
        return nonnull

    rep["numeric_fields_nonnull"] = {
        "taux_acces_parcoursup_2025": count_numeric(lambda f: f.get("taux_acces_parcoursup_2025")),
        "nombre_places": count_numeric(lambda f: f.get("nombre_places")),
        "insertion.taux_emploi_6m": count_numeric(lambda f: deep_get(f, "insertion_pro", "taux_emploi_6m")),
        "insertion.part_emploi_6m": count_numeric(lambda f: deep_get(f, "insertion_pro", "part_emploi_6m")),
        "insertion.part_poursuite_etudes": count_numeric(lambda f: deep_get(f, "insertion_pro", "part_poursuite_etudes")),
    }
    rep["numeric_fields_pct_of_corpus"] = {
        k: round(100 * v / n, 1) for k, v in rep["numeric_fields_nonnull"].items()
    }

    # 7. insertion_pro : combien de fiches ont le bloc mais avec TOUT a null
    ins_block = [f for f in fiches if isinstance(f, dict) and isinstance(f.get("insertion_pro"), dict)]
    ins_allnull = 0
    for f in ins_block:
        b = f["insertion_pro"]
        vals = [v for k, v in b.items() if k not in ("source", "annee")]
        if all(v is None for v in vals):
            ins_allnull += 1
    rep["insertion_block"] = {
        "fiches_with_block": len(ins_block),
        "block_all_null": ins_allnull,
        "block_all_null_pct_of_block": round(100 * ins_allnull / max(1, len(ins_block)), 1),
    }

    # 8. fraicheur : annee / collected_at
    annee = collections.Counter(str(f.get("annee")) for f in fiches
                                if isinstance(f, dict) and nonempty(f.get("annee")))
    rep["annee_distribution_top"] = dict(annee.most_common(15))

    # 9. DOM-TOM coverage
    domtom = sum(1 for f in eligible if (f.get("region") in DOMTOM))
    rep["domtom_eligible"] = domtom

    # 10. agricole coverage (heuristique nom/source/diplome)
    def is_agri(f):
        blob = " ".join(str(f.get(k, "")) for k in ("nom", "source", "type_diplome", "domaine")).lower()
        return any(t in blob for t in ("btsa", "agricol", "agronom", "parcoursupagri", "lycee agricole"))
    rep["agricole_count"] = sum(1 for f in fiches if isinstance(f, dict) and is_agri(f))

    # 11. structured vs text : presence du champ free-text `text` et `debouches`
    rep["text_fields"] = {
        "has_text_field": sum(1 for f in fiches if isinstance(f, dict) and nonempty(f.get("text"))),
        "has_debouches": sum(1 for f in fiches if isinstance(f, dict) and nonempty(f.get("debouches"))),
    }

    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=2))
    # print summary
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
