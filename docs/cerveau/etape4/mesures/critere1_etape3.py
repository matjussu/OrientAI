"""Pourquoi le critère 1 du v2 est à 61,9 % : chaque chiffre attendu du banc vertical, classé (aucun appel d'API).

Lecture seule : banc vertical (sha f467374be3d7), `results/cerveau_etape3/essentiel_fiche.json` (statut de chaque
attendu dans la base : egal, ecart, masque, absent), traces `results/multiversion/2026-09-25_v2/v2__vertical.jsonl`.
Même règle de citation que le critère 1 (`src.eval.multiversion.mesures.cite`). Depuis la racine du dépôt :
    python3 docs/cerveau/etape4/mesures/critere1_etape3.py
Sortie : docs/cerveau/etape4/mesures/critere1_etape3.json.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RACINE))
from src.eval.multiversion import mesures as me  # noqa: E402
from src.eval.multiversion.lanceur import BANCS, charger_banc  # noqa: E402

SORTIE = Path(__file__).with_suffix(".json")
LECTURE = ("lire_fiche", "comparer")


def main() -> dict:
    items, sha = charger_banc("vertical")
    ess = json.loads((RACINE / "results/cerveau_etape3/essentiel_fiche.json").read_text(encoding="utf-8"))
    par_conv = collections.defaultdict(list)
    for ligne in ess["lignes"]:
        par_conv[ligne["conversation"]].append(ligne)
    tours = {}
    for l in open(RACINE / "results/multiversion/2026-09-25_v2/v2__vertical.jsonl"):
        r = json.loads(l)
        tours[(r["id"], r["turn"])] = r
    classes = collections.Counter()
    detail = []
    for it in items:
        lignes = par_conv[it["id"]]
        attendus = it["attendus"]["chiffres"]
        assert len(lignes) == len(attendus), it["id"]
        for a, lg in zip(attendus, lignes):
            assert abs(float(a["valeur"]) - float(lg["valeur"])) < 1e-9, (it["id"], a, lg)
            if lg.get("fiche") is None:  # hors base C (18), hors critère 1
                continue
            suite = [tours[(it["id"], t)] for t in range(a["tour"], len(it["turns"])) if (it["id"], t) in tours]
            cite = me.cite(a, [t["answer"] for t in suite])
            fiche = lg["fiche"]
            rendue = lue = valeur_rendue = False
            for t in suite:
                for o in (t.get("trace") or {}).get("outils", []):
                    if not o.get("execute"):
                        continue
                    if fiche in (o.get("ids_rendus") or []):
                        rendue = True
                        if o["nom"] in LECTURE:
                            lue = True
                    for v in o.get("valeurs") or []:
                        if v.get("id") == fiche and abs(float(v["valeur"]) - float(lg["valeur"])) <= 0.5:
                            valeur_rendue = True
            if cite:
                classe = "cite_juste"
            elif lg["statut"] != "egal":
                classe = f"non_cite_base_{lg['statut']}"      # la base ne montre pas cette valeur au modèle
            elif not rendue:
                classe = "non_cite_fiche_jamais_rendue"       # recherche : la fiche n'est sortie d'aucun outil
            elif not lue:
                classe = "non_cite_fiche_rendue_non_lue"      # sortie d'une recherche, jamais lue ni comparée
            elif not valeur_rendue:
                classe = "non_cite_fiche_lue_valeur_non_rendue"  # lue, mais la valeur n'était pas dans ce qui a été rendu
            else:
                classe = "non_cite_valeur_rendue_non_reprise"  # le modèle avait la valeur et ne l'a pas écrite
            classes[classe] += 1
            detail.append({"conversation": it["id"], "tour": a["tour"], "valeur": a["valeur"], "unite": a["unite"],
                           "fiche": fiche, "notion": lg.get("notion"), "statut_base": lg["statut"], "classe": classe})
    n = sum(classes.values())
    egal = sum(1 for d in detail if d["statut_base"] == "egal")
    out = {"banc_sha256": sha, "attendus_dans_la_base": n, "classes": dict(classes.most_common()),
           "taux_critere1": round(classes["cite_juste"] / n, 4),
           "plafond_si_tout_egal_cite": round(egal / n, 4), "attendus_egal": egal,
           "detail": detail}
    SORTIE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps({k: v for k, v in o.items() if k != "detail"}, ensure_ascii=False, indent=1))
