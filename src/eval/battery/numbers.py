"""Controle deterministe des chiffres cites : zero LLM, zero cout, zero variance.

Question mesuree : un chiffre donne a l'eleve peut-il etre montre dans une fiche ? C'est
l'argument produit (« chaque chiffre verifiable »), et un juge LLM ne le voit pas (05/09 :
agent Sonnet 4,01 contre Sonnet seul 3,98 alors que seul le premier lit le corpus).

Un chiffre cite = un nombre suivi d'une unite : pourcentage, euros, places. Les nombres nus
(annees, « 3 pistes ») sont hors perimetre. Chaque chiffre recoit un statut :

- `adosse`       : la valeur est dans une fiche que le systeme a EXPOSEE sur ce tour (servie au
                   generateur, ou lue par l'agent). Provenance exacte, c'est la metrique de tete.
- `corpus`       : pas dans les fiches exposees, mais dans une des K fiches que la ligne designe
                   (recherche BM25 sur la ligne sans ses nombres). Indicatif seulement : calibre le
                   23/09 sur les runs du 05/09, cet ancrage ne retrouve que 37 a 60 % des chiffres
                   adosses et coincide par hasard sur ~15 % des chiffres (K=5).
- `non_retrouve` : ni l'un ni l'autre. Ce n'est PAS « faux » : l'absence d'une valeur dans le
                   corpus ne prouve pas qu'elle est fausse, seulement qu'on ne peut pas la montrer.

La comparaison est TYPEE : un % ne se verifie que contre des champs en %, un montant contre des
montants, des places contre `nombre_places`. Sans typage, n'importe quel entier de 0 a 100 se
retrouve dans une fiche.

Chaque taux est publie a cote de son temoin de hasard (`chance_rate`) : le meme calcul avec les
fiches d'une AUTRE conversation. Un taux adosse proche de son temoin ne mesure rien.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from src.rag.fact_card import fiche_to_fact_card

UNITS = ("pct", "eur", "places")

# Nombre FR (milliers a espace ou espace insecable, decimale , ou .) suivi de son unite.
_CLAIM = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,](\d+))?[  ]?(%|€|euros?\b|places?\b)",
    re.IGNORECASE,
)
_PCT = re.compile(r"(\d+(?:[.,]\d+)?)[  ]?%")
_EUR = re.compile(r"(\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,]\d+)?[  ]?(?:€|euros?\b)", re.IGNORECASE)

# Tolerance d'egalite par unite : arrondi a l'entier cote reponse (« 45 % » pour 45,4).
_TOLERANCE = {"pct": 0.51, "eur": 0.5, "places": 0.5}


@dataclass(frozen=True)
class NumberClaim:
    value: float
    unit: str
    line: str


def _to_float(integer_part: str, decimals: str | None = None) -> float:
    digits = integer_part.replace(" ", "").replace(" ", "")
    return float(f"{digits}.{decimals}" if decimals else digits)


def _unit(token: str) -> str:
    token = token.lower()
    if token == "%":
        return "pct"
    if token.startswith("place"):
        return "places"
    return "eur"


# Tableaux markdown : l'unite d'un nombre nu est dans l'en-tete de sa colonne ou dans le libelle de sa
# ligne (`| Taux d'acces (%) |`, `| Candidats | 3 779 |`). Defaut mesure en D (RAPPORT D section 7,
# biais_tableaux.json : C x GLM 5.2 perdait 7 pts de critere 1). Levier de falsification :
# ORIENTIA_NUMBERS_SANS_TABLEAUX=1 coupe la correction (et rejoue les rapports d'avant le 25/09).
_BARE = re.compile(r"^[~≈]?\s*(\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,](\d+))?\s*$")
_SEPARATOR = re.compile(r"^\|?\s*:?-{2,}")


def _unit_of_label(label: str) -> str | None:
    t = label.lower()
    if "%" in t or re.search(r"\b(taux|part|pourcentage)\b", t):
        return "pct"
    if "€" in t or re.search(r"\b(euros?|frais|co[uû]ts?|salaires?|prix)\b", t):
        return "eur"
    if re.search(r"\bplaces?\b", t):
        return "places"
    return None


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_numbers(answer: str, unit_of_label=_unit_of_label) -> list[tuple[float, str, str]]:
    """Nombres NUS des cellules de tableau, avec l'unite de leur colonne, sinon de leur ligne.

    Un nombre sans unite identifiable reste hors perimetre : compter les nombres de tableau sans unite
    accepte des coincidences (un « 33 » de colonne places pour un attendu a 33 %). Les cellules qui
    portent leur unite (« 34 % ») sont deja lues par la regle ordinaire et ne sont pas relues ici."""
    import os
    if os.environ.get("ORIENTIA_NUMBERS_SANS_TABLEAUX") == "1":
        return []
    out: list[tuple[float, str, str]] = []
    header: list[str] | None = None
    for line in (answer or "").splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        if _SEPARATOR.match(line.strip()):
            continue
        cells = _cells(line)
        if header is None:
            header = cells
            continue
        for i, cell in enumerate(cells):
            m = _BARE.match(cell)
            if not m:
                continue
            unit = unit_of_label(header[i]) if i < len(header) else None
            if unit is None and i > 0:
                unit = unit_of_label(cells[0])
            if unit is None:
                continue
            value = _to_float(m.group(1), m.group(2))
            if unit == "pct" and value > 100:
                continue
            out.append((value, unit, line.strip()))
    return out


def extract_claims(answer: str) -> list[NumberClaim]:
    claims = []
    for line in (answer or "").splitlines():
        for m in _CLAIM.finditer(line):
            value = _to_float(m.group(1), m.group(2))
            unit = _unit(m.group(3))
            if unit == "pct" and value > 100:
                continue
            claims.append(NumberClaim(value, unit, line.strip()))
    claims += [NumberClaim(v, u, line) for v, u, line in table_numbers(answer)]
    return claims


def _percent_forms(p: float) -> set[float]:
    return {p, float(round(p)), round(p, 1)}


def _ratio_as_percent(v: float) -> set[float]:
    """Champ numerique taux_/part_ : les ratios du corpus (taux_emploi 0.86) sont cites en %."""
    return _percent_forms(v * 100 if 0 < v <= 1 else v)


def fiche_values(fiche: dict) -> dict[str, set[float]]:
    """Valeurs citables d'une fiche, par unite, lues sur sa FactCard (ce que le generateur voit)."""
    card = fiche_to_fact_card(fiche, fact_id="S1")
    out: dict[str, set[float]] = {u: set() for u in UNITS}
    for name, v in vars(card.chiffres).items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if name.startswith(("taux_", "part_")):
            out["pct"] |= _ratio_as_percent(float(v))
        elif name.startswith(("salaire_", "frais_")):
            out["eur"].add(float(v))
        elif name == "nombre_places":
            out["places"].add(float(v))
    texts = [card.text_libre, card.profil_admis, card.tendance_acces, card.dispositifs_reconversion]
    texts += [v for v in vars(card.chiffres).values() if isinstance(v, str)]
    for text in filter(None, texts):
        for m in _PCT.finditer(text):
            # deja ecrit en % dans le texte : « 0,5 % » reste 0,5, jamais 50
            out["pct"] |= _percent_forms(float(m.group(1).replace(",", ".")))
        for m in _EUR.finditer(text):
            out["eur"].add(_to_float(m.group(1)))
    return out


def _found(claim: NumberClaim, values: dict[str, set[float]]) -> bool:
    tol = _TOLERANCE[claim.unit]
    return any(abs(claim.value - v) <= tol for v in values[claim.unit])


class NumberChecker:
    """Verifie les chiffres d'une reponse contre le corpus. Cache les valeurs par position."""

    def __init__(self, corpus, anchor_k: int = 5):
        self.corpus = corpus
        self.anchor_k = anchor_k
        self._values: dict[int, dict[str, set[float]]] = {}
        self._anchors: dict[str, list[int]] = {}

    def values_of(self, positions) -> dict[str, set[float]]:
        merged: dict[str, set[float]] = {u: set() for u in UNITS}
        for p in positions:
            if p not in self._values:
                self._values[p] = fiche_values(self.corpus.fiches[p])
            for u in UNITS:
                merged[u] |= self._values[p][u]
        return merged

    def anchor(self, line: str) -> list[int]:
        query = re.sub(r"\d+", " ", line)
        if query not in self._anchors:
            self._anchors[query] = self.corpus.search(query, k=self.anchor_k)
        return self._anchors[query]

    def check(self, answer: str, exposed_positions, anchor: bool = True) -> list[dict]:
        exposed = self.values_of(exposed_positions)
        out = []
        for c in extract_claims(answer):
            if _found(c, exposed):
                status = "adosse"
            elif anchor and _found(c, self.values_of(self.anchor(c.line))):
                status = "corpus"
            else:
                status = "non_retrouve"
            out.append({"value": c.value, "unit": c.unit, "status": status, "line": c.line[:240]})
        return out

    def chance_rate(self, answers: list[str], exposed: list[list[int]], conversations: list[str],
                    seed: int = 7) -> float | None:
        """Temoin de hasard du taux adosse : chaque reponse contre les fiches d'un tour d'une AUTRE
        conversation (les tours d'une meme conversation exposent des fiches voisines).

        Sa population est celle ou le taux adosse peut etre non nul : les tours qui ont expose des
        fiches. Rapporte sur tous les chiffres cites, comme le taux adosse, pour rester comparable.
        None si aucun tour n'expose de fiche (le taux adosse est alors 0 par construction)."""
        turns = [(a, e, c) for a, e, c in zip(answers, exposed, conversations) if e]
        if not turns:
            return None
        rng = random.Random(seed)
        n_claims = sum(len(extract_claims(a)) for a in answers)
        hit = 0
        for answer, _, conversation in turns:
            others = [e for _, e, c in turns if c != conversation]
            if not others:
                continue
            values = self.values_of(rng.choice(others))
            hit += sum(_found(c, values) for c in extract_claims(answer))
        return hit / n_claims if n_claims else None


@dataclass
class NumberSummary:
    n_claims: int = 0
    by_status: dict[str, int] = field(default_factory=lambda: {"adosse": 0, "corpus": 0, "non_retrouve": 0})
    by_unit: dict[str, int] = field(default_factory=lambda: {u: 0 for u in UNITS})
    turns_with_claims: int = 0
    turns_exposing_fiches: int = 0

    def add(self, checks: list[dict], exposed: bool) -> None:
        self.n_claims += len(checks)
        self.turns_with_claims += bool(checks)
        self.turns_exposing_fiches += bool(exposed)
        for c in checks:
            self.by_status[c["status"]] += 1
            self.by_unit[c["unit"]] += 1

    def rate(self, status: str) -> float | None:
        # Aucun chiffre cite : pas de taux (jamais un 100 % ou un 0 % fabrique).
        return self.by_status[status] / self.n_claims if self.n_claims else None
