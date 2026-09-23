"""Part des chiffres attendus du banc vertical présents dans le texte de LEUR fiche.

Question mesurée : quand le modèle lit la fiche qui porte un chiffre attendu, ce chiffre y
est-il écrit ? C'est une condition nécessaire pour qu'il puisse le citer juste. Zéro LLM :
le contrôle est une comparaison de nombres.

Pour chaque chiffre attendu `{valeur, unite, fiche}` du banc :
1. la fiche est retrouvée par identifiant exact (`cod_aff_form` pour Parcoursup,
   `id_mon_master.ifc` pour MonMaster, `id` pour un agrégat) ;
2. son texte est produit par `fiche_to_text` (version du code courant, ou d'une révision git) ;
3. le chiffre est « présent » si le texte contient un nombre du même type à la tolérance
   près : un pourcentage (±0,51, arrondi à l'entier côté texte) pour l'unité `%`, un montant
   en euros (±0,5) pour les euros, un entier exact pour les effectifs (places, vœux...).

Témoin de hasard : le même contrôle contre le texte d'une AUTRE fiche du banc (tirage à
graine fixe). Un taux de présence proche de son témoin ne mesurerait rien.

Usage :
    python -m src.eval.donnee.banc_textes --banc <battery_verticale.json> --corpus <formations.json>
        [--revision-texte origin/main] [--sortie resultat.json]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from src.eval.donnee.texte import charger_fiche_to_text

_POURCENT = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s?%")
_EUROS = re.compile(r"(?<![\d.,])(\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,]\d+)?\s?(?:€|euros?\b)", re.IGNORECASE)
_ENTIER = re.compile(r"(?<![\d.,])(\d{1,3}(?:[  ]\d{3})+|\d+)(?![\d.,]*\s?%)")
_UNITES_EFFECTIF = {"places", "voeux", "candidats", "propositions"}


def _float(s: str) -> float:
    return float(s.replace(" ", "").replace(" ", "").replace(",", "."))


def present(valeur: float, unite: str, texte: str) -> bool:
    if unite == "%":
        return any(abs(_float(m) - valeur) <= 0.51 for m in _POURCENT.findall(texte))
    if "euro" in unite:
        return any(abs(_float(m) - valeur) <= 0.5 for m in _EUROS.findall(texte))
    if unite in _UNITES_EFFECTIF:
        return any(_float(m) == float(valeur) for m in _ENTIER.findall(texte))
    raise ValueError(f"unité non prise en charge : {unite}")


def indexer(corpus: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for f in corpus:
        if f.get("source") == "parcoursup" and f.get("cod_aff_form"):
            index[f"psup:{f['cod_aff_form']}"] = f
        ifc = (f.get("id_mon_master") or {}).get("ifc") if isinstance(f.get("id_mon_master"), dict) else None
        if ifc:
            index[f"mm:{ifc}"] = f
        if f.get("id"):
            index.setdefault(f"id:{f['id']}", f)
    return index


def cle_fiche(ref: dict) -> str:
    if ref.get("cod_aff_form"):
        return f"psup:{ref['cod_aff_form']}"
    if ref.get("id_type") == "monmaster_ifc":
        return f"mm:{ref['id']}"
    return f"id:{ref['id']}"


def mesurer(banc: dict, corpus: list[dict], fiche_to_text, graine: int = 20260923) -> dict:
    index = indexer(corpus)
    chiffres = [(item["domaine"], c) for item in banc["items"] for c in item["attendus"]["chiffres"]]
    cles = sorted({cle_fiche(c["fiche"]) for _, c in chiffres})
    textes = {k: fiche_to_text(index[k]) for k in cles if k in index}
    rng = random.Random(graine)

    par_champ: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    par_domaine: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    absents, fiches_manquantes = [], []
    n_present = n_temoin = 0
    for domaine, c in chiffres:
        cle = cle_fiche(c["fiche"])
        if cle not in textes:
            fiches_manquantes.append(cle)
            continue
        ok = present(float(c["valeur"]), c["unite"], textes[cle])
        autre = rng.choice([k for k in textes if k != cle])
        n_temoin += present(float(c["valeur"]), c["unite"], textes[autre])
        n_present += ok
        for compteur in (par_champ[c["champ"]], par_domaine[domaine]):
            compteur[0] += ok
            compteur[1] += 1
        if not ok:
            absents.append({"fiche": cle, "champ": c["champ"], "valeur": c["valeur"], "unite": c["unite"]})

    n = len(chiffres) - len(fiches_manquantes)
    return {
        "chiffres_attendus": len(chiffres),
        "fiches_introuvables": sorted(set(fiches_manquantes)),
        "chiffres_mesures": n,
        "presents": n_present,
        "part_presents": round(n_present / n, 4) if n else None,
        "temoin_hasard": round(n_temoin / n, 4) if n else None,
        "par_domaine": {d: {"presents": v[0], "total": v[1]} for d, v in sorted(par_domaine.items())},
        "par_champ": {ch: {"presents": v[0], "total": v[1]} for ch, v in sorted(par_champ.items(), key=lambda kv: -kv[1][1])},
        "absents": absents,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banc", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--revision-texte", default=None, help="révision git de fiche_to_text (défaut : code courant)")
    ap.add_argument("--sortie", type=Path)
    args = ap.parse_args(argv)

    banc = json.loads(args.banc.read_text(encoding="utf-8"))
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    resultat = mesurer(banc, corpus, charger_fiche_to_text(args.revision_texte))
    resultat["entrees"] = {
        "banc": str(args.banc), "corpus": str(args.corpus),
        "revision_texte": args.revision_texte or "code courant",
    }
    sortie = json.dumps(resultat, ensure_ascii=False, indent=2)
    if args.sortie:
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(sortie + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in resultat.items() if k != "absents"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
