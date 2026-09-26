"""Rapport du juge de l'étape 4 (CONTRAT-etape4, sections 11 et 15), depuis les verdicts bruts. Aucun appel d'API.

Lit les verdicts `judge_v2` de l'étape 4 (v2e4 : vertical et gate F 1a), de l'étape 3 (v2) et de la référence figée
(prod et ChatGPT + recherche), et calcule :
- le critère principal : erreur de fait sur les 59 tours du vertical hors recouvrement avec le gate F, et sur les 79,
  de deux façons (demande de Jarvis, 26/09 19h17) : sur les tours jugés, et en comptant un tour en panne comme un
  échec de réponse (numérateur erreurs + pannes, dénominateur tous les tours). La décision se lit sur la seconde ;
- les garde-fous : refus <= 5 sur 79, note moyenne >= 4,17, note des tours sans outil de données >= 3,84 ;
- l'échantillon figé de 25 conversations, à côté de ChatGPT + recherche et de la prod ;
- la liste des erreurs de fait de l'étape 4, pour la relecture par famille (K, N, L, D, A, C).
    python3 docs/cerveau/etape4/mesures/rapport_juge.py
Sortie : docs/cerveau/etape4/mesures/rapport_juge.json.
"""
from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RACINE))
from src.eval.multiversion.lanceur import BANCS  # noqa: E402

R = RACINE / "results/multiversion"
VERDICTS = {"v2e4": R / "2026-09-26_v2e4/judge_v2/verdicts.jsonl", "v2": R / "2026-09-25_v2/judge_v2/verdicts.jsonl",
            "prod": R / "2026-09-25_reference/judge_v2/verdicts.jsonl",
            "chatgpt_web": R / "2026-09-25_reference/judge_v2/verdicts.jsonl"}
TRACES = {"v2e4": R / "2026-09-26_v2e4/v2e4__vertical.jsonl", "v2": R / "2026-09-25_v2/v2__vertical.jsonl"}
TRACES_GATEF = {"v2e4": R / "2026-09-26_v2e4/v2e4__gatef.jsonl", "v2": R / "2026-09-25_v2/v2__gatef.jsonl"}
OUTILS_DONNEES = {"chercher_formations", "chercher_masters", "lire_fiche", "comparer", "trouver_formation"}
CRITERES = ("references", "comprehension", "expression", "couverture")


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()).strip()


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    d = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, c - d) * 100, 1), round(min(1.0, c + d) * 100, 1)]


def recouvrement() -> set[tuple[str, int]]:
    g = json.loads(BANCS["gatef"].read_text())
    v = json.loads(BANCS["vertical"].read_text())
    gq = {_norm(t if isinstance(t, str) else t.get("question", "")) for q in g["questions"] for t in q["tours"]}
    return {(it["id"], i) for it in v["items"] for i, t in enumerate(it["turns"])
            if _norm(t if isinstance(t, str) else t.get("question", "")) in gq}


def verdicts(version: str, banc: str) -> dict:
    return {(x["id"], x["turn"]): x for x in map(json.loads, open(VERDICTS[version]))
            if x["version"] == version and x["banc"] == banc}


def note(x: dict) -> float:
    return sum(x[c] for c in CRITERES) / 4


def bloc(verd: dict, tours: list[tuple[str, int]], pannes: set) -> dict:
    juges = [verd[t] for t in tours if t in verd]
    k = sum(x["erreur_factuelle"] for x in juges)
    p = sum(1 for t in tours if t in pannes)
    n_tous = len(tours)
    return {"tours": n_tous, "juges": len(juges), "pannes": p,
            "erreurs": k, "part_sur_juges": round(100 * k / len(juges), 1) if juges else None,
            "ic95_sur_juges": wilson(k, len(juges)),
            "prudent_erreurs_plus_pannes": k + p, "part_prudente": round(100 * (k + p) / n_tous, 1),
            "ic95_prudent": wilson(k + p, n_tous),
            "refus": sum(x["refus"] for x in juges),
            "note": round(sum(note(x) for x in juges) / len(juges), 2) if juges else None}


def sans_outil_de_donnees(traces: Path) -> set[tuple[str, int]]:
    out = set()
    for r in map(json.loads, open(traces)):
        tr = r.get("trace") or {}
        if r.get("error") or tr.get("court_circuit"):
            continue
        if not any(o["nom"] in OUTILS_DONNEES and o.get("execute") for o in tr.get("outils", [])):
            out.add((r["id"], r["turn"]))
    return out


def main() -> dict:
    v = json.loads(BANCS["vertical"].read_text())
    tous = [(it["id"], i) for it in v["items"] for i in range(len(it["turns"]))]
    commun = recouvrement()
    hors = [t for t in tous if t not in commun]
    ech = json.loads((R / "echantillon_vertical_25.json").read_text())
    ids_ech = set(ech["ids"])
    tours_ech = [t for t in tous if t[0] in ids_ech]
    out = {"recouvrement": len(commun), "hors_recouvrement": len(hors)}
    for version in ("v2e4", "v2", "prod"):
        verd = verdicts(version, "vertical")
        pannes = set()
        if version in TRACES:
            pannes = {(r["id"], r["turn"]) for r in map(json.loads, open(TRACES[version])) if r.get("error")}
        d = {"vertical_79": bloc(verd, tous, pannes), "hors_recouvrement_59": bloc(verd, hors, pannes),
             "echantillon_34": bloc(verd, tours_ech, pannes),
             "pannes": sorted(f"{a}.{b}" for a, b in pannes),
             "pannes_hors_recouvrement": sorted(f"{a}.{b}" for a, b in pannes if (a, b) not in commun)}
        if version in TRACES:
            so = sans_outil_de_donnees(TRACES[version])
            j = [verd[t] for t in so if t in verd]
            d["sans_outil_de_donnees"] = {"tours": len(so), "juges": len(j), "erreurs": sum(x["erreur_factuelle"] for x in j),
                                          "note": round(sum(note(x) for x in j) / len(j), 2) if j else None}
        if version in TRACES_GATEF:
            vg = verdicts(version, "gatef")
            tg = [(r["id"], r["turn"]) for r in map(json.loads, open(TRACES_GATEF[version]))]
            d["gatef_32"] = bloc(vg, tg, set())
        out[version] = d
    out["chatgpt_web"] = {"echantillon_34": bloc(verdicts("chatgpt_web", "vertical"), tours_ech, set())}
    g = out["v2e4"]
    out["garde_fous"] = {
        "refus_le_5_sur_79": {"valeur": g["vertical_79"]["refus"], "tenu": g["vertical_79"]["refus"] <= 5},
        "note_ge_4_17": {"valeur": g["vertical_79"]["note"], "tenu": g["vertical_79"]["note"] >= 4.17},
        "note_sans_outil_ge_3_84": {"valeur": g["sans_outil_de_donnees"]["note"],
                                    "tenu": (g["sans_outil_de_donnees"]["note"] or 0) >= 3.84}}
    h = g["hors_recouvrement_59"]
    out["critere_principal"] = {"plancher": "< 10 %, au plus 5 sur 59 (version prudente)",
                                "sur_juges": f"{h['erreurs']}/{h['juges']}", "prudent": f"{h['prudent_erreurs_plus_pannes']}/{h['tours']}",
                                "tenu_version_prudente": h["prudent_erreurs_plus_pannes"] <= 5}
    out["erreurs_v2e4"] = [{"banc": x["banc"], "id": x["id"], "tour": x["turn"], "detail": x["erreur_detail"],
                            "hors_recouvrement": (x["id"], x["turn"]) not in commun if x["banc"] == "vertical" else None}
                           for b in ("vertical", "gatef") for x in verdicts("v2e4", b).values() if x["erreur_factuelle"]]
    Path(__file__).with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps({k: v for k, v in o.items() if k != "erreurs_v2e4"}, ensure_ascii=False, indent=1))
    print(f"{len(o['erreurs_v2e4'])} erreurs de fait (v2e4)")
