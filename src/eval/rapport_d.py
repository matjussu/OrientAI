"""Étape D : analyse de la grille et application de la règle écrite (PROTOCOLE.md v0.2, section 10).

    python -m src.eval.rapport_d            # écrit results/donnee_etape_d/analyse.json et l'export explorateur

Aucun appel payant. Tout ce qui est calculé ici était défini dans le protocole avant les résultats :
critère 1 (chiffres attendus cités justes, témoin de hasard), dispersion (bootstrap apparié sur les
conversations, écart entre les 2 générations de la référence), juge (génération 1, accord du rejugement),
règle de décision étape par étape. Les contrôles de complétude rougissent sur les fichiers, jamais sur un
code de sortie.
"""
from __future__ import annotations

import hashlib
import json
import random
import statistics as st
from pathlib import Path

from src.eval import critere_d as cd
from src.eval.battery.judge import CRITERIA
from src.eval.exposition_d import BANC

RACINE = Path(__file__).resolve().parents[2]
D = RACINE / "results/donnee_etape_d"
REF = "A-mistral-medium-2604"
FORMATS = ("A", "B", "C")
MODELES = ("mistral-medium-2604", "mistral-large-2512", "zai-glm-5-2")
COMBOS = [f"{f}-{m}" for f in FORMATS for m in MODELES]
TIRAGES = 10_000
GRAINE = 7
# Ordre de simplicité (règle §10.4) : A, puis B, puis C.
SIMPLICITE = {"A": 0, "B": 1, "C": 2}


def lire(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


# ── Complétude ───────────────────────────────────────────────────────────────────────────────
def completude(banc: dict) -> dict:
    tours = {(i["id"], t) for i in banc["items"] for t in range(len(i["turns"]))}
    out = {}
    for c in COMBOS:
        for g in (1, 2):
            recs = lire(D / "runs" / c / f"g{g}.jsonl")
            cles = [(r["id"], r["turn"]) for r in recs]
            out[f"{c}/g{g}"] = {"conversations": len({r["id"] for r in recs}), "tours": len(recs),
                                "doublons": len(cles) - len(set(cles)), "erreurs": sum(bool(r.get("erreur")) for r in recs),
                                "vert": set(cles) == tours and len(cles) == len(tours)
                                and not any(r.get("erreur") for r in recs)}
    return out


def erreurs_429() -> dict:
    out = {}
    for m in MODELES:
        n = 0
        for f in FORMATS:
            for g in (1, 2):
                for p in (D / "runs" / f"{f}-{m}").glob(f"g{g}.erreurs.jsonl"):
                    n += sum("429" in (r.get("erreur") or "") for r in lire(p))
        out[m] = n
    return out


# ── Critère 1 ────────────────────────────────────────────────────────────────────────────────
def critere1(banc: dict, expo: dict) -> dict:
    out = {}
    for c in COMBOS:
        par_gen = {}
        for g in (1, 2):
            recs = lire(D / "runs" / c / f"g{g}.jsonl")
            if not recs:
                continue
            rep = {(r["id"], r["turn"]): r.get("answer") or "" for r in recs}
            pc = cd.par_conversation(banc, expo, rep)
            par_gen[g] = {"pc": pc, "P": cd.taux(pc), "temoin": cd.temoin(banc, expo, rep)}
        out[c] = par_gen
    return out


def fusion(par_gen: dict) -> dict[str, dict]:
    """Les deux générations mises bout à bout par conversation : n et cités doublés, même poids."""
    ids = par_gen[1]["pc"].keys()
    return {i: {"n": sum(par_gen[g]["pc"][i]["n"] for g in par_gen),
                "cites": [x for g in par_gen for x in par_gen[g]["pc"][i]["cites"]]} for i in ids}


# ── Juge ─────────────────────────────────────────────────────────────────────────────────────
def verdicts() -> tuple[dict, dict]:
    v = {(x["combinaison"], x["id"], x["turn"]): x for x in lire(D / "judge/verdicts.jsonl")}
    r = {(x["combinaison"], x["id"], x["turn"]): x for x in lire(D / "judge/verdicts_rejuge.jsonl")}
    return v, r


def kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def accord_juge(v: dict, r: dict) -> dict:
    cles = [k for k in r if k in v]
    out = {"n": len(cles)}
    for champ in ("erreur_factuelle", "refus"):
        a = [bool(v[k].get(champ)) for k in cles]
        b = [bool(r[k].get(champ)) for k in cles]
        out[champ] = {"accord": sum(x == y for x, y in zip(a, b)) / len(cles) if cles else None,
                      "kappa": kappa(a, b), "desaccord": sum(x != y for x, y in zip(a, b)) / len(cles) if cles else None,
                      "taux_passe1": sum(a) / len(cles) if cles else None, "taux_passe2": sum(b) / len(cles) if cles else None}
    for c in CRITERIA:
        out[c] = {"ecart_absolu_moyen": st.mean(abs(v[k][c] - r[k][c]) for k in cles) if cles else None}
    return out


def juge_par_conversation(v: dict, combo: str, banc: dict) -> dict[str, dict]:
    """Par conversation : sommes et comptes des critères du juge (génération 1)."""
    out = {}
    for item in banc["items"]:
        ks = [(combo, item["id"], t) for t in range(len(item["turns"])) if (combo, item["id"], t) in v]
        out[item["id"]] = {"n": len(ks), **{c: sum(v[k][c] for k in ks) for c in CRITERIA},
                           "erreur_factuelle": sum(bool(v[k].get("erreur_factuelle")) for k in ks),
                           "refus": sum(bool(v[k].get("refus")) for k in ks)}
    return out


def boot(x: dict, r: dict, cle: str, tirages: int = TIRAGES, graine: int = GRAINE) -> dict:
    """IC95 apparié sur les conversations de moy(x) - moy(r) pour une somme `cle` rapportée au nombre de tours."""
    ids = [i for i in x if x[i]["n"] and r[i]["n"]]
    rng = random.Random(graine)
    def m(d, tir):
        n = sum(d[i]["n"] for i in tir)
        return sum(d[i][cle] for i in tir) / n
    deltas = sorted(m(x, t) - m(r, t) for t in ([rng.choice(ids) for _ in ids] for _ in range(tirages)))
    return {"delta": m(x, ids) - m(r, ids), "ic95": [deltas[int(0.025 * tirages)], deltas[int(0.975 * tirages) - 1]]}


# ── Secondaires ──────────────────────────────────────────────────────────────────────────────
def secondaires(c: str) -> dict:
    recs = lire(D / "runs" / c / "g1.jsonl") + lire(D / "runs" / c / "g2.jsonl")
    manifs = [json.loads((D / "runs" / c / f"manifest_g{g}.json").read_text()) for g in (1, 2)
              if (D / "runs" / c / f"manifest_g{g}.json").exists()]
    n = len(recs)
    return {"mots_mediane": st.median(len((r.get("answer") or "").split()) for r in recs) if recs else None,
            "secondes_mediane": st.median(r.get("secondes", 0) for r in recs) if recs else None,
            "cout_usd_par_tour": round(sum(m["cout_usd"] for m in manifs) / n, 5) if n else None,
            "cout_usd_total": round(sum(m["cout_usd"] for m in manifs), 3),
            "prix_source": manifs[0]["prix_source"] if manifs else None,
            "tours_avec_appel_outil": sum(bool(r.get("appels_outil")) for r in recs) / n if n else None,
            "appels_outil_erreurs": sum(1 for r in recs for a in r.get("appels_outil") or [] if a.get("erreur")),
            "commits": sorted({m["commit"][:7] for m in manifs}), "git_dirty": any(m["git_dirty"] for m in manifs)}


# ── Règle de décision (§10) ──────────────────────────────────────────────────────────────────
def decider(c1: dict, jpc: dict, accord: dict, sec: dict) -> dict:
    ref = fusion(c1[REF])
    ecart_ref = abs(c1[REF][1]["P"] - c1[REF][2]["P"]) if 2 in c1[REF] else None
    lignes = {}
    for c in COMBOS:
        if c == REF:
            lignes[c] = {"reference": True}
            continue
        x = fusion(c1[c])
        g = cd.bootstrap_delta(x, ref)
        gagne = g["ic95"][0] > 0 and (ecart_ref is None or g["delta"] > ecart_ref)
        motifs = []
        for champ in ("erreur_factuelle", "refus"):
            b = boot(jpc[c], jpc[REF], champ)
            if (b["delta"] > 0 and b["ic95"][0] > 0) or b["delta"] > accord[champ]["desaccord"]:
                motifs.append(f"{champ} : delta {b['delta']:+.3f}, IC95 [{b['ic95'][0]:+.3f} ; {b['ic95'][1]:+.3f}], "
                              f"desaccord du juge {accord[champ]['desaccord']:.3f}")
        for crit in ("expression", "comprehension", "couverture"):
            b = boot(jpc[c], jpc[REF], crit)
            if b["ic95"][1] < 0 or -b["delta"] > accord[crit]["ecart_absolu_moyen"]:
                motifs.append(f"{crit} : delta {b['delta']:+.3f}, IC95 [{b['ic95'][0]:+.3f} ; {b['ic95'][1]:+.3f}], "
                              f"ecart moyen du rejugement {accord[crit]['ecart_absolu_moyen']:.3f}")
        lignes[c] = {"gain": g, "ecart_generations_ref": ecart_ref, "gagne": gagne, "ecartee": bool(motifs),
                     "motifs_ecart": motifs}
    candidates = [c for c, l in lignes.items() if l.get("gagne") and not l.get("ecartee")]
    if not candidates:
        return {"lignes": lignes, "candidates": [], "choix": REF, "raison": "aucune candidate : on garde la reference (§10.5)"}
    candidates.sort(key=lambda c: -cd.taux(fusion(c1[c])))
    meilleure, egales = candidates[0], []
    for c in candidates[1:]:
        b = cd.bootstrap_delta(fusion(c1[meilleure]), fusion(c1[c]))
        if b["ic95"][0] <= 0:
            egales.append(c)
    groupe = [meilleure] + egales
    choix = min(groupe, key=lambda c: (SIMPLICITE[c[0]], sec[c]["cout_usd_par_tour"]))
    return {"lignes": lignes, "candidates": candidates, "egales_a_la_meilleure": egales, "choix": choix,
            "raison": f"meilleure P : {meilleure} ; egales dans l'IC95 : {egales or 'aucune'} ; "
                      "departage par simplicite (A, B, C) puis cout par tour (§10.4)"}


def main() -> int:
    banc = json.loads(BANC.read_bytes())
    expo = json.loads((D / "exposition.json").read_bytes())
    comp = completude(banc)
    c1 = critere1(banc, expo)
    v, r = verdicts()
    comp_juge = {c: sum(1 for k in v if k[0] == c) for c in COMBOS}
    juge_vert = all(n == 79 for n in comp_juge.values())
    accord = accord_juge(v, r)
    jpc = {c: juge_par_conversation(v, c, banc) for c in COMBOS}
    sec = {c: secondaires(c) for c in COMBOS}
    decision = decider(c1, jpc, accord, sec)
    matrice = {}
    for c in COMBOS:
        tot = {k: sum(jpc[c][i][k] for i in jpc[c]) for k in ("n", *CRITERIA, "erreur_factuelle", "refus")}
        matrice[c] = {
            "P_g1": c1[c][1]["P"], "P_g2": c1[c].get(2, {}).get("P"), "P": cd.taux(fusion(c1[c])),
            "temoin_g1": c1[c][1]["temoin"], "temoin_g2": c1[c].get(2, {}).get("temoin"),
            "juge": {**{k: tot[k] / tot["n"] for k in CRITERIA}, "moyenne_4": st.mean(tot[k] / tot["n"] for k in CRITERIA),
                     "erreur_factuelle": tot["erreur_factuelle"] / tot["n"], "refus": tot["refus"] / tot["n"]},
            **sec[c]}
    checker, position = outils_chiffres()
    ad = adosses(checker, position, expo)
    for c in COMBOS:
        matrice[c]["chiffres_adosses"] = ad[c]
    export = exporter(banc, expo, v, r, checker, position, matrice, D / "export/etape_d.explorateur.json")
    doc = {"protocole_sha256": hashlib.sha256((D / "PROTOCOLE.md").read_bytes()).hexdigest(),
           "export": export,
           "exposition_sha256": hashlib.sha256((D / "exposition.json").read_bytes()).hexdigest(),
           "attendus": {"critere": expo["n_attendus_critere"], "hors": expo["n_attendus_hors"]},
           "completude_generation": comp, "completude_generation_verte": all(x["vert"] for x in comp.values()),
           "completude_juge": comp_juge, "completude_juge_verte": juge_vert,
           "rejuges": accord["n"], "erreurs_429_par_modele": erreurs_429(),
           "accord_juge": accord, "matrice": matrice, "decision": decision}
    (D / "analyse.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"generation_verte": doc["completude_generation_verte"], "juge_vert": juge_vert,
                      "choix": decision["choix"]}, ensure_ascii=False))
    return 0 if doc["completude_generation_verte"] and juge_vert else 1



# ── Chiffres adossés aux fiches exposées (numbers.py, secondaire §7) et export explorateur ────
def outils_chiffres():
    """NumberChecker du banc sur le corpus B-2, avec les positions des fiches exposées."""
    from src.base_c.outils import Base
    from src.eval.battery.corpus import Corpus
    from src.eval.battery.numbers import NumberChecker
    from src.eval.format_d import Formats
    corpus = Corpus(RACINE / "data/processed/formations_etape_b2.json")
    formats = Formats(Base.ouvrir(RACINE / "data/processed/base_etape_c.sqlite"), corpus.fiches)
    position = {i: corpus.position_of(f) for i, f in formats.corpus.items()}
    return NumberChecker(corpus), position


def adosses(checker, position, expo: dict) -> dict:
    out = {}
    for c in COMBOS:
        recs = lire(D / "runs" / c / "g1.jsonl") + lire(D / "runs" / c / "g2.jsonl")
        n = ad = nr = 0
        reps, expos, convs = [], [], []
        for r in recs:
            pos = [position[i] for i in expo["conversations"][r["id"]]["exposees"]]
            chk = checker.check(r.get("answer") or "", pos, anchor=False)
            n += len(chk)
            ad += sum(x["status"] == "adosse" for x in chk)
            nr += sum(x["status"] == "non_retrouve" for x in chk)
            reps.append(r.get("answer") or "")
            expos.append(pos)
            convs.append(r["id"])
        out[c] = {"chiffres_cites": n, "adosses": ad / n if n else None, "non_retrouves": nr,
                  "temoin_adosses": checker.chance_rate(reps, expos, convs)}
    return out


def exporter(banc: dict, expo: dict, v: dict, r: dict, checker, position, matrice: dict, chemin: Path) -> dict:
    from src.eval.grille_d import PRIX
    formations = {}
    import sqlite3
    con = sqlite3.connect(f"file:{RACINE / 'data/processed/base_etape_c.sqlite'}?mode=ro", uri=True)
    for fid, intit, etab, lien, commune in con.execute(
            "SELECT f.id, f.intitule, f.etablissement, f.lien_officiel, l.commune FROM formation f "
            "LEFT JOIN lieu l ON l.id = f.id AND l.rang = 1"):
        formations[fid] = {"intitule": intit, "etablissement": etab, "commune": commune, "lien_officiel": lien}
    runs = {(c, g): {(x["id"], x["turn"]): x for x in lire(D / "runs" / c / f"g{g}.jsonl")} for c in COMBOS for g in (1, 2)}
    exposees_toutes = sorted({i for cv in expo["conversations"].values() for i in cv["exposees"]})
    conversations = []
    for item in banc["items"]:
        cv = expo["conversations"][item["id"]]
        pos = [position[i] for i in cv["exposees"]]
        tours = []
        for t, question in enumerate(item["turns"]):
            att = [(k, a) for k, a in enumerate(item["attendus"]["chiffres"]) if a["tour"] == t]
            attendus = [[a["valeur"], a["unite"], a["libelle"],
                         cv["cible_par_attendu"][k] or (a["fiche"].get("cod_aff_form") or a["fiche"].get("id")),
                         cv["cible_par_attendu"][k] is None] for k, a in att]
            reponses = {}
            for c in COMBOS:
                gens = []
                for g in (1, 2):
                    x = runs[(c, g)].get((item["id"], t))
                    if x is None:
                        continue
                    texte = x.get("answer") or ""
                    (pin, pout), _ = PRIX[x["modele"]]
                    gens.append({"texte": texte,
                                 "trouves": [j for j, (_, a) in enumerate(att) if cd.cite(a, [texte])],
                                 "chiffres": [[y["value"], y["unit"], y["status"]] for y in checker.check(texte, pos, anchor=False)],
                                 "mots": len(texte.split()),
                                 "cout_usd": round((x.get("tokens_in", 0) * pin + x.get("tokens_out", 0) * pout) / 1e6, 5),
                                 "secondes": x.get("secondes"),
                                 "outil": {"appels": len(x.get("appels_outil") or []),
                                           "erreurs": sum(1 for a in x.get("appels_outil") or [] if a.get("erreur"))}})
                cle = (c, item["id"], t)
                juge = None
                if cle in v:
                    juge = {k: v[cle].get(k) for k in (*CRITERIA, "refus", "erreur_factuelle", "erreur_detail", "commentaire")}
                    juge["rejuge"] = ({k: r[cle].get(k) for k in (*CRITERIA, "refus", "erreur_factuelle", "erreur_detail")}
                                      if cle in r else None)
                reponses[c] = {"g": gens, "juge": juge}
            tours.append({"i": t, "question": question, "attendus": attendus, "reponses": reponses})
        conversations.append({"id": item["id"], "domaine": item["domaine"], "persona": item["persona"],
                              "tags": item["tags"], "exposees": cv["exposees"], "tours": tours})
    doc = {"meta": {"protocole": "PROTOCOLE.md v0.2", "genere_le": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                    "banc_sha": expo["banc_sha256"][:12], "base_sha": expo["base_sha256"][:12],
                    "corpus_sha": expo["corpus_sha256"][:12],
                    "exposition_sha": hashlib.sha256((D / "exposition.json").read_bytes()).hexdigest()[:12],
                    "combinaisons": [{"code": c, "format": c[0], "modele": c[2:]} for c in COMBOS],
                    "n_conversations": len(conversations), "n_tours": sum(len(x["tours"]) for x in conversations),
                    "n_reponses": sum(len(rep["g"]) for x in conversations for t in x["tours"] for rep in t["reponses"].values()),
                    "n_attendus_critere": expo["n_attendus_critere"], "n_attendus_hors": expo["n_attendus_hors"],
                    "format": "export D v0 (accord Jarvis 23/09) + hors_critere + n_attendus_*"},
           "fiches": {i: formations[i] for i in exposees_toutes},
           "matrice": matrice, "conversations": conversations}
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"octets": chemin.stat().st_size, "n_reponses": doc["meta"]["n_reponses"]}


if __name__ == "__main__":
    raise SystemExit(main())
