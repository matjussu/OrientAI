"""Décomposition de la latence du v2 à l'étape 3, depuis les traces existantes (aucun appel d'API).

Lecture seule : results/multiversion/2026-09-25_v2/v2__{vertical,lot0,gatef}.jsonl (code joué 52a0b14).
Sortie : docs/cerveau/etape4/mesures/latence_etape3.json. Commande, depuis la racine du dépôt :
    python docs/cerveau/etape4/mesures/latence_etape3.py
Script d'analyse de la phase A du contrat de l'étape 4 : ne touche ni src/v2 ni les traces.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
TRACES = RACINE / "results/multiversion/2026-09-25_v2"
SORTIE = Path(__file__).with_suffix(".json")
BANCS = ("vertical", "lot0", "gatef")


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    i = int(k)
    return round(xs[i] + (xs[min(i + 1, len(xs) - 1)] - xs[i]) * (k - i), 2)


def resume(xs):
    return {"n": len(xs), "mediane": q(xs, 0.5), "p90": q(xs, 0.9), "max": round(max(xs), 2) if xs else None,
            "somme": round(sum(xs), 1)}


def moindres_carres(X, y):
    """y = X b, résolu par les équations normales (3 variables au plus, sans dépendance externe)."""
    n = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(n)] for i in range(n)]
    B = [sum(r[i] * yy for r, yy in zip(X, y)) for i in range(n)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[piv], B[c], B[piv] = A[piv], A[c], B[piv], B[c]
        for r in range(n):
            if r != c and A[c][c]:
                f = A[r][c] / A[c][c]
                A[r] = [a - f * b for a, b in zip(A[r], A[c])]
                B[r] -= f * B[c]
    return [B[i] / A[i][i] for i in range(n)]


def analyser(banc: str) -> dict:
    tours = [json.loads(l) for l in open(TRACES / f"v2__{banc}.jsonl")]
    tours = [t for t in tours if t.get("trace") and not t["trace"].get("court_circuit")]
    total, filtre, modele, outils, reste = [], [], [], [], []
    n_appels, n_outils, sec_appel, rais_appel, ent_appel, sort_appel = [], [], [], [], [], []
    txt_outil: dict[str, list[int]] = {}
    sec_outil: dict[str, list[float]] = {}
    reecr, relance, fin_sans_outils_non_prevenue, fin_sans_outils = 0, 0, 0, 0
    X, y = [], []
    par_tour = []
    for t in tours:
        tr = t["trace"]
        lat = tr["latence_s"]
        am = tr["appels_modele"]
        glm = [a for a in t.get("appels", []) if a.get("modele") == "zai-glm-5-3"]
        s_mod = sum(a["secondes"] for a in am)
        s_out = sum(o.get("secondes") or 0 for o in tr["outils"] if o.get("execute"))
        total.append(lat["total"])
        filtre.append(lat.get("filtre", 0))
        modele.append(s_mod)
        outils.append(s_out)
        reste.append(lat["total"] - lat.get("filtre", 0) - s_mod - s_out)
        n_appels.append(len(am))
        n_outils.append(sum(1 for o in tr["outils"] if o.get("execute")))
        for i, a in enumerate(am):
            sec_appel.append(a["secondes"])
            rais_appel.append(a.get("raisonnement") or 0)
            if len(glm) == len(am):
                ent_appel.append(glm[i]["entree"])
                sort_appel.append(glm[i]["sortie"])
                X.append([1.0, glm[i]["entree"] / 1000, glm[i]["sortie"] / 1000])
                y.append(a["secondes"])
        for o in tr["outils"]:
            if o.get("execute"):
                txt_outil.setdefault(o["nom"], []).append(len(o.get("texte") or ""))
                sec_outil.setdefault(o["nom"], []).append(o.get("secondes") or 0)
        reecr += len(tr["brouillons"]) > 1
        relance += bool(tr.get("relance_vide"))
        if am and not am[-1]["outils_permis"]:
            fin_sans_outils += 1
            if not tr["plafond_atteint"]:
                fin_sans_outils_non_prevenue += 1
        par_tour.append({"id": t["id"], "tour": t["turn"], "total": lat["total"], "appels": len(am),
                         "modele_s": round(s_mod, 2), "outils_s": round(s_out, 3)})
    b = moindres_carres(X, y) if X else None
    lents = sorted(par_tour, key=lambda r: -r["total"])[: max(1, len(par_tour) // 10)]
    return {
        "tours": len(tours),
        "latence_totale_s": resume(total),
        "filtre_s": resume(filtre),
        "appels_modele_cumul_s": resume(modele),
        "outils_cumul_s": resume(outils),
        "reste_s": resume(reste),
        "part_du_total": {"filtre": round(sum(filtre) / sum(total), 3), "modele": round(sum(modele) / sum(total), 3),
                          "outils": round(sum(outils) / sum(total), 3), "reste": round(sum(reste) / sum(total), 3)},
        "appels_modele_par_tour": resume(n_appels),
        "outils_executes_par_tour": resume(n_outils),
        "secondes_par_appel_modele": resume(sec_appel),
        "raisonnement_par_appel_caracteres": resume(rais_appel),
        "jetons_entree_par_appel": resume(ent_appel),
        "jetons_sortie_par_appel": resume(sort_appel),
        "regression_secondes_par_appel": None if not b else {
            "formule": "secondes = a + b x (milliers de jetons en entrée) + c x (milliers de jetons en sortie)",
            "a_s": round(b[0], 2), "b_s_par_k_entree": round(b[1], 3), "c_s_par_k_sortie": round(b[2], 2),
            "n_appels": len(X)},
        "caracteres_rendus_par_outil": {k: resume(v) for k, v in sorted(txt_outil.items())},
        "secondes_par_outil": {k: resume(v) for k, v in sorted(sec_outil.items())},
        "tours_avec_reecriture": reecr,
        "tours_avec_relance_vide": relance,
        "reponse_finale_d_un_appel_sans_outils": fin_sans_outils,
        "dont_modele_non_prevenu_du_plafond": fin_sans_outils_non_prevenue,
        "decile_le_plus_lent": lents,
    }


if __name__ == "__main__":
    out = {"source": "results/multiversion/2026-09-25_v2/v2__*.jsonl (code 52a0b14)", **{b: analyser(b) for b in BANCS}}
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for b in BANCS:
        r = out[b]
        print(b, json.dumps({k: r[k] for k in ("tours", "latence_totale_s", "part_du_total", "appels_modele_par_tour",
                                                "secondes_par_appel_modele", "regression_secondes_par_appel",
                                                "reponse_finale_d_un_appel_sans_outils",
                                                "dont_modele_non_prevenu_du_plafond")}, ensure_ascii=False))


# ── Leviers : latence contrefactuelle (estimation, pas une mesure) ─────────────────────────────────────────────────
def leviers(banc: str, reg: dict) -> dict:
    """Rejoue chaque tour avec la loi mesurée secondes = a + c x k_sortie (l'entrée n'a pas d'effet mesuré), en
    retirant une part du raisonnement, les appels de réécriture, ou le filtre (lancé en parallèle du 1er appel).
    La part de raisonnement d'un appel est estimée par ses caractères (raisonnement / (raisonnement + texte +
    arguments d'outils)) : c'est une approximation, pas un compte de jetons."""
    a, c = reg["a_s"], reg["c_s_par_k_sortie"]
    tours = [json.loads(l) for l in open(TRACES / f"v2__{banc}.jsonl")]
    sc = {"mesure": [], "estime_sans_levier": [], "raisonnement_moitie": [], "raisonnement_zero": [], "sans_reecriture": [],
          "filtre_en_parallele": [], "raisonnement_moitie_et_filtre_parallele": []}
    cout = {"entree": 0, "sortie": 0}
    for t in tours:
        tr = t.get("trace") or {}
        if not tr or tr.get("court_circuit"):
            continue
        am = tr["appels_modele"]
        glm = [x for x in t.get("appels", []) if x.get("modele") == "zai-glm-5-3"]
        if len(glm) != len(am):
            continue
        cout["entree"] += sum(x["entree"] for x in glm)
        cout["sortie"] += sum(x["sortie"] for x in glm)
        filtre = tr["latence_s"].get("filtre", 0)
        n_brouillon1 = None
        if len(tr["brouillons"]) > 1:   # appels après le 1er brouillon = réécriture
            fin1 = next(i for i, x in enumerate(am) if not x["outils_permis"] or x["finish_reason"] == "stop")
            n_brouillon1 = fin1 + 1
        args = {i: 0 for i in range(len(am))}
        def lat(r_rais: float, garder=lambda i: True) -> float:
            s = 0.0
            for i, (x, g) in enumerate(zip(am, glm)):
                if not garder(i):
                    continue
                rais, txt = x.get("raisonnement") or 0, x.get("caracteres_texte") or 0
                part = rais / (rais + txt + 200) if (rais + txt) else 0   # 200 caractères d'arguments d'outil, supposé
                s += a + c * g["sortie"] / 1000 * (1 - r_rais * part)
            return s
        base = lat(0)
        reste = tr["latence_s"]["total"] - filtre - sum(x["secondes"] for x in am)
        sc["mesure"].append(tr["latence_s"]["total"])
        sc["estime_sans_levier"].append(filtre + base + reste)
        premier = (a + c * glm[0]["sortie"] / 1000) if glm else 0
        sc["raisonnement_moitie"].append(filtre + lat(0.5) + reste)
        sc["raisonnement_zero"].append(filtre + lat(1.0) + reste)
        sc["sans_reecriture"].append(filtre + lat(0, (lambda i: i < n_brouillon1) if n_brouillon1 else (lambda i: True)) + reste)
        # filtre lancé en même temps que le 1er appel : on n'attend que le plus long des deux
        sc["filtre_en_parallele"].append(base + reste + max(0.0, filtre - premier))
        sc["raisonnement_moitie_et_filtre_parallele"].append(lat(0.5) + reste + max(0.0, filtre - premier))
    ref = {k: q(v, 0.9) for k, v in sc.items()}
    return {"modele_loi": reg, "comparer_a": "estime_sans_levier (même loi, aucun levier), pas à la mesure", "scenarios": {k: {"mediane": q(v, 0.5), "p90": q(v, 0.9)} for k, v in sc.items()},
            "jetons": cout, "cout_usd_entree_sortie": {"entree": round(cout["entree"] * 1.4e-6, 2),
                                                      "sortie": round(cout["sortie"] * 4.4e-6, 2)}}


if __name__ == "__main__":
    out = json.loads(SORTIE.read_text())
    for b in BANCS:
        out[b]["leviers_estimes"] = leviers(b, out[b]["regression_secondes_par_appel"])
        print(b, json.dumps(out[b]["leviers_estimes"]["scenarios"], ensure_ascii=False),
              out[b]["leviers_estimes"]["cout_usd_entree_sortie"])
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
