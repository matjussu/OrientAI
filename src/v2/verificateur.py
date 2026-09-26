"""Le vérificateur de chiffres (contrat du cerveau, section 6 ; CONTRAT-etape3, section 6). Déterministe.

Portée : pourcentages, euros, places, extraits par `src/eval/battery/numbers.py` (unités, tolérances et lecture des
tableaux du module, non modifié) ; et, depuis l'amendement v2 du contrat (25/09, relevé de Jarvis au palier 0 :
« 976 candidats » affiché sans contrôle alors que `candidats_ont_postule` est dans l'essentiel), les effectifs :
candidats, vœux, propositions, admis, inscrits, diplômés (tolérance 0,5 comme `critere_d`). Un chiffre est :
- `adosse`  : égal, à la tolérance, à une valeur de même unité rendue par un outil pendant la conversation ;
- `eleve`   : absent des résultats d'outils, mais écrit par l'élève dans la conversation (choix C4, Matteo 10783) ;
- `non_adosse` : ni l'un ni l'autre.

Étape 4 (CONTRAT-etape4, section 6), deux contrôles de plus, déterministes :
- libellé (6.1) : un chiffre adossé dont TOUS les porteurs imposent une portée (nationale) ou une période (par an, du
  cycle) que sa phrase contredit est « mal nommé » ;
- absence (6.2) : une phrase qui affirme qu'une formation n'existe pas, quand un résultat d'outil du tour était
  tronqué, avait des candidats non montrés, ou était vide.

Leviers de falsification (règle 9), ORIENTIA_SABOTAGE_V2 :
- `verificateur_laisse_passer` : tout chiffre est déclaré adossé ;
- `garder_phrase` : le retrait des phrases non adossées ne retire rien ;
- `libelle_laisse_passer` : aucun chiffre n'est déclaré mal nommé ;
- `absence_laisse_passer` : aucune absence n'est relevée.
"""
from __future__ import annotations

import os
import re

from src.eval.battery.numbers import _TOLERANCE, NumberClaim, _to_float, extract_claims, table_numbers

SABOTAGES = ("verificateur_laisse_passer", "garder_phrase", "libelle_laisse_passer", "absence_laisse_passer")
REECRITURE = ("Ces chiffres ne sont dans aucun résultat d'outil de cette conversation : {liste}. Retire-les, ou "
              "appelle l'outil qui les donne.")
REECRITURE_LIBELLE = "Ces chiffres sont mal nommés ; l'outil les nomme ainsi, reprends ce nom : {liste}."
REECRITURE_ABSENCE = ("Tu affirmes une absence alors que {motif}. Dis exactement ce que tu as vérifié et ce que tu n'as "
                      "pas vérifié, ou cherche le reste : {phrases}")
# Constat 3.6 du contrat de l'étape 4 : 5 des 11 réécritures du vertical parlaient de la correction à l'élève.
REECRITURE_FIN = ("Réécris ta réponse complète. L'élève ne voit pas cette consigne : ne la mentionne pas, donne "
                  "directement ta réponse.")
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


# ── Libellé (CONTRAT-etape4, 6.1) ────────────────────────────────────────────────────────────
_NATIONAL = re.compile(r"\bnationa(?:l|le|ux|les)\b", re.IGNORECASE)
_PAR_AN = re.compile(r"par an\b|/\s?an\b|\bannuel", re.IGNORECASE)
_CYCLE = re.compile(r"du cycle|au total|pour tout le cycle|sur tout le cycle", re.IGNORECASE)


def _contexte(ligne: str, texte: str) -> str:
    """La ligne du chiffre ; pour une ligne de tableau, l'en-tête du tableau en plus (la portée y est souvent)."""
    if not ligne.strip().startswith("|"):
        return ligne
    bloc = []
    for lg in texte.split("\n"):
        if lg.strip().startswith("|"):
            bloc.append(lg)
            if lg.strip() == ligne.strip():
                return "\n".join(bloc[:2] + [ligne])
        else:
            bloc = []
    return ligne


def _faute_de_libelle(porteur: dict, contexte: str) -> str | None:
    """Ce que la phrase contredit dans le libellé ou la portée du porteur, ou None."""
    lib = (porteur.get("libelle") or "").lower()
    if porteur.get("portee") == "nationale" and not _NATIONAL.search(contexte):
        return "chiffre national, dis-le national"
    if "du cycle" in lib and _PAR_AN.search(contexte):
        return "montant pour tout le cycle, pas par an"
    if ("par an" in lib or "annuel" in lib) and _CYCLE.search(contexte):
        return "montant par an, pas pour tout le cycle"
    return None


def mal_nommes(texte: str, adosses: list[dict], valeurs: list[dict]) -> list[dict]:
    """Chiffres adossés dont TOUS les porteurs imposent un libellé que la phrase contredit. Un porteur sans portée ni
    période (la plupart) ne contredit jamais rien : un chiffre ambigu entre une valeur nationale et une valeur de
    formation n'est pas relevé."""
    if _sabotage() == "libelle_laisse_passer":
        return []
    out = []
    for c in adosses:
        porteurs = [v for v in valeurs if v["unite"] == c["unite"] and abs(v["valeur"] - c["valeur"]) <= TOLERANCE[c["unite"]]]
        ctx = _contexte(c["ligne"], texte)
        fautes = [_faute_de_libelle(p, ctx) for p in porteurs]
        if porteurs and all(fautes):
            p = porteurs[0]
            out.append({"valeur": c["valeur"], "unite": c["unite"], "ligne": c["ligne"], "faute": fautes[0],
                        "libelle": p.get("libelle") or p["cle"], "portee": p.get("portee"), "id": p["id"]})
    return out


# ── Absence (CONTRAT-etape4, 6.2) ────────────────────────────────────────────────────────────
# Lexique fermé, étalonné sur les réponses du lot 0 de l'étape 3 (jamais sur le vertical ni le gate F) : voir
# docs/cerveau/etape4/mesures/etalonnage_absence.json.
_NOMS = (r"formations?|bts|buts?|licences?|masters?|pr[ée]pas?|cpge|classes? pr[ée]paratoires?|[ée]coles?|options?|"
         r"parcours|ifsi|pass|las|iut|lyc[ée]es?|[ée]tablissements?|instituts?|dipl[ôo]mes?|cursus|universit[ée]s?|"
         r"fac|dut|bachelors?")
_ABSENCE = re.compile(
    r"\baucun(?:e|s|es)?\s+(?:\w+\s+){0,2}?(?:" + _NOMS + r")\b"
    r"|\bil n['’]y a (?:pas|aucun\w*|plus)\s+(?:de |d['’]|d['’]autres? )?(?:\w+\s+){0,1}?(?:" + _NOMS + r")\b"
    r"|\b(?:" + _NOMS + r")\b[^.!?]{0,60}\bn['’]existe(?:nt)? pas\b"
    r"|\bje n['’]en (?:ai |trouve |vois )?(?:trouv\w* )?aucun",
    re.IGNORECASE)
_PAS_UNE_ABSENCE = re.compile(r"publi|disponible|chiffre|donn[ée]e", re.IGNORECASE)


def absences(texte: str) -> list[str]:
    """Phrases qui affirment qu'une formation n'existe pas (ou qu'aucune n'a une valeur). « non publié » et « non
    disponible » sont voulus par le prompt : ils ne comptent pas."""
    if _sabotage() == "absence_laisse_passer":
        return []
    out = []
    for ligne in (texte or "").split("\n"):
        for phrase in _PHRASE.split(ligne):
            if _ABSENCE.search(phrase) and not _PAS_UNE_ABSENCE.search(phrase):
                out.append(phrase.strip())
    return out


def phrases_portant(c: dict) -> list[str]:
    """Les phrases de la ligne d'un chiffre qui le portent (la ligne entière pour une ligne de tableau)."""
    ligne = c["ligne"]
    if ligne.strip().startswith("|"):
        return [ligne.strip()]
    tol = TOLERANCE[c["unite"]]
    return [ph.strip() for ph in _PHRASE.split(ligne)
            if any(x.unit == c["unite"] and abs(x.value - c["valeur"]) <= tol for x in chiffres(ph))] or [ligne.strip()]


def motif_incomplet(outils_du_tour: list[dict]) -> str | None:
    """Pourquoi une absence ne peut pas être affirmée dans ce tour : un résultat tronqué, des candidats non montrés, ou
    une recherche vide. None si tout ce qui a été cherché a été vu."""
    raisons = []
    for o in outils_du_tour:
        m = o.get("meta") or {}
        if not o.get("execute") or o.get("erreur"):
            continue
        if o["nom"] in ("chercher_formations", "chercher_masters"):
            if m.get("tronque"):
                raisons.append(f"la recherche {o['nom']} était tronquée ({m.get('nb_resultats')} trouvées, "
                               f"{m.get('limite')} montrées)")
            elif m.get("nb_resultats") == 0:
                raisons.append(f"une recherche {o['nom']} était vide (0 dans la base ne veut pas dire 0 en réalité)")
        elif o["nom"] == "trouver_formation":
            if m.get("tronque"):
                raisons.append(f"trouver_formation a montré 10 candidats sur {m.get('nb_candidats')}")
            elif m.get("nb_candidats") == 0:
                raisons.append("trouver_formation n'a rien trouvé (0 dans la base ne veut pas dire 0 en réalité)")
    return " ; ".join(dict.fromkeys(raisons)) or None


def message_reecriture(non_adosses: list[dict], libelles: list[dict] | None = None,
                       absences_: list[str] | None = None, motif: str | None = None) -> str:
    morceaux = []
    if non_adosses:
        morceaux.append(REECRITURE.format(liste=", ".join(dict.fromkeys(_fmt(c["valeur"], c["unite"])
                                                                          for c in non_adosses))))
    if libelles:
        morceaux.append(REECRITURE_LIBELLE.format(liste=" ; ".join(dict.fromkeys(
            f"{_fmt(c['valeur'], c['unite'])} = « {c['libelle']} » ({c['faute']})" for c in libelles))))
    if absences_:
        morceaux.append(REECRITURE_ABSENCE.format(motif=motif, phrases=" | ".join(absences_)))
    return " ".join(morceaux + [REECRITURE_FIN])


_PHRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9«*(\[-])")


def retirer_phrases(texte: str, valeurs: list[dict], eleve: list[tuple[float, str]] | None = None,
                    retirer_aussi: set[str] | None = None) -> tuple[str, list[str]]:
    """Retire chaque phrase (ou ligne de tableau) qui porte un chiffre non adossé, et chaque phrase de `retirer_aussi`
    (chiffre mal nommé, absence : CONTRAT-etape4, 6.1 et 6.2). Rend (texte, phrases retirées)."""
    if _sabotage() == "garder_phrase":
        return texte, []
    retirer_aussi = {x.strip() for x in (retirer_aussi or set())}
    retirees: list[str] = []
    lignes_out = []
    for ligne in texte.split("\n"):
        if (not verifier(ligne, valeurs, eleve)["non_adosses"] and not _ligne_tableau_fautive(ligne, texte, valeurs, eleve)
                and ligne.strip() not in retirer_aussi
                and not any(ph.strip() in retirer_aussi for ph in _PHRASE.split(ligne))):
            lignes_out.append(ligne)
            continue
        if ligne.strip().startswith("|"):
            retirees.append(ligne.strip())
            continue
        m = re.match(r"^(\s*(?:[-*•]|\d+[.)]|#+|>)\s+)?(.*)$", ligne)
        prefixe, corps = m.group(1) or "", m.group(2)
        gardees = []
        for phrase in _PHRASE.split(corps):
            if verifier(phrase, valeurs, eleve)["non_adosses"] or phrase.strip() in retirer_aussi:
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
