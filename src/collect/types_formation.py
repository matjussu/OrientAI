"""Type de formation dit en clair, à partir des champs officiels Parcoursup.

La filière très agrégée (`fili`) ne suffit pas à un lecteur : « Licence_Las » ne dit pas
qu'il s'agit d'une LAS, et une fiche PASS n'a de sens qu'avec son option (le taux d'accès
d'un PASS option Mathématiques n'est pas celui de l'option Sciences infirmières).

Entrées, toutes issues des jeux officiels :
- `fili` et `filiere_detaillee` (`fil_lib_voe_acc`) : jeu fr-esr-parcoursup 2025 ;
- `intitule_complet` (`nm`) : jeu fr-esr-cartographie_formations_parcoursup, année 2025,
  seul jeu ouvert qui nomme l'option d'un PASS.
Rien n'est déduit au-delà de ces libellés : une option absente reste absente.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.collect.niveau import infer_niveau

# Développé des sigles de voies de CPGE scientifiques. Non établi à l'étape A : écrit de
# mémoire, pas relu contre les arrêtés de programme ; à vérifier avant l'étape D (format).
_CPGE_VOIES = {
    "MPSI": "mathématiques, physique et sciences de l'ingénieur",
    "MP2I": "mathématiques, physique, ingénierie et informatique",
    "PCSI": "physique, chimie et sciences de l'ingénieur",
    "PTSI": "physique, technologie et sciences de l'ingénieur",
    "BCPST": "biologie, chimie, physique et sciences de la Terre",
    "TSI": "technologie et sciences industrielles",
    "TPC": "technologie, physique et chimie",
    "TB": "technologie et biologie",
}

_PASS_OPTION = re.compile(r"\(PASS\)\s*-\s*option\s+(?P<suite>.+)$", re.IGNORECASE)
_LAS_MAJEURE = re.compile(r"^Licence\s*-\s*(?:Portail\s+)?(?P<majeure>.+?)\s+-\s+Accès Santé \(LAS\)", re.IGNORECASE)


@dataclass(frozen=True)
class TypeFormation:
    libelle: str                 # « PASS (parcours d'accès spécifique santé) »
    precision: str | None = None  # « option Mathématiques », « majeure Droit », « spécialité Informatique »


def _propre(s: str | None) -> str:
    return re.sub(r"\s+", " ", s if isinstance(s, str) else "").strip(" -")


def _option_pass(intitule_complet: str) -> str | None:
    m = _PASS_OPTION.search(intitule_complet)
    if not m:
        return None
    morceaux = [_propre(p) for p in m.group("suite").split(" - ") if _propre(p)]
    option = morceaux[0]
    # Compléments (« enseignement à distance », site...) sans répéter ce que l'option dit déjà.
    complements = [p for p in morceaux[1:] if p.lower() not in option.lower()]
    dedoublonnes = list(dict.fromkeys(c.lower() for c in complements))
    garde = [next(c for c in complements if c.lower() == d) for d in dedoublonnes]
    return f"option {option}" + (f" ({', '.join(garde)})" if garde else "")


def decrire(fili: str | None, nom: str | None, intitule_complet: str | None,
            filiere_detaillee: str | None) -> TypeFormation | None:
    """Type de la formation et, s'il existe, ce qui la distingue (option, majeure, spécialité)."""
    fili = fili or ""
    nom = _propre(nom)
    complet = _propre(intitule_complet)
    detail = _propre(filiere_detaillee)

    if fili == "PASS":
        option = _option_pass(complet) or "option non précisée dans les données ouvertes"
        return TypeFormation("PASS (parcours d'accès spécifique santé)", option)
    if fili == "Licence_Las":
        m = _LAS_MAJEURE.search(complet) or _LAS_MAJEURE.search(nom)
        majeure = _propre(m.group("majeure")) if m else detail
        return TypeFormation("LAS (licence avec option accès santé)", f"majeure {majeure}" if majeure else None)
    if fili == "IFSI":
        return TypeFormation("IFSI (institut de formation en soins infirmiers), diplôme d'État d'infirmier")
    if fili == "BUT":
        return TypeFormation("BUT (bachelor universitaire de technologie)", f"spécialité {detail}" if detail else None)
    if fili == "BTS":
        return TypeFormation("BTS (brevet de technicien supérieur)", f"spécialité {detail}" if detail else None)
    if fili == "CPGE":
        voie = _CPGE_VOIES.get(detail.upper())
        precision = f"voie {detail}" + (f" ({voie})" if voie else "") if detail else None
        return TypeFormation("CPGE (classe préparatoire aux grandes écoles)", precision)
    if fili == "Ecole d'Ingénieur":
        if nom.lower().startswith("formation bac + 3"):
            return TypeFormation("Bachelor d'une école d'ingénieurs, recrutement post-bac (bac + 3)")
        return TypeFormation("Formation d'ingénieur en école d'ingénieurs, recrutement post-bac (bac + 5)")
    if fili == "Licence":
        return TypeFormation("Licence", f"mention {detail}" if detail else None)
    if fili == "Ecole de Commerce":
        return TypeFormation("École de commerce, recrutement post-bac")
    if fili == "EFTS":
        return TypeFormation("Diplôme d'État du travail social", detail or None)
    if fili == "Autre formation" and detail:
        return TypeFormation(detail)
    return None


# Niveau du diplôme visé par filière très agrégée Parcoursup. Remplace, pour ces filières,
# `infer_niveau`, qui cherche « ingénieur » ou « master » dans l'intitulé : mesuré le
# 23/09/2026, 70 licences « Sciences pour l'ingénieur », 21 LAS et 33 BTS y passaient en bac+5.
NIVEAU_PAR_FILI = {"BTS": "bac+2", "BUT": "bac+3", "Licence": "bac+3", "Licence_Las": "bac+3", "PASS": "bac+3"}
_BAC_PLUS = re.compile(r"\bbac\s*\+\s*(\d)\b", re.IGNORECASE)


def niveau_vise(fili: str | None, nom: str | None) -> tuple[str | None, str]:
    """(niveau du diplôme visé, origine) pour une formation Parcoursup.

    Ordre : niveau écrit dans l'intitulé (« Formation d'ingénieur Bac + 5 ») ; sinon niveau
    de la filière (`NIVEAU_PAR_FILI`) ; une CPGE ne délivre pas de diplôme de niveau, donc
    None ; sinon l'heuristique historique `infer_niveau`. Le premier « Bac + N » de l'intitulé
    est le niveau visé ; une condition d'accès (« réservée aux BAC +1 ») vient toujours après.
    """
    m = _BAC_PLUS.search(nom or "")
    if m:
        return f"bac+{m.group(1)}", "intitule"
    if fili in NIVEAU_PAR_FILI:
        return NIVEAU_PAR_FILI[fili], "filiere"
    if fili == "CPGE":
        return None, "cpge"
    return infer_niveau(nom or ""), "heuristique"
