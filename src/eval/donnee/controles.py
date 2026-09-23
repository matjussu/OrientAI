"""Contrôles déterministes du texte lu par le modèle pour une fiche Parcoursup.

Chaque contrôle correspond à un défaut mesuré le 23/09/2026 sur le corpus de la prod
(cahier des charges de la donnée verticale, section 2). Un contrôle rend le nom du défaut
quand il le trouve ; une fiche saine n'en rend aucun.

Usage (bilan sur un corpus) :
    python -m src.eval.donnee.controles --corpus <formations.json> [--revision-texte origin/main]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from src.collect.types_formation import NIVEAU_PAR_FILI
from src.eval.donnee.texte import charger_fiche_to_text

# Mot qui doit figurer dans le texte pour que le type de formation soit dit.
MOT_DU_TYPE = {
    "BTS": "BTS", "BUT": "BUT", "CPGE": "CPGE", "PASS": "PASS", "Licence_Las": "LAS", "IFSI": "IFSI",
    "Licence": "Licence", "Ecole d'Ingénieur": "ingénieur", "Ecole de Commerce": "commerce", "EFTS": "travail social",
}
_VILLE_BRUTE = re.compile(r"CEDEX|Arrondissement|\s{2,}|^\s|\s$", re.IGNORECASE)


def controler(fiche: dict, texte: str) -> list[str]:
    """Défauts trouvés dans le texte d'une fiche Parcoursup (liste vide = fiche saine)."""
    defauts = []
    if "taux d'accès par profil" in texte:
        defauts.append("repartition_nommee_taux_acces")
    if "Île-de-France" in texte and fiche.get("region") != "Île-de-France":
        defauts.append("meme_academie_nommee_ile_de_france")
    source_insertion = str((fiche.get("insertion_pro") or {}).get("source") or "").lower()
    if "insersup" in source_insertion and "Inserjeunes" in texte:
        defauts.append("insersup_attribue_a_inserjeunes")
    mot = MOT_DU_TYPE.get(fiche.get("fili_code") or "")
    if mot and mot.lower() not in texte.lower():
        defauts.append("type_non_dit")
    if fiche.get("fili_code") == "PASS" and "option" not in texte:
        defauts.append("option_pass_non_dite")
    if _VILLE_BRUTE.search(fiche.get("ville") or ""):
        defauts.append("ville_non_normalisee")
    if "taux d'accès" in texte and "rang du dernier appelé" not in texte:
        defauts.append("taux_acces_sans_definition")
    if "même académie" in texte and "(académie" not in texte:
        defauts.append("academie_non_nommee")
    if "taux d'accès" in texte and "session 2025" not in texte:
        defauts.append("session_non_dite")
    if "Phase : master" in texte:
        defauts.append("post_bac_lu_comme_master")
    attendu = NIVEAU_PAR_FILI.get(fiche.get("fili_code") or "")
    if attendu and not re.search(r"bac\s*\+\s*\d", fiche.get("nom") or "", re.IGNORECASE) \
            and re.search(r"(?:Niveau|Diplôme visé) : bac\+\d", texte) \
            and not re.search(rf"(?:Niveau|Diplôme visé) : {re.escape(attendu)}\b", texte):
        defauts.append("niveau_contredit_la_filiere")
    return defauts


# ── étape B-1 : coût, alternance, insertion (contrat results/donnee_etape_b/CONTRACT.md) ─────
CHAMPS_B = ("cout", "alternance", "insertion")
# Champs attendus par source : une fiche d'apprentissage EST une formation en alternance, elle
# ne porte pas le champ `alternance` (contrat, section 4).
CHAMPS_B_PAR_SOURCE = {"parcoursup": CHAMPS_B, "parcoursup_apprentissage": ("cout", "insertion")}
_LIGNE_COUT = re.compile(r"Coût[^|]*")


def controler_etape_b(fiche: dict, texte: str) -> list[str]:
    """Défauts de l'étape B-1. Muet sur une fiche qui ne porte aucun champ B (corpus antérieur)."""
    if not any(c in fiche for c in CHAMPS_B):
        return []
    defauts = []
    attendus = CHAMPS_B_PAR_SOURCE.get(fiche.get("source") or "", CHAMPS_B)
    for champ in attendus:
        valeur = fiche.get(champ)
        if not isinstance(valeur, dict) or valeur.get("statut") not in ("disponible", "non_disponible"):
            defauts.append(f"{champ}_absent")
        elif valeur["statut"] == "non_disponible" and not valeur.get("raison"):
            defauts.append(f"{champ}_non_disponible_sans_raison")
        elif valeur["statut"] == "disponible" and not (valeur.get("source") and valeur.get("millesime") and valeur.get("collecte")):
            defauts.append(f"{champ}_sans_source_millesime_collecte")
    cout = fiche.get("cout")
    if isinstance(cout, dict):
        ligne = (_LIGNE_COUT.search(texte) or [""])[0]
        if not ligne:
            defauts.append("cout_non_ecrit")
        elif cout.get("statut") == "disponible":
            v = cout["valeur"]
            montants = [v.get("droits_inscription_eur"), v.get("scolarite_total_eur"), v.get("scolarite_annuel_eur"),
                        *(v.get("fourchette_eur") or [])]
            for m in montants:
                if m and f"{m} euros" not in ligne:
                    defauts.append("cout_montant_non_ecrit")
                    break
            if not re.search(r"Onisep, tarif \d{4}|tableau ministériel|Service-Public", ligne):
                defauts.append("cout_sans_source")
        elif "non disponible" not in ligne:
            defauts.append("cout_non_disponible_non_dit")
    if "insertion" in fiche and ("médiane régionale" in texte or "Insertion pro (source" in texte):
        defauts.append("insertion_approchee_ecrite")
    if "emploi stable" in texte:
        defauts.append("emploi_stable_sans_definition")
    if "non disponible ()" in texte or "non disponible (None)" in texte:
        defauts.append("non_disponible_sans_raison_dans_le_texte")
    return defauts


def bilan(corpus: list[dict], fiche_to_text: Callable[[dict], str]) -> dict:
    fiches = [f for f in corpus if f.get("source") in CHAMPS_B_PAR_SOURCE]
    compte: Counter = Counter()
    for f in fiches:
        texte = fiche_to_text(f)
        compte.update(controler(f, texte) + controler_etape_b(f, texte))
    return {"fiches": dict(Counter(f["source"] for f in fiches)), "defauts": dict(compte.most_common())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--revision-texte", default=None)
    args = ap.parse_args(argv)
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    resultat = bilan(corpus, charger_fiche_to_text(args.revision_texte))
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
