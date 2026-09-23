"""Extrait des lignes RÉELLES des sources de l'étape B-1 pour les tests (aucune ligne inventée).

Pour une liste de fiches Parcoursup (`cod_aff_form`) du corpus de l'étape A, garde :
- les fiches elles-mêmes, telles que l'étape A les a produites ;
- les lignes Onisep de leurs lieux d'enseignement (UAI) ;
- les lignes Parcoursup apprentissage de leurs diplômes dans leurs départements, et une formation
  d'apprentissage des domaines de la démo ;
- les lignes InserSup de leurs établissements (identifiant Paysage) et InserJeunes de leurs lycées ;
- l'identifiant Paysage de chaque formation (cartographie Parcoursup) ;
- les communes INSEE de leurs départements (et de ceux des formations d'apprentissage gardées).

Rejouer (depuis la racine du dépôt, bruts présents et verrouillés) :
    python tests/fixtures/etape_b/extraire.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RACINE))

from src.collect.alternance import cle_diplome  # noqa: E402
from src.collect.corpus_etape_b import lire_csv  # noqa: E402
from src.collect.sources_officielles import chemin_verifie  # noqa: E402

ICI = Path(__file__).parent
CODES = [
    "10768",  # BTS privé, coût Onisep par intitulé
    "8296",   # CPGE privée, coût Onisep par intitulé (la voie BCPST)
    "31664",  # CPGE privée ECG, coût Onisep commun aux prépas du lycée (règle « même famille »)
    "4960",   # coûts Onisep différents dans la famille : non disponible
    "47188",  # école d'ingénieurs sans ligne Onisep à son UAI
    "32446",  # coût Onisep en fourchette
    "14476",  # CPGE publique : constante
    "39030",  # école d'ingénieurs, un seul diplôme InserSup
    "43422",  # licence dont InserSup ne diffuse aucun taux
    "8587",   # alternance rattachée par la commune
    "5399",   # BTS SIO privé, alternance au même UAI, InserJeunes à deux options
    "23289",  # IFSI, 0 euros Onisep, insertion paramédicale non disponible
    "4974",   # BUT R&T, InserSup par l'université
    "31712",  # PASS public : constante
    "8882",   # BTS SIO privé, coût Onisep avec « gratuit en apprentissage »
]
APPRENTISSAGE_DEMO = ["28094"]  # BTS SIO en apprentissage (fiche de la démo)


def main() -> int:
    corpus = json.loads((RACINE / "data/processed/formations_etape_a.json").read_text(encoding="utf-8"))
    fiches = {str(f["cod_aff_form"]): f for f in corpus if f.get("source") == "parcoursup" and str(f.get("cod_aff_form")) in CODES}
    manquants = set(CODES) - set(fiches)
    if manquants:
        raise SystemExit(f"fiches absentes du corpus de l'étape A : {sorted(manquants)}")

    uais = {f["cod_uai"] for f in fiches.values()}
    cles = {cle_diplome(f.get("form_lib_voe_acc"), f.get("filiere_detaillee")) for f in fiches.values()}
    carto = {l["gta"]: l["etablissement_id_paysage"] for l in lire_csv(chemin_verifie("cartographie_parcoursup_2025"))}
    paysages = {carto.get(c) for c in CODES} - {None, ""}

    onisep = [l for l in lire_csv(chemin_verifie("onisep_ideo_actions_es")) if l["ENS code UAI"] in uais]
    deps_fiches = {(f.get("code_departement") or "").lstrip("0") for f in fiches.values()}
    apprentissage = [
        l for l in lire_csv(chemin_verifie("parcoursup_apprentissage_2025"))
        if (cle_diplome(l["form_lib_voe_acc"], l["fil_lib_voe_acc"]) in cles and l["dep"].lstrip("0") in deps_fiches)
        or l["cod_aff_form"] in APPRENTISSAGE_DEMO
    ]
    insersup = [
        l for l in lire_csv(chemin_verifie("insersup"))
        if (l["id_paysage"] in paysages or l["id_paysage_actuel"] in paysages)
        and l["type_diplome"] in ("but", "Licence générale", "Formation ingénieur")
    ]
    inserjeunes = [l for l in lire_csv(chemin_verifie("inserjeunes_bts")) if l["uai"] in uais]
    deps = {f.get("code_departement") for f in fiches.values()} | {l["dep"] for l in apprentissage}
    deps = {d.lstrip("0").zfill(2) if d and d.isdigit() else d for d in deps if d}

    with chemin_verifie("insee_cog_communes_2025").open(encoding="utf-8-sig", newline="") as fh:
        lecteur = csv.DictReader(fh)
        colonnes = lecteur.fieldnames
        communes = [l for l in lecteur if l.get("DEP") in deps]
    with (ICI / "cog_extrait.csv").open("w", encoding="utf-8", newline="") as fh:
        ecrivain = csv.DictWriter(fh, fieldnames=colonnes)
        ecrivain.writeheader()
        ecrivain.writerows(communes)

    sortie = {
        "fiches": fiches,
        "onisep": onisep,
        "apprentissage": apprentissage,
        "insersup": insersup,
        "inserjeunes": inserjeunes,
        "paysage": {c: carto[c] for c in CODES if carto.get(c)},
    }
    (ICI / "sources.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print({k: len(v) for k, v in sortie.items()}, "communes", len(communes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
