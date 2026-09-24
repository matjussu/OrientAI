"""Étape D : fiches exposées au modèle, gelées une fois pour les 9 combinaisons (protocole §3).

Par conversation du banc vertical : les fiches de ses chiffres attendus que A et B savent rendre,
complétées jusqu'à N_EXPOSEES par les premiers résultats BM25 sur le texte de ses tours, restreints aux
fiches rendables et hors fiches attendues ; ordre mélangé par une graine fixe. Les mêmes fiches sont
exposées à chaque tour de la conversation.

    python -m src.eval.exposition_d --base <base C> --sortie results/donnee_etape_d/exposition.json

Aucun appel payant : BM25 local (rank_bm25). Deux exécutions donnent le même fichier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from src.base_c.outils import Base
from src.eval.battery.corpus import Corpus
from src.eval.format_d import Formats

N_EXPOSEES = 8
GRAINE = 7
BANC = Path.home() / "projets/_orientai-ref/verticale-2026-09/battery_verticale.json"


def id_attendu(fiche: dict) -> list[str]:
    """Identifiants de base C possibles pour la fiche d'un chiffre attendu."""
    if fiche.get("cod_aff_form"):
        return [f"psup:{fiche['cod_aff_form']}", f"psup_app:{fiche['cod_aff_form']}"]
    if fiche.get("id"):
        return [f"mm:{fiche['id']}"]
    return []


def construire(banc: dict, formats: Formats) -> dict:
    rendables = [(id_, f) for id_, f in formats.corpus.items() if formats.rendable(id_)]
    ids_rendables = [id_ for id_, _ in rendables]
    index = Corpus(Path("rendables"), fiches=[f for _, f in rendables])
    conversations, hors_critere = {}, 0
    for item in banc["items"]:
        attendus, attendus_ids = [], []
        for c in item["attendus"]["chiffres"]:
            cible = next((i for i in id_attendu(c["fiche"]) if formats.rendable(i)), None)
            attendus.append(cible)
            hors_critere += cible is None
            if cible and cible not in attendus_ids:
                attendus_ids.append(cible)
        distracteurs = []
        for pos in index.search(" ".join(item["turns"]), k=50):
            if len(attendus_ids) + len(distracteurs) >= N_EXPOSEES:
                break
            if ids_rendables[pos] not in attendus_ids and ids_rendables[pos] not in distracteurs:
                distracteurs.append(ids_rendables[pos])
        exposees = attendus_ids + distracteurs
        random.Random(f"{GRAINE}:{item['id']}").shuffle(exposees)
        conversations[item["id"]] = {"exposees": exposees, "attendues": attendus_ids, "distracteurs": distracteurs,
                                     "cible_par_attendu": attendus}
    n_attendus = sum(len(i["attendus"]["chiffres"]) for i in banc["items"])
    return {"n_exposees": N_EXPOSEES, "graine": GRAINE, "n_rendables": len(ids_rendables),
            "n_attendus": n_attendus, "n_attendus_critere": n_attendus - hors_critere, "n_attendus_hors": hors_critere,
            "conversations": conversations}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=Path("data/processed/base_etape_c.sqlite"))
    ap.add_argument("--corpus", type=Path, default=Path("data/processed/formations_etape_b2.json"))
    ap.add_argument("--banc", type=Path, default=BANC)
    ap.add_argument("--sortie", type=Path, default=Path("results/donnee_etape_d/exposition.json"))
    args = ap.parse_args(argv)
    banc_octets = args.banc.read_bytes()
    corpus_octets = args.corpus.read_bytes()
    formats = Formats(Base.ouvrir(args.base), json.loads(corpus_octets))
    doc = construire(json.loads(banc_octets), formats)
    doc = {"banc_sha256": hashlib.sha256(banc_octets).hexdigest(),
           "corpus_sha256": hashlib.sha256(corpus_octets).hexdigest(),
           "base_sha256": hashlib.sha256(args.base.read_bytes()).hexdigest(), **doc}
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{args.sortie} : {len(doc['conversations'])} conversations, attendus {doc['n_attendus_critere']} dans le "
          f"critère + {doc['n_attendus_hors']} hors, {doc['n_rendables']} fiches rendables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
