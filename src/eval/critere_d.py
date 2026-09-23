"""Étape D, critère 1 (sans juge) : part des chiffres attendus cités justes (protocole §7).

Un chiffre attendu est « cité juste » si la réponse de son tour, ou d'un tour suivant de la même
conversation, contient un chiffre de même unité égal à la tolérance de `numbers.py`. Seuls comptent
les attendus dont la fiche est dans la base C et rendable (exposition.json, `cible_par_attendu`) ;
les 18 autres sont publiés à part.

Unités (extraction typée, `numbers.py` intouché) :
- pct (« % ») et eur (« € », « euros ») comme `numbers.py` ;
- places (« place(s) ») comme `numbers.py` ;
- effectif, ajouté ici : vœux, candidats, propositions (protocole v0.2). Le banc écrit « voeux »,
  « candidats » ou « propositions » pour des effectifs que les réponses nomment librement (« 1 017
  candidats » pour des vœux) : ces mots forment une seule unité, et le témoin de hasard dit ce que
  ce regroupement coûte.

Témoin de hasard : les mêmes réponses confrontées aux attendus d'une AUTRE conversation (graine 7).
Dispersion : bootstrap apparié sur les conversations (10 000 tirages, graine 7).
"""
from __future__ import annotations

import random
import re

TOLERANCE = {"pct": 0.51, "eur": 0.5, "places": 0.5, "effectif": 0.5}
UNITE_ATTENDU = {"%": "pct", "places": "places", "voeux": "effectif", "candidats": "effectif",
                 "propositions": "effectif", "euros nets par mois": "eur"}

_CLAIM = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:[   ]\d{3})+|\d+)(?:[.,](\d+))?[   ]?"
    r"(%|€|euros?\b|places?\b|v(?:oe|œ)ux\b|candidat(?:e?s)?\b|propositions?\b)",
    re.IGNORECASE)


def _unite(token: str) -> str:
    t = token.lower()
    if t == "%":
        return "pct"
    if t == "€" or t.startswith("euro"):
        return "eur"
    if t.startswith("place"):
        return "places"
    return "effectif"


def chiffres(texte: str) -> list[tuple[float, str]]:
    out = []
    for m in _CLAIM.finditer(texte or ""):
        entier = re.sub(r"[   ]", "", m.group(1))
        v = float(f"{entier}.{m.group(2)}") if m.group(2) else float(entier)
        u = _unite(m.group(3))
        if u == "pct" and v > 100:
            continue
        out.append((v, u))
    return out


def cite(attendu: dict, reponses: list[str]) -> bool:
    u = UNITE_ATTENDU[attendu["unite"]]
    tol = TOLERANCE[u]
    return any(uu == u and abs(v - float(attendu["valeur"])) <= tol
               for texte in reponses for v, uu in chiffres(texte))


def par_conversation(banc: dict, exposition: dict, reponses: dict[tuple[str, int], str]) -> dict[str, dict]:
    """{conversation: {"n": attendus du critère, "cites": [bool...], "hors": n}} pour une génération."""
    out = {}
    for item in banc["items"]:
        cibles = exposition["conversations"][item["id"]]["cible_par_attendu"]
        n, cites, hors = 0, [], 0
        for a, cible in zip(item["attendus"]["chiffres"], cibles):
            if cible is None:
                hors += 1
                continue
            n += 1
            textes = [reponses.get((item["id"], t), "") for t in range(a["tour"], len(item["turns"]))]
            cites.append(cite(a, textes))
        out[item["id"]] = {"n": n, "cites": cites, "hors": hors}
    return out


def temoin(banc: dict, exposition: dict, reponses: dict[tuple[str, int], str], graine: int = 7) -> float | None:
    """Les réponses de chaque conversation contre les attendus d'une autre conversation tirée au sort."""
    rng = random.Random(graine)
    avec = [i for i in banc["items"] if any(c is not None for c in exposition["conversations"][i["id"]]["cible_par_attendu"])]
    hits = total = 0
    for item in avec:
        autre = rng.choice([x for x in avec if x["id"] != item["id"]])
        textes = [reponses.get((item["id"], t), "") for t in range(len(item["turns"]))]
        cibles = exposition["conversations"][autre["id"]]["cible_par_attendu"]
        for a, cible in zip(autre["attendus"]["chiffres"], cibles):
            if cible is None:
                continue
            total += 1
            hits += cite(a, textes)
    return hits / total if total else None


def taux(pc: dict[str, dict]) -> float | None:
    n = sum(v["n"] for v in pc.values())
    return sum(sum(v["cites"]) for v in pc.values()) / n if n else None


def bootstrap_delta(x: dict[str, dict], r: dict[str, dict], tirages: int = 10_000, graine: int = 7) -> dict:
    """IC95 de P(x) - P(r), tirage apparié des conversations (mêmes conversations des deux côtés)."""
    ids = [i for i in x if x[i]["n"]]
    rng = random.Random(graine)
    deltas = []
    for _ in range(tirages):
        tir = [rng.choice(ids) for _ in ids]
        n = sum(x[i]["n"] for i in tir)
        deltas.append((sum(sum(x[i]["cites"]) for i in tir) - sum(sum(r[i]["cites"]) for i in tir)) / n)
    deltas.sort()
    return {"delta": taux(x) - taux(r), "ic95": [deltas[int(0.025 * tirages)], deltas[int(0.975 * tirages) - 1]]}
