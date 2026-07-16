"""Vérification déterministe chiffre-vs-source-citée (H1 lot 1.2, ordre 0905).

Le contrat v4 promettait depuis 2026-05-06 une « vérification post-gen côté
pipeline (flag les chiffres non présents dans la fiche citée) » — risque 2
« source-coller mécanique » de la docstring system_v4_strict — qui n'avait
jamais été implémentée (audit 15/07 : rien de contraint mécaniquement).

Principe : pour chaque chiffre ATTRIBUABLE à un tag de citation
([source SX], [SX], variantes multi-sources [source S1, S2] / [S1/S2]),
vérifier que la valeur existe dans la FactCard SX que le LLM a réellement
vue. Zéro LLM, zéro coût, zéro variance : regex + comparaison numérique.

Philosophie HAUTE PRÉCISION (leçon feedback_gate_corpus_blindspot : sur un
circuit de sanction, un faux positif a la gravité d'un faux négatif) :
- seuls les chiffres attribuables à un tag sont vérifiés ;
- normalisations réelles du corpus : ratio 0-1 cité en % (taux_emploi 0.86
  -> « 86 % »), arrondis à l'entier / à la décimale, formats FR (« 1 740 € »,
  « 19,4 % ») ;
- les nombres des champs texte de la carte (duree, text_libre, profil_admis…)
  comptent comme présents (le LLM peut les citer légitimement) ;
- exclusions : URLs, numéros des tags eux-mêmes, « bac+3 », années nues,
  petits entiers sans unité (ambigus : « 3 pistes »).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.rag.fact_card import FactCard, fiche_to_fact_card

# Tag de citation : [source S1], [S1], [source S1, S4], [source S1/S2/S3]
_TAG = re.compile(r"\[(?:sources?\s+)?(S\d+(?:\s*[,/]\s*S\d+)*)\]", re.IGNORECASE)
# URL markdown ou nue : neutralisée avant extraction des nombres
_URL = re.compile(r"\(?https?://\S+\)?")
# Nombre FR : milliers à espace(s) ou insécable, décimale virgule ou point
_NUM = re.compile(r"\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")
# Unité collée au chiffre (autorise l'espace insécable)
_UNIT_AFTER = re.compile(r"^[  ]?(?:%|€|euros?\b)")

_YEAR_MIN, _YEAR_MAX = 1990, 2035
_SMALL_INT_MAX = 9  # entiers nus <= 9 sans unité : ambigus, non vérifiés


@dataclass(frozen=True)
class CitationMismatch:
    """Un chiffre attribué à [source SX] absent de la FactCard SX."""
    value: float
    source_ids: frozenset[str]
    context: str  # extrait de la réponse autour du chiffre


def _parse_number(raw: str) -> float:
    return float(raw.replace(" ", "").replace(" ", "").replace(",", "."))


def _blank_out(text: str, pattern: re.Pattern) -> str:
    """Remplace les matches par des espaces (préserve les positions)."""
    return pattern.sub(lambda m: " " * len(m.group(0)), text)


def extract_cited_numbers(answer: str) -> list[tuple[float, frozenset[str], str]]:
    """Extrait les (valeur, {SX…}, contexte) attribuables à un tag de citation.

    Attribution : par LIGNE (une puce = une ligne), chaque chiffre va au tag
    le plus proche de la ligne (avant ou après). Ligne sans tag -> aucun
    chiffre extrait (hors périmètre : c'est la couverture R3, pas ce check).
    """
    out: list[tuple[float, frozenset[str], str]] = []
    for line in answer.splitlines():
        tags = [
            (m.start(), m.end(),
             frozenset(s.strip().upper() for s in re.split(r"[,/]", m.group(1))))
            for m in _TAG.finditer(line)
        ]
        if not tags:
            continue
        # Fusionne les groupes de tags ADJACENTS (« [source S2][source S5] »,
        # séparés d'au plus 2 caractères non alphanumériques) en une union :
        # le LLM cite les deux sources pour le même fait, l'attribution au
        # « plus proche » seul serait un contresens (calibration 16/07, G19).
        merged: list[tuple[int, int, frozenset[str]]] = []
        for start, end, ids in tags:
            if merged and start - merged[-1][1] <= 2 \
                    and not any(ch.isalnum() for ch in line[merged[-1][1]:start]):
                pstart, _, pids = merged[-1]
                merged[-1] = (pstart, end, pids | ids)
            else:
                merged.append((start, end, ids))
        tags = merged
        # Neutralise tags + URLs pour ne pas extraire leurs nombres
        scan = _blank_out(line, _TAG)
        scan = _blank_out(scan, _URL)
        for m in _NUM.finditer(scan):
            raw = m.group(0)
            start, end = m.start(), m.end()
            # collé à une lettre (« 3e », « 24h ») ou précédé de « bac+ » : skip
            if end < len(scan) and scan[end].isalpha():
                continue
            prefix = scan[max(0, start - 5):start].lower()
            if prefix.endswith(("bac+", "bac +")):
                continue
            value = _parse_number(raw)
            has_unit = bool(_UNIT_AFTER.match(line[end:end + 8]))
            is_int = value == int(value)
            # année nue (sans % / €) : pas un claim R1
            if not has_unit and is_int and _YEAR_MIN <= value <= _YEAR_MAX:
                continue
            # petit entier nu : « 3 pistes », « 2 options » — ambigu, skip
            if not has_unit and is_int and value <= _SMALL_INT_MAX:
                continue
            # Attribution = UNION des tags encadrants (le précédent et le
            # suivant sur la ligne). Motif R3 « 25 % [S1] » -> tag suivant ;
            # motif R9 « fiche [S1] : 25 % » -> tag précédent ; énumération
            # « 2 125 € [S2], 2 200 € [S5] » -> chaque chiffre entre deux tags
            # peut légitimement appartenir à l'un ou l'autre (calibration
            # 16/07 : l'attribution au seul plus proche mal-attribuait des
            # citations correctes, cf feedback_validate_measurement_instrument).
            preceding = next((t for t in reversed(tags) if t[1] <= start), None)
            following = next((t for t in tags if t[0] >= end), None)
            ids: frozenset[str] = frozenset()
            if preceding is not None:
                ids |= preceding[2]
            if following is not None:
                ids |= following[2]
            context = line[max(0, start - 60):min(len(line), end + 60)].strip()
            out.append((value, ids, context))
    return out


def _representations(v: float) -> set[float]:
    """Formes sous lesquelles une valeur de carte peut légitimement être citée."""
    reps = {v, float(round(v)), round(v, 1)}
    if 0 < v <= 1:
        pct = v * 100
        reps |= {pct, float(round(pct)), round(pct, 1)}
    return reps


def card_numeric_values(card: FactCard) -> set[float]:
    """Toutes les valeurs numériques citables d'une FactCard (avec leurs
    représentations : arrondis, ratio->%)."""
    vals: set[float] = set()
    for v in vars(card.chiffres).values():
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            vals |= _representations(float(v))
        elif isinstance(v, str):
            for m in _NUM.finditer(v):
                vals |= _representations(_parse_number(m.group(0)))
    # Champs texte de la carte : le LLM peut en citer les nombres légitimement
    for text in (card.text_libre, card.tendance_acces, card.profil_admis,
                 card.dispositifs_reconversion, card.selectivite_code,
                 card.formation, card.etablissement):
        if text:
            for m in _NUM.finditer(text):
                vals |= _representations(_parse_number(m.group(0)))
    if card.annee_donnees is not None:
        vals |= _representations(float(card.annee_donnees))
    return vals


def _matches(value: float, card_values: set[float], tol: float = 0.051) -> bool:
    return any(abs(value - cv) <= tol for cv in card_values)


def check_citations(answer: str, cards: list[FactCard]) -> list[CitationMismatch]:
    """Vérifie chaque chiffre attribué à un tag contre la ou les FactCards citées.

    Un tag multi-sources ([source S1, S4]) matche si AU MOINS une des cartes
    contient la valeur. Un tag vers une source inexistante (S7 alors que le
    prompt s'arrêtait à S5) est un mismatch (fabrication de tag).
    """
    by_id = {c.id.upper(): card_numeric_values(c) for c in cards}
    mismatches: list[CitationMismatch] = []
    for value, source_ids, context in extract_cited_numbers(answer):
        known = [by_id[s] for s in source_ids if s in by_id]
        if known and any(_matches(value, vals) for vals in known):
            continue
        if not known:
            # tag fabriqué (aucune des sources citées n'existe)
            mismatches.append(CitationMismatch(value, source_ids, context))
            continue
        mismatches.append(CitationMismatch(value, source_ids, context))
    return mismatches


def cards_from_top_sources(top_sources: list[dict], max_sources: int) -> list[FactCard]:
    """Reconstruit les FactCards AVEC LA MÊME numérotation S1..SN que
    `format_sources_for_llm` (ce que le LLM a vu). `max_sources` DOIT être
    la même valeur que celle passée à la génération (5 en v4 strict,
    NARRATIVE_MAX_SOURCES en récit), sinon le check décale les identités."""
    cards: list[FactCard] = []
    for i, s in enumerate(top_sources[:max_sources], 1):
        fiche = s.get("fiche") if isinstance(s, dict) and "fiche" in s else s
        if not isinstance(fiche, dict):
            continue
        cards.append(fiche_to_fact_card(fiche, fact_id=f"S{i}"))
    return cards
