"""Banc E : analyse et application de la règle écrite (results/banc_e/PROTOCOLE.md v0.3, sections 4 et 6).

    python -m src.eval.rapport_e            # écrit results/banc_e/analyse.json (+ export explorateur avec --export)

Aucun appel payant. Réutilise les instruments de D sans les modifier : critère 1 et témoin (`critere_d`),
bootstrap apparié sur les conversations et accord du rejugement (`rapport_d`). Les contrôles de complétude
se lisent sur les fichiers, jamais sur un code de sortie.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics as st
from datetime import datetime
from pathlib import Path

from src.eval import critere_d as cd
from src.eval import rapport_d as rd
from src.eval.battery.judge import CRITERIA
from src.eval.exposition_d import BANC

RACINE = Path(__file__).resolve().parents[2]
E = RACINE / "results/banc_e"
EXPOSITION = RACINE / "results/donnee_etape_d/exposition.json"
REF = "A-mistral-medium-2604"
FORMATS = ("A", "C")
MODELES = ("mistral-medium-2604", "zai-glm-5-2", "zai-glm-5-3", "mistral-small-2603")
COMBOS = [f"{f}-{m}" for f in FORMATS for m in MODELES]
SOUVERAIN = "mistral-small-2603"

# Seuils écrits avant les résultats (protocole v0.3, section 6 ; dispersion de R dans D, RAPPORT D §3).
SEUIL_DEFAUTS = 0.02
MOTS = (200, 600)
MARGE_REFUS = 0.05
SEUIL_ERREURS_OUTIL = 0.05
NON_INFERIORITE_P = -0.03
DEPARTAGE_E = 0.02
DISPERSION_P = 0.022

_NOMBRE = re.compile(r"\d[\d\s  ]*(?:[.,]\d+)?")


def lire(p: Path) -> list[dict]:
    return rd.lire(p)


def recs(c: str, gens=(1, 2)) -> dict[int, list[dict]]:
    return {g: lire(E / "runs" / c / f"g{g}.jsonl") for g in gens if (E / "runs" / c / f"g{g}.jsonl").exists()}


# ── Complétude ───────────────────────────────────────────────────────────────────────────────
def completude(banc: dict) -> dict:
    tours = {(i["id"], t) for i in banc["items"] for t in range(len(i["turns"]))}
    out = {}
    for c in COMBOS:
        for g, rs in recs(c).items():
            cles = [(r["id"], r["turn"]) for r in rs]
            out[f"{c}/g{g}"] = {"tours": len(rs), "doublons": len(cles) - len(set(cles)),
                                "erreurs": sum(bool(r.get("erreur")) for r in rs),
                                "vert": set(cles) == tours and len(cles) == len(tours) and not any(r.get("erreur") for r in rs)}
    return out


# ── Critère 1, avec la mesure du biais des tableaux (signalement seulement, section 6 étape 1) ─
def cite_tableau(attendu: dict, textes: list[str]) -> bool:
    """Chiffre attendu présent dans une ligne de tableau markdown, sans exiger l'unité (elle est dans l'en-tête)."""
    tol = cd.TOLERANCE.get(cd.UNITE_ATTENDU.get(attendu["unite"], ""), 0.5)
    for t in textes:
        for ligne in t.splitlines():
            if ligne.lstrip().startswith("|"):
                for m in _NOMBRE.findall(ligne):
                    try:
                        v = float(re.sub(r"[\s  ]", "", m).replace(",", "."))
                    except ValueError:
                        continue
                    if abs(v - float(attendu["valeur"])) <= tol:
                        return True
    return False


def critere1(banc: dict, expo: dict) -> dict:
    out = {}
    for c in COMBOS:
        par_gen = {}
        for g, rs in recs(c).items():
            rep = {(r["id"], r["turn"]): r.get("answer") or "" for r in rs}
            pc = cd.par_conversation(banc, expo, rep)
            n = ok_tab = 0
            for item in banc["items"]:
                cibles = expo["conversations"][item["id"]]["cible_par_attendu"]
                for a, cible in zip(item["attendus"]["chiffres"], cibles):
                    if cible is None:
                        continue
                    textes = [rep.get((item["id"], t), "") for t in range(a["tour"], len(item["turns"]))]
                    n += 1
                    ok_tab += cd.cite(a, textes) or cite_tableau(a, textes)
            par_gen[g] = {"pc": pc, "P": cd.taux(pc), "temoin": cd.temoin(banc, expo, rep),
                          "P_ou_tableau": ok_tab / n if n else None}
        out[c] = par_gen
    return out


# ── Juge ─────────────────────────────────────────────────────────────────────────────────────
def verdicts() -> tuple[dict, dict]:
    v = {(x["combinaison"], x["id"], x["turn"], x.get("generation", 1)): x for x in lire(E / "judge/verdicts.jsonl")}
    r = {(x["combinaison"], x["id"], x["turn"], x.get("generation", 1)): x for x in lire(E / "judge/verdicts_rejuge.jsonl")}
    return v, r


def juge_par_conversation(v: dict, combo: str, banc: dict, gens=(1,)) -> dict[str, dict]:
    out = {}
    for item in banc["items"]:
        ks = [(combo, item["id"], t, g) for g in gens for t in range(len(item["turns"])) if (combo, item["id"], t, g) in v]
        out[item["id"]] = {"n": len(ks), **{c: sum(v[k][c] for k in ks) for c in CRITERIA},
                           "moyenne_4": sum(st.mean(v[k][c] for c in CRITERIA) for k in ks),
                           "erreur_factuelle": sum(bool(v[k].get("erreur_factuelle")) for k in ks),
                           "refus": sum(bool(v[k].get("refus")) for k in ks)}
    return out


# ── Secondaires, forme, coût, débit ──────────────────────────────────────────────────────────
def secondaires(c: str) -> dict:
    par_g = recs(c)
    rs = [r for g in sorted(par_g) for r in par_g[g]]
    manifs = [json.loads((E / "runs" / c / f"manifest_g{g}.json").read_text()) for g in par_g
              if (E / "runs" / c / f"manifest_g{g}.json").exists()]
    n = len(rs)
    appels = [a for r in rs for a in r.get("appels_outil") or []]
    g1 = par_g.get(1, [])
    debits = []
    for m in manifs:
        for p in m.get("passages", []):
            if p["tours_joues"] and p["secondes_mur"]:
                debits.append({"workers": p["workers"], "tours": p["tours_joues"], "secondes_mur": p["secondes_mur"],
                               "tours_par_minute": round(60 * p["tours_joues"] / p["secondes_mur"], 1)})
    return {"tours": n,
            "defauts_g1": sum(1 for r in g1 if r.get("erreur") or not (r.get("answer") or "").strip()
                              or r.get("finish_reason") == "length") / len(g1) if g1 else None,
            "mots_mediane": st.median(len((r.get("answer") or "").split()) for r in rs) if rs else None,
            "secondes_mediane": st.median(r.get("secondes", 0) for r in rs) if rs else None,
            "cout_usd_par_tour": round(sum(m["cout_usd"] for m in manifs) / n, 5) if n else None,
            "cout_usd_total": round(sum(m["cout_usd"] for m in manifs), 3),
            "prix_source": manifs[0]["prix_source"] if manifs else None,
            "tours_avec_appel_outil": sum(bool(r.get("appels_outil")) for r in rs) / n if n else None,
            "appels_outil": len(appels), "appels_outil_erreurs": sum(1 for a in appels if a.get("erreur")),
            "n429": sum(m.get("n429", 0) for m in manifs), "debit": debits,
            "modeles_rendus": sorted({x for m in manifs for x in m["modeles_rendus"]}),
            "commits": sorted({m["commit"][:7] for m in manifs}), "git_dirty": any(m["git_dirty"] for m in manifs)}


# ── Règle de décision (section 6) et déclenchement de la génération 2 (section 4) ───────────────
def taux_juge(jpc: dict, cle: str) -> float:
    n = sum(x["n"] for x in jpc.values())
    return sum(x[cle] for x in jpc.values()) / n if n else float("nan")


def decider(c1: dict, jpc: dict, sec: dict, pc_fusion) -> dict:
    ref_refus = taux_juge(jpc[REF], "refus")
    P = {c: cd.taux(pc_fusion(c1[c])) for c in COMBOS}
    Ptab = {c: st.mean(g["P_ou_tableau"] for g in c1[c].values()) for c in COMBOS}
    lignes = {}
    for c in COMBOS:
        s, motifs0 = sec[c], []
        if s["defauts_g1"] is None or s["defauts_g1"] > SEUIL_DEFAUTS:
            motifs0.append(f"défauts {s['defauts_g1']}")
        if s["mots_mediane"] is None or not MOTS[0] <= s["mots_mediane"] <= MOTS[1]:
            motifs0.append(f"mots médians {s['mots_mediane']}")
        refus = taux_juge(jpc[c], "refus")
        if refus > ref_refus + MARGE_REFUS:
            motifs0.append(f"refus {refus:.3f} > R {ref_refus:.3f} + {MARGE_REFUS}")
        if c.startswith("C-") and s["appels_outil"] and s["appels_outil_erreurs"] / s["appels_outil"] > SEUIL_ERREURS_OUTIL:
            motifs0.append(f"erreurs d'outil {s['appels_outil_erreurs']}/{s['appels_outil']}")
        dP, dPtab = P[c] - P[REF], Ptab[c] - Ptab[REF]
        etape1 = dP >= NON_INFERIORITE_P
        signale_tableau = (not etape1) and dPtab >= NON_INFERIORITE_P
        dE = rd.boot(jpc[c], jpc[REF], "erreur_factuelle") if c != REF else None
        bat_r = bool(dE and dE["ic95"][1] < 0)
        lignes[c] = {"etape0_ecartee": bool(motifs0), "motifs_etape0": motifs0, "P": P[c], "dP": dP,
                     "P_ou_tableau": Ptab[c], "dP_ou_tableau": dPtab, "etape1_non_inferieure": etape1,
                     "signalee_biais_tableaux": signale_tableau, "erreur_factuelle": taux_juge(jpc[c], "erreur_factuelle"),
                     "moyenne_4": taux_juge(jpc[c], "moyenne_4"), "dE_contre_R": dE, "bat_R": bat_r,
                     "cout_usd_par_tour": sec[c]["cout_usd_par_tour"]}
    cand = [c for c, l in lignes.items() if c != REF and not l["etape0_ecartee"] and l["etape1_non_inferieure"] and l["bat_R"]]
    cand.sort(key=lambda c: lignes[c]["dE_contre_R"]["delta"])
    # Classement par dE ; deux voisines à moins de 2 points se départagent par la moyenne des 4 critères, puis le coût.
    classement, critere_depart = list(cand), {}
    change = True
    while change:
        change = False
        for i in range(len(classement) - 1):
            a, b = lignes[classement[i]], lignes[classement[i + 1]]
            if (b["dE_contre_R"]["delta"] - a["dE_contre_R"]["delta"] < DEPARTAGE_E
                    and (b["moyenne_4"], -b["cout_usd_par_tour"]) > (a["moyenne_4"], -a["cout_usd_par_tour"])):
                classement[i], classement[i + 1] = classement[i + 1], classement[i]
                change = True
    choix = classement[0] if classement else REF
    g2 = {"declenchee": False, "raison": "moins de 2 combinaisons battent R : rien à départager"}
    if len(classement) >= 2:
        a, b = classement[:2]
        ecart_e = abs(lignes[a]["dE_contre_R"]["delta"] - lignes[b]["dE_contre_R"]["delta"])
        if ecart_e < DEPARTAGE_E:
            critere_depart = {"critere": "moyenne_4", **rd.boot(jpc[a], jpc[b], "moyenne_4")}
        else:
            critere_depart = {"critere": "erreur_factuelle", **rd.boot(jpc[a], jpc[b], "erreur_factuelle")}
        ic = critere_depart["ic95"]
        g2 = {"declenchee": ic[0] <= 0 <= ic[1], "combinaisons": [a, b], "comparaison": critere_depart,
              "raison": f"IC95 de {critere_depart['critere']} ({a} - {b}) = [{ic[0]:+.3f} ; {ic[1]:+.3f}]"}
    souverain = {}
    for c in COMBOS:
        if c.endswith(SOUVERAIN) and c != choix:
            l = lignes[c]
            b = rd.boot(jpc[c], jpc[choix], "erreur_factuelle")
            souverain[c] = {"etape0_ok": not l["etape0_ecartee"], "etape1_ok": l["etape1_non_inferieure"],
                            "dE_contre_choix": b,
                            "equivalent_souverain": (not l["etape0_ecartee"]) and l["etape1_non_inferieure"]
                            and b["ic95"][0] <= 0 <= b["ic95"][1]}
    return {"reference": REF, "lignes": lignes, "candidates_classees": classement, "choix": choix,
            "raison": "aucune combinaison ne bat R : on garde R" if not classement else f"1re du classement : {choix}",
            "generation_2": g2, "temoin_souverain": souverain}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--export", action="store_true")
    args = ap.parse_args(argv)
    banc = json.loads(BANC.read_bytes())
    expo = json.loads(EXPOSITION.read_bytes())
    comp = completude(banc)
    c1 = critere1(banc, expo)
    v, r = verdicts()
    gens_juge = sorted({k[3] for k in v}) or [1]
    comp_juge = {c: {g: sum(1 for k in v if k[0] == c and k[3] == g) for g in gens_juge} for c in COMBOS}
    accord = rd.accord_juge(v, r)
    jpc = {c: juge_par_conversation(v, c, banc, gens=tuple(gens_juge)) for c in COMBOS}
    sec = {c: secondaires(c) for c in COMBOS}
    decision = decider(c1, jpc, sec, rd.fusion)
    matrice = {}
    for c in COMBOS:
        tot = {k: sum(jpc[c][i][k] for i in jpc[c]) for k in ("n", *CRITERIA, "erreur_factuelle", "refus")}
        n = tot["n"] or float("nan")
        matrice[c] = {**{f"P_g{g}": x["P"] for g, x in c1[c].items()}, "P": decision["lignes"][c]["P"],
                      **{f"temoin_g{g}": x["temoin"] for g, x in c1[c].items()},
                      "juge": {**{k: tot[k] / n for k in CRITERIA}, "moyenne_4": st.mean(tot[k] / n for k in CRITERIA),
                               "erreur_factuelle": tot["erreur_factuelle"] / n, "refus": tot["refus"] / n, "n": tot["n"]},
                      **sec[c]}
    doc = {"protocole_sha256": hashlib.sha256((E / "PROTOCOLE.md").read_bytes()).hexdigest(),
           "genere_le": datetime.now().isoformat(timespec="seconds"),
           "exposition_sha256": hashlib.sha256(EXPOSITION.read_bytes()).hexdigest(),
           "completude_generation": comp, "completude_generation_verte": all(x["vert"] for x in comp.values()),
           "completude_juge": comp_juge,
           "completude_juge_verte": all(n == 79 for c in comp_juge for n in comp_juge[c].values())
           and all(1 in comp_juge[c] for c in COMBOS),
           "rejuges": accord["n"], "accord_juge": accord, "matrice": matrice, "decision": decision}
    if args.export:
        from src.eval import grille_d, grille_e
        rd.D, rd.COMBOS = E, COMBOS  # l'export de D, pointé sur E (lecture seule, dans ce processus)
        grille_d.PRIX = {**grille_d.PRIX, **grille_e.PRIX}
        checker, position = rd.outils_chiffres()
        doc["export"] = rd.exporter(banc, expo, v and {k[:3]: x for k, x in v.items() if k[3] == 1},
                                    r and {k[:3]: x for k, x in r.items() if k[3] == 1}, checker, position, matrice,
                                    E / "export/banc_e.explorateur.json")
    (E / "analyse.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"generation_verte": doc["completude_generation_verte"], "juge_vert": doc["completude_juge_verte"],
                      "choix": decision["choix"], "g2": decision["generation_2"]}, ensure_ascii=False, default=str))
    return 0 if doc["completude_generation_verte"] and doc["completude_juge_verte"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
