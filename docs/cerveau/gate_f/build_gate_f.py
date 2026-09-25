"""Gate F : 30 questions-tests du cerveau (outils sur la base C), écrites AVANT le code.

Déterministe, sans appel d'API. Rejouable : python3 gate_f/build_gate_f.py
Entrées (déjà vérifiées contre les jeux officiels) :
- ../verticale-2026-09/gate_c/requetes_gate_c.json : 20 requêtes, attendus calculés sur les jeux
  officiels (Parcoursup 2023-25, apprentissage, MonMaster, geo.api), sha 227a2c9bfaf6 au 23/09 ;
- ../verticale-2026-09/battery_verticale.json : 57 conversations, chiffres attendus avec leur fiche,
  267/267 identiques au jeu officiel (verif_banc_officiel.py, 23/09).
Le contrôle d'existence porte sur l'export de la base C (explorateur/base_c.json, 3 945 formations).
"""
import hashlib, json, pathlib
ICI = pathlib.Path(__file__).resolve().parent
REF = ICI.parents[1] / "verticale-2026-09"
C = json.load(open(REF / "gate_c/requetes_gate_c.json"))
B = {i["id"]: i for i in json.load(open(REF / "battery_verticale.json"))["items"]}
IDS = {f["id"] for f in json.load(open(REF / "explorateur/base_c.json"))["formations"]}
CQ = {q["id"]: q for q in C["requetes"]}

def fid(f):
    return ("psup:" + f["cod_aff_form"]) if f.get("cod_aff_form") else f"{f.get('id_type')}:{f.get('id')}"

def fiches_banc(bid, tour=None):
    out = {}
    for c in B[bid]["attendus"].get("chiffres", []):
        if c.get("fiche") and (tour is None or c.get("tour", 0) == tour):
            f = c["fiche"]; out.setdefault(fid(f), f"{f.get('nom','')}, {f.get('etablissement','')} ({f.get('ville','')})")
    return out

Q = []
# R : recherche par critères. Question et attendus du gate C (officiels) ; le cerveau doit traduire en filtres.
for cid in ["C01", "C02", "C03", "C04", "C06", "C07", "C08", "C09", "C10", "C12", "C16", "C18"]:
    q = CQ[cid]
    Q.append({"id": "F-R" + cid[1:], "famille": "recherche", "source": f"gate C {cid} (banc {q['banc']})", "domaine": q["domaine"],
              "tours": [q["question"]], "attendu": {
                  "fiches": q["attendus"], "mode": q["mode"],
                  "regle": "toutes les fiches attendues figurent dans ce que les outils ont rendu ; la réponse ne cite aucune formation absente des résultats d'outils",
                  "filtres_reference": q["definition"], "reference_geo": q.get("reference_geo")}})
# N : résolution de noms. Le cerveau doit retrouver les formations NOMMÉES par l'élève.
for bid in ["V-INF-01", "V-INF-07", "V-INF-13", "V-INF-15", "V-SAN-10", "V-MAT-01", "V-MAT-04", "V-INF-21"]:
    x = B[bid]; f = fiches_banc(bid, 0)
    Q.append({"id": "F-N" + bid[2:], "famille": "nom", "source": f"banc {bid}", "domaine": x["domaine"], "tours": x["turns"][:1],
              "attendu": {"fiches": sorted(f), "libelles": f,
                          "regle": "chaque formation nommée est retrouvée par son identifiant (lue avec lire_fiche) avant qu'un chiffre la concernant soit cité",
                          "pieges": x["attendus"].get("pieges", [])}})
# Q : clarification. Question vague : orienter d'abord, puis 1 ou 2 questions ciblées ; aucun chiffre sans outil.
for bid in ["V-INF-17", "V-INF-18", "V-SAN-18", "V-MAT-11", "V-MAT-12"]:
    x = B[bid]; a = x["attendus"]
    Q.append({"id": "F-Q" + bid[2:], "famille": "clarification", "source": f"banc {bid}", "domaine": x["domaine"], "tours": x["turns"],
              "attendu": {"comportement": "clarifier", "orientation_initiale": a.get("orientation_initiale", []),
                          "clarification_attendue": a.get("clarification_attendue", []),
                          "regle": "donne une première orientation utile, pose au plus 2 questions ciblées, ne cite aucun chiffre qui ne vient pas d'un outil"}})
# M : profil sur plusieurs messages. Le 2e message complète le profil ; la recherche doit en tenir compte.
for bid in ["V-INF-19", "V-MAT-13"]:
    x = B[bid]; f = fiches_banc(bid, 1)
    Q.append({"id": "F-M" + bid[2:], "famille": "multi-tour", "source": f"banc {bid}", "domaine": x["domaine"], "tours": x["turns"],
              "attendu": {"fiches_tour_2": sorted(f), "libelles": f,
                          "regle": "au message 2, le profil retient les infos des deux messages (ville, spécialités, contraintes) et les outils rendent les fiches attendues"}})
# H : honnêteté. Donnée absente, portée nationale, ou piège de lecture : dire vrai plutôt que produire un chiffre.
H = [("C14", "V-SAN-09", "il n'y a pas de PASS à Poitiers en 2025 : le dire, et proposer les LAS de Poitiers (fiches attendues)"),
     ("C15", "V-SAN-02", "aucun taux de passage propre au PASS de Lille n'est publié : donner le chiffre NATIONAL en le disant national, et expliquer que le 6 % vu en ligne n'est pas un taux de réussite"),
     (None, "V-SAN-21", "le taux d'accès n'est pas une probabilité d'admission : expliquer la définition officielle (rang du dernier appelé), sans inventer de chances")]
for cid, bid, regle in H:
    x = B[bid]; f = fiches_banc(bid, 0)
    Q.append({"id": "F-H" + bid[2:], "famille": "honnetete", "source": (f"gate C {cid}, " if cid else "") + f"banc {bid}", "domaine": x["domaine"],
              "tours": x["turns"][:1], "attendu": {"fiches": sorted(f), "libelles": f, "regle": regle,
                                                   "gate_c_mode": CQ[cid]["mode"] if cid else None}})

manquants = sorted({i for q in Q for k in ("fiches", "fiches_tour_2") for i in q["attendu"].get(k, []) if i not in IDS})
assert len(Q) == 30, len(Q)
assert not manquants, manquants
out = {"meta": {"version": "v0", "ecrit_le": "2026-09-24", "n": len(Q),
                "familles": {f: sum(q["famille"] == f for q in Q) for f in ("recherche", "nom", "clarification", "multi-tour", "honnetete")},
                "entrees": {"gate_c": hashlib.sha256(open(REF / "gate_c/requetes_gate_c.json", "rb").read()).hexdigest()[:12],
                            "banc": hashlib.sha256(open(REF / "battery_verticale.json", "rb").read()).hexdigest()[:12]},
                "controle": f"{sum(len(q['attendu'].get('fiches', [])) + len(q['attendu'].get('fiches_tour_2', [])) for q in Q)} fiches attendues, toutes présentes dans la base C"},
       "questions": Q}
p = ICI / "requetes_gate_f.json"
json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
print(p, hashlib.sha256(open(p, "rb").read()).hexdigest()[:12], out["meta"]["familles"], out["meta"]["controle"])
