"""Étape A de la donnée verticale : corriger les fiches Parcoursup sans nouvelle source de chiffres.

Construit un NOUVEAU corpus à partir du corpus de référence (celui de la prod) et des jeux
officiels bruts verrouillés (`src.collect.sources_officielles`). Le corpus de référence n'est
jamais réécrit.

Ce que fait la construction, pour chaque ligne du jeu officiel fr-esr-parcoursup 2025 :
1. retrouve la fiche du corpus par `cod_aff_form` (identifiant Parcoursup de la formation) ;
   si elle n'existe pas, la crée depuis la ligne officielle (A4) ;
2. normalise la ville et pose le code commune INSEE (A3, `src.collect.communes`) ;
3. reclasse le domaine par la table de correspondance (A2, `src.collect.domaines`) ;
4. pose le type de formation en clair, l'option ou la majeure, l'intitulé officiel complet,
   l'académie et l'effectif d'admis (A1, champs repris tels quels des jeux officiels).
Les fiches des autres sources (MonMaster, RNCP, corpus annexes...) sont recopiées à l'identique.

Cause mesurée de l'écart 13 011 / 14 252 (23/09/2026) : les 1 241 lignes absentes du corpus
partagent toutes leur clé (intitulé, établissement, ville) avec une ligne gardée ; le
dédoublonnage de `run_merge_v3.stage_dedup` les a fusionnées (options PASS, majeures LAS,
voies d'accès des écoles d'ingénieurs...). Ce module n'utilise pas cette clé : l'identité
d'une formation Parcoursup est son `cod_aff_form`.

Une fiche créée ici hérite de sa fiche sœur (même clé intitulé, établissement, ville) les
enrichissements qui dépendent de cette clé et pas de l'option : domaine (quand aucune règle
de la table ne s'applique), débouchés, insertion InserSup, labels, type de diplôme ONISEP.
L'héritage est écrit dans `provenance`.

Usage :
    python -m src.collect.corpus_etape_a [--reference data/processed/formations.json]
                                         [--sortie data/processed/formations_etape_a.json]
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from src.collect.communes import ReferentielCommunes
from src.collect.domaines import REGLE_ANTERIEURE, REGLE_CASCADE, charger_table, classer
from src.collect.parcoursup import (
    _clean_str,
    _safe_float,
    _safe_int,
    domaine_cascade,
    extract_fiche,
)
from src.collect.sources_officielles import RACINE, charger_verrou, chemin_verifie
from src.collect.trends import compute_trends, load_historical_snapshots
from src.collect.types_formation import decrire

REFERENCE = RACINE / "data/processed/formations.json"
SORTIE = RACINE / "data/processed/formations_etape_a.json"

# Enrichissements qu'une fiche créée reprend de sa sœur (cf. docstring du module).
CHAMPS_HERITES = ("domaine", "debouches", "insertion_pro", "labels", "type_diplome", "tutelle", "duree", "url_onisep")


def _cle_soeur(nom: str | None, etablissement: str | None, ville: str | None) -> tuple[str, str, str]:
    return tuple(" ".join(str(x or "").split()).lower() for x in (nom, etablissement, ville))


def _intitule_cartographie(nm: str | None) -> str | None:
    """Le champ `nm` de la cartographie est une liste JSON à un élément : on en sort le texte."""
    if not isinstance(nm, str) or not nm.strip():
        return None
    try:
        valeur = json.loads(nm)
    except json.JSONDecodeError:
        return _clean_str(nm)
    if isinstance(valeur, list):
        return _clean_str(" - ".join(str(v) for v in valeur)) if valeur else None
    return _clean_str(valeur)


class ConstructeurEtapeA:
    """Entrées injectées (testable sans fichiers) ; `depuis_sources()` lit les bruts verrouillés."""

    def __init__(
        self,
        officiel: pd.DataFrame,
        intitules: dict[str, str | None],
        communes: ReferentielCommunes,
        regles: list,
        historique: dict[int, dict[str, dict]],
        date_collecte: str,
    ) -> None:
        self.officiel = officiel
        # Date de téléchargement du jeu officiel (verrou), pas la date du jour : deux
        # constructions sur les mêmes bruts produisent le même fichier, octet pour octet.
        self.date_collecte = date_collecte
        self.intitules = intitules
        self.communes = communes
        self.regles = regles
        self.historique = historique
        self.stats: Counter = Counter()

    @classmethod
    def depuis_sources(cls) -> ConstructeurEtapeA:
        officiel = pd.read_csv(
            chemin_verifie("parcoursup_2025"), sep=";", dtype=str, keep_default_na=False, na_values=[""]
        )
        carto = pd.read_csv(chemin_verifie("cartographie_parcoursup_2025"), sep=";", dtype=str)
        return cls(
            officiel=officiel,
            intitules={g: _intitule_cartographie(nm) for g, nm in zip(carto["gta"], carto["nm"])},
            communes=ReferentielCommunes(
                chemin_verifie("insee_cog_communes_2025"), chemin_verifie("insee_cog_comer_2025")
            ),
            regles=charger_table(),
            historique={
                annee: load_historical_snapshots(chemin_verifie(f"parcoursup_{annee}"), annee)
                for annee in (2023, 2024, 2025)
            },
            date_collecte=charger_verrou()["parcoursup_2025"]["telecharge_le"],
        )

    # ── enrichissements appliqués à toute fiche Parcoursup ──────────────────────────
    def corriger(self, fiche: dict, ligne: pd.Series) -> dict:
        cod = str(ligne["cod_aff_form"])
        intitule_complet = self.intitules.get(cod)
        filiere = _clean_str(ligne.get("form_lib_voe_acc"))
        filiere_detaillee = _clean_str(ligne.get("fil_lib_voe_acc"))

        commune = self.communes.resoudre(ligne.get("ville_etab"), ligne.get("dep"))
        fiche["ville_source"] = _clean_str(ligne.get("ville_etab"))
        fiche["ville"] = commune.ville
        fiche["code_insee"] = commune.code_insee
        fiche["arrondissement"] = commune.arrondissement
        fiche["code_insee_arrondissement"] = commune.code_insee_arrondissement
        fiche["code_departement"] = _clean_str(ligne.get("dep"))
        fiche["academie"] = _clean_str(ligne.get("acad_mies"))

        fiche["intitule_officiel"] = intitule_complet
        fiche["form_lib_voe_acc"] = filiere
        fiche["filiere_detaillee"] = filiere_detaillee
        type_formation = decrire(ligne.get("fili"), fiche.get("nom"), intitule_complet, filiere_detaillee)
        fiche["type_formation"] = type_formation.libelle if type_formation else None
        fiche["precision_formation"] = type_formation.precision if type_formation else None

        intitule = " ".join(x for x in (fiche.get("nom"), intitule_complet, _clean_str(ligne.get("detail_forma"))) if x)
        classe = classer(self.regles, ligne.get("fili"), filiere, intitule)
        ancien = fiche.get("domaine")
        if classe:
            fiche["domaine"], fiche["domaine_regle"] = classe
        elif ancien:
            # Hors table, l'étape A ne revoit pas le classement : la fiche garde son domaine.
            # (Rejouer le classement historique en changerait 53, tous vers « social » : la
            # règle du 11/06 n'est pas reflétée dans le corpus, cause non établie. Hors
            # périmètre, signalé dans results/donnee_etape_a/RAPPORT.md.)
            fiche["domaine_regle"] = REGLE_ANTERIEURE
        else:
            fiche["domaine"], fiche["domaine_regle"] = domaine_cascade(ligne), REGLE_CASCADE

        volumes = fiche.setdefault("admission", {}).setdefault("volumes", {})
        volumes["admis_total"] = _safe_int(ligne.get("acc_tot"))
        # Deux parts de la répartition par mention jamais ingérées : sans elles, la répartition
        # ne somme à 100 que sur 89,6 % des lignes renseignées, avec elles sur 100 % (23/09/2026).
        mentions = fiche.setdefault("profil_admis", {}).setdefault("mentions_pct", {})
        mentions["tbf"] = _safe_float(ligne.get("pct_tbf"))
        mentions["non_renseignee"] = _safe_float(ligne.get("pct_mention_nonrenseignee"))
        return fiche

    # ── création d'une fiche absente du corpus de référence (A4) ────────────────────
    def creer(self, ligne: pd.Series, soeur: dict | None, date_collecte: str) -> dict:
        fiche = extract_fiche(ligne)
        cod = fiche["cod_aff_form"]
        historique = {a: s[cod] for a, s in self.historique.items() if cod in s}
        if historique:
            fiche["admission"]["historique"] = {str(a): v for a, v in sorted(historique.items())}
            tendances = compute_trends(historique)
            if tendances:
                fiche["trends"] = tendances
        fiche.update(
            provenance={"admission": "parcoursup_2025", "profil_admis": "parcoursup_2025"},
            collected_at={"parcoursup": date_collecte},
            merge_confidence={"parcoursup": 1.0},
            retrieval_eligible=True,
            url_canonical=fiche.get("lien_form_psup"),
            url_type="direct_parcoursup" if fiche.get("lien_form_psup") else None,
        )
        if soeur:
            herites = [c for c in CHAMPS_HERITES if soeur.get(c) not in (None, [], {})]
            for champ in herites:
                fiche[champ] = copy.deepcopy(soeur[champ])
            if herites:
                fiche["provenance"]["herite_de"] = {"cod_aff_form": soeur.get("cod_aff_form"), "champs": herites}
        return fiche

    def construire(self, reference: list[dict]) -> list[dict]:
        date_collecte = self.date_collecte
        par_code = {str(f["cod_aff_form"]): i for i, f in enumerate(reference) if f.get("source") == "parcoursup"}
        sortie = [copy.deepcopy(f) for f in reference]
        soeurs = {
            _cle_soeur(f.get("nom"), f.get("etablissement"), f.get("ville")): f
            for f in reference if f.get("source") == "parcoursup"
        }
        nouvelles_apres: dict[int, list[dict]] = {}
        vus: set[str] = set()
        for _, ligne in self.officiel.iterrows():
            cod = str(ligne["cod_aff_form"])
            vus.add(cod)
            if cod in par_code:
                fiche = sortie[par_code[cod]]
                domaine_avant = fiche.get("domaine")
                self.corriger(fiche, ligne)
                self.stats["corrigees"] += 1
                self.stats["corrigees_domaine_change"] += int(domaine_avant != fiche["domaine"])
                continue
            cle = _cle_soeur(ligne.get("lib_for_voe_ins"), ligne.get("g_ea_lib_vx"), ligne.get("ville_etab"))
            soeur = soeurs.get(cle)
            fiche = self.corriger(self.creer(ligne, soeur, date_collecte), ligne)
            self.stats["creees"] += 1
            self.stats["creees_avec_soeur"] += int(soeur is not None)
            position = par_code[str(soeur["cod_aff_form"])] if soeur else len(sortie) - 1
            nouvelles_apres.setdefault(position, []).append(fiche)
        self.stats["reference_hors_officiel"] = len(set(par_code) - vus)

        resultat: list[dict] = []
        for i, fiche in enumerate(sortie):
            resultat.append(fiche)
            resultat.extend(nouvelles_apres.get(i, []))
        return resultat


def _sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Construit le corpus de l'étape A (donnée verticale).")
    ap.add_argument("--reference", type=Path, default=REFERENCE)
    ap.add_argument("--sortie", type=Path, default=SORTIE)
    args = ap.parse_args(argv)
    if args.sortie.resolve() == args.reference.resolve():
        ap.error("la sortie doit être distincte du corpus de référence")

    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    constructeur = ConstructeurEtapeA.depuis_sources()
    corpus = constructeur.construire(reference)

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    ps = [f for f in corpus if f.get("source") == "parcoursup"]
    manifeste = {
        "genere_le": dt.datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "commande": "python -m src.collect.corpus_etape_a",
        "reference": {"chemin": str(args.reference), "sha256": _sha256(args.reference), "fiches": len(reference)},
        "sortie": {"chemin": str(args.sortie), "sha256": _sha256(args.sortie), "fiches": len(corpus)},
        "sources": {k: v.get("sha256") for k, v in charger_verrou().items()},
        "parcoursup": {
            "fiches": len(ps),
            "lignes_officielles": len(constructeur.officiel),
            **dict(constructeur.stats),
            "sans_code_insee": sum(1 for f in ps if not f.get("code_insee")),
            "domaine_par_regle": dict(Counter(f.get("domaine_regle") for f in ps).most_common()),
        },
    }
    manifeste_path = args.sortie.with_suffix(".manifest.json")
    manifeste_path.write_text(json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifeste, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
