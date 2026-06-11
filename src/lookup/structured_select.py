"""SELECT structuré déterministe — Chantier 2 (2026-05-03).

Pour les questions factuelles pointues sur UNE formation nommée, on bypasse
le RAG et on fait un lookup direct sur `formations.json`. Argument démo INRIA :
« les chiffres viennent toujours d'un lookup, jamais d'une génération.
Zéro hallu chiffres par construction. »

## Pipeline

1. `extract_entity_simple(question)` → `Entity(formation_name, ville, niveau)`
   via regex patterns (zero coût LLM, déterministe).
2. `lookup_formation(entity, fiches)` → fuzzy match `rapidfuzz` ≥ FUZZY_THRESHOLD.
   Sous le seuil → None → fallback RAG.
3. `extract_field(fiche, field_key)` → SELECT avec INVALID_VALUES guard.
   Si valeur invalide (None, 0, "-", "N/A") → None → fallback unifié.
4. `format_select_response(fiche, field, value)` → templater déterministe
   « Le taux d'accès Parcoursup 2025 de [formation] est [X]%. Source: [URL]. »

## Garde-fous expert

- **Seuil de confiance ≥85** : aucun SELECT à confiance basse (sinon
  hallu déterministe « le taux de la formation X est Y » alors que X
  n'est pas la vraie formation visée).
- **INVALID_VALUES guard** : champ présent mais valeur 0/N/A/None →
  fallback unifié (sinon « taux EFREI Bordeaux est 0% » bug visible démo).
- **Multi-match ambigu** : si scores ≥85 sur multiple fiches avec ex-aequo
  proches → demander précision à l'utilisateur (« Plusieurs formations
  matchent : EFREI Paris ou EFREI Bordeaux ? »).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz, process

from src.rag.fallback_response import format_unknown_response


def _strip_accents(s: str) -> str:
    """Normalisation accents pour matching robuste."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


# Seuil de confiance fuzzy match. Sous ce score, on refuse le SELECT
# pour ne pas créer une hallu déterministe (« taux de Bachelor cyber
# est X » alors que le match était sur le mauvais Bachelor cyber).
FUZZY_THRESHOLD = 85

# Si plusieurs fiches matchent ≥ FUZZY_THRESHOLD avec un écart < ce
# nombre de points, on considère le match ambigu → demande précision.
# Sprint refonte 2026-05-05 : abaissé de 5 à 2 après pré-filtrage par
# ville. Sur 55k fiches le filtrage ville réduit déjà massivement le bruit
# (top match devient correct), et l'ambiguity check ne sert plus qu'à
# distinguer les cas où plusieurs ÉCOLES distinctes (etab différent) à la
# même ville matchent bien — auquel cas on veut quand même demander précision.
# Le grouping (etab, ville) protège des fiches multi-voies de la même école.
AMBIGUITY_DELTA = 2

# Pool filter SELECT (J2 U1, 2026-06-11) — exclusion NOMMÉE des fiches
# NON-formation qui polluaient le rang-1 du fuzzy. Une fiche « Logements CROUS
# à Lyon » (texte cherchable = nom de ville seul) était scorée ~90 par WRatio
# sur toute query « [formation] [ville] » et squattait le rang-1 sur 27/48
# questions SELECT mesurées. Servir ce dominant = hallu déterministe (un taux
# d'accès servi depuis une fiche logement). Le SELECT ne sert QUE des faits de
# FORMATION nommée -> on restreint le pool de candidats aux fiches
# formation-identité. Aucun domaine FORMATION ne contient ces sous-chaînes
# (vérifié corpus 2026-06 : eco_gestion, sciences_*, droit, sante, ...).
# Extensible : si le SELECT s'étend un jour aux lookups métier/INSEE légitimes
# (post-VivaTech), retirer ICI le domaine concerné de façon explicite — pas un
# blanket silencieux.
_NONFORM_SELECT_DOMAIN_SUBSTR = ("crous", "insee", "metier", "aides")


def is_select_candidate(fiche: Any) -> bool:
    """True si la fiche est une formation nommée éligible au SELECT déterministe.

    Exclut (1) les fiches sans identité (ni `nom` ni `etablissement`) et (2) les
    fiches de domaine non-formation (crous, insee, metier, aides). cf
    `_NONFORM_SELECT_DOMAIN_SUBSTR`.
    """
    if not isinstance(fiche, dict):
        return False
    if not (fiche.get("nom") or fiche.get("etablissement")):
        return False
    dom = str(fiche.get("domain") or fiche.get("domaine") or "").lower()
    if any(sub in dom for sub in _NONFORM_SELECT_DOMAIN_SUBSTR):
        return False
    return True


# Suffixe de site d'un établissement multi-sites (« IUT Lyon1 Site de
# Villeurbanne Doua » -> racine « iut lyon1 »). Regroupe les variantes de SITE
# d'un même établissement pour ne pas les compter comme établissements distincts
# (sinon faux ambigu sur fact-001 : BUT Info Doua vs Bourg = même formation).
_SITE_SUFFIX_RE = re.compile(r"\s*[-,]?\s*site\s+d[e'].*$", re.IGNORECASE)


def _etab_root(etab: str | None) -> str:
    return _SITE_SUFFIX_RE.sub("", (etab or "").strip().lower()).strip()


def _norm_nom(nom: str | None) -> str:
    return (nom or "").strip().lower()


# Critique expert #4b (2026-05-03) — mots discriminateurs métier qui DOIVENT
# matcher dans la fiche cible si présents dans la query, sinon match suspect.
# Ex : « prépa commerciales Henri IV » ne doit PAS matcher la prépa A/L
# (lettres) d'Henri IV juste parce que « prépa » + « Henri IV » overlap —
# « commerciales » est un discriminateur qui doit aussi être dans la fiche.
# Liste conservatrice (pas exhaustive) — couvre les cas critiques observés
# en prépa CPGE, séries L/ES/S, options de master, spécialités d'ingénieur.
_DISCRIMINATORS = frozenset({
    # Voies CPGE
    "commercial", "commerciale", "commerciales", "ec", "ecg", "ect", "ecs", "ece",
    "scientifique", "scientifiques", "mp", "pc", "psi", "mpsi", "pcsi", "bcpst", "tpc",
    "litteraire", "litteraires", "littéraire", "littéraires", "al", "a/l", "bl", "b/l",
    "khagne", "hypokhagne",
    # Spécialités ingé / domaines majeurs
    "informatique", "info", "cybersecurite", "cybersécurité", "cyber", "data",
    "mecanique", "mécanique", "civil", "electronique", "électronique", "biotech",
    "biologique", "chimie", "chimique", "energie", "énergie", "telecoms", "télécoms",
    "reseau", "réseau", "reseaux", "réseaux", "aero", "aéro", "aerospatial", "aérospatial",
    # Options de droit
    "international", "internationale", "internationales", "europeen", "européen",
    "europeenne", "européenne", "affaires", "penal", "pénal", "fiscal", "civil",
    "social", "notarial", "constitutionnel", "administratif",
    # Spécialités santé / paramédical
    "kine", "kiné", "kinesitherapie", "kinésithérapie", "infirmier", "infirmiere",
    "infirmière", "psychologue", "orthophonie", "orthophoniste", "podologue",
})


def _query_discriminators_match_fiche(query_tokens: list[str], fiche_text: str) -> bool:
    """Garde anti-faux-positifs : si la query contient un mot discriminateur
    métier (commercial, MP, kiné, international, etc.), ce mot DOIT être
    présent dans le texte de la fiche.

    Match accepté si :
      - exact match d'un mot fiche, OU
      - préfixe match (discriminator est préfixe d'un mot fiche, ou inverse)
        ex : « cyber » matche « cybersécurité » via préfixe.

    Sinon le fuzzy match est trompeur (mauvais sous-domaine matché par
    overlap accidentel — ex « prépa commerciales » → « prépa A/L »).
    """
    query_discriminators = {t.lower() for t in query_tokens if t.lower() in _DISCRIMINATORS}
    if not query_discriminators:
        return True
    fiche_words = set(re.findall(r"\w+", fiche_text.lower()))

    def _matches(disc: str) -> bool:
        if disc in fiche_words:
            return True
        # Préfixe / inclusion (cyber ↔ cybersécurité, kiné ↔ kinésithérapie)
        for w in fiche_words:
            if len(disc) >= 3 and (w.startswith(disc) or disc.startswith(w)):
                return True
        return False

    return all(_matches(d) for d in query_discriminators)

# Valeurs considérées comme invalides — déclenchent le fallback unifié.
# Le set est conservatif : 0 et -1 sont marqueurs Parcoursup pour
# « capacité fermée » ou « non renseigné », pas une vraie valeur.
INVALID_VALUES: frozenset = frozenset({None, "", "N/A", "n/a", "-", "non renseigné", "non renseignee", 0, -1, 0.0})


@dataclass(frozen=True)
class Entity:
    """Entité extraite d'une question factual_pointed.

    Au moins UNE des trois (formation_name, ville, niveau) doit être
    non-None pour avoir une chance de matcher. La combinaison améliore
    le fuzzy score (e.g. "EFREI Bordeaux" > juste "EFREI").
    """

    formation_name: str | None = None
    ville: str | None = None
    niveau: str | None = None

    def is_empty(self) -> bool:
        return not (self.formation_name or self.ville or self.niveau)

    def to_query_string(self) -> str:
        """Concatène les composantes pour le fuzzy match (lowercase, trim)."""
        parts = [p for p in (self.formation_name, self.ville, self.niveau) if p]
        return " ".join(p.strip().lower() for p in parts)


@dataclass(frozen=True)
class SelectResult:
    """Résultat d'un SELECT — soit un fait formaté, soit un fallback."""

    text: str
    via_select: bool       # True = SELECT déterministe, False = fallback unifié
    matched_fiche_id: str | None = None
    fuzzy_score: float | None = None
    field_key: str | None = None  # ex: "taux_acces_parcoursup_2025"
    reason: str | None = None     # 'select_no_entity' | 'select_no_match' | 'select_invalid_value' | 'select_ambiguous'


# ──────────────────────── Field key detection ────────────────────────

# Mapping pattern question → field key dans la fiche
SELECT_FIELD_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    # (pattern, field_key, label_humain)
    (
        re.compile(r"\btaux\s+d['e]\s*acces", re.IGNORECASE),
        "taux_acces_parcoursup_2025",
        "taux d'accès Parcoursup 2025",
    ),
    (
        re.compile(r"\b(?:nombre\s+de\s+)?places?\s+(?:disponibles?\s+)?(?:à|en|dans|de|d['e]\s*)", re.IGNORECASE),
        "nombre_places",
        "nombre de places",
    ),
    (
        re.compile(r"\bcombien\s+de\s+places?", re.IGNORECASE),
        "nombre_places",
        "nombre de places",
    ),
    (
        re.compile(r"\bselectivit", re.IGNORECASE),
        "taux_acces_parcoursup_2025",
        "sélectivité (taux d'accès Parcoursup 2025)",
    ),
    (
        re.compile(r"\bsalaire\s+(?:median|moyen|annuel|net|brut|de\s+(?:sortie|debut|embauche))", re.IGNORECASE),
        "insertion_pro.salaire_median_embauche",
        "salaire médian à l'embauche",
    ),
    # Critique expert #4a (2026-05-03) — « Quel salaire après LEA ? » sans
    # qualificatif (médian/moyen). Pattern complémentaire moins strict.
    (
        re.compile(r"\b(?:quel\s+)?salaire\s+(?:apres|post|en\s+sortie\s+de|au\s+sortir)", re.IGNORECASE),
        "insertion_pro.salaire_median_embauche",
        "salaire à la sortie",
    ),
    (
        re.compile(r"\bcombien\s+gagne", re.IGNORECASE),
        "insertion_pro.salaire_median_embauche",
        "rémunération",
    ),
    (
        re.compile(r"\btaux\s+d['e]\s*emploi\s+(?:a|au\s+bout\s+de\s+)?\s*(?:3\s+ans?|3ans?)", re.IGNORECASE),
        "insertion_pro.taux_emploi_3ans",
        "taux d'emploi à 3 ans",
    ),
    (
        re.compile(r"\btaux\s+d['e]\s*emploi\s+(?:a|au\s+bout\s+de\s+)?\s*(?:6\s+ans?|6ans?)", re.IGNORECASE),
        "insertion_pro.taux_emploi_6ans",
        "taux d'emploi à 6 ans",
    ),
    (
        re.compile(r"\btaux\s+(?:de\s+)?cdi", re.IGNORECASE),
        "insertion_pro.taux_cdi",
        "taux de CDI à l'embauche",
    ),
    # Critique expert #4a (2026-05-03) — frais / coût / scolarité.
    # Champ rarement présent dans formations.json (~0.7% sample) → SELECT
    # tombera en fallback unifié pour la majorité, c'est ce qu'on veut :
    # mieux qu'une hallu RAG (« 8000 €/an » inventé pour une fac publique).
    (
        re.compile(r"\bcombien\s+(?:ca\s+|cela\s+)?co[uû]te", re.IGNORECASE),
        "frais_annuels",
        "frais de scolarité",
    ),
    (
        re.compile(r"\b(?:co[uû]t|frais|tarif)\s+(?:de\s+(?:la\s+|l['e]\s*))?(?:formation|scolarit|inscription|annuel)", re.IGNORECASE),
        "frais_annuels",
        "frais de scolarité",
    ),
    (
        re.compile(r"\b(?:quel|quels)\s+(?:sont\s+(?:les\s+)?)?frais", re.IGNORECASE),
        "frais_annuels",
        "frais de scolarité",
    ),
    # Durée de formation (champ `duree` présent dans ~2% des fiches).
    # Matche « durée du BUT », « durée de la formation », « combien d'années dure ».
    (
        re.compile(r"\bdur[ée]e\s+(?:de\s+(?:la\s+|l['e]\s*)|du\s+|des\s+|d['e]\s*)?(?:formation|cursus|etudes?|but|bts|licence|master|bachelor|prepa|prépa)", re.IGNORECASE),
        "duree",
        "durée de la formation",
    ),
    (
        re.compile(r"\bcombien\s+(?:de\s+|d['e]\s*)?(?:temps|annees?|ans)\s+dure", re.IGNORECASE),
        "duree",
        "durée de la formation",
    ),
    (
        re.compile(r"\bcombien\s+(?:de\s+|d['e]\s*)annees?\b", re.IGNORECASE),
        "duree",
        "durée de la formation",
    ),
    # Sprint refonte 2026-05-05 — patterns manquants identifiés par forensic
    # Q14 ("taux insertion 18 mois Master Droit Intl Assas") qui ne matchait
    # AUCUN pattern existant. Ajout pour couvrir les questions factuelles
    # pointues sur l'insertion et la volumétrie Parcoursup.
    #
    # Insertion à N mois — schéma CFA Inserjeunes (taux_emploi_6m/12m/18m/24m)
    # et générique. Distingue de "taux d'emploi à 3/6 ans" (Céreq) déjà couverts.
    (
        re.compile(r"\btaux\s+(?:d['e]\s*)?(?:insertion|emploi)\s+(?:a|au\s+bout\s+de\s+)?\s*6\s+mois?", re.IGNORECASE),
        "insertion_pro.taux_emploi_6m",
        "taux d'insertion à 6 mois",
    ),
    (
        re.compile(r"\btaux\s+(?:d['e]\s*)?(?:insertion|emploi)\s+(?:a|au\s+bout\s+de\s+)?\s*12\s+mois?", re.IGNORECASE),
        "insertion_pro.taux_emploi_12m",
        "taux d'insertion à 12 mois",
    ),
    (
        re.compile(r"\btaux\s+(?:d['e]\s*)?(?:insertion|emploi)\s+(?:a|au\s+bout\s+de\s+)?\s*18\s+mois?", re.IGNORECASE),
        "insertion_pro.taux_emploi_18m",
        "taux d'insertion à 18 mois",
    ),
    (
        re.compile(r"\btaux\s+(?:d['e]\s*)?(?:insertion|emploi)\s+(?:a|au\s+bout\s+de\s+)?\s*24\s+mois?", re.IGNORECASE),
        "insertion_pro.taux_emploi_24m",
        "taux d'insertion à 24 mois",
    ),
    # Volumétrie Parcoursup — voeux et candidats, exposés dans
    # admission.volumes.* sur les fiches Parcoursup (10 536 fiches sur 55 606).
    (
        re.compile(r"\bcombien\s+(?:de\s+|d['e]\s*)?(?:vœux|voeux|candidats?\s+ont\s+postule|candidatures?)", re.IGNORECASE),
        "admission.volumes.voeux_totaux",
        "nombre de vœux Parcoursup",
    ),
    (
        re.compile(r"\bnombre\s+(?:de\s+|d['e]\s*)?(?:vœux|voeux|candidatures?)", re.IGNORECASE),
        "admission.volumes.voeux_totaux",
        "nombre de vœux Parcoursup",
    ),
]


def detect_field_key(question: str) -> tuple[str, str] | None:
    """Détecte quel champ est demandé.

    Strip accents avant matching pour robustesse (sélectivité → selectivite,
    accès → acces, etc. — les regex sont écrites sans accents).

    Returns:
        Tuple (field_key, label_humain) ou None si aucun pattern ne match.
    """
    norm = _strip_accents(question)
    for pattern, field_key, label in SELECT_FIELD_PATTERNS:
        if pattern.search(norm):
            return field_key, label
    return None


# ──────────────────────── Entity extraction (regex-based, no LLM) ────────────────────────

# Mots-outils à filtrer pour ne pas polluer le fuzzy match.
# Inclut les mots-clés de field detection (taux, places, salaire, etc.) pour
# éviter qu'ils polluent le score de match contre les noms de formations.
_STOPWORDS = frozenset({
    # articles, prépositions, pronoms basiques
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "à", "a",
    "en", "et", "ou", "est", "sont", "que", "qui", "quoi", "comment",
    "pour", "par", "sur", "dans", "avec", "sans", "quel", "quelle",
    "quels", "quelles", "combien", "année", "annees", "ans", "ce", "cette",
    "ces", "ma", "mon", "mes", "ta", "ton", "tes", "sa", "son", "ses",
    "il", "elle", "on", "nous", "vous", "ils", "elles", "je", "tu",
    "moi", "toi", "lui", "leur", "leurs", "y", "se", "ne", "pas", "plus",
    "moins", "très", "tres", "trop", "bien", "mieux", "mal", "fort",
    "ai", "ai-je", "as-tu", "a-t-il", "avons", "avez", "ont",
    "suis", "es", "est-ce", "sommes", "êtes", "etes",
    "veux", "voulez", "voudrais", "souhaite", "souhaitez",
    "savoir", "connaitre", "connaître", "voir", "trouver",
    "formation", "formations", "ecole", "ecoles", "université", "universite",
    "fac", "diplome", "cursus",
    # mots-clés de field detection (à filtrer pour ne pas polluer fuzzy)
    "taux", "accès", "acces", "selectivite", "sélectivité", "selectivité",
    "places", "place", "candidats", "candidatures", "voeux", "vœux", "inscrits",
    "salaire", "salaires", "rémunération", "remuneration", "gagne", "gagner",
    "frais", "coût", "cout", "tarif", "cotisation", "scolarité", "scolarite",
    "emploi", "insertion", "cdi", "réussite", "reussite", "admission",
    "median", "médian", "moyen", "moyenne", "annuel", "annuelle", "net",
    "brut",
    # Sources / plateformes — Sprint refonte 2026-05-05 (forensic S1 :
    # "Parcoursup" et "2025" parasitent l'extract_entity → top match
    # devient une fiche RNCP générique "Cybersécurité")
    "parcoursup", "onisep", "rncp", "monmaster", "lba",
    "officiel", "officielle", "fiche", "fiches",
    "postule", "postuler", "postulé", "postulent",
    "mois", "mois?",
    # Prépositions de causalité/temps qui parasitent ("après EPITA" → match
    # ECAM Lyon car "après" garde puis fuzzy bouffe "EPITA" sur des bouts)
    "apres", "après", "post", "depuis", "avant", "pendant", "durant",
    "sortie", "sortir", "fin",
})

# Liste des villes courantes (réutilise la liste intent.py)
from src.rag.intent import _FRENCH_CITIES


def extract_entity_simple(question: str) -> Entity:
    """Extraction d'entité regex-based (zero LLM, déterministe).

    Stratégie :
    1. Tokenize la question, filtre stopwords + mots courts.
    2. Détecte une ville française (closed set _FRENCH_CITIES).
    3. Détecte un niveau (BTS, BUT, Licence, Master, Bachelor, etc.).
    4. Le reste = candidate formation_name (joined).

    Returns:
        Entity. is_empty() == True si rien d'utile détecté.
    """
    if not question or not question.strip():
        return Entity()

    # Tokens (préserve majuscules pour acronymes types EFREI, EPITA)
    # Apostrophe NON incluse dans le pattern : "d'accès" → ["d", "accès"]
    # pour permettre le filtrage stopwords mot par mot. Tirets conservés
    # pour noms composés ("Saint-Étienne").
    raw_tokens = re.findall(r"[a-zA-Zéèêàùôîçâïü0-9][a-zA-Zéèêàùôîçâïü0-9\-]*", question)

    ville = None
    niveau = None
    name_tokens: list[str] = []
    for tok in raw_tokens:
        low = tok.lower()
        if low in _STOPWORDS:
            continue
        # Sprint refonte 2026-05-05 — skip purs nombres (années 2024/2025/2026,
        # codes ROME M18xx, etc.) qui parasitent le formation_name.
        if tok.isdigit():
            continue
        if low in _FRENCH_CITIES:
            ville = ville or tok  # garde le premier match
            continue
        # Niveau patterns
        if re.match(r"^(bts|but|dut|licence|master|bachelor|prépa|prepa|cap|deust|deaes|deamp|pass|las)$", low):
            niveau = niveau or tok.upper()
            continue
        if re.match(r"^bac\+?\d$", low):
            niveau = niveau or tok
            continue
        # Sinon = candidate formation name
        if len(tok) > 1:
            name_tokens.append(tok)

    formation_name = " ".join(name_tokens).strip() if name_tokens else None
    return Entity(formation_name=formation_name, ville=ville, niveau=niveau)


# ──────────────────────── Lookup formations ────────────────────────


def _fiche_searchable_text(fiche: dict) -> str:
    """Construit la string concatenée à matcher pour le fuzzy."""
    parts = []
    for key in ("nom", "etablissement", "ville", "niveau"):
        v = fiche.get(key)
        if v:
            parts.append(str(v))
    return " ".join(parts).lower()


def lookup_formation(entity: Entity, fiches: list[dict]) -> tuple[dict | None, float, bool]:
    """Fuzzy match entity → fiche.

    Critique expert #4b (2026-05-03) : ajout d'une garde discriminateurs
    métier — si la query contient un mot discriminateur (commercial, MP,
    kiné, international, etc.) qui n'est PAS dans le top match, on rejette
    le match (mieux qu'un mauvais SELECT confiant).

    Returns:
        (best_fiche, score, ambiguous_flag)
        - best_fiche: la fiche matchée (ou None si score < FUZZY_THRESHOLD
          OU discriminateur query absent)
        - score: float 0-100
        - ambiguous_flag: True si plusieurs fiches matchent ≥ FUZZY_THRESHOLD
          avec un écart < AMBIGUITY_DELTA (besoin de précision)
    """
    if entity.is_empty() or not fiches:
        return None, 0.0, False

    # Pool filter (J2 U1) — exclure les fiches non-formation AVANT le fuzzy.
    # Sans ça, une fiche CROUS/INSEE squatte le rang-1 (WRatio inflate les
    # chaînes courtes) et provoque refus (ambigu/no_match) ou garbage-SELECT.
    fiches = [f for f in fiches if is_select_candidate(f)]
    if not fiches:
        return None, 0.0, False

    query = entity.to_query_string()
    if not query:
        return None, 0.0, False

    # Tokens query (sans stopwords) pour la garde discriminateur
    query_tokens = [t for t in re.findall(r"\w+", query) if t.lower() not in _STOPWORDS]

    # Sprint refonte 2026-05-05 — pré-filtrage par ville quand fournie.
    # Sur 55k fiches dont beaucoup RNCP génériques sans ville, le fuzzy
    # global est bruité (top match était "Cybersécurité" RNCP sans etab/
    # ville pour query "EFREI Bordeaux Cybersécurité"). Filtrer d'abord
    # par ville réduit le bruit massivement et garantit que les top
    # matches sont des fiches Parcoursup/MonMaster vraiment localisées.
    # Si aucune fiche ne match la ville → return None (évite hallu sur
    # fiche hors-ville).
    fiches_filtered = fiches
    if entity.ville:
        ville_lower = entity.ville.lower().strip()
        # J2 U1 bug 2 — match la ville contre le champ `ville` OU `etablissement`.
        # 581 fiches métropole ont « lyon » dans l'etab (« IUT Lyon1 ») mais une
        # ville de commune (Villeurbanne, Bron) -> le pré-filtre ville strict les
        # excluait à tort (poste de sur-refus au-delà de fact-001).
        fiches_filtered = [
            f for f in fiches
            if ville_lower in (f.get("ville") or "").lower().strip()
            or ville_lower in (f.get("etablissement") or "").lower()
        ]
        if not fiches_filtered:
            return None, 0.0, False

    # rapidfuzz.process.extract pour les top matches
    candidates = [(i, _fiche_searchable_text(f)) for i, f in enumerate(fiches_filtered)]

    # Score chaque candidate avec WRatio (robuste aux variations)
    results = process.extract(
        query,
        {i: text for i, text in candidates},
        scorer=fuzz.WRatio,
        limit=5,
    )
    # results = [(text, score, key), ...] format rapidfuzz
    if not results:
        return None, 0.0, False

    top_text, top_score, top_idx = results[0]
    if top_score < FUZZY_THRESHOLD:
        return None, top_score, False

    # GARDE DISCRIMINATEUR (critique expert #4b) : si la query contient un mot
    # discriminateur métier qui n'est PAS dans la fiche top → rejeter, mieux
    # qu'un faux positif (ex « prépa commerciales » → « prépa A/L »).
    if not _query_discriminators_match_fiche(query_tokens, top_text):
        # Tenter de trouver un match parmi les top-5 qui satisfait le discriminateur
        for text, score, idx in results[1:]:
            if score < FUZZY_THRESHOLD:
                break
            if _query_discriminators_match_fiche(query_tokens, text):
                return fiches_filtered[idx], score, False
        # Aucun candidat ne matche le discriminateur → reject (None, conservatif)
        return None, top_score, False

    # Détection ambiguité (Sprint refonte 2026-05-05 — fix bottleneck SELECT) :
    # Une fiche multi-voies (ex EFREI Bordeaux Bachelor cyber × 5 fiches
    # Parcoursup pour 5 voies d'admission) déclencherait ambiguous=True
    # naïvement (top_score 90 / second 89 / écart < AMBIGUITY_DELTA), alors
    # qu'il s'agit de la MÊME école sous variants de voie. On vérifie donc
    # que les top matches pointent sur des écoles DISTINCTES (etab, ville).
    # Si tous partagent etab+ville → pas ambigu, prendre le best.
    # J2 U1 (c) — clé d'identité pour l'ambiguïté, conditionnée à la localisation :
    #  - ville PRÉCISÉE -> (nom normalisé, racine d'établissement). Les variantes
    #    de SITE d'une même formation/etab dans la localité demandée ne sont PAS
    #    ambiguës -> on sert la meilleure (le site exact est affiché = honnête).
    #    fact-001 : BUT Info IUT Lyon1 Doua vs Bourg (même nom, racine « iut lyon1 »).
    #  - PAS de ville -> (etab, ville) : des campus en villes différentes du même
    #    établissement restent ambigus (EFREI Paris vs Bordeaux : « quel campus ? »).
    # Reste ambigu si nom OU racine etab diffèrent (formations/établissements
    # distincts ex-aequo, même avec ville : refus/clarification conservé).
    def _school_key(f: dict) -> tuple:
        if entity.ville:
            return (_norm_nom(f.get("nom")), _etab_root(f.get("etablissement")))
        return (
            (f.get("etablissement") or "").strip().lower(),
            (f.get("ville") or "").strip().lower(),
        )

    ambiguous = False
    top_school = _school_key(fiches_filtered[top_idx])
    for _, score, idx in results[1:]:
        if score < FUZZY_THRESHOLD:
            break
        if (top_score - score) >= AMBIGUITY_DELTA:
            break
        if _school_key(fiches_filtered[idx]) != top_school:
            ambiguous = True
            break

    return fiches_filtered[top_idx], top_score, ambiguous


# ──────────────────────── Field extraction with INVALID_VALUES guard ────────────────────────


def is_valid_field_value(value: Any) -> bool:
    """Garde de validité — INVALID_VALUES expansion + handling NaN.

    Évite catastrophe démo : « Le taux d'accès EFREI Bordeaux est 0% »
    quand le champ est présent mais vide dans les fiches mergées.
    """
    if value in INVALID_VALUES:
        return False
    # NaN check pour les float
    if isinstance(value, float):
        import math
        if math.isnan(value) or math.isinf(value):
            return False
    # String "0", "0.0" considérée invalide (cas edge Parcoursup)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("0", "0.0", "0%", ""):
            return False
    return True


def extract_field(fiche: dict, field_key: str) -> Any | None:
    """Extrait field_key d'une fiche, support du dotted path (e.g. 'insertion_pro.taux_emploi_3ans').

    Returns:
        La valeur si valide, sinon None (déclenche le fallback unifié).
    """
    if not fiche or not field_key:
        return None

    # Support dotted path : insertion_pro.taux_emploi_3ans
    keys = field_key.split(".")
    current: Any = fiche
    for k in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(k)
        if current is None:
            return None

    if not is_valid_field_value(current):
        return None

    return current


# ──────────────────────── Response templater ────────────────────────


def _format_value(value: Any, field_key: str) -> str:
    """Formate la valeur selon son type (taux %, salaire €, places nombre)."""
    if "taux" in field_key or "selectivit" in field_key:
        # Taux Parcoursup : float déjà en %, ou ratio 0-1
        try:
            f = float(value)
            if 0.0 <= f <= 1.0:
                return f"{int(round(f * 100))} %"
            return f"{int(round(f))} %"
        except (ValueError, TypeError):
            return str(value)
    if "salaire" in field_key:
        try:
            return f"{int(round(float(value)))} €"
        except (ValueError, TypeError):
            return str(value)
    if field_key in ("nombre_places",):
        try:
            return f"{int(value)} places"
        except (ValueError, TypeError):
            return str(value)
    return str(value)


def format_select_response(
    fiche: dict,
    field_key: str,
    field_label: str,
    value: Any,
) -> str:
    """Templater déterministe pour la réponse SELECT.

    Format : « Le [label] de [formation] (à [ville]) est [value formatée]. Source: [URL]. »
    """
    nom = (fiche.get("nom") or "").strip()
    etab = (fiche.get("etablissement") or "").strip()
    ville = (fiche.get("ville") or "").strip()

    # Identifier la formation pour l'utilisateur (lisible)
    formation_id = nom
    if etab and etab != nom:
        formation_id = f"{nom} ({etab})" if nom else etab
    if ville:
        formation_id = f"{formation_id} à {ville}"

    formatted_value = _format_value(value, field_key)

    # URL source : préférence à lien_form_psup, fallback URL ONISEP
    url = (
        fiche.get("lien_form_psup")
        or fiche.get("url_onisep")
        or fiche.get("url")
        or ""
    )
    source_suffix = ""
    if url:
        source_suffix = f" Source : [fiche officielle Parcoursup]({url})."
    elif fiche.get("source"):
        source_suffix = f" (Source : {fiche.get('source')})."

    return (
        f"Le {field_label} de **{formation_id}** est **{formatted_value}**.{source_suffix}"
    )


# ──────────────────────── Garde anti-stale ────────────────────────


def _fiche_is_stale(fiche: dict, max_age_months: int = 18) -> bool:
    """Détecte si une fiche est trop ancienne pour servir un SELECT.

    Lit `fiche.collected_at` (dict source → date ISO "YYYY-MM-DD") et
    prend la date la plus récente parmi les sources. Si cette date est
    antérieure à `today - max_age_months`, la fiche est considérée stale.

    Sprint refonte 2026-05-05 — évite de servir des taux Parcoursup 2024
    sur une question 2025 (cf rapport expert : "fraîcheur > 18 mois pollue").
    Cron refresh automation prévu Phase D7 — garde manuelle en attendant.

    Returns True si stale (le SELECT doit fallback unifié).
    Returns False si fiche fraîche OU si collected_at absent (legacy safe).
    """
    collected_at = fiche.get("collected_at")
    if not isinstance(collected_at, dict) or not collected_at:
        return False  # legacy fiche sans tracking → on laisse passer

    from datetime import date, datetime

    most_recent: date | None = None
    for source_date_str in collected_at.values():
        if not isinstance(source_date_str, str):
            continue
        try:
            d = datetime.strptime(source_date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if most_recent is None or d > most_recent:
            most_recent = d

    if most_recent is None:
        return False  # aucune date parseable → safe default

    today = date.today()
    # Approximation : 1 mois = 30.44 jours (365.25/12)
    age_days = (today - most_recent).days
    return age_days > (max_age_months * 30.44)


# ──────────────────────── End-to-end orchestrator ────────────────────────


def try_select_or_none(
    question: str,
    fiches: list[dict],
) -> SelectResult | None:
    """Tentative de SELECT déterministe end-to-end.

    Returns:
        SelectResult avec via_select=True si le SELECT a réussi.
        SelectResult avec via_select=False (fallback) si :
          - pas d'entité reconnue (`reason='select_no_entity'`)
          - pas de field key détecté → return None (le router gère)
          - fuzzy < FUZZY_THRESHOLD (`reason='select_no_match'`)
          - multi-match ambigu (`reason='select_ambiguous'`)
          - field absent/invalide dans la fiche matchée (`reason='select_invalid_value'`)
        None si le pattern ne matche pas du tout (le router fallback RAG).
    """
    # 1. Field key detection
    field_info = detect_field_key(question)
    if field_info is None:
        return None  # pas une question SELECT — laisser le router décider
    field_key, field_label = field_info

    # 2. Entity extraction
    entity = extract_entity_simple(question)
    if entity.is_empty():
        return SelectResult(
            text=format_unknown_response(missing_field=field_label),
            via_select=False,
            field_key=field_key,
            reason="select_no_entity",
        )

    # 3. Fuzzy lookup
    fiche, score, ambiguous = lookup_formation(entity, fiches)
    if fiche is None:
        return SelectResult(
            text=format_unknown_response(
                missing_field=f"{field_label} pour la formation que tu décris",
                near_match=(
                    f"Je n'ai pas trouvé de formation correspondant suffisamment "
                    f"précisément à « {entity.to_query_string()} » dans mes sources "
                    f"(meilleur score : {score:.0f}/100, seuil requis : {FUZZY_THRESHOLD})."
                ),
            ),
            via_select=False,
            field_key=field_key,
            fuzzy_score=score,
            reason="select_no_match",
        )

    if ambiguous:
        return SelectResult(
            text=format_unknown_response(
                missing_field=field_label,
                near_match=(
                    f"Plusieurs formations matchent ta demande. Précise davantage "
                    f"(ville, établissement, niveau) pour que je puisse te donner "
                    f"le chiffre exact."
                ),
                suggestion=None,  # pas de redirection externe — précision interne demandée
            ),
            via_select=False,
            matched_fiche_id=str(fiche.get("id") or fiche.get("nom") or ""),
            fuzzy_score=score,
            field_key=field_key,
            reason="select_ambiguous",
        )

    # 3.5. Garde anti-stale (Sprint refonte 2026-05-05) — refuser le SELECT
    # si la fiche source date de plus de 18 mois. Évite de servir des taux
    # Parcoursup 2024 sur une question 2025 (cas où la fiche n'a pas été
    # rafraîchie). Cron refresh prévu Phase D7 — en attendant, garde manuelle.
    if _fiche_is_stale(fiche, max_age_months=18):
        return SelectResult(
            text=format_unknown_response(
                missing_field=field_label,
                near_match=(
                    f"J'ai trouvé la fiche **{fiche.get('nom') or '?'}** "
                    f"mais la donnée source date de plus de 18 mois — "
                    f"vérifie le chiffre actualisé sur Parcoursup ou ONISEP."
                ),
            ),
            via_select=False,
            matched_fiche_id=str(fiche.get("id") or fiche.get("nom") or ""),
            fuzzy_score=score,
            field_key=field_key,
            reason="select_stale_fiche",
        )

    # 4. Field extraction avec INVALID_VALUES guard
    value = extract_field(fiche, field_key)
    if value is None:
        return SelectResult(
            text=format_unknown_response(
                missing_field=f"{field_label} pour cette formation",
                near_match=(
                    f"J'ai trouvé la fiche **{fiche.get('nom') or '?'}** "
                    f"mais le champ « {field_label} » n'est pas renseigné "
                    f"dans la source."
                ),
            ),
            via_select=False,
            matched_fiche_id=str(fiche.get("id") or fiche.get("nom") or ""),
            fuzzy_score=score,
            field_key=field_key,
            reason="select_invalid_value",
        )

    # 5. SUCCESS — réponse déterministe
    return SelectResult(
        text=format_select_response(fiche, field_key, field_label, value),
        via_select=True,
        matched_fiche_id=str(fiche.get("id") or fiche.get("nom") or ""),
        fuzzy_score=score,
        field_key=field_key,
        reason=None,
    )
