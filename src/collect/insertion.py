"""Insertion professionnelle (étape B-1, champ `insertion`).

Forme : `results/donnee_etape_b/CONTRACT.md`, section 5 (version 1.1). Seule la granularité
« diplôme x établissement » est admise : une ligne de la source qui décrit CE diplôme (même
spécialité, même mention) dans CET établissement. Un agrégat régional, national ou « tous les BUT
de l'université » n'est pas une information sur la formation : `non_disponible`.

Rattachement, mesuré le 23/09/2026 :
- InserSup (BUT, licence, école d'ingénieurs, grade licence) : InserSup compte par
  **établissement d'inscription** (l'université, pas l'IUT ni le site). Les UAI Parcoursup des
  IUT ne sont pas dans InserSup (0 fiche BUT sur 820 par l'UAI) ; l'identifiant Paysage de
  l'établissement, publié par la cartographie Parcoursup (`etablissement_id_paysage`), l'est
  (797 BUT sur 820). La valeur couvre donc tous les sites de l'université, et le dit.
- InserJeunes (BTS en lycée) : UAI du lycée + libellé de la spécialité. Une spécialité à
  options (BTS SIO option A / option B) donne une ligne par option ; toutes sont gardées.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from src.collect.valeur_sourcee import Referentiel

INSERSUP = "insersup"
INSERJEUNES = "inserjeunes_bts"
INSERJEUNES_ANNEE = "cumul 2023-2024"  # dernière période du jeu au 20/07/2026
GRANULARITE = "diplome_etablissement"

# Promotions InserSup, de la plus récente à la plus ancienne. InserSup publie aussi des promotions
# cumulées (« 2023,2024 ») ; une seule ligne est retenue par diplôme, la première de cet ordre.
ORDRE_PROMOS = ("2024", "2023,2024", "2023", "2022,2023")

# Filière Parcoursup -> types InserSup (`type_diplome`) du même diplôme.
TYPES_INSERSUP = {
    "BUT": frozenset({"but"}),
    "Licence": frozenset({"Licence générale"}),
    "Ecole d'Ingénieur": frozenset({"Formation ingénieur"}),
}

# Filières sans source d'insertion par formation : la raison est écrite telle quelle.
SANS_SOURCE = {
    "PASS": "l'insertion professionnelle n'est pas mesurée pour une première année d'accès aux études de santé",
    "Licence_Las": (
        "l'insertion d'une LAS n'est pas mesurée en tant que telle : elle ouvre l'accès aux études "
        "de santé, et InserSup ne distingue pas la licence suivie avec l'option santé"
    ),
    "CPGE": "une classe préparatoire ne délivre pas de diplôme : aucun dispositif d'insertion ne la couvre",
    "IFSI": (
        "aucune source nationale récente ne publie l'insertion par institut pour les formations "
        "paramédicales"
    ),
}

def norme_libelle(texte: str | None) -> str:
    """Majuscules sans accents ni ponctuation ; le parcours d'un BUT est retiré (InserSup publie
    la spécialité, pas le parcours)."""
    s = unicodedata.normalize("NFKD", texte or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).upper()
    s = re.sub(r"\s+PARCOURS\s+.*$", "", s)
    return " ".join(re.findall(r"[A-Z0-9]+", s))


def _taux(v) -> float | None:
    """Taux publié (0 à 100) ; None si vide ou « nd » (non diffusé par la source)."""
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if not s or s.lower() == "nd":
        return None
    try:
        return float(s)  # valeur publiée telle quelle, jamais arrondie
    except ValueError:
        return None


def _entier(v) -> int | None:
    t = _taux(v)
    return None if t is None else int(t)


def _nd(v) -> bool:
    return str(v or "").strip().lower() == "nd"


def _a_un_taux(ligne: dict) -> bool:
    """Une ligne dont tous les indicateurs sont non diffusés ne dit rien de la formation : elle
    ne compte pas comme une insertion disponible (sinon le taux de remplissage mentirait)."""
    return any(v is not None for v in ligne["indicateurs"].values())


class CalculInsertion:
    def __init__(
        self,
        insersup: list[dict],
        inserjeunes: list[dict],
        paysage_par_formation: dict[str, str],
        referentiel: Referentiel,
    ) -> None:
        self.ref = referentiel
        self.paysage = paysage_par_formation
        # InserSup : (id_paysage, type, libellé normé) -> ligne de la promo la plus récente.
        rang = {p: i for i, p in enumerate(ORDRE_PROMOS)}
        self.insersup: dict[tuple[str, str, str], dict] = {}
        for ligne in insersup:
            if ligne.get("libelle_diplome", "").startswith("Tout"):
                continue  # agrégat « tous les diplômes du type » : pas une formation
            promo = ligne.get("promo") or ""
            if promo not in rang:
                continue
            for pid in {ligne.get("id_paysage"), ligne.get("id_paysage_actuel")} - {None, ""}:
                cle = (pid, ligne.get("type_diplome"), norme_libelle(ligne.get("libelle_diplome")))
                garde = self.insersup.get(cle)
                if garde is None or rang[promo] < rang[garde["promo"]]:
                    self.insersup[cle] = ligne
        self.ingenieur_par_paysage: dict[str, list[dict]] = defaultdict(list)
        for (pid, typ, _), ligne in self.insersup.items():
            if typ == "Formation ingénieur":
                self.ingenieur_par_paysage[pid].append(ligne)
        # InserJeunes : (UAI, libellé normé sans option) -> lignes de la dernière période.
        self.inserjeunes: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for ligne in inserjeunes:
            if ligne.get("annee") != INSERJEUNES_ANNEE:
                continue
            specialite = re.sub(r"\s+OPTION\s+.*$", "", norme_libelle(ligne.get("libelle_formation")))
            self.inserjeunes[(ligne.get("uai"), specialite)].append(ligne)

    # ── InserSup ──────────────────────────────────────────────────────────────────────────
    def _ligne_insersup(self, ligne: dict) -> dict:
        non_diffuse = []
        indicateurs = {}
        for cle, col in (
            ("taux_emploi_salarie_fr_6m", "tx_sortants_en_emploi_sal_fr_6"),
            ("taux_emploi_salarie_fr_12m", "tx_sortants_en_emploi_sal_fr_12"),
            ("taux_emploi_salarie_fr_18m", "tx_sortants_en_emploi_sal_fr_18"),
            ("taux_emploi_stable_12m", "tx_sortants_en_emploi_stable_12"),
            ("salaire_median_net_12m_eur", "salaire_q2_12"),
        ):
            indicateurs[cle] = _taux(ligne.get(col))
            if _nd(ligne.get(col)):
                non_diffuse.append(cle)
        if indicateurs["salaire_median_net_12m_eur"] is not None:
            indicateurs["salaire_median_net_12m_eur"] = int(indicateurs["salaire_median_net_12m_eur"])
        return {
            "perimetre": {
                "etablissement": ligne.get("uo_lib"),
                "diplome": ligne.get("libelle_diplome"),
                "type_diplome": ligne.get("type_diplome_long"),
                "granularite": GRANULARITE,
                "code_diplome_sise": ligne.get("diplome"),
            },
            "effectif_sortants": _entier(ligne.get("nb_sortants_12")),
            "effectif_poursuivants": _entier(ligne.get("nb_poursuivants_12")),
            "indicateurs": indicateurs,
            "non_diffuse": non_diffuse,
        }

    def _insersup(self, fiche: dict) -> dict:
        fili = fiche.get("fili_code")
        pid = self.paysage.get(str(fiche.get("cod_aff_form")))
        if not pid:
            return self.ref.non_disponible(
                "établissement de la formation non identifié dans la cartographie Parcoursup",
                INSERSUP, rattachement="paysage_etablissement",
            )
        if fili == "Ecole d'Ingénieur":
            lignes = self.ingenieur_par_paysage.get(pid, [])
            if len(lignes) != 1:
                raison = (
                    "aucun diplôme d'ingénieur de cette école dans InserSup" if not lignes else
                    f"{len(lignes)} diplômes d'ingénieur de cette école dans InserSup : "
                    "impossible de dire lequel suit cette formation post-bac"
                )
                return self.ref.non_disponible(raison, INSERSUP, rattachement="paysage_etablissement")
            ligne = lignes[0]
        else:
            libelle = norme_libelle(fiche.get("filiere_detaillee"))
            ligne = next(
                (self.insersup[(pid, t, libelle)] for t in TYPES_INSERSUP[fili] if (pid, t, libelle) in self.insersup),
                None,
            )
            if ligne is None:
                return self.ref.non_disponible(
                    "InserSup ne publie pas ce diplôme pour cet établissement (effectif trop faible "
                    "ou diplôme absent du dispositif)",
                    INSERSUP, rattachement="paysage_etablissement",
                )
        publiee = self._ligne_insersup(ligne)
        if not _a_un_taux(publiee):
            effectif = publiee["effectif_sortants"]
            return self.ref.non_disponible(
                "InserSup ne diffuse aucun taux pour ce diplôme dans cet établissement"
                + (f" ({effectif} sortant{'s' if effectif > 1 else ''}, effectif trop faible)" if effectif is not None else ""),
                INSERSUP, f"promotion {ligne.get('promo')}", "paysage_etablissement",
            )
        valeur = {"dispositif": "InserSup", "promotion": ligne.get("promo"), "regime": "ensemble",
                  "lignes": [publiee]}
        return self.ref.disponible(valeur, INSERSUP, f"promotion {ligne.get('promo')}", "paysage_etablissement")

    # ── InserJeunes ───────────────────────────────────────────────────────────────────────
    def _inserjeunes(self, fiche: dict) -> dict:
        cle = (fiche.get("cod_uai"), norme_libelle(fiche.get("filiere_detaillee")))
        lignes = self.inserjeunes.get(cle, [])
        if not lignes:
            return self.ref.non_disponible(
                "InserJeunes ne publie pas ce BTS pour ce lycée (effectif trop faible ou lycée hors "
                "dispositif)",
                INSERJEUNES, INSERJEUNES_ANNEE, "uai_specialite",
            )
        sortie = []
        for ligne in sorted(lignes, key=lambda x: x.get("libelle_formation") or ""):
            indicateurs = {
                "taux_emploi_6m": _taux(ligne.get("taux_emploi_6_mois")),
                "taux_emploi_12m": _taux(ligne.get("taux_emploi_12_mois")),
                "taux_poursuite_etudes": _taux(ligne.get("taux_poursuite_etudes")),
            }
            sortie.append({
                "perimetre": {
                    "etablissement": ligne.get("libelle"),
                    "diplome": f"BTS {ligne.get('libelle_formation')}",
                    "granularite": GRANULARITE,
                    "code_formation_mefstat11": ligne.get("code_formation_mefstat11"),
                },
                "effectif_sortants": None,  # non publié par InserJeunes
                "indicateurs": indicateurs,
                "non_diffuse": [k for k, v in indicateurs.items() if v is None],
            })
        if not any(_a_un_taux(x) for x in sortie):
            return self.ref.non_disponible(
                "InserJeunes ne diffuse aucun taux pour ce BTS dans ce lycée (effectif trop faible)",
                INSERJEUNES, INSERJEUNES_ANNEE, "uai_specialite",
            )
        valeur = {"dispositif": "InserJeunes", "promotion": INSERJEUNES_ANNEE, "regime": "voie scolaire",
                  "lignes": sortie}
        return self.ref.disponible(valeur, INSERJEUNES, INSERJEUNES_ANNEE, "uai_specialite")

    def calculer(self, fiche: dict) -> dict:
        fili = fiche.get("fili_code")
        if fiche.get("source") == "parcoursup_apprentissage":
            return self.ref.non_disponible(
                "l'insertion des formations en apprentissage n'est pas dans les jeux ouverts utilisés "
                "(InserJeunes lycée ne couvre que la voie scolaire)"
            )
        if fili in SANS_SOURCE:
            return self.ref.non_disponible(SANS_SOURCE[fili])
        if fili == "Autre formation" and fiche.get("domaine") == "sante":
            return self.ref.non_disponible(SANS_SOURCE["IFSI"])
        if fili == "BTS":
            return self._inserjeunes(fiche)
        if fili in TYPES_INSERSUP:
            return self._insersup(fiche)
        return self.ref.non_disponible(
            "aucune source d'insertion par formation rattachée pour ce type de formation"
        )
