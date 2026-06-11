"""Garde-fou helpfulness DÉTERMINISTE : cohérence géographique (J3, 2026-06-11, NARROW).

Quand une question cible une ville/région explicite et qu'AUCUNE source récupérée ne
couvre cette zone (ni la ville, ni sa région), refuser proprement avec relais plutôt
que de proposer une alternative hors-zone (motif Papeete-pour-Nantes).

CONSERVATEUR PAR CONSTRUCTION (spec Matteo, option B) : on ne tire QUE sur l'out-of-zone
CLAIR. Au moindre doute de résolution (ville hors table, homonyme), on NE TIRE PAS
(retour None) -> comportement RÈGLE 8 / pipeline standard. Précisément, on ne tire que si :
  1. la zone cible se résout avec certitude (table, hors homonymes), ET
  2. aucune source ne couvre la zone (ni même ville, ni même région), ET
  3. au moins une source a une géo IDENTIFIABLE qui la place HORS de la zone (preuve
     positive d'out-of-zone). Si toutes les sources sont géo-inconnues -> doute -> pas de tir.

Remplace le prompt-only RÈGLE 9 (reverté : un prédicat déterministe sur champ region
nullable n'est pas un travail de prompt). La table résout AUSSI les sources à region=None
(trou DOM-TOM corpus), donc Papeete redevient résoluble côté source sans attendre le fix data.
"""
from __future__ import annotations

import re
import unicodedata


def _norm(s) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


# Table ville -> région normalisée (métropole + DOM-TOM). NARROW : couvre les villes
# courantes d'orientation + capitales régionales. Une ville absente = NON résolue =
# on ne tire pas (conservateur). Régions en forme normalisée (sans accent/tiret).
_AURA = "auvergne rhone alpes"
_BFC = "bourgogne franche comte"
_BRE = "bretagne"
_CVL = "centre val de loire"
_COR = "corse"
_GES = "grand est"
_HDF = "hauts de france"
_IDF = "ile de france"
_NOR = "normandie"
_NAQ = "nouvelle aquitaine"
_OCC = "occitanie"
_PDL = "pays de la loire"
_PACA = "provence alpes cote d azur"

REGION_BY_CITY: dict[str, str] = {
    # Auvergne-Rhône-Alpes
    "lyon": _AURA, "villeurbanne": _AURA, "grenoble": _AURA, "annecy": _AURA,
    "saint etienne": _AURA, "clermont ferrand": _AURA, "chambery": _AURA,
    "valence": _AURA, "bourg en bresse": _AURA, "roanne": _AURA, "vienne": _AURA,
    # Bourgogne-Franche-Comté
    "dijon": _BFC, "besancon": _BFC, "belfort": _BFC, "chalon sur saone": _BFC,
    "nevers": _BFC, "auxerre": _BFC, "macon": _BFC,
    # Bretagne
    "rennes": _BRE, "brest": _BRE, "quimper": _BRE, "lorient": _BRE, "vannes": _BRE,
    "saint brieuc": _BRE, "lannion": _BRE,
    # Centre-Val de Loire
    "orleans": _CVL, "tours": _CVL, "bourges": _CVL, "blois": _CVL, "chartres": _CVL,
    "chateauroux": _CVL,
    # Corse
    "ajaccio": _COR, "bastia": _COR, "corte": _COR,
    # Grand Est
    "strasbourg": _GES, "reims": _GES, "metz": _GES, "nancy": _GES, "mulhouse": _GES,
    "troyes": _GES, "colmar": _GES, "epinal": _GES, "charleville mezieres": _GES,
    # Hauts-de-France
    "lille": _HDF, "amiens": _HDF, "roubaix": _HDF, "tourcoing": _HDF, "valenciennes": _HDF,
    "douai": _HDF, "arras": _HDF, "compiegne": _HDF, "beauvais": _HDF, "dunkerque": _HDF,
    # Île-de-France
    "paris": _IDF, "versailles": _IDF, "nanterre": _IDF, "creteil": _IDF, "cergy": _IDF,
    "evry": _IDF, "orsay": _IDF, "palaiseau": _IDF, "marne la vallee": _IDF,
    "saint quentin en yvelines": _IDF,
    # Normandie
    "caen": _NOR, "rouen": _NOR, "le havre": _NOR, "cherbourg": _NOR, "evreux": _NOR,
    "alencon": _NOR,
    # Nouvelle-Aquitaine
    "bordeaux": _NAQ, "limoges": _NAQ, "poitiers": _NAQ, "pau": _NAQ, "la rochelle": _NAQ,
    "bayonne": _NAQ, "angouleme": _NAQ, "niort": _NAQ, "agen": _NAQ, "perigueux": _NAQ,
    # Occitanie
    "toulouse": _OCC, "montpellier": _OCC, "nimes": _OCC, "perpignan": _OCC, "albi": _OCC,
    "carcassonne": _OCC, "tarbes": _OCC, "beziers": _OCC, "rodez": _OCC,
    # Pays de la Loire
    "nantes": _PDL, "angers": _PDL, "le mans": _PDL, "la roche sur yon": _PDL,
    "laval": _PDL, "saint nazaire": _PDL, "cholet": _PDL,
    # PACA
    "marseille": _PACA, "nice": _PACA, "toulon": _PACA, "aix en provence": _PACA,
    "avignon": _PACA, "cannes": _PACA, "gap": _PACA, "antibes": _PACA,
    # DOM-TOM (le trou corpus region=None — résolu ici)
    "papeete": "polynesie francaise", "noumea": "nouvelle caledonie",
    "fort de france": "martinique", "pointe a pitre": "guadeloupe",
    "basse terre": "guadeloupe", "cayenne": "guyane", "mamoudzou": "mayotte",
    "saint pierre": "la reunion",  # Saint-Pierre (Réunion) — distinct de St-Pierre-et-Miquelon (rare)
}

# Régions nommées directement dans une question ("en Bretagne", "en Occitanie")
REGION_NAMES: dict[str, str] = {
    "auvergne rhone alpes": _AURA, "auvergne": _AURA, "rhone alpes": _AURA,
    "bourgogne franche comte": _BFC, "bourgogne": _BFC, "franche comte": _BFC,
    "bretagne": _BRE, "centre val de loire": _CVL, "corse": _COR, "grand est": _GES,
    "alsace": _GES, "lorraine": _GES, "champagne ardenne": _GES,
    "hauts de france": _HDF, "nord pas de calais": _HDF, "picardie": _HDF,
    "ile de france": _IDF, "normandie": _NOR, "nouvelle aquitaine": _NAQ,
    "aquitaine": _NAQ, "limousin": _NAQ, "poitou charentes": _NAQ,
    "occitanie": _OCC, "languedoc roussillon": _OCC, "midi pyrenees": _OCC,
    "pays de la loire": _PDL, "provence alpes cote d azur": _PACA, "paca": _PACA,
    "polynesie": "polynesie francaise", "nouvelle caledonie": "nouvelle caledonie",
    "martinique": "martinique", "guadeloupe": "guadeloupe", "guyane": "guyane",
    "reunion": "la reunion", "mayotte": "mayotte",
}

# Homonymes / villes à NE JAMAIS résoudre (incertitude de zone) -> jamais de tir.
AMBIGUOUS_CITIES: set[str] = {
    "saint denis",   # Seine-Saint-Denis (IDF) vs Saint-Denis (Réunion)
    "saint paul",    # multiples
    "saint louis",   # Alsace vs Réunion
    "saint pierre",  # Réunion vs St-Pierre-et-Miquelon vs autres — prudence
}
# (saint pierre retiré de REGION_BY_CITY effectif via ce set : voir _resolve_city)


REFUSAL_TEMPLATE = (
    "Je n'ai pas de formation à {zone} dans mes sources. "
    "Pour une recherche ciblée sur {zone}, le mieux est de consulter directement "
    "[Parcoursup](https://www.parcoursup.fr/), l'ONISEP ou le CIO le plus proche."
)


def _resolve_city(city_norm: str) -> str | None:
    """Région normalisée d'une ville, ou None si inconnue/ambiguë (conservateur)."""
    if not city_norm or city_norm in AMBIGUOUS_CITIES:
        return None
    return REGION_BY_CITY.get(city_norm)


def extract_target_zone(question: str) -> tuple[str | None, str | None]:
    """(ville_affichage, region_norm) ciblée par la question, sinon (None, None).

    Conservateur : si la question contient des villes de régions DIFFÉRENTES
    (comparaison multi-zones) ou une ville ambiguë -> (None, None), pas de tir.
    """
    qn = _norm(question)
    # 1) région nommée directement (prioritaire, ex "en Bretagne")
    region_hit = None
    for name, reg in REGION_NAMES.items():
        if re.search(r"\b" + re.escape(name) + r"\b", qn):
            if region_hit and region_hit != reg:
                return (None, None)  # 2 régions nommées -> multi-zone
            region_hit = reg
    # 2) villes connues présentes (token-boundary)
    found_cities: list[str] = []
    for city in REGION_BY_CITY:
        if re.search(r"\b" + re.escape(city) + r"\b", qn):
            found_cities.append(city)
    # ville ambiguë présente -> abstention
    for amb in AMBIGUOUS_CITIES:
        if re.search(r"\b" + re.escape(amb) + r"\b", qn):
            return (None, None)
    # garder la plus longue match si une ville en contient une autre (ex "bourg en bresse")
    found_cities = [c for c in found_cities
                    if not any(c != o and c in o for o in found_cities)]
    regions_of_found = {_resolve_city(c) for c in found_cities}
    regions_of_found.discard(None)
    if region_hit and not found_cities:
        return (None, region_hit)
    if len(found_cities) == 1:
        c = found_cities[0]
        reg = _resolve_city(c)
        if region_hit and reg and region_hit != reg:
            return (None, None)  # ville et région nommées incohérentes -> abstention
        return (c, reg)
    if len(found_cities) > 1:
        # plusieurs villes : multi-zone (comparaison) -> abstention
        return (None, None)
    # aucune ville, une seule région nommée
    if region_hit:
        return (None, region_hit)
    return (None, None)


def _source_zone(source: dict) -> tuple[str | None, str | None, bool]:
    """(ville_norm, region_norm, identifiable). region depuis le champ si présent,
    sinon résolue via la table (comble region=None). identifiable = ville connue
    OU region renseignée."""
    if not isinstance(source, dict):
        return (None, None, False)
    # Les sources live du pipeline sont des wrappers retrieval
    # {_sub_index, score, fiche, ...} : le contenu réel est sous `fiche`.
    # On gère les deux formes (wrapper live ET dict aplati des tests/serialize).
    fiche = source.get("fiche") if isinstance(source.get("fiche"), dict) else source
    s_city = _norm(fiche.get("ville") or fiche.get("etablissement_ville") or "")
    field_region = _norm(fiche.get("region") or "")
    region = field_region or (_resolve_city(s_city) or "")
    identifiable = bool((s_city and s_city in REGION_BY_CITY) or field_region)
    return (s_city or None, region or None, identifiable)


def geo_coherence_check(question: str, sources: list) -> str | None:
    """Texte de refus+relais si la question cible une zone qu'AUCUNE source ne couvre
    (out-of-zone clair), sinon None (comportement standard). Voir docstring module.
    """
    target_city, target_region = extract_target_zone(question)
    if not target_region:
        return None  # zone cible non résolue avec certitude -> abstention

    covers = False
    has_out_of_zone_evidence = False
    for s in sources or []:
        s_city, s_region, identifiable = _source_zone(s)
        if target_city and s_city and s_city == _norm(target_city):
            covers = True
            break
        if s_region and s_region == target_region:
            covers = True
            break
        if identifiable and (s_region and s_region != target_region):
            has_out_of_zone_evidence = True

    if covers:
        return None
    if not has_out_of_zone_evidence:
        return None  # aucune preuve positive d'out-of-zone -> doute -> abstention

    zone = (target_city or target_region or "cette zone").title()
    return REFUSAL_TEMPLATE.format(zone=zone)
