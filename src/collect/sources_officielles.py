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
        # ── étape B-2 : santé (documents lus, chiffres recopiés dans src.collect.sante*) ──
        Source(
            "sies_nf_2025_31", "data/raw/sante/nf-sies-2025-31.pdf",
            "https://www.enseignementsup-recherche.gouv.fr/sites/default/files/2025-11/nf-sies-2025-31-38644.pdf",
            "MESRE-SIES, Note Flash n°31 (novembre 2025), parcours et réussite des étudiants en première année d'études de santé, session 2024", "publication statistique publique",
        ),
        Source(
            "univ_paris_cite_jpo_2026", "data/raw/sante/paris_cite_jpo_2026.pdf",
            "https://u-paris.fr/sante/wp-content/uploads/sites/19/2026/02/Acce%CC%80s-Sante%CC%81-PASS-JPO-7-fe%CC%81vrier-2026.pdf",
            "Université Paris Cité, Faculté de Santé, diaporama « Accès Santé PASS/L.AS », journée portes ouvertes du 07/02/2026", "document public de l'université",
        ),
        Source(
            "univ_spn_mmop_2026_2027", "data/raw/sante/spn_mmop_2026_2027.pdf",
            "https://smbh.univ-paris13.fr/images/Formations/Passerelles_sante/CA_rentree_2026.pdf",
            "Université Sorbonne Paris Nord, UFR SMBH, capacités d'accueil en 2e année MMOP pour 2026-2027", "document public de l'université",
        ),
        Source(
            "univ_lille_mmopk_2026", "data/raw/sante/lille_mmopk_2026.pdf",
            "https://ufr3s.univ-lille.fr/fileufr3s/user_upload/ufr3s-formations/pass-las/generalites/2026-27-numerus-apertus.pdf",
            "Université de Lille, UFR3S, capacités d'accueil en 2e année MMOPK pour la rentrée 2026", "document public de l'université",
        ),
        Source(
            "univ_lyon1_mmop_2026_2027", "data/raw/sante/lyon1_mmop_2026_2027.pdf",
            "https://lyon-sud.univ-lyon1.fr/medias/fichier/capacites-d-accueil-mmop-2026-2027_1774602177702-pdf",
            "Université Claude Bernard Lyon 1, délibération du CA du 23/09/2025, capacités d'accueil MMOP 2026-2027", "document public de l'université",
        ),
        Source(
            "univ_lyon1_kine_2026_2027", "data/raw/sante/lyon1_kine_2026_2027.pdf",
            "https://lyon-sud.univ-lyon1.fr/medias/fichier/capacites-d-accueil-kine-2026-2027_1774602187382-pdf",
            "Université Claude Bernard Lyon 1, délibération du CA du 25/11/2025, capacités d'accueil en kinésithérapie 2026-2027", "document public de l'université",
        ),
        Source(
            "univ_montpellier_mmop_2026_2027", "data/raw/sante/montpellier_mmop_2026_2027.pdf",
            "https://sciences.edu.umontpellier.fr/files/2025/10/CAPACITES-ACCUEIL-MMOP-votees-2025-2026.pdf",
            "Université de Montpellier, répartition des capacités d'accueil par filière MMOP (places ouvertes en DFGS2 en 2026-2027)", "document public de l'université",
        ),
        Source(
            "univ_bordeaux_mmop_2026_2027", "data/raw/sante/bordeaux_mmop_2026_2027.pdf",
            "https://sante.u-bordeaux.fr/application/files/4417/7444/3955/Capacites_daccueil_MMOP_2026_27.pdf",
            "Université de Bordeaux, capacités d'accueil MMOP rentrée 2026/27 (document du 25/11/2025)", "document public de l'université",
        ),
        Source(
            "univ_bordeaux_kine_2025_2026", "data/raw/sante/bordeaux_kine_2025_2026.pdf",
            "https://sante.u-bordeaux.fr/application/files/8517/5214/1803/Capacites_daccueil_Kinesitherapie_2025-2026.pdf",
            "Université de Bordeaux, capacité d'accueil en kinésithérapie 2025/2026", "document public de l'université",
        ),
        Source(
            "univ_nantes_mmopk_2026_2027", "data/raw/sante/nantes_mmopk_2026_2027.pdf",
            "https://medecine.univ-nantes.fr/medias/fichier/capacite-accueil-mmopk-2026-2027_1763540007643-pdf",
            "Nantes Université, délibération du Conseil académique n°CAC_250919-05 (19/09/2025), capacités d'accueil MMOP-K 2026-2027", "document public de l'université",
        ),
        Source(
            "univ_amu_mmop_rentree_2024", "data/raw/sante/amu_mmop_rentree_2024.pdf",
            "https://daji.univ-amu.fr/sites/daji.univ-amu.fr/files/ca_deliberations/ca2023_09_18_05_capacites_daccueil_0.pdf",
            "Aix-Marseille Université, délibération du CA du 19/09/2023, capacités d'accueil MMOP pour la rentrée 2024", "document public de l'université",
        ),
        Source(
            "univ_toulouse_mmopk_2025_2026", "data/raw/sante/toulouse_mmopk_2025_2026.pdf",
            "https://sante.utoulouse.fr/medias/fichier/2025-2026-numerus-apertus-pass-las_1759410255556-pdf",
            "Université de Toulouse, Faculté de santé, numerus apertus PASS-LAS 2025/2026 (21/07/2025)", "document public de l'université",
        ),
        # ── étape C : base structurée (contrat results/donnee_etape_c/CONTRACT.md v1) ──
        # MonMaster en JSON : `modalite_enseignement` y est une liste, que le CSV aplatit.
        Source(
            "monmaster_2025", "data/raw/monmaster_2025.json",
            f"{_ESR}/fr-esr-mon_master/exports/json?where=session%3D%222025%22",
            "MESR (SIES), jeu fr-esr-mon_master, session 2025", "Licence Ouverte v2.0",
        ),
        # Centre des communes (champ `centre`) pour la distance « à moins de N km de ».
        Source(
            "geo_api_communes", "data/raw/geo_api_communes.json",
            "https://geo.api.gouv.fr/communes?fields=code,nom,centre,codeDepartement,codeRegion&format=json",
            "DINUM (Etalab), API Découpage administratif geo.api.gouv.fr, communes et leur centre",
            "Licence Ouverte v2.0",
        ),
    )
}


def _aujourdhui() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Paris")).date().isoformat()


class EmpreinteDivergente(RuntimeError):
    """Un fichier brut ne correspond plus à l'empreinte du verrou."""


def empreinte(chemin: Path) -> dict:
    data = chemin.read_bytes()
    if chemin.suffix == ".json":
        # Un export JSON est un tableau sur une seule ligne : on compte ses éléments.
        contenu = json.loads(data)
        lignes = len(contenu) if isinstance(contenu, list) else 1
    else:
        lignes = max(data.count(b"\n") - 1, 0)  # hors ligne d'en-tête
    return {"sha256": hashlib.sha256(data).hexdigest(), "octets": len(data), "lignes": lignes}


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
