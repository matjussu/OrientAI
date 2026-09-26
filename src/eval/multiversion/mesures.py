"""Mesures déterministes d'un run (protocole section 4) : critère 1 et chiffres adossés. Zéro appel d'API.

Critère 1 = définition de D et E (`src/eval/critere_d.py`, périmètre `results/banc_e/exposition.json`), avec
l'extracteur corrigé pour les tableaux : un nombre nu de tableau prend l'unité de sa colonne, sinon de sa ligne
(`numbers.table_numbers`). `critere_d.py` n'est pas modifié, pour que les rapports D et E restent rejouables.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from src.eval import critere_d as cd
from src.eval.battery.config import REPO
from src.eval.battery.numbers import _unit_of_label, table_numbers

EXPOSITION = REPO / "results/banc_e/exposition.json"


def _unite_critere(libelle: str) -> str | None:
    u = _unit_of_label(libelle)
    if u:
        return u
    if re.search(r"\b(v(?:oe|œ)ux|candidat(?:e?s)?|propositions?)\b", libelle.lower()):
        return "effectif"
    return None


def chiffres(texte: str, tableaux: bool = True) -> list[tuple[float, str]]:
    out = cd.chiffres(texte)
    if tableaux:
        out += [(v, u) for v, u, _ in table_numbers(texte, _unite_critere)]
    return out


def cite(attendu: dict, textes: list[str], tableaux: bool = True) -> bool:
    u = cd.UNITE_ATTENDU[attendu["unite"]]
    tol = cd.TOLERANCE[u]
    return any(uu == u and abs(v - float(attendu["valeur"])) <= tol
               for t in textes for v, uu in chiffres(t, tableaux))


def critere1(banc: dict, reponses: dict[tuple[str, int], str], tableaux: bool = True,
             exposition: dict | None = None) -> dict:
    """Taux de chiffres attendus cités justes, par conversation, avec le témoin de hasard (graine 7, comme D).

    Périmètre = conversations dont TOUS les tours ont une réponse : sur un run partiel, compter les attendus des
    conversations non jouées ferait un taux faux (trouvé sur l'essai du 25/09 : 0,6 % sur 1 conversation sur 57)."""
    exposition = exposition or json.loads(EXPOSITION.read_text(encoding="utf-8"))
    jouees = [i for i in banc["items"] if all((i["id"], t) in reponses for t in range(len(i["turns"])))]
    banc = {**banc, "items": jouees}
    par_conv, hors = {}, 0
    for item in banc["items"]:
        cibles = exposition["conversations"][item["id"]]["cible_par_attendu"]
        n, cites = 0, []
        for a, cible in zip(item["attendus"]["chiffres"], cibles):
            if cible is None:
                hors += 1
                continue
            n += 1
            cites.append(cite(a, [reponses.get((item["id"], t), "") for t in range(a["tour"], len(item["turns"]))],
                              tableaux))
        par_conv[item["id"]] = {"n": n, "cites": cites}
    rng = random.Random(7)
    avec = [i for i in banc["items"] if any(c is not None for c in exposition["conversations"][i["id"]]["cible_par_attendu"])]
    hits = total = 0
    for item in avec if len(avec) > 1 else []:  # une seule conversation : pas de témoin (None), jamais un faux 0
        autre = rng.choice([x for x in avec if x["id"] != item["id"]])
        textes = [reponses.get((item["id"], t), "") for t in range(len(item["turns"]))]
        for a, cible in zip(autre["attendus"]["chiffres"], exposition["conversations"][autre["id"]]["cible_par_attendu"]):
            if cible is None:
                continue
            total += 1
            hits += cite(a, textes, tableaux)
    n = sum(v["n"] for v in par_conv.values())
    if n == 0:
        raise ValueError("critère 1 sur zéro attendu : le banc ou l'exposition ne correspond pas")
    return {"taux": sum(sum(v["cites"]) for v in par_conv.values()) / n, "attendus": n, "hors_base_c": hors,
            "conversations": len(jouees),
            "temoin_hasard": hits / total if total else None, "par_conversation": par_conv}


def est_v2(version: str) -> bool:
    """Le cerveau v2 et ses variantes (v2 à l'étape 3, v2e4 et v2e4r à l'étape 4) : même trace, mêmes mesures."""
    return version == "v2" or version.startswith("v2e")


def vitesse_sortie(records: list[dict], modele: str = "zai-glm-5-3") -> dict:
    """Secondes par millier de jetons de sortie, médiane par appel au modèle (amendement v1.1 du CONTRAT-etape4 :
    publiée à côté de la latence brute, parce que la vitesse de l'API a varié de 4,4 s à 11-21 s entre le 25 et le
    26/09). Appels de la trace v2 appariés dans l'ordre aux appels comptés ; un tour dont les deux listes n'ont pas la
    même longueur est écarté, et compté."""
    import statistics
    s_par_k, ecartes = [], 0
    for r in records:
        am = (r.get("trace") or {}).get("appels_modele") or []
        comptes = [a for a in (r.get("appels") or []) if a.get("modele") == modele]
        if not am:
            continue
        if len(am) != len(comptes):
            ecartes += 1
            continue
        s_par_k += [a["secondes"] / (c["sortie"] / 1000) for a, c in zip(am, comptes) if c.get("sortie")]
    return {"secondes_par_k_sortie_mediane": round(statistics.median(s_par_k), 2) if s_par_k else None,
            "appels_mesures": len(s_par_k), "tours_ecartes": ecartes}


def adosses(records: list[dict], version: str) -> dict:
    """Chiffres affichés adossés aux fiches que la version a exposées (numbers.py), avec le témoin de hasard.

    - version sans fiche (chatgpt) : 0 % par construction, publié tel quel ;
    - version dont les sources ne sont pas nos fiches (chatgpt_web) : non calculable, jamais 0 %."""
    from src.eval.battery.corpus import Corpus
    from src.eval.battery.numbers import NumberChecker, NumberSummary, extract_claims
    if est_v2(version):
        return adosses_v2(records)
    if version == "chatgpt_web":
        n = sum(len(extract_claims(r["answer"])) for r in records)
        return {"statut": "non calculable (sources web, pas nos fiches)", "chiffres_cites": n, "taux": None}
    checker = NumberChecker(Corpus())
    resume, par_tour = NumberSummary(), {}
    for r in records:
        pos = [p for p in r.get("source_positions") or [] if p is not None]
        checks = checker.check(r["answer"], pos, anchor=False)
        resume.add(checks, bool(pos))
        par_tour[(r["id"], r["turn"])] = checks
    temoin = checker.chance_rate([r["answer"] for r in records],
                                 [[p for p in r.get("source_positions") or [] if p is not None] for r in records],
                                 [r["id"] for r in records])
    return {"statut": "sans fiche : 0 % par construction" if not resume.turns_exposing_fiches else "mesuré",
            "chiffres_cites": resume.n_claims, "taux": resume.rate("adosse"), "temoin_hasard": temoin,
            "tours_avec_fiches": resume.turns_exposing_fiches, "par_tour": par_tour}


def adosses_v2(records: list[dict]) -> dict:
    """v2 : chiffres affichés adossés aux valeurs que les outils ont rendues dans la conversation (gardées par la trace
    de chaque appel), ou écrits par l'élève (choix C4). Recompté ici avec l'extraction typée du critère 1 (`chiffres` :
    pct, eur, places, effectifs, tableaux compris ; tolérances de `critere_d`), sans passer par
    `src/v2/verificateur.py`. Les « admis », « inscrits », « diplômés » ne sont lus que par le vérificateur. Les fiches ne sont pas des positions du corpus : pas de témoin de
    hasard par permutation de fiches, le taux est une garantie structurelle vérifiée a posteriori."""
    par_conv: dict[str, list[dict]] = {}
    for r in sorted(records, key=lambda r: (r["id"], r["turn"])):
        par_conv.setdefault(r["id"], []).append(r)
    n, fautes, par_tour = 0, [], {}
    for tours in par_conv.values():
        valeurs, eleve = [], []
        for t in tours:
            for appel in (t.get("trace") or {}).get("outils", []):
                valeurs += appel.get("valeurs") or []
            eleve += chiffres(t["question"])
            checks = []
            for valeur, unite in chiffres(t["answer"]):
                tol = cd.TOLERANCE[unite]
                ok = any(v["unite"] == unite and abs(v["valeur"] - valeur) <= tol for v in valeurs)
                el = not ok and any(u == unite and abs(x - valeur) <= tol for x, u in eleve)
                checks.append({"value": valeur, "unit": unite, "status": "adosse" if ok else ("eleve" if el else "non_retrouve")})
                n += 1
                if not ok and not el:
                    fautes.append({"id": t["id"], "turn": t["turn"], "valeur": valeur, "unite": unite})
            par_tour[(t["id"], t["turn"])] = checks
    return {"statut": "mesuré (valeurs des outils tracées)", "chiffres_cites": n,
            "taux": (n - len(fautes)) / n if n else None, "non_adosses": fautes, "par_tour": par_tour}


def lire_banc(chemin: Path) -> dict:
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


def detail_par_tour(banc: dict, reponses: dict[tuple[str, int], str], tableaux: bool = True,
                    exposition: dict | None = None) -> dict[tuple[str, int], dict]:
    """Par tour : les chiffres attendus posés à ce tour, et s'ils sont cités justes (dans ce tour ou un suivant,
    même règle que `critere1`). Les attendus hors base C sont listés avec `trouve: None` (hors critère)."""
    exposition = exposition or json.loads(EXPOSITION.read_text(encoding="utf-8"))
    out: dict[tuple[str, int], dict] = {}
    for item in banc["items"]:
        if not all((item["id"], t) in reponses for t in range(len(item["turns"]))):
            continue
        cibles = exposition["conversations"][item["id"]]["cible_par_attendu"]
        for t in range(len(item["turns"])):
            out[(item["id"], t)] = {"attendus": 0, "cites_justes": 0, "hors_base_c": 0, "detail": []}
        for a, cible in zip(item["attendus"]["chiffres"], cibles):
            fiche = a.get("fiche") or {}
            libelle = f"{fiche.get('nom')} | {fiche.get('etablissement')}"
            case = out[(item["id"], a["tour"])]
            if cible is None:
                case["hors_base_c"] += 1
                case["detail"].append([a["valeur"], a["unite"], libelle, None])
                continue
            ok = cite(a, [reponses[(item["id"], t)] for t in range(a["tour"], len(item["turns"]))], tableaux)
            case["attendus"] += 1
            case["cites_justes"] += ok
            case["detail"].append([a["valeur"], a["unite"], libelle, ok])
    return out
