"""Checker brut/net deterministe, source-aware (garde-fou salaire volet b).

Detecte les cas ou le modele qualifie un salaire 'brut'/'net' en contradiction
avec le champ source qui porte ce chiffre. Independant du juge LLM : sert
d'instrument de MESURE du volet (b) before/after le garde-fou.

Convention source (partition insee_salaire / salaan 2023) :
  salaire_net_*  -> 'net'  ;  salaire_brut_median_annuel -> 'brut'.

Principe : on n'accuse QUE si le nombre cite correspond exactement a une valeur
de source, que cette valeur a UN seul qualificatif en source, et que le
qualificatif le plus proche dans la meme clause de la reponse le contredit.
Conservateur par construction (pas de faux positif sur un nombre non source,
ni sur une valeur ambigue net+brut).
"""
from __future__ import annotations

import re

_NET_FIELDS = (
    "salaire_net_median_annuel", "salaire_net_median_mensuel",
    "salaire_net_q1_mensuel", "salaire_net_q3_mensuel",
)
_BRUT_FIELDS = ("salaire_brut_median_annuel",)

# Separateurs de milliers FR : espace U+0020, nbsp U+00A0, narrow-nbsp U+202F.
_THOUSANDS = "   "
_NUM_RE = re.compile(r"\d[\d" + _THOUSANDS + r"]*\d|\d")
_QUAL_RE = re.compile(r"\b(brut|net)\b", re.IGNORECASE)
# Frontieres de clause : fin de phrase, retour ligne, virgule+espace, puce, tiret entoure.
_CLAUSE_SPLIT = re.compile(r"(?:[.;:]\s)|\n|(?:,\s)|[•·]|(?:\s[-–]\s)")


def _norm_num(raw: str) -> int | None:
    digits = re.sub(r"[" + _THOUSANDS + r"]", "", raw)
    return int(digits) if digits.isdigit() else None


def _source_value_quals(sources) -> dict[int, set[str]]:
    """map valeur(int) -> ensemble des qualificatifs source ('net'/'brut')."""
    out: dict[int, set[str]] = {}
    for s in sources or []:
        if not isinstance(s, dict):
            continue
        for f in _NET_FIELDS:
            v = s.get(f)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.setdefault(int(v), set()).add("net")
        for f in _BRUT_FIELDS:
            v = s.get(f)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.setdefault(int(v), set()).add("brut")
    return out


def check_salary_qualifier(answer: str, sources) -> list[dict]:
    """Retourne la liste des violations brut/net.

    Chaque violation : {value, claimed, source_qualifiers}.
    """
    vq = _source_value_quals(sources)
    if not vq or not answer:
        return []
    violations: list[dict] = []
    for clause in _CLAUSE_SPLIT.split(answer):
        if not clause:
            continue
        quals = [(m.start(), m.group(1).lower()) for m in _QUAL_RE.finditer(clause)]
        if not quals:
            continue
        for m in _NUM_RE.finditer(clause):
            val = _norm_num(m.group(0))
            if val is None or val not in vq:
                continue
            src_quals = vq[val]
            if len(src_quals) > 1:
                continue  # valeur ambigue en source (net ET brut) -> pas d'accusation
            npos = m.start()
            claimed = min(quals, key=lambda q: abs(q[0] - npos))[1]
            if claimed not in src_quals:
                violations.append({
                    "value": val,
                    "claimed": claimed,
                    "source_qualifiers": sorted(src_quals),
                })
    return violations


def count_violations(answer: str, sources) -> int:
    return len(check_salary_qualifier(answer, sources))
