"""Étape B-2 de la donnée verticale : accès aux études de santé des fiches PASS et LAS.

Entrée : le corpus de l'étape B-1 (`data/processed/formations_etape_b1.json`), jamais réécrit.
Sortie : `data/processed/formations_etape_b2.json` et son manifeste.

Chaque fiche Parcoursup PASS ou LAS reçoit `sante` (`src.collect.sante`, contrat
`results/donnee_etape_b/CONTRACT.md` section 10). La fiche concept `reforme_sante_2027` est ajoutée
en fin de corpus. Les sources lues de B-1 reçoivent leurs nouveaux témoins (article L6211-1). Les
autres fiches sont recopiées à l'identique.

Usage :
    python -m src.collect.corpus_etape_b2 [--entree ...] [--sortie ...]
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

from src.collect import sante, sante_universites
from src.collect.sources_officielles import RACINE, charger_verrou
from src.collect.valeur_sourcee import SOURCES_LUES, Referentiel

ENTREE = RACINE / "data/processed/formations_etape_b1.json"
SORTIE = RACINE / "data/processed/formations_etape_b2.json"
SOUS_CHAMPS = ("passage_national", "passage_universite", "capacites_universite", "reforme_2027")


def universites_avec_pass(corpus: list[dict]) -> set[str]:
    return {
        sante.universite_de(f.get("etablissement") or "")
        for f in corpus if f.get("source") == "parcoursup" and f.get("fili_code") == "PASS"
    }


def temoins_sources_lues(fiche: dict) -> None:
    """Reporte sur les champs B-1 les témoins ajoutés depuis à une source lue (second témoin en
    ligne de l'article L6211-1, demandé par Jarvis le 23/09/2026), sans réécrire le corpus B-1."""
    for champ in ("cout", "alternance", "insertion"):
        valeur = fiche.get(champ)
        # Des fiches d'autres sources portent un `alternance` booléen hérité : pas une enveloppe.
        source = (valeur.get("source") or {}) if isinstance(valeur, dict) else {}
        lue = SOURCES_LUES.get(source.get("id"))
        if lue and lue.temoins and "temoins" not in source:
            source["temoins"] = [dict(t) for t in lue.temoins]


def construire(entree: list[dict], calcul: sante.CalculSante) -> list[dict]:
    sortie = []
    for fiche in entree:
        fiche = copy.deepcopy(fiche)
        temoins_sources_lues(fiche)
        if sante.CalculSante.concernee(fiche):
            fiche["sante"] = calcul.calculer(fiche)
        sortie.append(fiche)
    sortie.append(sante.fiche_reforme())
    return sortie


def remplissage(corpus: list[dict]) -> dict:
    """Par voie (PASS, LAS) et par sous-champ : `disponible`, `non_disponible`, absent."""
    compte: dict = defaultdict(lambda: defaultdict(Counter))
    for f in corpus:
        if not sante.CalculSante.concernee(f):
            continue
        voie = sante.VOIE[f["fili_code"]]
        for champ in SOUS_CHAMPS:
            v = (f.get("sante") or {}).get(champ)
            compte[voie][champ][v["statut"] if isinstance(v, dict) else "absent"] += 1
    return {voie: {c: dict(v) for c, v in champs.items()} for voie, champs in sorted(compte.items())}


def raisons(corpus: list[dict]) -> dict:
    compte: dict = defaultdict(Counter)
    for f in corpus:
        for champ in ("passage_universite", "capacites_universite"):
            v = (f.get("sante") or {}).get(champ)
            if isinstance(v, dict) and v["statut"] == "non_disponible":
                compte[champ][v["raison"]] += 1
    return {c: dict(v.most_common()) for c, v in compte.items()}


def par_universite(corpus: list[dict]) -> dict:
    compte: Counter = Counter()
    for f in corpus:
        cap = (f.get("sante") or {}).get("capacites_universite")
        if isinstance(cap, dict) and cap["statut"] == "disponible":
            compte[cap["valeur"]["universite"]] += 1
    return dict(compte.most_common())


def _sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Construit le corpus de l'étape B-2 (santé).")
    ap.add_argument("--entree", type=Path, default=ENTREE)
    ap.add_argument("--sortie", type=Path, default=SORTIE)
    args = ap.parse_args(argv)
    if args.sortie.resolve() == args.entree.resolve():
        ap.error("la sortie doit être distincte du corpus d'entrée")

    entree = json.loads(args.entree.read_text(encoding="utf-8"))
    calcul = sante.CalculSante(Referentiel(), sante_universites.RECHERCHES, universites_avec_pass(entree))
    corpus = construire(entree, calcul)

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    verrou = charger_verrou()
    manifeste = {
        "genere_le": dt.datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "commande": "python -m src.collect.corpus_etape_b2",
        "entree": {"chemin": str(args.entree), "sha256": _sha256(args.entree), "fiches": len(entree)},
        "sortie": {"chemin": str(args.sortie), "sha256": _sha256(args.sortie), "fiches": len(corpus)},
        "sources_sante": {k: v.get("sha256") for k, v in verrou.items() if k.startswith(("sies_", "univ_"))},
        "panel": list(sante.PANEL),
        "remplissage": remplissage(corpus),
        "fiches_avec_capacites_par_universite": par_universite(corpus),
        "raisons_non_disponible": raisons(corpus),
        "fiche_concept": sante.REFORME_ID,
    }
    args.sortie.with_suffix(".manifest.json").write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifeste, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
