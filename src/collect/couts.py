"""Coût d'une formation Parcoursup (étape B-1, champ `cout`).

Forme du champ : `results/donnee_etape_b/CONTRACT.md`, section 3. Trois règles, dans l'ordre :

1. **Constante légale** : établissement public et diplôme national dont le montant est fixé par
   arrêté (licence, LAS, PASS, BUT, CPGE de lycée public : 178 euros ; BTS public : pas de droits).
   Ces montants priment sur Onisep, car ils sont la règle et Onisep n'en est qu'un écho.
2. **Onisep, même intitulé** : une ligne Idéo-Actions du même lieu (UAI) et de la même famille de
   formation, dont l'intitulé correspond à celui de la fiche sans ambiguïté.
3. **Onisep, même famille** (CPGE et BTS seulement) : au moins deux lignes Onisep de la même famille
   au même UAI, toutes avec le même coût (tarif du lycée). Le rattachement le dit (`onisep_uai_famille`).

Hors de ces cas, le coût est `non_disponible`, avec la raison. Aucun montant n'est déduit d'une
autre formation, d'un autre lieu ou d'une moyenne.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from src.collect.valeur_sourcee import Referentiel

# ── montants recopiés des sources lues (voir `src.collect.valeur_sourcee`) ──────────────────
ANNEE_UNIVERSITAIRE = "2026-2027"
# Tableau ministériel 2026-2027 : « Diplôme national relevant du cycle de licence » (dont licence,
# licence professionnelle, BUT, DEUST, DFGSM...) 178 euros, taux normal ; « Élèves inscrits dans
# une classe préparatoire aux grandes écoles d'un lycée public » 178 euros.
DROITS_CYCLE_LICENCE_EUR = 178
DROITS_CPGE_LYCEE_PUBLIC_EUR = 178
# Service-Public F36520 : « Le montant de la CVEC pour la rentrée 2026-2027 est de 105 € », pour
# les étudiants en formation initiale et « En classe préparatoire aux grandes écoles (CPGE) ».
CVEC_EUR = 105
# Service-Public F36520 : « L'inscription dans un BTS public ne donne pas lieu au paiement de
# droits d'inscription. » Rien n'est dit de la CVEC en BTS : elle reste non écrite.
DROITS_BTS_PUBLIC_EUR = 0

FILIERES_CYCLE_LICENCE = frozenset({"Licence", "Licence_Las", "PASS", "BUT"})
# Diplômes du même groupe du tableau, rangés par Parcoursup en « Autre formation » : reconnus par
# leur type en clair (`type_formation`, étape A), jamais par un mot de l'intitulé.
TYPES_CYCLE_LICENCE = frozenset({"Licence professionnelle", "DEUST"})

# Familles de formation Onisep (`FOR type`) comparables à une filière Parcoursup (`fili_code`).
# « Autre formation » n'a pas de famille : seul l'intitulé peut la rattacher.
FAMILLES_ONISEP: dict[str, frozenset[str]] = {
    "BTS": frozenset({"brevet de technicien supérieur", "brevet de technicien supérieur agricole"}),
    "BUT": frozenset({"bachelor universitaire de technologie"}),
    "CPGE": frozenset({
        "prépa scientifique et technologique", "prépa littéraire et artistique",
        "prépa économique et commerciale",
    }),
    "IFSI": frozenset({"diplôme d'État du paramédical"}),
    "EFTS": frozenset({"diplôme d'État du travail social"}),
    "Licence": frozenset({"licence"}),
    "Licence_Las": frozenset({"licence"}),
    "PASS": frozenset({"licence"}),
    "Ecole d'Ingénieur": frozenset({
        "diplôme d'ingénieur", "cycle préparatoire intégré", "bachelor en sciences et ingénierie",
        "formation d'école spécialisée",
    }),
    "Ecole de Commerce": frozenset({
        "diplôme d'école de commerce visé (bac + 3)",
        "diplôme d'école de commerce visé de niveau bac + 4 ou 5", "formation d'école spécialisée",
    }),
}

# Filières dont un lycée publie un tarif commun à ses classes : seules à admettre la règle 3.
FILIERES_TARIF_ETABLISSEMENT = frozenset({"CPGE", "BTS"})

# Seuil de correspondance des intitulés : part des mots de l'intitulé le plus court présents dans
# l'autre. 0,8 rattache « BTS - Services - Services informatiques aux organisations » à « BTS
# services informatiques aux organisations option B... » et rejette « Formation d'ingénieur Bac + 5
# - Bacs généraux » face à « diplôme d'ingénieur de l'Institut... » (échantillon relu le 23/09/2026).
SEUIL_INTITULE = 0.8

# « cpge » est vidé comme « classe préparatoire » : sinon « CPGE - PCSI » (2 mots) ne rejoint pas
# « classe préparatoire ... (PCSI) 1re année » (relecture des 30 coûts, 23/09/2026).
_MOTS_VIDES = frozenset(
    "de des du la le les et en a au aux l d un une pour option parcours mention bts but licence "
    "formation diplome specialite classe preparatoire cpge annee 1re 2e cycle bac".split()
)
# La lettre d'une option (« Option A », « option B ») distingue deux formations : elle est gardée
# comme un mot (« option_b »), sans quoi une option B se rattache à la ligne Onisep de l'option A.
_OPTION = re.compile(r"\boption\s*([a-z])\b")


def _mots(texte: str | None) -> frozenset[str]:
    s = unicodedata.normalize("NFKD", (texte or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _OPTION.sub(r" option_\1 ", s)
    return frozenset(m for m in re.findall(r"[a-z0-9_]+", s) if m not in _MOTS_VIDES and len(m) > 1)


def score_intitule(a: str | None, b: str | None) -> float:
    ma, mb = _mots(a), _mots(b)
    if not ma or not mb:
        return 0.0
    oa, ob = {m for m in ma if m.startswith("option_")}, {m for m in mb if m.startswith("option_")}
    if oa and ob and not oa & ob:
        return 0.0  # deux options différentes du même diplôme ne sont pas la même formation
    return len(ma & mb) / min(len(ma), len(mb))


# ── lecture du texte libre `AF coût scolarité` ─────────────────────────────────────────────
# Deux formes couvrent les 10 468 textes renseignés du fichier du 23/09/2026 (mesure : 9 433
# « N euros en AAAA », 1 035 « de N euros jusqu'à M euros en AAAA », 0 hors grammaire).
_N = r"(\d[\d  ]*)"
_TOTAL = re.compile(rf"^{_N} euros en (\d{{4}})(?:\s*\((.*)\))?\.?$", re.S)
_FOURCHETTE = re.compile(rf"^de {_N} euros jusqu'à {_N} euros en (\d{{4}})(?:\s*\((.*)\))?\.?$", re.S)
_ANNUEL = re.compile(rf"^{_N}\s*(?:euros)?\s*par (?:ans?|année)\b")
_APPRENTISSAGE = re.compile(r"gratuite? en apprentissage", re.I)
_BOURSIERS = re.compile(r"gratuite? pour les boursiers", re.I)


def _entier(txt: str) -> int:
    return int(re.sub(r"\D", "", txt))


@dataclass(frozen=True)
class CoutOnisep:
    total_eur: int | None
    fourchette_eur: tuple[int, int] | None
    annuel_eur: int | None
    annee: str
    gratuit_apprentissage: bool
    gratuit_boursiers: bool


def lire_cout_onisep(texte: str | None) -> CoutOnisep | None:
    """Montants d'un texte `AF coût scolarité` ; None si vide ou hors grammaire (jamais deviné)."""
    t = " ".join((texte or "").split())
    if not t:
        return None
    total = fourchette = None
    if m := _TOTAL.match(t):
        total, annee, precision = _entier(m.group(1)), m.group(2), m.group(3) or ""
    elif m := _FOURCHETTE.match(t):
        fourchette = (_entier(m.group(1)), _entier(m.group(2)))
        annee, precision = m.group(3), m.group(4) or ""
    else:
        return None
    annuel = _ANNUEL.match(precision.strip())
    return CoutOnisep(
        total_eur=total,
        fourchette_eur=fourchette,
        annuel_eur=_entier(annuel.group(1)) if annuel else None,
        annee=annee,
        gratuit_apprentissage=bool(_APPRENTISSAGE.search(precision)),
        gratuit_boursiers=bool(_BOURSIERS.search(precision)),
    )


def _valeur_vide() -> dict:
    return {
        "droits_inscription_eur": None,
        "cvec_eur": None,
        "cvec_source": None,
        "scolarite_total_eur": None,
        "scolarite_annuel_eur": None,
        "fourchette_eur": None,
        "annee_tarif": None,
        "gratuit_en_apprentissage": None,
        "gratuit_boursiers": None,
        "texte_source": None,
    }


# ── attribution ────────────────────────────────────────────────────────────────────────────
class CalculCout:
    """Coût d'une fiche. `lignes_onisep` : lignes du CSV Idéo-Actions (dict par colonne)."""

    COL_UAI = "ENS code UAI"
    COL_TYPE = "FOR type"
    COL_INTITULE = "Formation (FOR) libellé"
    COL_COUT = "AF coût scolarité"
    COL_ID = "Action de Formation (AF) identifiant Onisep"

    def __init__(self, lignes_onisep: list[dict], referentiel: Referentiel) -> None:
        self.ref = referentiel
        self.par_uai: dict[str, list[dict]] = defaultdict(list)
        for ligne in lignes_onisep:
            self.par_uai[(ligne.get(self.COL_UAI) or "").strip()].append(ligne)

    # règle 1
    def _constante(self, fiche: dict) -> dict | None:
        if fiche.get("statut") != "Public":
            return None
        fili = fiche.get("fili_code")
        valeur = _valeur_vide() | {"annee_tarif": ANNEE_UNIVERSITAIRE}
        if fili in FILIERES_CYCLE_LICENCE or fiche.get("type_formation") in TYPES_CYCLE_LICENCE:
            valeur |= {"droits_inscription_eur": DROITS_CYCLE_LICENCE_EUR, "cvec_eur": CVEC_EUR,
                       "cvec_source": "service_public_f36520"}
            source = "tableau_droits_2026_2027"
        elif fili == "CPGE":
            valeur |= {"droits_inscription_eur": DROITS_CPGE_LYCEE_PUBLIC_EUR, "cvec_eur": CVEC_EUR,
                       "cvec_source": "service_public_f36520"}
            source = "tableau_droits_2026_2027"
        elif fili == "BTS":
            valeur |= {"droits_inscription_eur": DROITS_BTS_PUBLIC_EUR}
            source = "service_public_f36520"
        else:
            return None
        return self.ref.disponible(valeur, source, ANNEE_UNIVERSITAIRE, "constante_type_statut")

    def _depuis_onisep(self, ligne: dict, rattachement: str) -> dict:
        texte = " ".join((ligne.get(self.COL_COUT) or "").split())
        lu = lire_cout_onisep(texte)
        if lu is None:
            return self.ref.non_disponible(
                "l'Onisep ne publie pas de coût lisible pour cette formation",
                "onisep_ideo_actions_es", rattachement=rattachement,
            )
        valeur = _valeur_vide() | {
            "scolarite_total_eur": lu.total_eur,
            "scolarite_annuel_eur": lu.annuel_eur,
            "fourchette_eur": list(lu.fourchette_eur) if lu.fourchette_eur else None,
            "annee_tarif": lu.annee,
            "gratuit_en_apprentissage": True if lu.gratuit_apprentissage else None,
            "gratuit_boursiers": True if lu.gratuit_boursiers else None,
            "texte_source": texte,
            "onisep_action": ligne.get(self.COL_ID),
            "onisep_intitule": ligne.get(self.COL_INTITULE),
        }
        return self.ref.disponible(valeur, "onisep_ideo_actions_es", lu.annee, rattachement)

    def calculer(self, fiche: dict) -> dict:
        constante = self._constante(fiche)
        if constante:
            return constante

        lignes = self.par_uai.get((fiche.get("cod_uai") or "").strip(), [])
        if not lignes:
            return self.ref.non_disponible(
                "aucune formation de ce lieu d'enseignement dans le jeu Onisep",
                "onisep_ideo_actions_es", rattachement="onisep_uai",
            )
        famille = FAMILLES_ONISEP.get(fiche.get("fili_code"))
        candidates = [x for x in lignes if famille is None or x.get(self.COL_TYPE) in famille]

        # règle 2 : même intitulé
        intitule = " ".join(
            x for x in (fiche.get("nom"), fiche.get("intitule_officiel"), fiche.get("filiere_detaillee")) if x
        )
        notes = [(score_intitule(intitule, x.get(self.COL_INTITULE)), x) for x in candidates]
        meilleur = max((s for s, _ in notes), default=0.0)
        if meilleur >= SEUIL_INTITULE:
            retenues = [x for s, x in notes if s == meilleur]
            textes = {" ".join((x.get(self.COL_COUT) or "").split()) for x in retenues}
            if len(textes) == 1:
                return self._depuis_onisep(retenues[0], "onisep_uai_intitule")
            return self.ref.non_disponible(
                "plusieurs formations Onisep de même intitulé à ce lieu, avec des coûts différents",
                "onisep_ideo_actions_es", rattachement="onisep_uai_intitule",
            )

        # règle 3 : même famille, coût unanime (aucune ligne de la famille sans coût), seulement là où
        # un lycée publie un tarif commun à ses classes (CPGE, BTS) et sur au moins deux lignes. Ailleurs,
        # la « famille » est une autre formation : le 23/09/2026, elle donnait à un IFSI le coût du
        # diplôme de puéricultrice et à un bachelor celui du diplôme d'ingénieur de l'école.
        if fiche.get("fili_code") in FILIERES_TARIF_ETABLISSEMENT and len(candidates) >= 2:
            textes = {" ".join((x.get(self.COL_COUT) or "").split()) for x in candidates}
            if len(textes) == 1 and "" not in textes:
                return self._depuis_onisep(candidates[0], "onisep_uai_famille")
            if len(textes - {""}) > 1:
                raison = "coûts différents selon les formations de ce type à ce lieu (Onisep)"
            else:
                raison = "l'Onisep ne publie pas de coût pour les formations de ce type à ce lieu"
            return self.ref.non_disponible(raison, "onisep_ideo_actions_es", rattachement="onisep_uai_famille")

        if famille is not None and candidates and not any(x.get(self.COL_COUT) for x in candidates):
            return self.ref.non_disponible(
                "l'Onisep ne publie pas de coût pour les formations de ce type à ce lieu",
                "onisep_ideo_actions_es", rattachement="onisep_uai_famille",
            )
        return self.ref.non_disponible(
            "aucune formation Onisep de ce lieu ne correspond à cet intitulé",
            "onisep_ideo_actions_es", rattachement="onisep_uai_intitule",
        )
