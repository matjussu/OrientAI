"""Étape B-1 de la donnée verticale : compléter les fiches Parcoursup (coût, alternance, insertion).

Entrée : le corpus de l'étape A (`data/processed/formations_etape_a.json`), jamais réécrit.
Sortie : `data/processed/formations_etape_b1.json` et son manifeste.

Pour chaque fiche Parcoursup (`source == "parcoursup"`), trois champs à l'enveloppe commune
(`src.collect.valeur_sourcee`, contrat `results/donnee_etape_b/CONTRACT.md`) :
- `cout` (`src.collect.couts`) ;
- `alternance` (`src.collect.alternance`) ;
- `insertion` (`src.collect.insertion`).
Puis les fiches `parcoursup_apprentissage` des domaines de la démo, placées en fin de corpus,
avec leurs propres `cout` et `insertion`. Les fiches des autres sources sont recopiées à l'identique.

Usage :
    python -m src.collect.corpus_etape_b [--entree data/processed/formations_etape_a.json]
                                         [--sortie data/processed/formations_etape_b1.json]
"""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

from src.collect.alternance import Alternance
from src.collect.communes import ReferentielCommunes
from src.collect.couts import CalculCout
from src.collect.domaines import charger_table
from src.collect.insertion import CalculInsertion
from src.collect.sources_officielles import RACINE, charger_verrou, chemin_verifie
from src.collect.valeur_sourcee import Referentiel

ENTREE = RACINE / "data/processed/formations_etape_a.json"
SORTIE = RACINE / "data/processed/formations_etape_b1.json"
CHAMPS = ("cout", "alternance", "insertion")
SOURCES_FICHES = ("parcoursup", "parcoursup_apprentissage")


def lire_csv(chemin: Path) -> list[dict]:
    with chemin.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


class ConstructeurEtapeB1:
    def __init__(self, cout: CalculCout, alternance: Alternance, insertion: CalculInsertion, regles: list) -> None:
        self.cout = cout
        self.alternance = alternance
        self.insertion = insertion
        self.regles = regles

    @classmethod
    def depuis_sources(cls) -> ConstructeurEtapeB1:
        ref = Referentiel()
        communes = ReferentielCommunes(chemin_verifie("insee_cog_communes_2025"), chemin_verifie("insee_cog_comer_2025"))
        paysage = {
            ligne["gta"]: ligne["etablissement_id_paysage"]
            for ligne in lire_csv(chemin_verifie("cartographie_parcoursup_2025"))
            if ligne.get("etablissement_id_paysage")
        }
        return cls(
            cout=CalculCout(lire_csv(chemin_verifie("onisep_ideo_actions_es")), ref),
            alternance=Alternance(lire_csv(chemin_verifie("parcoursup_apprentissage_2025")), communes, ref),
            insertion=CalculInsertion(
                lire_csv(chemin_verifie("insersup")), lire_csv(chemin_verifie("inserjeunes_bts")), paysage, ref
            ),
            regles=charger_table(),
        )

    def construire(self, entree: list[dict]) -> list[dict]:
        sortie = []
        for fiche in entree:
            fiche = copy.deepcopy(fiche)
            if fiche.get("source") == "parcoursup":
                fiche["cout"] = self.cout.calculer(fiche)
                fiche["alternance"] = self.alternance.rattacher(fiche)
                fiche["insertion"] = self.insertion.calculer(fiche)
            sortie.append(fiche)
        for fiche in self.alternance.fiches(self.regles):
            fiche["cout"] = self.cout.ref.non_disponible(
                "le coût d'une formation en apprentissage n'est pas publié dans les jeux ouverts "
                "utilisés (le jeu Onisep Idéo-Actions exclut l'apprentissage)"
            )
            fiche["insertion"] = self.insertion.calculer(fiche)
            sortie.append(fiche)
        return sortie


def remplissage(corpus: list[dict], domaines: dict[str, list[str]] | None = None) -> dict:
    """Par source et par champ : fiches `disponible`, `non_disponible`, absentes. Avec `domaines`
    (cod_aff_form -> domaines), la même chose par domaine de la démo."""
    compte: dict = defaultdict(lambda: defaultdict(Counter))
    for fiche in corpus:
        if fiche.get("source") not in SOURCES_FICHES:
            continue
        groupes = [fiche["source"]]
        if domaines is not None:
            groupes = [f"{fiche['source']}:{d}" for d in domaines.get(str(fiche.get("cod_aff_form")), [])]
        for groupe in groupes:
            for champ in CHAMPS:
                valeur = fiche.get(champ)
                compte[groupe][champ][valeur["statut"] if isinstance(valeur, dict) else "absent"] += 1
    return {g: {c: dict(v) for c, v in champs.items()} for g, champs in sorted(compte.items())}


def rattachements(corpus: list[dict]) -> dict:
    compte: dict = defaultdict(Counter)
    for fiche in corpus:
        for champ in CHAMPS:
            valeur = fiche.get(champ)
            if isinstance(valeur, dict):
                compte[champ][f"{valeur['statut']}:{valeur.get('rattachement')}"] += 1
    return {c: dict(v.most_common()) for c, v in compte.items()}


def _sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Construit le corpus de l'étape B-1 (donnée verticale).")
    ap.add_argument("--entree", type=Path, default=ENTREE)
    ap.add_argument("--sortie", type=Path, default=SORTIE)
    args = ap.parse_args(argv)
    if args.sortie.resolve() == args.entree.resolve():
        ap.error("la sortie doit être distincte du corpus d'entrée")

    entree = json.loads(args.entree.read_text(encoding="utf-8"))
    corpus = ConstructeurEtapeB1.depuis_sources().construire(entree)

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    manifeste = {
        "genere_le": dt.datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "commande": "python -m src.collect.corpus_etape_b",
        "entree": {"chemin": str(args.entree), "sha256": _sha256(args.entree), "fiches": len(entree)},
        "sortie": {"chemin": str(args.sortie), "sha256": _sha256(args.sortie), "fiches": len(corpus)},
        "sources": {k: v.get("sha256") for k, v in charger_verrou().items()},
        "fiches_apprentissage": sum(1 for f in corpus if f.get("source") == "parcoursup_apprentissage"),
        "remplissage": remplissage(corpus),
        "rattachements": rattachements(corpus),
    }
    args.sortie.with_suffix(".manifest.json").write_text(
        json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifeste, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
