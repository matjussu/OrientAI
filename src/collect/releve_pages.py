"""Relevé complet des pages publiques de toutes les formations de la base C (contrat results/concordance/CONTRAT.md §6).

    python -m src.collect.releve_pages [--espaces psup,psup_app,mm] [--limite N]

Séquentiel, une requête par 1,5 s au plus, reprise sur cache (`data/raw/pages_publiques/`, hors git). Arrêts :
- ARRET_ERREURS requêtes en échec d'affilée (panne, blocage) ;
- ARRET_VIDES pages Parcoursup lues sans aucun chiffre d'affilée (la page a changé de structure).
Le manifeste versionné (`results/concordance/manifeste_releve.json`) porte l'empreinte du cache.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time

from src.collect.pages_publiques import Releve, lire_mm, lire_psup, page_psup, reponse_mm
from src.collect.sources_officielles import RACINE

CACHE = RACINE / "data/raw/pages_publiques"
BASE = RACINE / "data/processed/base_etape_c.sqlite"
MANIFESTE = RACINE / "results/concordance/manifeste_releve.json"
ARRET_ERREURS = 10
ARRET_VIDES = 20


def cibles(espaces: set[str]) -> list[tuple[str, str, str]]:
    """(espace, id, clé de requête) de toutes les formations des espaces demandés, dans un ordre stable."""
    db = sqlite3.connect(f"file:{BASE}?mode=ro", uri=True)
    out = []
    for esp, id_, ident, uai in db.execute(
            "SELECT espace, id, identifiant_source, uai FROM formation ORDER BY espace, id"):
        if esp not in espaces:
            continue
        out.append((esp, id_, ident if esp != "mm" else f"{uai}|{ident}"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--espaces", default="psup,psup_app,mm")
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args(argv)
    r = Releve(CACHE)
    todo = cibles(set(a.espaces.split(",")))
    if a.limite:
        todo = todo[:a.limite]
    erreurs_suite = vides_suite = 0
    bilan = {"formations": len(todo), "lues": 0, "echecs": 0, "vides": 0, "masters_sans_fiche": 0}
    vus_mm: dict[tuple[str, str], list | None] = {}
    t0 = time.time()
    for k, (esp, id_, cle) in enumerate(todo, 1):
        if esp == "mm":
            uai, ifc = cle.split("|")
            if (uai, ifc[:8]) not in vus_mm:
                vus_mm[(uai, ifc[:8])] = reponse_mm(r, uai, ifc[:8])
            contenu = vus_mm[(uai, ifc[:8])]
            ok = contenu is not None
            lu = lire_mm(contenu, ifc) if ok else None
            bilan["masters_sans_fiche"] += ok and lu is None
        else:
            corps = page_psup(r, cle)
            ok = corps is not None
            lu = lire_psup(corps.decode("utf-8", errors="replace")) if ok else None
            vide = ok and not lu
            bilan["vides"] += vide
            vides_suite = vides_suite + 1 if vide else 0
        bilan["lues" if ok else "echecs"] += 1
        erreurs_suite = 0 if ok else erreurs_suite + 1
        if k % 100 == 0 or not ok:
            print(f"{k}/{len(todo)} {esp} {id_} {'ok' if ok else 'ECHEC'} {time.time() - t0:.0f}s {bilan}", flush=True)
        if erreurs_suite >= ARRET_ERREURS or vides_suite >= ARRET_VIDES:
            bilan["arret"] = f"{erreurs_suite} échecs ou {vides_suite} pages vides d'affilée à {id_}"
            break
    bilan |= {"empreinte_cache": r.empreinte(), "fichiers": len(r.manifeste), "secondes": round(time.time() - t0)}
    MANIFESTE.parent.mkdir(parents=True, exist_ok=True)
    MANIFESTE.write_text(json.dumps({"bilan": bilan, "manifeste": r.manifeste}, ensure_ascii=False, indent=0,
                                    sort_keys=True) + "\n")
    print(json.dumps(bilan, ensure_ascii=False), flush=True)
    return 1 if "arret" in bilan else 0


if __name__ == "__main__":
    sys.exit(main())
