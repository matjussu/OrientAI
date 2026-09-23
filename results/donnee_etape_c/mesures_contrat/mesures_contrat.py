"""Mesures citées par le contrat de l'étape C (ordre 2026-09-23-1358). LECTURE SEULE.

Ce script n'est pas du code de construction : il ne crée aucune base. Il rejoue les chiffres sur
lesquels le contrat s'appuie (périmètre, géographie, masters, identifiants, couverture du gate) et
les écrit dans `mesures_contrat.json`, à côté de lui.

Usage (depuis la racine du dépôt) :
    python results/donnee_etape_c/mesures_contrat/mesures_contrat.py \
        --corpus data/processed/formations_etape_b2.json \
        --bruts ~/projets/OrientIA/data/raw \
        --gate ~/projets/_orientai-ref/verticale-2026-09/gate_c/requetes_gate_c.json \
        --monmaster ~/projets/_orientai-ref/verticale-2026-09/gate_c/cache/mm_2025.json \
        --communes <fichier geo.api.gouv.fr communes?fields=code,nom,centre> \
        --explorateur ~/projets/_orientai-ref/verticale-2026-09/explorateur/data_b2.json
"""
from __future__ import annotations

import argparse
import collections as C
import csv
import hashlib
import json
import math
import re
from pathlib import Path

DOMAINES_DIRECTS = {"informatique", "cyber", "data_ia", "sante"}
REGLES_MATHS = {"M01", "M02", "M03"}
SUFFIXE_APPRENTISSAGE = " - en apprentissage"
SECTEURS_MASTERS = {"Informatique", "Mathématiques", "Mathématique et informatique",
                    "Mathématiques appliquées et sciences sociales"}


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def dans_perimetre(f: dict) -> bool:
    if f["source"] not in ("parcoursup", "parcoursup_apprentissage"):
        return False
    dom = f.get("domaine")
    return dom in DOMAINES_DIRECTS or (dom == "sciences_fondamentales" and f.get("domaine_regle") in REGLES_MATHS)


def fid(f: dict) -> str | None:
    s = f["source"]
    if s == "parcoursup":
        return "psup:" + f["cod_aff_form"]
    if s == "parcoursup_apprentissage":
        return "psup_app:" + f["cod_aff_form"]
    if s == "monmaster":
        return "mm:" + f["id_mon_master"]["ifc"]
    return None


def coord(s: str | None):
    try:
        a, b = (float(x) for x in (s or "").split(","))
        return a, b
    except ValueError:
        return None


def haversine(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def lire_csv(p: Path) -> list[dict]:
    with p.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--bruts", type=Path, required=True)
    ap.add_argument("--gate", type=Path, required=True)
    ap.add_argument("--monmaster", type=Path, required=True)
    ap.add_argument("--communes", type=Path, required=True)
    ap.add_argument("--explorateur", type=Path, help="data_b2.json de l'explorateur (témoin de périmètre)")
    a = ap.parse_args()

    corpus = json.loads(a.corpus.read_bytes())
    m: dict = {"entrees": {"corpus_sha256_12": sha12(a.corpus), "gate_sha256_12": sha12(a.gate)}}

    # 1. Périmètre des lignes
    peri = [f for f in corpus if dans_perimetre(f)]
    m["corpus_par_source"] = dict(C.Counter(f["source"] for f in corpus).most_common())
    m["perimetre"] = {
        "fiches": len(peri),
        "par_source": dict(C.Counter(f["source"] for f in peri)),
        "par_domaine": dict(C.Counter(f["domaine"] for f in peri)),
        "par_fili": dict(C.Counter(f["fili_code"] for f in peri).most_common()),
        "par_regle": dict(C.Counter(f.get("domaine_regle") for f in peri).most_common()),
    }
    m["regles_maths_detail"] = {r: dict(C.Counter(f["filiere_detaillee"] for f in peri if f.get("domaine_regle") == r).most_common())
                                for r in sorted(REGLES_MATHS)}
    anterieur = [f for f in corpus if f["source"] in ("parcoursup", "parcoursup_apprentissage")
                 and f.get("domaine") == "sciences_fondamentales" and f.get("domaine_regle") not in REGLES_MATHS]
    m["exclus_sciences_fondamentales_hors_regle_maths"] = {
        "fiches": len(anterieur),
        "top_filieres": [[f"{k[0]} / {k[1]}", n] for k, n in
                         C.Counter((f["fili_code"], f["filiere_detaillee"]) for f in anterieur).most_common(12)],
    }
    sante_ant = [f for f in peri if f["domaine"] == "sante" and f.get("domaine_regle") == "anterieur"]
    m["sante_par_regle_anterieure"] = {
        "fiches": len(sante_ant),
        "top_filieres": [[f"{k[0]} / {k[1]}", n] for k, n in
                         C.Counter((f["fili_code"], f["filiere_detaillee"]) for f in sante_ant).most_common(10)],
    }

    # 2. Remplissage des champs dans le périmètre
    dispo = lambda f, k: isinstance(f.get(k), dict) and f[k].get("statut") == "disponible"
    m["remplissage"] = {
        "cout_disponible": sum(dispo(f, "cout") for f in peri),
        "alternance_disponible": sum(dispo(f, "alternance") for f in peri),
        "insertion_disponible": sum(dispo(f, "insertion") for f in peri),
        "champ_sante": sum(1 for f in peri if f.get("sante")),
        "debouches_non_vides": sum(1 for f in peri if f.get("debouches")),
        "insertion_pro_heritee_du_corpus_historique": sum(1 for f in peri if f.get("insertion_pro")),
        "provenance_herite_de": sum(1 for f in peri if (f.get("provenance") or {}).get("herite_de")),
        "historique_nb_sessions": dict(C.Counter(len((f.get("admission") or {}).get("historique") or {}) for f in peri)),
        "statut": dict(C.Counter(f["statut"] for f in peri)),
    }
    m["valeurs_distinctes"] = {
        "filiere_detaillee": len({f["filiere_detaillee"] for f in peri}),
        "filiere_sans_suffixe_apprentissage": len({(f["filiere_detaillee"] or "").removesuffix(SUFFIXE_APPRENTISSAGE) for f in peri}),
        "type_formation": len({f["type_formation"] for f in peri}),
        "filieres_avec_suffixe_apprentissage": sum(1 for f in peri if (f["filiere_detaillee"] or "").endswith(SUFFIXE_APPRENTISSAGE)),
    }

    # 3. Identifiants
    ids = C.Counter(fid(f) for f in corpus if fid(f))
    m["identifiants"] = {
        "doublons": sum(1 for v in ids.values() if v > 1),
        "cod_aff_form_communs_parcoursup_apprentissage": len(
            {f["cod_aff_form"] for f in corpus if f["source"] == "parcoursup"}
            & {f["cod_aff_form"] for f in corpus if f["source"] == "parcoursup_apprentissage"}),
    }

    # 4. Valeurs d'admission contre le brut verrouillé (contrôle de la dérivation future)
    brut25 = {r["cod_aff_form"]: r for r in lire_csv(a.bruts / "parcoursup_2025.csv")}
    ecarts = C.Counter()
    compares = C.Counter()
    for f in corpus:
        if f["source"] != "parcoursup":
            continue
        r = brut25[f["cod_aff_form"]]
        vol = (f.get("admission") or {}).get("volumes") or {}
        paires = (("taux_acces_ens", f["taux_acces_parcoursup_2025"], float),
                  ("capa_fin", f["nombre_places"], lambda x: int(float(x))),
                  ("voe_tot", vol.get("voeux_totaux"), lambda x: int(float(x))))
        for champ, v, conv in paires:
            if r.get(champ) in ("", None) or v is None:
                continue
            compares[champ] += 1
            if conv(r[champ]) != v:
                ecarts[champ] += 1
    m["admission_2025_contre_brut"] = {"compares": dict(compares), "ecarts": dict(ecarts)}
    # Dénominateur des parts par type de bac : on garde les lignes où admis total et admis
    # néo-bacheliers diffèrent (sinon les deux hypothèses donnent le même nombre).
    neo = tot = n = 0
    for r in brut25.values():
        try:
            bt, nb, at, p = (float(r[k]) for k in ("acc_bt", "acc_neobac", "acc_tot", "pct_bt"))
        except ValueError:
            continue
        if nb < 20 or at == nb:
            continue
        n += 1
        neo += abs(100 * bt / nb - p) <= 0.6
        tot += abs(100 * bt / at - p) <= 0.6
    m["pct_bt_denominateur"] = {"lignes_discriminantes": n, "egal_acc_bt_sur_acc_neobac": neo, "egal_acc_bt_sur_acc_tot": tot}
    m["filiere_detaillee_contre_fil_lib_voe_acc"] = sum(
        1 for f in corpus if f["source"] == "parcoursup" and f["filiere_detaillee"] != brut25[f["cod_aff_form"]]["fil_lib_voe_acc"])

    # 5. Géographie
    carto = {}
    for r in lire_csv(a.bruts / "cartographie_parcoursup_2025.csv"):
        c = coord(r["etab_gps"])
        if c:
            for g in r["gta"].split(","):
                carto[g.strip()] = c
    geo = {k: coord(r["g_olocalisation_des_formations"]) for k, r in brut25.items()}
    ecarts_km = sorted(haversine(geo[k], carto[k]) for k in geo if geo[k] and k in carto)
    brut_app = lire_csv(a.bruts / "parcoursup_apprentissage_2025.csv")
    geo_app = {r["cod_aff_form"]: coord(r["g_olocalisation_des_formations"]) for r in brut_app}
    m["geographie"] = {
        "parcoursup_2025_avec_g_olocalisation": sum(1 for c in geo.values() if c),
        "parcoursup_2025_lignes": len(geo),
        "comparees_a_la_cartographie": len(ecarts_km),
        "ecart_max_km": round(ecarts_km[-1], 4) if ecarts_km else None,
        "apprentissage_brut_lignes": len(brut_app),
        "apprentissage_fiches_avec_g_olocalisation": sum(
            1 for f in peri if f["source"] == "parcoursup_apprentissage" and geo_app.get(f["cod_aff_form"])),
        "perimetre_sans_coordonnees": sorted(
            fid(f) for f in peri
            if not (geo if f["source"] == "parcoursup" else geo_app).get(f["cod_aff_form"])),
        "perimetre_sans_code_insee": dict(C.Counter(f["source"] for f in peri if not f.get("code_insee"))),
        "apprentissage_sans_insee_forme_departement": dict(C.Counter(
            len(f.get("code_departement") or "") for f in peri
            if f["source"] == "parcoursup_apprentissage" and not f.get("code_insee"))),
    }
    communes = json.loads(a.communes.read_bytes())
    centres = {c["code"]: c for c in communes}
    rennes = centres["35238"]["centre"]["coordinates"]
    buts = []
    for f in peri:
        c = geo.get(f["cod_aff_form"]) if f["source"] == "parcoursup" else None
        if c and f["fili_code"] == "BUT" and f["filiere_detaillee"] == "Informatique":
            buts.append((round(haversine(c, (rennes[1], rennes[0])), 1), fid(f), f["etablissement"], f["taux_acces_parcoursup_2025"]))
    buts.sort()
    m["cas_test_rennes"] = {
        "centre_rennes_geo_api": rennes,
        "communes_geo_api": len(communes),
        "but_informatique_france": len(buts),
        "a_moins_de_50_km": [b for b in buts if b[0] < 50],
        "les_3_plus_proches": buts[:3],
    }
    homonymes = C.Counter(c["nom"] for c in communes)
    m["communes_homonymes"] = {"noms_portes_par_plusieurs_communes": sum(1 for n in homonymes.values() if n > 1),
                               "saint_denis": homonymes.get("Saint-Denis")}

    # 6. Masters : corpus contre le jeu officiel MonMaster 2025 lu par Jarvis
    officiel = json.loads(a.monmaster.read_bytes())
    sel = {x["ifc"]: x for x in officiel if x.get("secteur_disci_lib") in SECTEURS_MASTERS}
    mm = {f["id_mon_master"]["ifc"]: f for f in corpus if f["source"] == "monmaster"}
    communs = set(sel) & set(mm)
    e = C.Counter()
    for k in communs:
        f, o = mm[k], sel[k]
        e["capacite"] += f["capacite"] != o["col"]
        e["n_candidats_pp"] += f["n_candidats_pp"] != o["n_can_pp"]
        e["alternance"] += bool(f["alternance"]) != (o["alternance"] == "1")
    m["masters"] = {
        "corpus_monmaster": len(mm),
        "corpus_par_session": dict(C.Counter(f["id_mon_master"]["session"] for f in mm.values())),
        "corpus_url_type": dict(C.Counter(f["url_type"] for f in mm.values())),
        "officiel_2025_lignes": len(officiel),
        "officiel_2025_info_maths": len(sel),
        "presents_dans_le_corpus": len(communs),
        "absents_du_corpus": len(set(sel) - set(mm)),
        "ecarts_sur_les_presents": dict(e),
        "corpus_info_maths_ville_avec_cedex": sum(
            1 for f in mm.values() if f["secteur_discipline"] in SECTEURS_MASTERS and "CEDEX" in (f.get("ville") or "").upper()),
        "corpus_info_maths_par_secteur": dict(C.Counter(
            f["secteur_discipline"] for f in mm.values() if f["secteur_discipline"] in SECTEURS_MASTERS)),
    }

    # 7. Couverture du gate de Jarvis par le périmètre proposé
    gate = json.loads(a.gate.read_bytes())
    peri_ids = {fid(f) for f in peri} | {"mm:" + k for k in sel}
    corpus_ids = set(ids)
    m["gate"] = {r["id"]: {
        "attendus": len(r["attendus"]),
        "frontiere": len(r.get("frontiere") or []),
        "hors_corpus": [i for i in r["attendus"] + (r.get("frontiere") or []) if i not in corpus_ids],
        "hors_perimetre": [i for i in r["attendus"] + (r.get("frontiere") or []) if i not in peri_ids],
    } for r in gate["requetes"]}
    # Témoin : le même contrôle, appliqué au classement par mots-clés de l'explorateur, doit trouver
    # des manquants. S'il rendait 0 lui aussi, le contrôle ci-dessus ne prouverait rien.
    if a.explorateur:
        ex = json.loads(a.explorateur.read_bytes())
        ex_ids = {("psup:" if r["src"] == "parcoursup" else "psup_app:") + r["id"] for r in ex["fiches"]}
        manquants = sorted({i for r in gate["requetes"] for i in r["attendus"] + (r.get("frontiere") or [])
                            if not i.startswith("mm:") and i not in ex_ids})
        m["temoin_perimetre_explorateur"] = {"fiches": len(ex_ids), "attendus_du_gate_hors_perimetre": manquants}

    out = Path(__file__).with_name("mesures_contrat.json")
    out.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n")
    print(out)


if __name__ == "__main__":
    main()
