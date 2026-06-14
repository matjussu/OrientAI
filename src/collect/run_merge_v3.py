"""Runner v3 — corpus de référence v5 unifié multi-corpus (ADR-057).

Phase B.1 du plan corpus v5. Remplace `run_merge_v2.py` (deprecated) en
appliquant les ADR-054 (purge Cereq), ADR-055 (liste blanche tier 1/2/3)
et ADR-057 (corpus unifié multi-corpus avec 23 sources annexes intégrées).

## Architecture en 12 stages purs et idempotents

Chaque stage est une fonction `list[dict] → list[dict]` (ou pure helper)
testable indépendamment. Les stats par stage sont collectées dans un
dict `stage_stats` et retournées avec le résultat final pour audit.

```
Stage 1.  LOAD_PRIMARY        — charge sources principales
Stage 2.  MERGE_FUZZY         — fuzzy merger Parcoursup × ONISEP × MonMaster
Stage 3.  DEDUP               — dédup (nom_norm, etablissement_norm, ville_norm)
Stage 4.  DROP_EMPTY          — filter fiches sans aucun champ exploitable
Stage 5.  NORMALIZE           — régions / niveaux / statuts canonisés
Stage 6.  ATTACH_DEBOUCHES    — métiers ROME (existant)
Stage 7.  ATTACH_METADATA     — provenance fiche (existant)
Stage 8.  ATTACH_TRENDS       — tendances Parcoursup historiques (existant)
Stage 9.  ATTACH_INSERSUP     — chiffres InserSup spécifiques (Phase A.3)
Stage 10. APPEND_ANNEXES      — 22 corpora annexes via config tableau-driven
Stage 11. SORT_DETERMINISTIC  — sort par (domain, source, id) pour idempotence
Stage 12. WRITE_OUT           — écriture JSON UTF-8 indenté
```

## Différences avec v2 (run_merge_v2.py)

| Aspect | v2 | v3 |
|---|---|---|
| Output | `formations.json` | `formations_v5.json` |
| Cereq agrégat | activé | **purgé** (ADR-054) |
| InserSup attach | CSV legacy | nouveau module `insersup_attach.py` |
| Corpora annexes | 0 intégré | **22 intégrés** via `domain` natif |
| Dédup | non explicite | Stage 3 dédié |
| Drop empty | non | Stage 4 dédié |
| Normalize | partiel | Stage 5 dédié |
| Idempotence | non garantie | sort déterministe Stage 11 |

## Usage

```bash
# Build par défaut → data/processed/formations_v5.json
python -m src.collect.run_merge_v3

# Override path output
ORIENTIA_MERGE_OUT_PATH=/tmp/test_v5.json python -m src.collect.run_merge_v3
```

## Conformité Phase A.4 audit

Le merger consomme les 14 corpora annexes 100% conformes (Phase A.4 vert).
Les 2 corpora avec issues (`onisep_metiers.json`, `ip_doc_doctorat.json`)
sont skippés gracieusement avec warning — Phase B doit les transformer
avant intégration finale.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from src.collect.cross_ref import attach_cross_refs
from src.collect.derive_fields import derive_type_diplome, geocode_region
from src.collect.insersup import attach_insertion as _legacy_insertion_attach  # noqa: F401
from src.collect.insersup_attach import attach_insersup_to_fiches
from src.collect.merge import (
    attach_debouches,
    attach_metadata,
    merge_all_extended,
    reclassify_social_health,
)
from src.collect.parcoursup import collect_parcoursup_fiches, collect_parcoursup_all_cascade
from src.collect.secnumedu import load_secnumedu
from src.collect.trends import attach_trends


_logger = logging.getLogger(__name__)


# ─────────────── Paths ───────────────

DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed")
DEFAULT_OUT_PATH = DATA_PROCESSED / "formations_v5.json"


# ─────────────── Configuration des corpora annexes (Stage 10) ───────────────

# Tuple : (label, path, expected_domain, source_canonique_si_overide)
# Les 14 corpora annexes 100% conformes selon Phase A.4 audit
# (`docs/CORPORA_SCHEMA_AUDIT_2026-05-07.md`).
ANNEX_CORPORA: list[tuple[str, Path, str, str | None]] = [
    ("ROME 4.0 métiers", DATA_PROCESSED / "rome_metier_corpus.json", "metier_detail", None),
    ("Métiers IDEO ONISEP", DATA_PROCESSED / "metiers_corpus.json", "metier", None),
    ("ONISEP métiers (catalogue)", DATA_PROCESSED / "onisep_metiers_corpus.json", "metier", None),
    ("DARES Métiers 2030", DATA_PROCESSED / "dares_corpus.json", "metier_prospective", None),
    ("APEC régions", DATA_PROCESSED / "apec_regions_corpus.json", "apec_region", None),
    ("CROUS corpus", DATA_PROCESSED / "crous_corpus.json", "crous", None),
    ("INSEE salaires PCS", DATA_PROCESSED / "insee_salaan_corpus.json", "insee_salaire", None),
    ("France Compétences blocs", DATA_PROCESSED / "france_comp_blocs_corpus.json", "competences_certif", None),
    ("Inserjeunes lycée pro", DATA_PROCESSED / "inserjeunes_lycee_pro_corpus.json", "formation_insertion", None),
    ("InserSup corpus agrégé", DATA_PROCESSED / "insersup_corpus.json", "insertion_pro", None),
    ("Doctorat IP MESR", DATA_PROCESSED / "doctorat_corpus.json", "insertion_pro", None),
    ("Parcours bacheliers", DATA_PROCESSED / "parcours_bacheliers_corpus.json", "parcours_bacheliers", None),
    ("DROM-COM territoires", DATA_PROCESSED / "domtom_corpus.json", "territoire_drom", None),
    ("Voie pré-bac", DATA_PROCESSED / "voie_pre_bac_corpus.json", "voie_pre_bac", None),
    ("Financement", DATA_PROCESSED / "financement_corpus.json", "financement_etudes", None),
    ("Corrections factuelles", DATA_PROCESSED / "corrections_factuelles_corpus.json", "correction_factuelle", None),
    # Vague 3.4 (2026-05-08) — Calendriers Parcoursup + MonMaster
    # Comble le gap mesuré ground-truth 50q (recall@5 catégorie calendaire = 0%).
    ("Calendrier Parcoursup/MonMaster", DATA_PROCESSED / "calendrier_corpus.json", "calendrier", None),
]


# ─────────────── Helpers normalization ───────────────


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def _norm_text(s: Any) -> str:
    """Normalisation texte pour clés de dédup : strip accents + lower + whitespace."""
    if not s:
        return ""
    return _strip_accents(str(s)).lower().strip()


# Régions canoniques France (13 métropolitaines + 5 DROM-COM).
# Vague 1.E (2026-05-08) — extension complète des variantes mesurées dans
# le corpus v5 (44 valeurs distinctes vs 18 attendues). Couvre :
# - UPPERCASE (sources `inserjeunes_lycee_pro` qui ne normalisent pas)
# - Variantes tiret/espace (Parcoursup, DARES)
# - Anciens libellés (Centre → Centre-Val de Loire post-réforme 2016)
# - DROM courts ("Réunion" sans "La")
_REGION_CANONICAL = {
    # Île-de-France
    "ile-de-france": "Île-de-France",
    "ile de france": "Île-de-France",
    # Auvergne-Rhône-Alpes
    "auvergne-rhone-alpes": "Auvergne-Rhône-Alpes",
    "auvergne rhone alpes": "Auvergne-Rhône-Alpes",
    # Occitanie
    "occitanie": "Occitanie",
    # Hauts-de-France
    "hauts-de-france": "Hauts-de-France",
    "hauts de france": "Hauts-de-France",
    # Provence-Alpes-Côte d'Azur
    "provence-alpes-cote d'azur": "Provence-Alpes-Côte d'Azur",
    "provence alpes cote d azur": "Provence-Alpes-Côte d'Azur",
    "provence alpes cote d'azur": "Provence-Alpes-Côte d'Azur",
    "paca": "Provence-Alpes-Côte d'Azur",
    # Nouvelle-Aquitaine — Vague 1.E : variante sans tiret (762 fiches Parcoursup)
    "nouvelle-aquitaine": "Nouvelle-Aquitaine",
    "nouvelle aquitaine": "Nouvelle-Aquitaine",
    # Grand Est — Vague 1.E : variante avec tiret (715 fiches Parcoursup)
    "grand est": "Grand Est",
    "grand-est": "Grand Est",
    # Bretagne
    "bretagne": "Bretagne",
    # Normandie
    "normandie": "Normandie",
    # Bourgogne-Franche-Comté
    "bourgogne-franche-comte": "Bourgogne-Franche-Comté",
    "bourgogne franche comte": "Bourgogne-Franche-Comté",
    "bourgogne-franche-comté": "Bourgogne-Franche-Comté",
    # Centre-Val de Loire — Vague 1.E : "Centre" legacy (275 fiches, pré-2016)
    "centre-val de loire": "Centre-Val de Loire",
    "centre val de loire": "Centre-Val de Loire",
    "centre": "Centre-Val de Loire",
    # Pays de la Loire — Vague 1.E : avec tirets (491 fiches)
    "pays de la loire": "Pays de la Loire",
    "pays-de-la-loire": "Pays de la Loire",
    # Corse
    "corse": "Corse",
    # DROM-COM
    "guadeloupe": "Guadeloupe",
    "martinique": "Martinique",
    "guyane": "Guyane",
    # La Réunion — Vague 1.E : "Réunion" court (123 fiches)
    "la reunion": "La Réunion",
    "la réunion": "La Réunion",
    "reunion": "La Réunion",
    "réunion": "La Réunion",
    "mayotte": "Mayotte",
}


def _canonicalize_region(region: Any) -> str | None:
    """Canonise une région vers la forme officielle (avec accents)."""
    if not region:
        return None
    norm = _norm_text(region)
    return _REGION_CANONICAL.get(norm) or (str(region).strip() if region else None)


# Mapping ville → région pour combler les régions manquantes.
# Top ~150 villes françaises principales + préfectures de département.
# Source : INSEE communes (open data), curated à la main pour les villes
# les plus fréquentes du corpus OrientIA. Les villes non-listées laissent
# `region=None` (Phase 3.x — élargir le référentiel via INSEE complet).
_VILLE_TO_REGION: dict[str, str] = {
    # Île-de-France
    **{v: "Île-de-France" for v in [
        "paris", "boulogne-billancourt", "saint-denis", "argenteuil", "montreuil",
        "nanterre", "vitry-sur-seine", "creteil", "asnieres-sur-seine", "courbevoie",
        "versailles", "colombes", "aulnay-sous-bois", "rueil-malmaison", "champigny-sur-marne",
        "saint-maur-des-fosses", "drancy", "issy-les-moulineaux", "noisy-le-grand", "levallois-perret",
        "neuilly-sur-seine", "antony", "ivry-sur-seine", "cergy", "evry", "evry-courcouronnes",
        "clichy", "pantin", "sarcelles", "le blanc-mesnil", "epinay-sur-seine",
        "sevres", "puteaux", "meudon", "malakoff", "vincennes", "fontainebleau",
        "bobigny", "le kremlin-bicetre", "villejuif", "saint-cloud", "saint-quentin-en-yvelines",
        "marne-la-vallee", "saclay", "palaiseau", "orsay",
    ]},
    # Auvergne-Rhône-Alpes
    **{v: "Auvergne-Rhône-Alpes" for v in [
        "lyon", "saint-etienne", "grenoble", "villeurbanne", "clermont-ferrand",
        "annecy", "chambery", "valence", "bourg-en-bresse", "roanne",
        "vienne", "annonay", "aurillac", "moulins", "le puy-en-velay",
        "vaulx-en-velin", "venissieux", "caluire-et-cuire", "bron", "ecully",
    ]},
    # Provence-Alpes-Côte d'Azur
    **{v: "Provence-Alpes-Côte d'Azur" for v in [
        "marseille", "nice", "toulon", "aix-en-provence", "avignon",
        "antibes", "cannes", "la seyne-sur-mer", "hyeres", "arles",
        "frejus", "grasse", "martigues", "aubagne", "salon-de-provence",
        "gap", "digne-les-bains", "draguignan",
    ]},
    # Occitanie
    **{v: "Occitanie" for v in [
        "toulouse", "montpellier", "nimes", "perpignan", "beziers", "narbonne",
        "albi", "carcassonne", "tarbes", "rodez", "auch", "cahors",
        "mende", "foix", "montauban", "alby",
    ]},
    # Hauts-de-France
    **{v: "Hauts-de-France" for v in [
        "lille", "amiens", "roubaix", "tourcoing", "dunkerque", "calais",
        "valenciennes", "boulogne-sur-mer", "arras", "saint-quentin",
        "douai", "beauvais", "compiegne", "soissons", "lens", "maubeuge",
        "wattrelos", "villeneuve-d'ascq", "cambrai", "loos",
    ]},
    # Nouvelle-Aquitaine
    **{v: "Nouvelle-Aquitaine" for v in [
        "bordeaux", "limoges", "poitiers", "pau", "la rochelle", "agen",
        "perigueux", "angouleme", "niort", "merignac", "pessac", "talence",
        "bayonne", "biarritz", "anglet", "bressuire", "dax", "tarbes",
        "saintes", "rochefort",
    ]},
    # Grand Est
    **{v: "Grand Est" for v in [
        "strasbourg", "reims", "metz", "nancy", "mulhouse", "colmar",
        "troyes", "chalons-en-champagne", "epinal", "haguenau", "schiltigheim",
        "thionville", "charleville-mezieres", "saint-dizier", "verdun",
        "bar-le-duc", "chaumont", "sedan", "vandoeuvre-les-nancy",
    ]},
    # Bretagne
    **{v: "Bretagne" for v in [
        "rennes", "brest", "quimper", "lorient", "vannes", "saint-malo",
        "saint-brieuc", "concarneau", "lannion", "fougeres", "morlaix",
        "pontivy",
    ]},
    # Pays de la Loire
    **{v: "Pays de la Loire" for v in [
        "nantes", "angers", "le mans", "saint-nazaire", "cholet", "la roche-sur-yon",
        "laval", "saumur", "rezé", "saint-herblain", "saint-sebastien-sur-loire",
    ]},
    # Normandie
    **{v: "Normandie" for v in [
        "rouen", "le havre", "caen", "cherbourg-en-cotentin", "evreux",
        "saint-lo", "alencon", "vire", "lisieux", "dieppe", "fécamp",
        "saint-etienne-du-rouvray", "mont-saint-aignan",
    ]},
    # Bourgogne-Franche-Comté
    **{v: "Bourgogne-Franche-Comté" for v in [
        "dijon", "besancon", "belfort", "chalon-sur-saone", "auxerre",
        "nevers", "macon", "sens", "vesoul", "lons-le-saunier", "montbeliard",
        "le creusot", "beaune",
    ]},
    # Centre-Val de Loire
    **{v: "Centre-Val de Loire" for v in [
        "tours", "orleans", "bourges", "blois", "chartres", "chateauroux",
        "joue-les-tours", "saint-jean-de-braye", "fleury-les-aubrais",
        "olivet", "vendome", "issoudun",
    ]},
    # Corse
    **{v: "Corse" for v in [
        "ajaccio", "bastia", "porto-vecchio", "calvi", "corte",
    ]},
    # DROM-COM
    **{v: "Guadeloupe" for v in ["pointe-a-pitre", "basse-terre", "les abymes", "baie-mahault"]},
    **{v: "Martinique" for v in ["fort-de-france", "le lamentin", "schoelcher", "saint-joseph"]},
    **{v: "Guyane" for v in ["cayenne", "saint-laurent-du-maroni", "kourou", "matoury"]},
    **{v: "La Réunion" for v in [
        "saint-denis-de-la-reunion", "saint-paul", "saint-pierre", "le tampon",
        "saint-andre", "saint-louis", "le port",
    ]},
    **{v: "Mayotte" for v in ["mamoudzou", "koungou", "dembeni"]},
}


def _infer_region_from_ville(ville: Any) -> str | None:
    """Devine la région française depuis le nom de ville (~250 villes mappées).

    Retourne None si la ville n'est pas dans le référentiel — le merger garde
    `region=None` plutôt que d'inventer.
    """
    if not ville:
        return None
    norm = _norm_text(ville)
    if not norm:
        return None
    # Match exact prioritaire
    if norm in _VILLE_TO_REGION:
        return _VILLE_TO_REGION[norm]
    # Match sans tirets (ex: "saint denis" vs "saint-denis")
    norm_no_dash = norm.replace("-", " ")
    if norm_no_dash in _VILLE_TO_REGION:
        return _VILLE_TO_REGION[norm_no_dash]
    # Match avec tirets (cas inverse)
    norm_dashed = norm.replace(" ", "-")
    if norm_dashed in _VILLE_TO_REGION:
        return _VILLE_TO_REGION[norm_dashed]
    return None


# Niveaux canoniques (cohérent avec les enums du pipeline)
_NIVEAU_CANONICAL = {
    "bac+5": "bac+5", "bac+3": "bac+3", "bac+2": "bac+2",
    "bac": "bac", "bac+8": "bac+8", "cap-bep": "cap-bep",
    # Variations communes
    "bac + 5": "bac+5", "bac +5": "bac+5", "Bac+5": "bac+5",
    "bac + 3": "bac+3", "Bac+3": "bac+3",
    "bac + 2": "bac+2", "Bac+2": "bac+2",
    "Bac": "bac", "Bac+8": "bac+8",
    "CAP": "cap-bep", "BEP": "cap-bep", "cap": "cap-bep", "bep": "cap-bep",
}


def _canonicalize_niveau(niveau: Any) -> str | None:
    if not niveau:
        return None
    raw = str(niveau).strip()
    return _NIVEAU_CANONICAL.get(raw) or _NIVEAU_CANONICAL.get(raw.lower()) or raw


# Statuts canoniques
_STATUT_CANONICAL_PUBLIC = {"public", "etablissement public", "université publique"}
_STATUT_CANONICAL_PRIVE = {"prive", "privé", "ecole privee", "etablissement privé"}


def _canonicalize_statut(statut: Any) -> str | None:
    """Normalise statut vers {Public, Privé, CFA Apprentissage, Inconnu, NULL}."""
    if not statut:
        return None
    raw = str(statut).strip()
    norm = _norm_text(raw)
    if norm in _STATUT_CANONICAL_PUBLIC:
        return "Public"
    if norm in _STATUT_CANONICAL_PRIVE:
        return "Privé"
    return raw  # garde tel quel pour les cas spéciaux (CFA Apprentissage, etc.)


# ─────────────── Vague 1.C — Tagger fiches polluantes retrieval ───────────────
#
# Audit Phase 0 v5 (politique v1, archivée) : 18 012 fiches sur 47 193 (38%)
# inadaptées au retrieval via blacklist source :
# - source=rncp (5181)         : référentiels nationaux sans école nommée
# - source=onisep (4758)       : descriptifs nationaux (0% etab+ville mesuré)
# - source=labonnealternance (4008) : offres distantes alternance
# - source=inserjeunes_cfa (4065)   : nom == etablissement, pas formation
#
# Step 11.7 (2026-05-09) — politique v2 GRANULAIRE :
# La politique blacklist était trop violente. Audit empirique 2026-05-09
# (lecture des 10 .md du dump qualitatif step 11.5) a révélé que
# `source=onisep` exclut HEC (32 fiches), CentraleSupélec (20),
# IMT Atlantique (5), INSA Rennes (5), HEI Lille, ENS Paris, etc. — toutes
# des écoles prestigieuses indexées en "descriptif national ONISEP" mais
# **avec un `etablissement` parfaitement populé** ("École CentraleSupélec",
# "INSA Rennes - filière classique"). La justification "0% etab+ville"
# était inexacte — la mesure portait sur `ville` strict, pas sur l'identité.
#
# Conséquence pré-fix : dans 4 questions du dump (B1 "HEC 11/20",
# L02 "écoles ingé cyber Bretagne", F1 "ENSEIRB vs EPITA", D5 "cyber
# Bretagne"), le système refuse de répondre faute de retrouver des
# écoles QUI SONT DANS LE CORPUS mais exclues du retrieve.
#
# Politique v2 : on garde si AU MOINS UN signal d'identité fort est
# populé — etablissement OR nom OR ville OR region. Seule LBA reste
# exclue (offres alternance distantes ≠ formations identifiables).
#
# Risque résiduel : récupère ~10-15k fiches dont quelques RNCP/CFA
# pollueurs. Mitigation amont : le RouterLLM + sub-indexes par domaine
# (steps 5-8) filtrent déjà via routing intent → sub-index ciblé.
# Mitigation aval : metadata_filter peut exclure post-rerank si besoin.

_RETRIEVAL_INELIGIBLE_SOURCES = frozenset({
    "labonnealternance",  # offres alternance distantes ≠ formation identifiable
})


def _is_retrieval_eligible(fiche: dict[str, Any]) -> bool:
    """True si la fiche est adaptée au retrieval formation+ville.

    Step 11.7 (2026-05-09) — politique granulaire.

    Critère : exclure UNIQUEMENT `source=labonnealternance` (offres
    alternance distantes, pas des formations identifiables). Pour les
    autres sources (parcoursup, monmaster, onisep, rncp, inserjeunes_cfa,
    etc.), on inclut si au moins un signal d'identité fort est populé :
    etablissement OR nom non-générique OR ville OR region.

    Cette politique remplace la blacklist source v1 (Vague 1.C originale)
    qui excluait 31 000 fiches dont les écoles prestigieuses ONISEP
    (HEC, CentraleSupélec, IMT, INSA, etc.) — bug confirmé empiriquement
    par le dump qualitatif step 11.5 (audit Matteo 2026-05-09).
    """
    source = _safe_str_field(fiche, "source")
    if source in _RETRIEVAL_INELIGIBLE_SOURCES:
        return False

    # Critère d'inclusion granulaire : au moins UN signal d'identité fort.
    etab = _safe_str_field(fiche, "etablissement")
    nom = _safe_str_field(fiche, "nom")
    ville = _safe_str_field(fiche, "ville")
    region = _safe_str_field(fiche, "region")

    # Annexes typées (domain set) — toujours éligibles (CROUS, INSEE,
    # DARES, etc. n'ont pas tous de ville/etablissement mais sont
    # légitimement retrievables sur leur domaine).
    if _safe_str_field(fiche, "domain"):
        return True

    # Au moins un signal d'identité parmi etab/nom/ville/region.
    if etab or nom or ville or region:
        return True

    return False


def _safe_str_field(fiche: dict, key: str) -> str:
    """Helper : retrieve un champ string-coerced sans accent."""
    val = fiche.get(key)
    return str(val).strip() if val else ""


# ─────────────── Vague 3.8 — URL fallback ONISEP search ───────────────
#
# Audit Phase 0 v5 : couverture URL vérifiable 33% (15 594 / 47 193 fiches).
# Sources avec URL native : parcoursup (lien_form_psup 99,8%), onisep
# (url_onisep 100%), rome_api_v4 (url 100%), onisep_metiers (url 100%).
# Sources sans URL : monmaster (0%), rncp (0%), inserjeunes_cfa, lba, dares,
# inserjeunes_lycee_pro, etc. → 31 599 fiches sans URL.
#
# Stratégie : pour les fiches sans URL native mais avec un nom identifiant,
# générer un fallback `url_fallback = https://www.onisep.fr/recherche?q=<nom>`.
# L'utilisateur peut cliquer pour faire la recherche ONISEP officielle.
# Différenciateur démo INRIA : "100% des fiches sont vérifiables côté source".
#
# Champ `url_type` exposé : "direct_*" pour URLs natives, "fallback_search"
# pour les URLs générées. Le LLM peut adapter son discours.
#
# Couverture mesurée potentielle : 33% → ~80% post-build v7.

import urllib.parse


def _build_url_fallback(fiche: dict[str, Any]) -> str | None:
    """Construit une URL ONISEP search depuis le `nom` de la fiche.

    Returns None si pas de nom ou nom trop court (<3 chars utiles).
    """
    nom = fiche.get("nom") or fiche.get("libelle_metier") or fiche.get("libelle")
    if not nom or len(str(nom).strip()) < 3:
        return None
    query = urllib.parse.quote(str(nom).strip())
    return f"https://www.onisep.fr/recherche?q={query}"


def _resolve_fiche_url(fiche: dict[str, Any]) -> tuple[str | None, str]:
    """Détermine l'URL canonique + type pour une fiche.

    Vague 3.8 — cascade de priorité :
    1. lien_form_psup (Parcoursup)         → "direct_parcoursup"
    2. url_onisep                          → "direct_onisep"
    3. url (générique : ROME, INSEE, etc.) → "direct_other"
    4. fallback ONISEP search depuis nom   → "fallback_search"
    5. None                                → "none"
    """
    if fiche.get("lien_form_psup"):
        return str(fiche["lien_form_psup"]), "direct_parcoursup"
    if fiche.get("url_onisep"):
        return str(fiche["url_onisep"]), "direct_onisep"
    if fiche.get("url"):
        return str(fiche["url"]), "direct_other"
    fb = _build_url_fallback(fiche)
    if fb:
        return fb, "fallback_search"
    return None, "none"


# ─────────────── Helpers loading ───────────────


def _load_json_if_available(path: Path, label: str) -> list[dict[str, Any]]:
    """Charge un JSON liste, gracieusement vide si absent/malformé."""
    if not path.exists():
        _logger.info("[skip] %s : %s absent", label, path)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            _logger.warning("[skip] %s : %s n'est pas une liste", label, path)
            return []
        return data
    except (json.JSONDecodeError, OSError) as e:
        _logger.warning("[skip] %s : erreur lecture %s (%s)", label, path, e)
        return []


def _load_secnumedu_if_available(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return load_secnumedu(path)
    except (OSError, ValueError) as e:
        _logger.warning("[skip] secnumedu : %s", e)
        return []


def _load_parcoursup_raw_if_available(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return collect_parcoursup_fiches(str(path))
    except (OSError, ValueError) as e:
        _logger.warning("[skip] parcoursup CSV : %s", e)
        return []


# ─────────────── Stage 1 — LOAD_PRIMARY ───────────────


def stage_load_primary() -> dict[str, list[dict[str, Any]]]:
    """Charge toutes les sources principales (formations classiques)."""
    raw_dir = DATA_RAW
    proc_dir = DATA_PROCESSED
    sources = {
        "parcoursup_raw": _load_parcoursup_raw_if_available(raw_dir / "parcoursup_2025.csv"),
        "onisep_raw": _load_json_if_available(raw_dir / "onisep_formations.json", "onisep raw"),
        "secnumedu_raw": _load_secnumedu_if_available(raw_dir / "secnumedu.json"),
        "parcoursup_extended": _load_json_if_available(proc_dir / "parcoursup_extended.json", "parcoursup_extended"),
        "onisep_extended": _load_json_if_available(proc_dir / "onisep_formations_extended.json", "onisep_extended"),
        "monmaster": _load_json_if_available(proc_dir / "monmaster_formations.json", "monmaster"),
        "rncp": _load_json_if_available(proc_dir / "rncp_certifications.json", "rncp"),
        "lba": _load_json_if_available(proc_dir / "lba_formations.json", "lba"),
        "inserjeunes_cfa": _load_json_if_available(proc_dir / "inserjeunes_cfa.json", "inserjeunes_cfa"),
    }
    # Manual labels (curated)
    manual_path = Path("data/manual_labels.json")
    if manual_path.exists():
        manual_data = json.loads(manual_path.read_text(encoding="utf-8"))
        sources["manual_labels"] = manual_data.get("entries", [])
    else:
        sources["manual_labels"] = []

    # C1 (2026-06-09) — élargissement ingestion Parcoursup : ajoute les formations
    # HORS taxonomie keyword (~6000 : BTS, D.E social/sanitaire, licences portail…)
    # avec domaine assigné par cascade. ADDITIF : inputs existants intacts, on
    # APPEND uniquement les cod_aff_form absents des sources Parcoursup déjà
    # chargées. run_merge_v3 (fuzzy-merge + dedup) gère nativement les ~1021
    # déjà couvertes par une autre source (enrichissement max-merge).
    ps_csv = raw_dir / "parcoursup_2025.csv"
    if ps_csv.exists():
        existing_codes = {
            (f.get("cod_aff_form") or "").strip()
            for f in (sources["parcoursup_raw"] + sources["parcoursup_extended"])
            if isinstance(f, dict) and (f.get("cod_aff_form") or "").strip()
        }
        new_ps = [
            f for f in collect_parcoursup_all_cascade(str(ps_csv))
            if (f.get("cod_aff_form") or "").strip() not in existing_codes
        ]
        sources["parcoursup_extended"] = sources["parcoursup_extended"] + new_ps
        _logger.info("[C1] +%d formations Parcoursup hors taxonomie ajoutées", len(new_ps))
    return sources


# ─────────────── Stage 2 — MERGE_FUZZY ───────────────


def stage_merge_fuzzy(sources: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Fuzzy merger Parcoursup × ONISEP × MonMaster × ... (réutilise merge.py).

    Important — ADR-054 : on passe `cereq=None` (purge totale). La fonction
    `attach_cereq_insertion` retourne early si cereq vide → pas d'agrégat
    Cereq dans le résultat.
    """
    return merge_all_extended(
        parcoursup=sources["parcoursup_raw"],
        onisep=sources["onisep_raw"],
        secnumedu=sources["secnumedu_raw"],
        monmaster=sources["monmaster"],
        rncp=sources["rncp"],
        cereq=None,  # ADR-054 — purge totale Cereq
        parcoursup_extended=sources["parcoursup_extended"],
        onisep_extended=sources["onisep_extended"],
        lba=sources["lba"],
        inserjeunes_cfa=sources["inserjeunes_cfa"],
        manual_labels=sources["manual_labels"],
    )


# ─────────────── Stage 3 — DEDUP ───────────────


def stage_dedup(fiches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Dédup par clé (nom_norm, etablissement_norm, ville_norm).

    Stratégie max-merge : pour les doublons, on garde la fiche la plus complète
    (celle qui a le plus de champs non-null). Sinon on garde la première vue
    (préserve l'ordre de priorité du Stage 2 : legacy > ext > monmaster > etc.).
    """
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    n_dups = 0
    for fiche in fiches:
        if not isinstance(fiche, dict):
            continue
        nom_norm = _norm_text(fiche.get("nom"))
        etab_norm = _norm_text(fiche.get("etablissement"))
        ville_norm = _norm_text(fiche.get("ville"))
        key = (nom_norm, etab_norm, ville_norm)
        # Skip dédup pour fiches sans nom (Inserjeunes CFA stat-only par cohorte,
        # records non-formation purs). Une dédup sur etab seul mergerait des
        # fiches de cohortes/années différentes — ce n'est pas le but.
        if not nom_norm:
            seen[(f"__no_nom_{id(fiche)}__", "", "")] = fiche
            continue
        if key in seen:
            n_dups += 1
            existing = seen[key]
            # Max-merge : garde la fiche avec le plus de champs non-null
            n_existing = sum(1 for v in existing.values() if v not in (None, "", [], {}))
            n_new = sum(1 for v in fiche.values() if v not in (None, "", [], {}))
            if n_new > n_existing:
                seen[key] = fiche
            continue
        seen[key] = fiche
    deduped = list(seen.values())
    stats = {"n_in": len(fiches), "n_out": len(deduped), "n_dups_removed": n_dups}
    return deduped, stats


# ─────────────── Stage 4 — DROP_EMPTY ───────────────


def stage_drop_empty(fiches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Drop les fiches sans aucun champ exploitable.

    Critère : la fiche a au moins (nom OU etablissement OU titre RNCP) ET
    au moins un autre signal informatif (niveau, ville, type_diplome, debouches).
    Pure stat-only fiches (Inserjeunes CFA agrégées) sont gardées si elles
    ont un UAI — elles seront attachées par Stage 9.
    """
    out: list[dict[str, Any]] = []
    n_dropped = 0
    for fiche in fiches:
        if not isinstance(fiche, dict):
            n_dropped += 1
            continue
        # Identité minimum : nom OU etablissement
        nom = fiche.get("nom") or ""
        etab = fiche.get("etablissement") or ""
        if not (nom or etab):
            n_dropped += 1
            continue
        # Au moins un autre champ informatif
        has_niveau = bool(fiche.get("niveau"))
        has_type = bool(fiche.get("type_diplome"))
        has_debouches = bool(fiche.get("debouches"))
        has_ville = bool(fiche.get("ville"))
        has_uai = bool(fiche.get("uai") or fiche.get("cod_uai"))
        if not (has_niveau or has_type or has_debouches or has_ville or has_uai):
            n_dropped += 1
            continue
        out.append(fiche)
    stats = {"n_in": len(fiches), "n_out": len(out), "n_dropped": n_dropped}
    return out, stats


# ─────────────── Stage 5 — NORMALIZE ───────────────


def stage_normalize(fiches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Normalise région / niveau / statut sur place. Idempotent.

    Étapes par fiche :
      1. Canonise région existante (casse, accents)
      2. Si région absente : tente d'inférer depuis `ville` (mapping ~250 villes)
      3. Canonise niveau et statut
    """
    n_region_canonized = 0
    n_region_inferred_from_ville = 0
    n_niveau_canonized = 0
    n_statut_canonized = 0
    n_retrieval_ineligible = 0
    url_type_counts = {"direct_parcoursup": 0, "direct_onisep": 0,
                       "direct_other": 0, "fallback_search": 0, "none": 0}
    for fiche in fiches:
        if not isinstance(fiche, dict):
            continue
        original_region = fiche.get("region")
        canonical_region = _canonicalize_region(original_region)
        if canonical_region != original_region and canonical_region:
            fiche["region"] = canonical_region
            n_region_canonized += 1
        # Si région toujours absente, tenter via ville
        if not fiche.get("region"):
            inferred = _infer_region_from_ville(fiche.get("ville"))
            if inferred:
                fiche["region"] = inferred
                n_region_inferred_from_ville += 1
        original_niveau = fiche.get("niveau")
        canonical_niveau = _canonicalize_niveau(original_niveau)
        if canonical_niveau != original_niveau and canonical_niveau:
            fiche["niveau"] = canonical_niveau
            n_niveau_canonized += 1
        original_statut = fiche.get("statut")
        canonical_statut = _canonicalize_statut(original_statut)
        if canonical_statut != original_statut and canonical_statut:
            fiche["statut"] = canonical_statut
            n_statut_canonized += 1
        # Vague 1.C — flag retrieval_eligible (idempotent : recalculé à chaque run)
        eligible = _is_retrieval_eligible(fiche)
        fiche["retrieval_eligible"] = eligible
        if not eligible:
            n_retrieval_ineligible += 1
        # Vague 3.8 — URL canonique + type (fallback ONISEP search si pas d'URL native).
        # Idempotent : recalculé à chaque run. Différenciateur démo INRIA
        # ("100% des fiches sont vérifiables côté source").
        url_canonical, url_type = _resolve_fiche_url(fiche)
        if url_canonical:
            fiche["url_canonical"] = url_canonical
        elif "url_canonical" in fiche:
            # Reset si fiche modifiée a perdu son URL — préserve idempotence
            del fiche["url_canonical"]
        fiche["url_type"] = url_type
        url_type_counts[url_type] = url_type_counts.get(url_type, 0) + 1
    stats = {
        "n_region_canonized": n_region_canonized,
        "n_region_inferred_from_ville": n_region_inferred_from_ville,
        "n_niveau_canonized": n_niveau_canonized,
        "n_statut_canonized": n_statut_canonized,
        "n_retrieval_ineligible": n_retrieval_ineligible,
        "url_type_distribution": url_type_counts,
    }
    return fiches, stats


# ─────────────── Stage 8 — ATTACH_TRENDS ───────────────


def stage_attach_trends(fiches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tendances Parcoursup historiques (existant)."""
    return attach_trends(fiches, {
        2023: str(DATA_RAW / "parcoursup_2023.csv"),
        2024: str(DATA_RAW / "parcoursup_2024.csv"),
        2025: str(DATA_RAW / "parcoursup_2025.csv"),
    })


# ─────────────── Stage 9 — ATTACH_INSERSUP ───────────────


def stage_attach_insersup(fiches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attache InserSup spécifique via cascade niveau 1/2/3 (Phase A.3).

    `replace_existing=True` puisque Cereq est déjà absent (Stage 2 cereq=None).
    """
    return attach_insersup_to_fiches(fiches, replace_existing=True)


# ─────────────── Stage 10 — APPEND_ANNEXES ───────────────


def stage_append_annexes(
    fiches: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Ajoute les corpora annexes (avec `domain` natif) au corpus principal.

    Chaque corpus annexe garde son schéma natif. Le merger n'aggrège PAS
    avec les fiches formations — append simple en queue. Le retrieval
    FAISS + le reranker domain-aware (ADR-049) feront le tri en runtime
    selon le `domain_hint` de la query.

    Skip gracieusement les corpora absents (stub-mode).
    """
    counts_by_domain: dict[str, int] = {}
    n_annexes_total = 0
    for label, path, expected_domain, source_override in ANNEX_CORPORA:
        if not path.exists():
            _logger.info("[append-annexes] skip %s : %s absent", label, path)
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _logger.warning("[append-annexes] skip %s : %s", label, e)
            continue
        if not isinstance(data, list):
            _logger.warning("[append-annexes] skip %s : pas une liste", label)
            continue
        for record in data:
            if not isinstance(record, dict):
                continue
            # Override source si demandé (rarement utile)
            if source_override:
                record = dict(record)
                record["source"] = source_override
            fiches.append(record)
            n_annexes_total += 1
            domain_key = record.get("domain") or expected_domain or "__no_domain__"
            counts_by_domain[domain_key] = counts_by_domain.get(domain_key, 0) + 1
    stats = {"n_annexes_total": n_annexes_total, "by_domain": counts_by_domain}
    return fiches, stats


# ─────────────── Stage 11 — SORT_DETERMINISTIC ───────────────


def stage_sort_deterministic(fiches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tri stable pour idempotence : (domain, source, id|nom|etablissement).

    Les fiches formations principales (sans `domain`) trient par
    (source, nom_norm, etablissement_norm). Les annexes trient par
    (domain, id ou nom).
    """
    def _sort_key(f: dict[str, Any]) -> tuple:
        domain = f.get("domain") or ""
        source = f.get("source") or ""
        # Pour annexes : id stable
        if f.get("id"):
            return (domain, source, str(f["id"]), "")
        # Pour formations : (nom, etab, ville)
        return (
            domain,
            source,
            _norm_text(f.get("nom")),
            _norm_text(f.get("etablissement")),
        )

    return sorted(fiches, key=_sort_key)


# ─────────────── Stage 12 — WRITE_OUT ───────────────


def stage_write_out(fiches: list[dict[str, Any]], path: Path) -> Path:
    """Écrit le corpus en JSON UTF-8 indenté (idempotent : mêmes bytes par run)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(fiches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


# ─────────────── Pipeline orchestrateur ───────────────


def run_merge_v3(
    output_path: Path | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """Orchestrateur principal — exécute les 12 stages dans l'ordre.

    Args:
        output_path: chemin override (défaut `data/processed/formations_v5.json`,
            ou env var `ORIENTIA_MERGE_OUT_PATH`).
        verbose: si True, affiche les stats par stage à stdout.

    Returns:
        Dict avec :
        - `output_path`: Path écrit
        - `n_total`: nombre de fiches finales
        - `stage_stats`: dict des stats par stage
        - `domain_distribution`: Counter par domain
        - `source_distribution`: Counter par source
    """
    if output_path is None:
        output_path = Path(os.environ.get("ORIENTIA_MERGE_OUT_PATH", str(DEFAULT_OUT_PATH)))

    stage_stats: dict[str, Any] = {}

    if verbose:
        print("=" * 70)
        print("Pipeline merge v3 — corpus de référence v5 unifié multi-corpus")
        print("ADR-054 (purge Cereq) + ADR-055 (liste blanche) + ADR-057 (v5)")
        print("=" * 70)

    # Stage 1 — LOAD_PRIMARY
    if verbose:
        print("\n[Stage 1] LOAD_PRIMARY — chargement sources principales...")
    sources = stage_load_primary()
    stage_stats["1_load_primary"] = {k: len(v) for k, v in sources.items()}
    if verbose:
        for k, n in stage_stats["1_load_primary"].items():
            print(f"  {k}: {n}")

    # Stage 2 — MERGE_FUZZY
    if verbose:
        print("\n[Stage 2] MERGE_FUZZY — fuzzy merger Parcoursup × ONISEP × MonMaster × ...")
    fiches = stage_merge_fuzzy(sources)
    stage_stats["2_merge_fuzzy"] = {"n_out": len(fiches)}
    if verbose:
        print(f"  total fiches après merge : {len(fiches)}")

    # Stage 3 — DEDUP
    if verbose:
        print("\n[Stage 3] DEDUP — dédup par (nom, etablissement, ville)...")
    fiches, stats3 = stage_dedup(fiches)
    stage_stats["3_dedup"] = stats3
    if verbose:
        print(f"  in: {stats3['n_in']} → out: {stats3['n_out']} ({stats3['n_dups_removed']} doublons)")

    # Stage 4 — DROP_EMPTY
    if verbose:
        print("\n[Stage 4] DROP_EMPTY — drop fiches sans champs exploitables...")
    fiches, stats4 = stage_drop_empty(fiches)
    stage_stats["4_drop_empty"] = stats4
    if verbose:
        print(f"  in: {stats4['n_in']} → out: {stats4['n_out']} ({stats4['n_dropped']} droppées)")

    # Stage 5 — NORMALIZE
    if verbose:
        print("\n[Stage 5] NORMALIZE — régions / niveaux / statuts...")
    fiches, stats5 = stage_normalize(fiches)
    stage_stats["5_normalize"] = stats5
    if verbose:
        for k, v in stats5.items():
            print(f"  {k}: {v}")

    # Stage 5.9 — RECLASSIFY_SOCIAL_HEALTH (fix order 2026-06-11)
    # Sort les formations TRAVAIL SOCIAL (CESF, AES, éducateurs) du domaine=sante
    # AVANT attach_debouches, sinon elles héritent des 10 débouchés médicaux J11xx.
    _n_sante_before = sum(1 for f in fiches if f.get("domaine") == "sante")
    fiches = reclassify_social_health(fiches)
    _n_sante_after = sum(1 for f in fiches if f.get("domaine") == "sante")
    stage_stats["5_9_reclassify_social"] = {
        "n_reclassified_sante_to_social": _n_sante_before - _n_sante_after,
        "n_social_total": sum(1 for f in fiches if f.get("domaine") == "social"),
    }
    if verbose:
        print(f"\n[Stage 5.9] RECLASSIFY_SOCIAL — {_n_sante_before - _n_sante_after} fiches sante→social")

    # Stage 5.95 — DERIVE_FIELDS (fix order 2026-06-14-1230, phase 1a fill)
    # Remplit type_diplome (parcoursup via fili_code structuré + monmaster->Master)
    # et region (departement->region appris du corpus + supplément overseas), en
    # PRÉCISION > RAPPEL. Vide laissé tel quel au moindre doute. Aucune région
    # fabriquée sur les fiches nationales (RNCP/ONISEP/ROME) sans departement.
    _td_before = sum(1 for f in fiches if f.get("type_diplome"))
    _rg_before = sum(1 for f in fiches if f.get("region"))
    fiches = derive_type_diplome(fiches)
    fiches = geocode_region(fiches)
    stage_stats["5_95_derive_fields"] = {
        "type_diplome_filled": sum(1 for f in fiches if f.get("type_diplome")) - _td_before,
        "region_filled": sum(1 for f in fiches if f.get("region")) - _rg_before,
    }
    if verbose:
        s = stage_stats["5_95_derive_fields"]
        print(f"\n[Stage 5.95] DERIVE_FIELDS — +{s['type_diplome_filled']} type_diplome, +{s['region_filled']} region")

    # Stage 6 — ATTACH_DEBOUCHES
    if verbose:
        print("\n[Stage 6] ATTACH_DEBOUCHES — métiers ROME...")
    fiches = attach_debouches(fiches)
    stage_stats["6_attach_debouches"] = {"n_with_debouches": sum(1 for f in fiches if f.get("debouches"))}

    # Stage 7 — ATTACH_METADATA
    if verbose:
        print("\n[Stage 7] ATTACH_METADATA — provenance fiches...")
    fiches = attach_metadata(fiches)
    stage_stats["7_attach_metadata"] = {"n_total": len(fiches)}

    # Stage 8 — ATTACH_TRENDS
    if verbose:
        print("\n[Stage 8] ATTACH_TRENDS — tendances Parcoursup historiques...")
    fiches = stage_attach_trends(fiches)
    stage_stats["8_attach_trends"] = {"n_with_trends": sum(1 for f in fiches if f.get("trends"))}

    # Stage 9 — ATTACH_INSERSUP
    if verbose:
        print("\n[Stage 9] ATTACH_INSERSUP — chiffres InserSup spécifiques (ADR-054)...")
    fiches, stats9 = stage_attach_insersup(fiches)
    stage_stats["9_attach_insersup"] = stats9
    if verbose:
        for k, v in stats9.items():
            print(f"  {k}: {v}")

    # Stage 10 — APPEND_ANNEXES
    if verbose:
        print("\n[Stage 10] APPEND_ANNEXES — 14 corpora annexes...")
    fiches, stats10 = stage_append_annexes(fiches)
    stage_stats["10_append_annexes"] = stats10
    if verbose:
        print(f"  total annexes appendées : {stats10['n_annexes_total']}")
        for d, c in sorted(stats10["by_domain"].items(), key=lambda x: -x[1]):
            print(f"    {d}: {c}")

    # Stage 10.5 — RE-NORMALIZE après APPEND_ANNEXES.
    # Vague 1.E (2026-05-08) — Stage 5 normalise les fiches principales
    # (post-merge_fuzzy) mais pas les annexes appendées Stage 10. Or les
    # annexes (notamment inserjeunes_lycee_pro = 1755 fiches UPPERCASE)
    # apportent leurs propres variantes de région. Ré-application idempotente
    # de stage_normalize sur tout le corpus pour canoniser les annexes.
    if verbose:
        print("\n[Stage 10.5] RE-NORMALIZE — canonise régions annexes...")
    fiches, stats10_5 = stage_normalize(fiches)
    stage_stats["10_5_renormalize"] = stats10_5
    if verbose:
        for k, v in stats10_5.items():
            print(f"  {k}: {v}")

    # Stage 10.7 — ATTACH_CROSS_REFS (Vague 1.D).
    # Construit les cross-références ROME ↔ formations. Les fiches RNCP avec
    # codes_rome natifs gagnent un champ `cross_refs.metiers` pointant vers
    # les fiches metier_detail (ROME 4.0). Les fiches metier_detail gagnent
    # `cross_refs.formations` listant les RNCP qui mènent à ce métier.
    # Permet au LLM de répondre "comment devenir actuaire (M1402)" en citant
    # les Masters Actuariat correspondants.
    if verbose:
        print("\n[Stage 10.7] ATTACH_CROSS_REFS — ROME ↔ formations (Vague 1.D)...")
    fiches, stats10_7 = attach_cross_refs(fiches)
    stage_stats["10_7_cross_refs"] = stats10_7
    if verbose:
        for k, v in stats10_7.items():
            print(f"  {k}: {v}")

    # Stage 11 — SORT_DETERMINISTIC
    if verbose:
        print("\n[Stage 11] SORT_DETERMINISTIC — tri stable pour idempotence...")
    fiches = stage_sort_deterministic(fiches)
    stage_stats["11_sort"] = {"n_total": len(fiches)}

    # Stage 12 — WRITE_OUT
    if verbose:
        print(f"\n[Stage 12] WRITE_OUT — {output_path}")
    written_path = stage_write_out(fiches, output_path)

    # Distributions finales pour audit
    domain_dist = Counter(f.get("domain") or "__none__" for f in fiches)
    source_dist = Counter(f.get("source") or "__none__" for f in fiches)
    n_with_insertion_pro = sum(1 for f in fiches if f.get("insertion_pro"))
    n_with_url = sum(
        1 for f in fiches
        if (isinstance(f, dict) and (
            f.get("url") or f.get("url_parcoursup") or f.get("url_onisep")
            or f.get("lien_form_psup")
        ))
    )

    if verbose:
        size_mb = written_path.stat().st_size / 1024 / 1024
        print()
        print("=" * 70)
        print(f"Corpus v5 écrit : {written_path} ({size_mb:.1f} MB)")
        print(f"Total fiches    : {len(fiches)}")
        print(f"Avec insertion_pro : {n_with_insertion_pro} ({n_with_insertion_pro/len(fiches)*100:.1f}%)")
        print(f"Avec URL          : {n_with_url} ({n_with_url/len(fiches)*100:.1f}%)")
        print(f"Distribution domain (top 10):")
        for d, c in domain_dist.most_common(10):
            print(f"  {d}: {c}")
        print("=" * 70)

    return {
        "output_path": written_path,
        "n_total": len(fiches),
        "n_with_insertion_pro": n_with_insertion_pro,
        "n_with_url": n_with_url,
        "stage_stats": stage_stats,
        "domain_distribution": dict(domain_dist),
        "source_distribution": dict(source_dist),
    }


def main() -> int:  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        run_merge_v3()
        return 0
    except Exception as e:
        _logger.exception("Pipeline merge v3 échoué : %s", e)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
