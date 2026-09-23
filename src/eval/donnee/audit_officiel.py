"""Audit d'exactitude : fiches tirées au hasard, comparées une à une au jeu officiel en ligne.

Le témoin est l'API publique du jeu fr-esr-parcoursup 2025 (data.education.gouv.fr),
interrogée au moment de l'audit : pas le fichier brut téléchargé par le pipeline, pour que
l'audit ne partage pas son instrument avec ce qu'il vérifie.

Par fiche, deux niveaux :
- la DONNÉE : taux d'accès, places, candidats, établissement, ville de la fiche contre la
  ligne officielle de même `cod_aff_form` ;
- le TEXTE lu par le modèle (`fiche_to_text`) : les valeurs officielles de taux, places et
  candidats y figurent-elles ?
Un écart est « expliqué » quand il résulte d'une transformation documentée (ville
normalisée par le COG INSEE : arrondissement, CEDEX, accents). Tout autre écart est « non
expliqué » et fait échouer l'audit (code de sortie 1).

Tirage : fiches Parcoursup des trois domaines de la démo, à graine fixe, réparties entre
informatique, santé et maths.

Usage :
    python -m src.eval.donnee.audit_officiel --corpus <formations_etape_a.json>
        [--n 50] [--graine 20260923] [--sortie results/donnee_etape_a/audit_officiel.json]
        [--revision-texte origin/main]   # contrôle positif : l'ancien texte doit échouer
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from src.collect.communes import cle_nom, nettoyer_libelle
from src.eval.donnee.banc_textes import present
from src.eval.donnee.texte import charger_fiche_to_text

API = "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-esr-parcoursup/records"
DOMAINES_INFO = {"informatique", "cyber", "data_ia"}
REGLES_MATHS = {"M01", "M02", "M03"}


def verticale(fiche: dict) -> str | None:
    if fiche.get("domaine") in DOMAINES_INFO:
        return "informatique"
    if fiche.get("domaine") == "sante":
        return "sante"
    if fiche.get("domaine_regle") in REGLES_MATHS:
        return "maths"
    return None


def tirer(corpus: list[dict], n: int, graine: int) -> list[dict]:
    par_dom: dict[str, list[dict]] = {"informatique": [], "sante": [], "maths": []}
    for f in corpus:
        if f.get("source") == "parcoursup" and (v := verticale(f)):
            par_dom[v].append(f)
    rng = random.Random(graine)
    tirage: list[dict] = []
    quotas = {d: n // 3 + (1 if i < n % 3 else 0) for i, d in enumerate(sorted(par_dom))}
    for dom in sorted(par_dom):
        tirage.extend(rng.sample(sorted(par_dom[dom], key=lambda f: f["cod_aff_form"]), quotas[dom]))
    return tirage


def ligne_officielle(cod: str) -> dict:
    url = API + "?" + urllib.parse.urlencode({"where": f'cod_aff_form="{cod}"', "limit": 2})
    for essai in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as rep:
                resultats = json.load(rep)["results"]
            if len(resultats) != 1:
                raise LookupError(f"cod_aff_form {cod} : {len(resultats)} lignes officielles")
            return resultats[0]
        except (OSError, json.JSONDecodeError):
            if essai == 2:
                raise
            time.sleep(2 * (essai + 1))
    raise AssertionError("inaccessible")


def _egal_nombre(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) < 1e-9


def auditer_fiche(fiche: dict, officiel: dict, texte: str) -> dict:
    volumes = (fiche.get("admission") or {}).get("volumes") or {}
    comparaisons = {
        "taux_acces": (fiche.get("taux_acces_parcoursup_2025"), officiel.get("taux_acces_ens")),
        "places": (fiche.get("nombre_places"), officiel.get("capa_fin")),
        "candidats": (volumes.get("voeux_totaux"), officiel.get("voe_tot")),
    }
    ecarts, expliques = [], []
    for champ, (notre, off) in comparaisons.items():
        if not _egal_nombre(notre, off):
            ecarts.append({"champ": champ, "corpus": notre, "officiel": off})
    etab_off = " ".join(str(officiel.get("g_ea_lib_vx") or "").split())
    if " ".join(str(fiche.get("etablissement") or "").split()) != etab_off:
        ecarts.append({"champ": "etablissement", "corpus": fiche.get("etablissement"), "officiel": etab_off})
    ville_off = str(officiel.get("ville_etab") or "")
    if fiche.get("ville") != ville_off:
        brut = nettoyer_libelle(ville_off)
        if fiche.get("arrondissement") and brut.lower().startswith(fiche["ville"].lower()):
            expliques.append({"champ": "ville", "corpus": fiche["ville"], "officiel": ville_off,
                              "explication": "arrondissement ramené à la commune (COG INSEE)"})
        elif cle_nom(fiche.get("ville") or "") == cle_nom(brut):
            expliques.append({"champ": "ville", "corpus": fiche["ville"], "officiel": ville_off,
                              "explication": "libellé de la commune dans le COG INSEE (accents, CEDEX, espaces)"})
        else:
            ecarts.append({"champ": "ville", "corpus": fiche.get("ville"), "officiel": ville_off})

    texte_absents = []
    for champ, unite in (("taux_acces", "%"), ("places", "places"), ("candidats", "candidats")):
        valeur = comparaisons[champ][1]
        if valeur is not None and not present(float(valeur), unite, texte):
            texte_absents.append({"champ": champ, "officiel": valeur})
    return {
        "cod_aff_form": fiche["cod_aff_form"], "verticale": verticale(fiche),
        "nom": fiche.get("nom"), "precision": fiche.get("precision_formation"),
        "etablissement": fiche.get("etablissement"), "ville": fiche.get("ville"),
        "lien_form_psup": fiche.get("lien_form_psup"),
        "ecarts_non_expliques": ecarts, "ecarts_expliques": expliques,
        "absents_du_texte": texte_absents,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--graine", type=int, default=20260923)
    ap.add_argument("--sortie", type=Path)
    ap.add_argument("--revision-texte", default=None,
                    help="révision git de fiche_to_text à auditer (contrôle positif : origin/main doit échouer)")
    args = ap.parse_args(argv)

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    fiche_to_text = charger_fiche_to_text(args.revision_texte)
    lignes = [
        auditer_fiche(f, ligne_officielle(f["cod_aff_form"]), fiche_to_text(f))
        for f in tirer(corpus, args.n, args.graine)
    ]
    non_expliques = sum(len(l["ecarts_non_expliques"]) for l in lignes)
    absents = sum(len(l["absents_du_texte"]) for l in lignes)
    resultat = {
        "date": dt.datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds"),
        "temoin": API,
        "corpus": str(args.corpus),
        "graine": args.graine,
        "revision_texte": args.revision_texte or "code courant",
        "fiches": len(lignes),
        "par_verticale": {v: sum(1 for l in lignes if l["verticale"] == v) for v in ("informatique", "sante", "maths")},
        "ecarts_non_expliques": non_expliques,
        "ecarts_expliques": sum(len(l["ecarts_expliques"]) for l in lignes),
        "valeurs_officielles_absentes_du_texte": absents,
        "lignes": lignes,
    }
    if args.sortie:
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in resultat.items() if k != "lignes"}, ensure_ascii=False, indent=2))
    # Un audit sur zéro fiche ne prouve rien : il échoue.
    return 1 if not lignes or non_expliques or absents else 0


if __name__ == "__main__":
    sys.exit(main())
