"""Rejeu du gate C : les 20 requêtes de Jarvis contre la base, par mes traductions en filtres.

- Requêtes et attendus : fichier de Jarvis (zone Jarvis, lu seulement), tirés des sources officielles.
- Traductions : `results/donnee_etape_c/gate/filtres_gate_c.json`, écrites avant la construction, qui
  portent le sha du fichier traduit. Un sha différent arrête le rejeu.
- Verdict (contrat §10) : exact = mêmes identifiants hors frontière ; inclut ; exclut ; vide = 0
  résultat ; ordre = même valeur de tri à chaque rang (ex aequo permutables) ; valeurs = égalité stricte.

Usage :
    python -m src.eval.gate_c --requetes <requetes_gate_c.json> [--base data/processed/base_etape_c.sqlite]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from src.base_c import outils
from src.collect.base_etape_c import RACINE, par_espace

TRADUCTIONS = RACINE / "results/donnee_etape_c/gate/filtres_gate_c.json"
SORTIE = RACINE / "results/donnee_etape_c/gate"
OUTILS = {"chercher_formations": outils.chercher_formations, "chercher_masters": outils.chercher_masters}


def jouer(base: outils.Base, appels: list[dict]) -> tuple[list[dict], list[dict]]:
    """Union des résultats des appels, dans l'ordre des appels, sans doublon ; + les filtres appliqués."""
    rendues, vus, filtres = [], set(), []
    for a in appels:
        res = OUTILS[a["outil"]](base, **a["arguments"])
        filtres.append({"outil": a["outil"], "filtres_appliques": res["filtres_appliques"],
                        "nb_resultats": res["nb_resultats"], "tronque": res["tronque"],
                        "ecartees_non_disponible": res["ecartees_non_disponible"]})
        for r in res["resultats"]:
            if r["id"] not in vus:
                vus.add(r["id"])
                rendues.append(r)
    return rendues, filtres


def en_clair(appels_joues: list[dict]) -> str:
    morceaux = []
    for a in appels_joues:
        f = a["filtres_appliques"]
        m = []
        if "types" in f:
            m.append("type " + " ou ".join(f["types"]))
        if "filieres" in f:
            m.append("filière " + " ou ".join(f["filieres"]))
        if "mention_contient" in f:
            m.append(f"mention contenant « {f['mention_contient']} »")
        if "apprentissage" in f:
            m.append("en apprentissage" if f["apprentissage"] else "hors apprentissage")
        if "alternance" in f:
            m.append("en alternance" if f["alternance"] else "hors alternance")
        for k, lib in (("communes", "commune"), ("departements", "département"), ("regions", "région"),
                       ("regions_academiques", "région académique")):
            if k in f:
                m.append(f"{lib} " + ", ".join(f[k]))
        if "pres_de" in f:
            p = f["pres_de"]
            m.append(f"à moins de {p['rayon_km']:g} km de {p['commune']} ({p['code_insee']}), à vol d'oiseau")
        for k, v in f.items():
            if k.endswith("_min"):
                m.append(f"{k[:-4]} >= {v:g}")
            elif k.endswith("_max"):
                m.append(f"{k[:-4]} < {v:g}")
        if "tri" in f:
            m.append(f"trié par {f['tri']['champ']} {'décroissant' if f['tri']['sens'] == 'desc' else 'croissant'}")
        morceaux.append(" ; ".join(m) + f" [{a['outil']}, session {f.get('session')}]")
    return " PUIS ".join(morceaux)


def champ_de_la_base(base: outils.Base, officiel: str, espace: str) -> tuple[str, str | None]:
    """« taux_acces_ens@2023 » -> ("taux_acces", "2023") pour l'espace de la fiche ; un nom de champ de la base passe tel quel."""
    nom, _, session = officiel.partition("@")
    for r in base.con.execute("SELECT champ, nom_officiel, sessions FROM champ"):
        if par_espace(r["nom_officiel"]).get(espace) == nom or r["champ"] == nom:
            if r["sessions"] == "-":
                return r["champ"], None
            return r["champ"], session or "2025"
    raise KeyError(f"champ officiel {officiel!r} sans correspondance pour {espace}")


def verdict(base: outils.Base, req: dict, rendues: list[dict], tri: dict | None) -> dict:
    frontiere = set(req.get("frontiere") or [])
    ids = [r["id"] for r in rendues if r["id"] not in frontiere]
    attendus = [a for a in req["attendus"] if a not in frontiere]
    mode = req["mode"]
    manquantes = [a for a in attendus if a not in ids]
    en_trop = [i for i in ids if i not in attendus]
    if mode == "exact":
        juste = not manquantes and not en_trop
    elif mode == "inclut":
        juste = not manquantes
        en_trop = []
    elif mode == "exclut":
        juste = not [i for i in ids if i in attendus]
        manquantes = []
    elif mode == "vide":
        juste = not ids
    else:
        raise ValueError(f"mode inconnu {mode!r}")
    ordre_ok = None
    if req.get("ordre"):
        par_id = {r["id"]: r for r in rendues}

        def valeur_tri(i):
            if tri is None or i not in par_id:
                return None
            if tri["champ"] == "distance":
                return par_id[i].get("distance_km")
            v = par_id[i]["valeurs"].get(f"{tri['champ']}@2025") or par_id[i]["valeurs"].get(tri["champ"])
            return v["valeur"] if v else None
        rendus_attendus = [i for i in ids if i in attendus]
        ordre_ok = [valeur_tri(i) for i in rendus_attendus] == [valeur_tri(i) for i in attendus]
        juste = juste and ordre_ok
    ecarts = []
    par_id = {r["id"]: r for r in rendues}
    for v in req.get("valeurs") or []:
        fiche = v["fiche"]
        espace = fiche.split(":", 1)[0]
        champ, session = champ_de_la_base(base, v["champ"], espace)
        cle = champ if session is None else f"{champ}@{session}"
        rendu = (par_id.get(fiche) or {}).get("valeurs", {}).get(cle)
        attendu = v["valeur"]
        try:
            attendu = float(attendu)
        except (TypeError, ValueError):
            pass
        obtenu = None if rendu is None else rendu["valeur"]
        ok = rendu is not None and rendu["statut"] == "disponible" and float(obtenu) == attendu
        if ok and v.get("portee"):
            ok = rendu["portee"] == v["portee"]
        if not ok:
            ecarts.append({"fiche": fiche, "champ": v["champ"], "champ_base": cle, "attendu": v["valeur"],
                           "obtenu": obtenu, "portee_attendue": v.get("portee"),
                           "portee_obtenue": None if rendu is None else rendu["portee"],
                           "statut": None if rendu is None else rendu["statut"]})
    juste = juste and not ecarts
    return {"juste": juste, "manquantes": manquantes, "en_trop": en_trop, "ordre_ok": ordre_ok,
            "valeurs_verifiees": len(req.get("valeurs") or []), "valeurs_ecarts": ecarts}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--requetes", type=Path, required=True)
    ap.add_argument("--base", type=Path, default=outils.BASE_DEFAUT)
    ap.add_argument("--traductions", type=Path, default=TRADUCTIONS)
    ap.add_argument("--sortie", type=Path, default=SORTIE)
    args = ap.parse_args(argv)

    octets = args.requetes.read_bytes()
    sha = hashlib.sha256(octets).hexdigest()
    trad = json.loads(args.traductions.read_text(encoding="utf-8"))
    if trad["gate_traduit"]["sha256"] != sha:
        print(f"Les traductions portent le sha {trad['gate_traduit']['sha256'][:12]}, le fichier de requêtes {sha[:12]} : "
              "rejeu arrêté.", file=sys.stderr)
        return 2
    gate = json.loads(octets)
    base = outils.Base.ouvrir(args.base)
    resultats = []
    for req in gate["requetes"]:
        appels = trad["requetes"][req["id"]]["appels"]
        tri = next((a["arguments"].get("tri") for a in appels if a["arguments"].get("tri")), None)
        try:
            rendues, joues = jouer(base, appels)
            v = verdict(base, req, rendues, tri)
        except outils.FiltreInvalide as e:
            # Un filtre refusé par la base est une requête fausse, dite avec son erreur, pas un plantage.
            rendues, joues = [], []
            v = {"juste": False, "erreur": str(e), "manquantes": list(req["attendus"]), "en_trop": [],
                 "ordre_ok": None, "valeurs_verifiees": len(req.get("valeurs") or []), "valeurs_ecarts": []}
        resultats.append({
            "id": req["id"], "question": req["question"], "domaine": req.get("domaine"), "mode": req["mode"],
            "ordre": bool(req.get("ordre")), "filtres": appels, "filtres_appliques": joues, "filtres_en_clair": en_clair(joues),
            "rendues": [{"id": r["id"], "intitule": r["intitule"], "etablissement": r["etablissement"],
                         "commune": r["commune"], "distance_km": r.get("distance_km"), "valeurs": r["valeurs"]} for r in rendues],
            "attendues": req["attendus"], "frontiere": req.get("frontiere") or [], "verdict": v,
        })
    base.fermer()
    justes = sum(r["verdict"]["juste"] for r in resultats)
    doc = {"gate": {"chemin": str(args.requetes), "sha256": sha}, "base": str(args.base),
           "justes": justes, "total": len(resultats), "requetes": resultats}
    args.sortie.mkdir(parents=True, exist_ok=True)
    (args.sortie / "resultats.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (args.sortie / "REPORT.md").write_text(rapport(doc), encoding="utf-8")
    print(f"gate C : {justes}/{len(resultats)} justes")
    for r in resultats:
        if not r["verdict"]["juste"]:
            v = r["verdict"]
            print(f"  {r['id']} FAUX  erreur={v.get('erreur')} manquantes={v['manquantes']} en_trop={v['en_trop']} ordre={v['ordre_ok']} "
                  f"valeurs={v['valeurs_ecarts'][:3]}")
    return 0 if justes == len(resultats) else 1


def rapport(doc: dict) -> str:
    l = [f"# Gate C : {doc['justes']}/{doc['total']} requêtes justes", "",
         f"Requêtes : `{doc['gate']['chemin']}` (sha256 `{doc['gate']['sha256'][:12]}`), base `{doc['base']}`.",
         "Rejouer : `python -m src.eval.gate_c --requetes <fichier>`.", "",
         "| Req. | Mode | Juste | Attendues | Rendues | Manquantes | En trop | Ordre | Valeurs |", "|---|---|---|---|---|---|---|---|---|"]
    for r in doc["requetes"]:
        v = r["verdict"]
        l.append(f"| {r['id']} | {r['mode']}{' + ordre' if r['ordre'] else ''} | {'oui' if v['juste'] else '**non**'} | "
                 f"{len(r['attendues'])} | {len(r['rendues'])} | {', '.join(v['manquantes']) or '-'} | "
                 f"{', '.join(v['en_trop']) or '-'} | {'-' if v['ordre_ok'] is None else ('oui' if v['ordre_ok'] else 'non')} | "
                 f"{v['valeurs_verifiees'] - len(v['valeurs_ecarts'])}/{v['valeurs_verifiees']} |")
    l += ["", "## Détail des requêtes", ""]
    for r in doc["requetes"]:
        l += [f"### {r['id']} : {r['question']}", "", f"Filtres : {r['filtres_en_clair']}", ""]
        for x in r["verdict"]["valeurs_ecarts"]:
            l.append(f"- écart de valeur : {x}")
    return "\n".join(l) + "\n"


if __name__ == "__main__":
    sys.exit(main())
