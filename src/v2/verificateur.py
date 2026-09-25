"""Le vérificateur de chiffres (contrat du cerveau, section 6 ; CONTRAT-etape3, section 6). Déterministe.

Portée : pourcentages, euros, places, extraits par `src/eval/battery/numbers.py` (unités, tolérances et lecture des
tableaux du module, non modifié) ; et, depuis l'amendement v2 du contrat (25/09, relevé de Jarvis au palier 0 :
« 976 candidats » affiché sans contrôle alors que `candidats_ont_postule` est dans l'essentiel), les effectifs :
candidats, vœux, propositions, admis, inscrits, diplômés (tolérance 0,5 comme `critere_d`). Un chiffre est :
- `adosse`  : égal, à la tolérance, à une valeur de même unité rendue par un outil pendant la conversation ;
- `eleve`   : absent des résultats d'outils, mais écrit par l'élève dans la conversation (choix C4, Matteo 10783) ;
- `non_adosse` : ni l'un ni l'autre.

Levier de falsification (règle 9), ORIENTIA_SABOTAGE_V2 :
- `verificateur_laisse_passer` : tout chiffre est déclaré adossé ;
- `garder_phrase` : le retrait des phrases non adossées ne retire rien.
"""
from __future__ import annotations

import os
import re

from src.eval.battery.numbers import _TOLERANCE, NumberClaim, _to_float, extract_claims, table_numbers

SABOTAGES = ("verificateur_laisse_passer", "garder_phrase")
REECRITURE = ("Ces chiffres ne sont dans aucun résultat d'outil de cette conversation : {liste}. Retire-les, ou "
              "appelle l'outil qui les donne. Réécris ta réponse complète.")
REPONSE_VIDE = ("Je n'ai pas pu vérifier les chiffres de ma réponse avec les données officielles. Tu peux consulter "
                "directement la fiche officielle de la formation sur Parcoursup ou MonMaster, ou me reposer la "
                "question en précisant la formation et la ville.")


def _sabotage() -> str | None:
    s = os.environ.get("ORIENTIA_SABOTAGE_V2") or None
    return s if s in SABOTAGES else None


TOLERANCE = {**_TOLERANCE, "effectif": 0.5}
_EFFECTIF = re.compile(r"(?<![\d.,])(\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,](\d+))?[  ]?"
                       r"(candidat(?:e?s)?|v(?:oe|œ)ux|propositions?|admise?s?|inscrite?s?|diplômée?s?)\b", re.IGNORECASE)
_LIBELLE_EFFECTIF = re.compile(r"candidat|v(?:oe|œ)ux|proposition|admis|inscrit|diplômé", re.IGNORECASE)


def _unite_effectif(libelle: str) -> str | None:
    return "effectif" if _LIBELLE_EFFECTIF.search(libelle) else None


def chiffres(texte: str) -> list[NumberClaim]:
    """Chiffres contrôlés : ceux de `numbers.py` (pct, eur, places, tableaux compris), plus les effectifs."""
    out = list(extract_claims(texte))
    for ligne in (texte or "").splitlines():
        out += [NumberClaim(_to_float(m.group(1), m.group(2)), "effectif", ligne.strip()) for m in _EFFECTIF.finditer(ligne)]
    out += [NumberClaim(v, u, ligne) for v, u, ligne in table_numbers(texte, _unite_effectif) if u == "effectif"
            and not any(c.unit == "effectif" and c.line == ligne and c.value == v for c in out)]
    return out


def _fmt(v: float, unite: str) -> str:
    n = str(int(v)) if float(v).is_integer() else f"{v}".replace(".", ",")
    return n + {"pct": " %", "eur": " €", "places": " places", "effectif": ""}[unite]


def chiffres_eleve(messages: list[str]) -> list[tuple[float, str]]:
    return [(c.value, c.unit) for m in messages for c in chiffres(m)]


def verifier(texte: str, valeurs: list[dict], eleve: list[tuple[float, str]] | None = None) -> dict:
    """Statut de chaque chiffre du texte. `valeurs` : les valeurs structurées rendues par les outils."""
    eleve = eleve or []
    out = {"adosses": [], "eleve": [], "non_adosses": []}
    laisse_passer = _sabotage() == "verificateur_laisse_passer"
    for c in chiffres(texte):
        tol = TOLERANCE[c.unit]
        porteurs = [{"id": v["id"], "cle": v["cle"], "source_id": v["source_id"], "valeur": v["valeur"]}
                    for v in valeurs if v["unite"] == c.unit and abs(v["valeur"] - c.value) <= tol]
        rec = {"valeur": c.value, "unite": c.unit, "ligne": c.line}
        if porteurs or laisse_passer:
            out["adosses"].append(rec | {"porteurs": porteurs, "ambigu": len({p["id"] for p in porteurs}) > 1})
        elif any(u == c.unit and abs(v - c.value) <= tol for v, u in eleve):
            out["eleve"].append(rec)
        else:
            out["non_adosses"].append(rec)
    return out


def message_reecriture(non_adosses: list[dict]) -> str:
    liste = ", ".join(dict.fromkeys(_fmt(c["valeur"], c["unite"]) for c in non_adosses))
    return REECRITURE.format(liste=liste)


_PHRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9«*(\[-])")


def retirer_phrases(texte: str, valeurs: list[dict], eleve: list[tuple[float, str]] | None = None) -> tuple[str, list[str]]:
    """Retire chaque phrase (ou ligne de tableau) qui porte un chiffre non adossé. Rend (texte, phrases retirées)."""
    if _sabotage() == "garder_phrase":
        return texte, []
    retirees: list[str] = []
    lignes_out = []
    for ligne in texte.split("\n"):
        if not verifier(ligne, valeurs, eleve)["non_adosses"] and not _ligne_tableau_fautive(ligne, texte, valeurs, eleve):
            lignes_out.append(ligne)
            continue
        if ligne.strip().startswith("|"):
            retirees.append(ligne.strip())
            continue
        m = re.match(r"^(\s*(?:[-*•]|\d+[.)]|#+|>)\s+)?(.*)$", ligne)
        prefixe, corps = m.group(1) or "", m.group(2)
        gardees = []
        for phrase in _PHRASE.split(corps):
            if verifier(phrase, valeurs, eleve)["non_adosses"]:
                retirees.append(phrase.strip())
            elif phrase.strip():
                gardees.append(phrase.strip())
        if gardees:
            lignes_out.append(prefixe + " ".join(gardees))
    propre = re.sub(r"\n{3,}", "\n\n", "\n".join(lignes_out)).strip()
    return propre, retirees


def _ligne_tableau_fautive(ligne: str, texte: str, valeurs: list[dict], eleve) -> bool:
    """Une ligne de tableau dont un nombre nu (unité lue dans l'en-tête) n'est pas adossé : lue dans son tableau."""
    if not ligne.strip().startswith("|"):
        return False
    bloc = []
    for lg in texte.split("\n"):
        if lg.strip().startswith("|"):
            bloc.append(lg)
            if lg == ligne:
                break
        else:
            bloc = []
    if len(bloc) < 3:
        return False
    en_tete = "\n".join([bloc[0], bloc[1], ligne])
    return any(ligne.strip() == c["ligne"] for c in verifier(en_tete, valeurs, eleve)["non_adosses"])
