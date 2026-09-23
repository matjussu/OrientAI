"""Normalisation des villes Parcoursup et rattachement au code commune INSEE.

Le champ `ville_etab` du jeu fr-esr-parcoursup est saisi tel que l'établissement l'a
déclaré : arrondissements (« Paris  6e  Arrondissement »), mentions CEDEX, espaces doublés.
Ce module ramène chaque valeur à la commune du Code officiel géographique (COG) de l'INSEE
et lui attache son code commune.

Référentiel : COG 2025 de l'INSEE, deux fichiers (France et collectivités d'outre-mer),
téléchargés par `src.collect.sources_officielles`. La jointure se fait sur le couple
(département, nom normalisé) : un nom de commune seul n'est pas unique en France.

Ordre de résolution, du plus sûr au moins sûr :
1. arrondissement de Paris, Lyon ou Marseille -> commune parente (75056, 69123, 13055) ;
2. commune (TYPECOM = COM) du département ;
3. commune déléguée ou associée (COMD, COMA) -> sa commune parente ;
4. collectivité d'outre-mer (fichier COMER).
Une ville introuvable garde son libellé nettoyé et un code INSEE `None` : on ne devine pas.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_ARRONDISSEMENT = re.compile(
    r"^(?P<ville>Paris|Lyon|Marseille)\s+(?P<num>\d{1,2})\s*(?:er|e|ème)\s+arrondissement$",
    re.IGNORECASE,
)
_CEDEX = re.compile(r"\s+cedex(?:\s*\d+)?\s*$", re.IGNORECASE)
# Département « 99 » du jeu Parcoursup = établissement à l'étranger (aucun code INSEE).
DEPARTEMENT_ETRANGER = "99"
# Le jeu Parcoursup code la Corse « 20 » ; le COG la découpe en 2A et 2B.
_DEPARTEMENTS_COG = {"20": ("2A", "2B")}


@dataclass(frozen=True)
class Commune:
    """Ville normalisée. `code_insee` est None quand la commune n'a pas été trouvée."""

    ville: str
    code_insee: str | None
    arrondissement: str | None = None
    code_insee_arrondissement: str | None = None


def cle_nom(nom: str) -> str:
    """Clé de comparaison d'un nom de commune : sans accents, majuscules, séparateurs unifiés.

    « Saint-Étienne », « ST ETIENNE » et « St-Etienne » donnent la même clé.
    """
    s = nom.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[-'’\s]+", " ", s.upper()).strip()
    s = re.sub(r"^STE ", "SAINTE ", s)
    s = re.sub(r"^ST ", "SAINT ", s)
    s = re.sub(r" STE ", " SAINTE ", s)
    s = re.sub(r" ST ", " SAINT ", s)
    return s


def nettoyer_libelle(ville: str) -> str:
    """Retire CEDEX et les espaces parasites, sans rien changer d'autre."""
    return _CEDEX.sub("", re.sub(r"\s+", " ", ville or "").strip())


def _code_departement(dep: str | None) -> str:
    d = (dep or "").strip()
    # Le jeu Parcoursup écrit « 1 » pour l'Ain ; le COG écrit « 01 ».
    return d.zfill(2) if d.isdigit() and len(d) < 2 else d


class ReferentielCommunes:
    """Index du COG INSEE pour résoudre (ville brute, département) en commune."""

    def __init__(self, communes_csv: Path, comer_csv: Path | None = None):
        self._communes: dict[tuple[str, str], tuple[str, str]] = {}
        self._deleguees: dict[tuple[str, str], str] = {}
        self._arrondissements: dict[str, tuple[str, str]] = {}
        self._libelles: dict[str, str] = {}
        self._comer: dict[tuple[str, str], tuple[str, str]] = {}
        with communes_csv.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        departement_de: dict[str, str] = {}
        for r in rows:
            if r["TYPECOM"] == "COM":
                self._libelles[r["COM"]] = r["LIBELLE"]
                departement_de[r["COM"]] = r["DEP"]
        for r in rows:
            if r["TYPECOM"] == "COM":
                self._communes[(r["DEP"], cle_nom(r["LIBELLE"]))] = (r["COM"], r["LIBELLE"])
            elif r["TYPECOM"] == "ARM":
                self._arrondissements[r["COM"]] = (r["COMPARENT"], r["LIBELLE"])
            elif r["TYPECOM"] in ("COMD", "COMA") and r["COMPARENT"]:
                # Le COG laisse DEP vide sur les communes déléguées et associées (mesuré le
                # 23/09/2026) : leur département est celui de la commune parente.
                dep = departement_de.get(r["COMPARENT"], "")
                self._deleguees.setdefault((dep, cle_nom(r["LIBELLE"])), r["COMPARENT"])
        if comer_csv and comer_csv.exists():
            with comer_csv.open(encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    self._comer[(r["COMER"], cle_nom(r["LIBELLE"]))] = (r["COM_COMER"], r["LIBELLE"])

    def resoudre(self, ville_brute: str | None, departement: str | None) -> Commune:
        libelle = nettoyer_libelle(ville_brute or "")
        dep = _code_departement(departement)
        if not libelle:
            return Commune(ville="", code_insee=None)

        m = _ARRONDISSEMENT.match(libelle)
        if m:
            return self._arrondissement(m.group("ville"), int(m.group("num")), libelle)

        if dep == DEPARTEMENT_ETRANGER:
            return Commune(ville=libelle, code_insee=None)

        cle = cle_nom(libelle)
        for dep_cog in _DEPARTEMENTS_COG.get(dep, (dep,)):
            trouve = self._communes.get((dep_cog, cle))
            if trouve:
                return Commune(ville=trouve[1], code_insee=trouve[0])
            parent = self._deleguees.get((dep_cog, cle))
            if parent and parent in self._libelles:
                return Commune(ville=self._libelles[parent], code_insee=parent)
        trouve = self._comer.get((dep, cle))
        if trouve:
            return Commune(ville=trouve[1], code_insee=trouve[0])
        return Commune(ville=libelle, code_insee=None)

    def _arrondissement(self, ville: str, numero: int, libelle: str) -> Commune:
        base = {"paris": 75100, "lyon": 69380, "marseille": 13200}[ville.lower()]
        code_arm = str(base + numero)
        trouve = self._arrondissements.get(code_arm)
        suffixe = "1er" if numero == 1 else f"{numero}e"
        if not trouve:
            return Commune(ville=libelle, code_insee=None)
        parent, _ = trouve
        return Commune(
            ville=self._libelles.get(parent, ville.title()),
            code_insee=parent,
            arrondissement=f"{suffixe} arrondissement",
            code_insee_arrondissement=code_arm,
        )
