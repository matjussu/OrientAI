"""A3 - Enrichissement/hygiene data (NON destructif : ecrit un nouveau fichier).

Findings empiriques (mesures, pas supposes) :
1. "Deriver region depuis ville" est INEFFICACE : seulement ~17 fiches ont une
   ville connue mais une region manquante. Les fiches sans region n'ont
   majoritairement PAS de ville non plus (RNCP/ONISEP nationaux). Le trou region
   est STRUCTUREL, pas derivable depuis ville. On applique quand meme les 17.
2. Le vrai gain hygiene : purger les 18012 villes = chaine vide -> null, pour
   supprimer le piege "present mais vide" qui fait echouer silencieusement les
   filtres geo. Sans impact embedding (le texte embedde est deja "Ville : " vide).

Ecrit data/processed/formations_enriched_a3.json (NOUVEAU). Le swap en prod +
le re-embed eventuel (region est dans le texte embedde) restent soumis a la
validation de Matteo. On mesure le delta via data_contract/GE sur le nouveau
fichier.

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/enrich_data_a3.py
"""
from __future__ import annotations

import json
import collections
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data/processed/formations.json"
OUT = REPO / "data/processed/formations_enriched_a3.json"


def ne(v):
    return isinstance(v, str) and v.strip() != ""


def main():
    fiches = json.loads(SRC.read_text())
    # map ville->region depuis les fiches qui ont les deux
    vr = collections.defaultdict(collections.Counter)
    for f in fiches:
        if ne(f.get("ville")) and ne(f.get("region")):
            vr[f["ville"].strip().upper()][f["region"]] += 1
    ville_to_region = {v: c.most_common(1)[0][0] for v, c in vr.items()}

    purged_ville = 0
    filled_region = 0
    for f in fiches:
        # purge ville vide -> None (supprime le piege present-but-empty)
        if "ville" in f and not ne(f.get("ville")):
            f["ville"] = None
            purged_ville += 1
        # derive region depuis ville quand possible (gain reel : ~17)
        if ne(f.get("ville")) and not ne(f.get("region")):
            r = ville_to_region.get(f["ville"].strip().upper())
            if r:
                f["region"] = r
                f["_region_derived"] = True
                filled_region += 1

    OUT.write_text(json.dumps(fiches, ensure_ascii=False))
    # mesure delta
    empty_after = sum(1 for f in fiches if "ville" in f and not ne(f.get("ville")) and f.get("ville") is not None)
    region_present = sum(1 for f in fiches if ne(f.get("region")))
    print(f"=== A3 enrichissement (-> {OUT.name}) ===")
    print(f"villes vides purgees (\"\" -> null) : {purged_ville}")
    print(f"regions derivees depuis ville      : {filled_region} (gain structurellement faible, documente)")
    print(f"empty ville string restants        : {empty_after} (cible 0)")
    print(f"region presente apres              : {region_present}/{len(fiches)} ({round(100*region_present/len(fiches),1)}%)")
    print("NB : swap prod + re-embed (region embedde) = decision Matteo.")


if __name__ == "__main__":
    main()
