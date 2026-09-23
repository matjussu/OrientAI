"""Texte lu par le modèle pour une fiche Parcoursup : chaque chiffre nommé, défini, daté, sourcé.

Appelé par `src.rag.embeddings.fiche_to_text`, qui reste le point d'entrée unique.

Règles d'écriture :
- un indicateur porte le libellé du jeu officiel, et sa définition figure dans le bloc
  « Définitions » (libellés du jeu fr-esr-parcoursup 2025, lus sur l'API
  data.education.gouv.fr le 23/09/2026) ;
- une valeur absente n'est pas écrite (ni 0, ni « non renseigné » inventé) ;
- la session des chiffres est dite (« Parcoursup, session 2025 »), la source aussi.
"""
from __future__ import annotations

import math

SESSION = 2025
SOURCE = (
    f"Parcoursup, session {SESSION} : jeu open data fr-esr-parcoursup du ministère de "
    "l'Enseignement supérieur (SIES)"
)

# Libellés officiels des champs du jeu fr-esr-parcoursup 2025 (API data.education.gouv.fr,
# métadonnées lues le 23/09/2026). Le taux d'accès est le seul champ à porter une description
# en plus de son libellé ; elle est reprise mot pour mot.
DEFINITIONS = {
    "taux_acces": (
        "taux d'accès : rapport entre le nombre de candidats dont le rang de classement est "
        "inférieur ou égal au rang du dernier appelé de son groupe et le nombre de candidats "
        "ayant validé un vœu pour la formation étudiée en phase principale (ce n'est pas le "
        "rapport entre places et candidats)"
    ),
    "places": "places : capacité de l'établissement pour cette formation",
    "candidats": "candidats : effectif total des candidats pour la formation",
    "candidats_pp": "candidats en phase principale : effectif total des candidats en phase principale",
    "classes": "candidats classés : effectif des candidats classés par l'établissement en phase principale",
    "propositions": (
        "propositions : effectif des candidats ayant reçu une proposition d'admission de la part "
        "de l'établissement"
    ),
    "admis": "admis : effectif des candidats ayant accepté la proposition de l'établissement",
    "debut_pp": (
        "admis dès l'ouverture : part des admis ayant reçu leur proposition d'admission à "
        "l'ouverture de la procédure principale"
    ),
}


def _nombre(val) -> int | None:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return round(val)


def _pct(val) -> str | None:
    n = _nombre(val)
    return None if n is None else f"{n} %"


def _type(fiche: dict) -> str | None:
    libelle = fiche.get("type_formation")
    if not libelle:
        return None
    precision = fiche.get("precision_formation")
    return f"Type de formation : {libelle}" + (f", {precision}" if precision else "")


def _lieu(fiche: dict) -> list[str]:
    parts = [f"Établissement : {fiche.get('etablissement', '')}"]
    ville = fiche.get("ville", "")
    arrondissement = fiche.get("arrondissement")
    parts.append(f"Ville : {ville}" + (f" ({arrondissement})" if arrondissement else ""))
    if fiche.get("academie"):
        parts.append(f"Académie : {fiche['academie']}")
    return parts


def _admission(fiche: dict) -> tuple[str | None, list[str]]:
    """Ligne des chiffres d'admission + clés des définitions à publier."""
    adm = fiche.get("admission") or {}
    volumes = adm.get("volumes") or {}
    morceaux: list[str] = []
    definis: list[str] = []

    taux = _pct(fiche.get("taux_acces_parcoursup_2025", adm.get("taux_acces")))
    if taux:
        morceaux.append(f"taux d'accès {taux}")
        definis.append("taux_acces")
    places = _nombre(fiche.get("nombre_places", adm.get("places")))
    if places is not None:
        morceaux.append(f"{places} places")
        definis.append("places")
    candidats = _nombre(volumes.get("voeux_totaux"))
    candidats_pp = _nombre(volumes.get("voeux_phase_principale"))
    if candidats is not None:
        morceaux.append(f"{candidats} candidats" + (f", dont {candidats_pp} en phase principale" if candidats_pp is not None else ""))
        definis.append("candidats")
        if candidats_pp is not None:
            definis.append("candidats_pp")
    classes = _nombre(volumes.get("classes_phase_principale"))
    if classes is not None:
        morceaux.append(f"{classes} candidats classés")
        definis.append("classes")
    propositions = _nombre(fiche.get("propositions_totales"))
    if propositions is not None:
        morceaux.append(f"{propositions} propositions d'admission")
        definis.append("propositions")
    admis = _nombre(volumes.get("admis_total"))
    if admis is not None:
        morceaux.append(f"{admis} admis")
        definis.append("admis")
    debut = _pct(fiche.get("pct_acceptes_debut_pp"))
    if debut:
        morceaux.append(f"{debut} des admis ont reçu leur proposition dès l'ouverture de la phase principale")
        definis.append("debut_pp")

    if not morceaux:
        return None, []
    return f"Admission (Parcoursup, session {SESSION}) : " + " ; ".join(morceaux), definis


def _historique(fiche: dict) -> str | None:
    historique = (fiche.get("admission") or {}).get("historique") or {}
    if len(historique) < 2:
        return None
    sessions = []
    for annee in sorted(historique):
        snap = historique[annee] or {}
        bits = []
        taux = _pct(snap.get("taux_acces"))
        if taux:
            bits.append(f"taux d'accès {taux}")
        places = _nombre(snap.get("places"))
        if places is not None:
            bits.append(f"{places} places")
        candidats = _nombre(snap.get("voeux_totaux"))
        if candidats is not None:
            bits.append(f"{candidats} candidats")
        if bits:
            sessions.append(f"session {annee} : " + ", ".join(bits))
    return ("Évolution Parcoursup : " + " ; ".join(sessions)) if len(sessions) >= 2 else None


def blocs_parcoursup(fiche: dict) -> dict[str, list[str]]:
    """Blocs de texte propres à une fiche Parcoursup, rangés par position dans la fiche.

    - `identite` : type, lieu, académie (après le nom de la formation) ;
    - `admission` : chiffres d'admission, définitions, évolution ;
    - `fin` : lien vers la fiche officielle et source.
    """
    identite: list[str] = []
    t = _type(fiche)
    if t:
        identite.append(t)
    intitule = fiche.get("intitule_officiel")
    if intitule and intitule.strip() != (fiche.get("nom") or "").strip():
        identite.append(f"Intitulé officiel : {intitule}")
    identite.extend(_lieu(fiche))
    identite.append("Accès : après le bac, sur Parcoursup")
    if fiche.get("niveau"):
        identite.append(f"Diplôme visé : {fiche['niveau']}")
    if fiche.get("selectivite_code"):
        identite.append(f"Sélectivité (Parcoursup) : {fiche['selectivite_code']}")

    admission: list[str] = []
    ligne, definis = _admission(fiche)
    evolution = _historique(fiche)
    # Tout indicateur écrit porte sa définition, y compris quand il n'apparaît que dans
    # l'évolution (taux 2023-2024 présents, taux 2025 absent : 3 fiches le 23/09/2026).
    if evolution:
        for cle, mot in (("taux_acces", "taux d'accès"), ("places", " places"), ("candidats", " candidats")):
            if mot in evolution and cle not in definis:
                definis.append(cle)
    if ligne:
        admission.append(ligne)
    if definis:
        admission.append("Définitions (libellés officiels Parcoursup) : " + " ; ".join(DEFINITIONS[k] for k in definis))
    if evolution:
        admission.append(evolution)

    fin: list[str] = []
    if fiche.get("lien_form_psup"):
        fin.append(f"Fiche Parcoursup : {fiche['lien_form_psup']}")
    fin.append(f"Source : {SOURCE}")
    return {"identite": identite, "admission": admission, "fin": fin}
