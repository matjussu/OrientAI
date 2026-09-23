"""Jeux de données officiels bruts de l'étape A : téléchargement et empreintes.

Les fichiers bruts vivent dans `data/raw/` (hors git, trop lourds). Leur identité est
figée dans un verrou commité, `data/reference/sources_officielles.json` : URL, date de
téléchargement, sha256, taille et nombre de lignes. Le pipeline refuse de tourner sur un
fichier dont l'empreinte ne correspond plus au verrou : une mise à jour de la source est
une décision explicite (`--mettre-a-jour`), jamais un effet de bord.

Usage :
    python -m src.collect.sources_officielles                 # vérifie les fichiers présents
    python -m src.collect.sources_officielles --telecharger   # télécharge les manquants
    python -m src.collect.sources_officielles --mettre-a-jour # réécrit le verrou
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parents[2]
VERROU = RACINE / "data/reference/sources_officielles.json"

_ESR = "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets"
_DEPP = "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets"
_INSEE = "https://www.insee.fr/fr/statistiques/fichier/8377162"
_ONISEP = "https://api.opendata.onisep.fr/downloads"

# InserSup : 1 036 781 lignes au 29/07/2026, toutes les ventilations croisées. On ne garde que la
# ligne « ensemble » (genre, nationalité, régime) des diplômés des deux dernières promotions : ce
# sont les seuls chiffres que le texte cite. Le filtre fait partie de l'URL, donc du verrou.
_INSERSUP_FILTRE = (
    'genre%3D%22ensemble%22%20and%20nationalite%3D%22ensemble%22%20and%20'
    'regime_inscription%3D%22ensemble%22%20and%20obtention_diplome%3D%22dipl%C3%B4m%C3%A9%22%20and%20'
    '(promo%3D%222024%22%20or%20promo%3D%222023%22)'
)


@dataclass(frozen=True)
class Source:
    nom: str
    chemin: str
    url: str
    producteur: str
    licence: str


SOURCES: dict[str, Source] = {
    s.nom: s
    for s in (
        Source(
            "parcoursup_2025", "data/raw/parcoursup_2025.csv",
            f"{_ESR}/fr-esr-parcoursup/exports/csv?delimiter=%3B",
            "MESR (SIES), jeu fr-esr-parcoursup, session 2025", "Licence Ouverte v2.0",
        ),
        Source(
            "parcoursup_2024", "data/raw/parcoursup_2024.csv",
            f"{_ESR}/fr-esr-parcoursup_2024/exports/csv?delimiter=%3B",
            "MESR (SIES), jeu fr-esr-parcoursup_2024, session 2024", "Licence Ouverte v2.0",
        ),
        Source(
            "parcoursup_2023", "data/raw/parcoursup_2023.csv",
            f"{_ESR}/fr-esr-parcoursup_2023/exports/csv?delimiter=%3B",
            "MESR (SIES), jeu fr-esr-parcoursup_2023, session 2023", "Licence Ouverte v2.0",
        ),
        Source(
            "cartographie_parcoursup_2025", "data/raw/cartographie_parcoursup_2025.csv",
            f"{_ESR}/fr-esr-cartographie_formations_parcoursup/exports/csv"
            "?delimiter=%3B&where=annee%3D%222025%22",
            "MESR (SIES), jeu fr-esr-cartographie_formations_parcoursup, année 2025",
            "Licence Ouverte v2.0",
        ),
        Source(
            "insee_cog_communes_2025", "data/raw/insee_cog/v_commune_2025.csv",
            f"{_INSEE}/v_commune_2025.csv",
            "INSEE, Code officiel géographique 2025, communes", "Licence Ouverte v2.0",
        ),
        Source(
            "insee_cog_comer_2025", "data/raw/insee_cog/v_commune_comer_2025.csv",
            f"{_INSEE}/v_commune_comer_2025.csv",
            "INSEE, Code officiel géographique 2025, collectivités d'outre-mer",
            "Licence Ouverte v2.0",
        ),
        # ── étape B-1 ────────────────────────────────────────────────────────────────
        Source(
            "onisep_ideo_actions_es", "data/raw/onisep/ideo_actions_es.csv",
            f"{_ONISEP}/605344579a7d7/605344579a7d7.csv",
            "Onisep, Idéo-Actions de formation initiale, univers enseignement supérieur", "ODbL",
        ),
        Source(
            "parcoursup_apprentissage_2025", "data/raw/parcoursup_apprentissage_2025.csv",
            f"{_ESR}/fr-esr-parcoursup-apprentissage/exports/csv"
            "?delimiter=%3B&where=session%3D%222025%22",
            "MESR (SIES), jeu fr-esr-parcoursup-apprentissage, session 2025", "Licence Ouverte v2.0",
        ),
        Source(
            "insersup", "data/raw/insersup_diplomes_ensemble_2023_2024.csv",
            f"{_ESR}/fr-esr-insersup/exports/csv?delimiter=%3B&where={_INSERSUP_FILTRE}",
            "MESR (SIES), jeu fr-esr-insersup (dispositif InserSup), diplômés, promos 2023 et 2024",
            "Licence Ouverte v2.0",
        ),
        Source(
            "inserjeunes_bts", "data/raw/inserjeunes_lycee_pro_bts.csv",
            f"{_DEPP}/fr-en-inserjeunes-lycee_pro-formation-fine/exports/csv"
            "?delimiter=%3B&where=type_diplome%3D%22BTS%22",
            "DEPP-DARES, jeu fr-en-inserjeunes-lycee_pro-formation-fine, BTS", "Licence Ouverte v2.0",
        ),
    )
}


def _aujourdhui() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Paris")).date().isoformat()


class EmpreinteDivergente(RuntimeError):
    """Un fichier brut ne correspond plus à l'empreinte du verrou."""


def empreinte(chemin: Path) -> dict:
    data = chemin.read_bytes()
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "octets": len(data),
        "lignes": max(data.count(b"\n") - 1, 0),  # hors ligne d'en-tête
    }


def charger_verrou() -> dict:
    return json.loads(VERROU.read_text(encoding="utf-8")) if VERROU.exists() else {}


def chemin_verifie(nom: str) -> Path:
    """Chemin d'un fichier brut, après contrôle de son empreinte contre le verrou."""
    source = SOURCES[nom]
    chemin = RACINE / source.chemin
    if not chemin.exists():
        raise FileNotFoundError(
            f"{chemin} absent : lancer `python -m src.collect.sources_officielles --telecharger`"
        )
    attendu = charger_verrou().get(nom, {}).get("sha256")
    if attendu is None:
        raise EmpreinteDivergente(f"{nom} n'est pas dans le verrou {VERROU.name}")
    obtenu = hashlib.sha256(chemin.read_bytes()).hexdigest()
    if obtenu != attendu:
        raise EmpreinteDivergente(f"{nom} : sha256 {obtenu[:12]} au lieu de {attendu[:12]}")
    return chemin


def telecharger(source: Source) -> None:
    cible = RACINE / source.chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(source.url, timeout=300) as rep:
        cible.write_bytes(rep.read())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--telecharger", action="store_true", help="télécharge les fichiers absents")
    ap.add_argument("--mettre-a-jour", action="store_true", help="réécrit le verrou avec les fichiers présents")
    args = ap.parse_args(argv)

    verrou = charger_verrou()
    divergences = 0
    for source in SOURCES.values():
        chemin = RACINE / source.chemin
        if not chemin.exists() and args.telecharger:
            telecharger(source)
            if source.nom not in verrou:
                verrou[source.nom] = {"telecharge_le": _aujourdhui()}
        if not chemin.exists():
            print(f"ABSENT      {source.nom}")
            divergences += 1
            continue
        mesure = empreinte(chemin)
        attendu = verrou.get(source.nom, {}).get("sha256")
        if args.mettre_a_jour:
            verrou[source.nom] = {
                "chemin": source.chemin, "url": source.url, "producteur": source.producteur,
                "licence": source.licence,
                "telecharge_le": verrou.get(source.nom, {}).get("telecharge_le")
                or _aujourdhui(),
                **mesure,
            }
            print(f"VERROUILLE  {source.nom}  {mesure['sha256'][:12]}  {mesure['lignes']} lignes")
        elif attendu == mesure["sha256"]:
            print(f"OK          {source.nom}  {attendu[:12]}")
        else:
            print(f"DIVERGENT   {source.nom}  {mesure['sha256'][:12]} (verrou : {str(attendu)[:12]})")
            divergences += 1
    if args.mettre_a_jour:
        VERROU.parent.mkdir(parents=True, exist_ok=True)
        VERROU.write_text(json.dumps(verrou, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    return 1 if divergences else 0


if __name__ == "__main__":
    sys.exit(main())
