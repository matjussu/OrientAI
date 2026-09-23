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
import re

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
    - `complements` : coût, alternance, insertion (étape B-1 ; vide sur un corpus antérieur) ;
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

    if fiche.get("source") == "parcoursup_apprentissage":
        return {
            "identite": identite,
            "admission": blocs_apprentissage(fiche),
            "complements": blocs_complements(fiche),
            "fin": ([f"Fiche Parcoursup : {fiche['lien_form_psup']}"] if fiche.get("lien_form_psup") else [])
            + [f"Source : {SOURCE_APPRENTISSAGE}"],
        }

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
    return {"identite": identite, "admission": admission, "complements": blocs_complements(fiche), "fin": fin}


# ── Étape B-1 : coût, alternance, insertion (contrat results/donnee_etape_b/CONTRACT.md) ──────
# Chaque champ est une enveloppe {statut, valeur, raison, source, millesime, collecte,
# rattachement}. Une donnée non disponible est écrite comme telle, avec sa raison : le modèle ne
# doit pas combler un trou par un chiffre de mémoire.


# Définitions des indicateurs d'insertion, reprises des descriptions des champs des jeux InserSup
# et InserJeunes (API, métadonnées lues le 23/09/2026). Le « taux de sortants en emploi stable »
# d'InserSup n'a pas de description publiée : il reste dans la donnée, il n'est pas écrit dans le
# texte (sa valeur dépasse souvent le taux d'emploi, son dénominateur n'est donc pas le même, et
# on ne l'écrit pas sans savoir lequel).
DEFINITIONS_INSERTION = {
    "taux_emploi_salarie_fr": (
        "taux d'emploi salarié en France (InserSup) : part des diplômés en emploi salarié en France "
        "parmi l'ensemble des diplômés actifs (en emploi ou en recherche) ou inactifs, 6, 12 ou 18 "
        "mois après le diplôme"
    ),
    "salaire_median": "salaire (InserSup) : salaire mensuel net médian en équivalent temps plein, 12 mois après le diplôme",
    "sortants": "diplômés sortis des études (InserSup) : nombre de sortants 12 mois après le diplôme",
    "inserjeunes_taux_emploi": (
        "taux d'emploi (InserJeunes) : parmi les lycéens et étudiants inscrits en dernière année "
        "d'un cycle d'études professionnel de niveau CAP à BTS et qui ne sont plus en formation en "
        "France à la rentrée suivante, part de ceux qui sont en emploi salarié 6 ou 12 mois après "
        "leur sortie d'études (cumul sur deux cohortes de sortants)"
    ),
    "inserjeunes_poursuite": (
        "taux de poursuite d'études (InserJeunes) : parmi les lycéens et étudiants inscrits en "
        "dernière année d'un cycle d'études professionnel de niveau CAP à BTS, part de ceux qui sont "
        "toujours en formation en France à la rentrée suivante, y compris en cas de redoublement "
        "(cumul sur deux années scolaires)"
    ),
}


def _eur(n) -> str | None:
    n = _nombre(n)
    return None if n is None else f"{n} euros"


def _taux_fr(val) -> str | None:
    if isinstance(val, bool) or not isinstance(val, (int, float)) or math.isnan(val):
        return None
    # Le taux est écrit comme la source le publie (44,83 reste 44,83), à la virgule française.
    return (repr(float(val)).rstrip("0").rstrip(".") if val != int(val) else str(int(val))).replace(".", ",") + " %"


_SOURCES_COURTES = {
    "tableau_droits_2026_2027": "tableau ministériel des droits de scolarité 2026-2027",
    "service_public_f36520": "Service-Public, fiche F36520",
}


def _source_courte(champ: dict) -> str:
    source = champ.get("source") or {}
    return _SOURCES_COURTES.get(source.get("id"), source.get("libelle") or "")


def _cout(fiche: dict) -> str | None:
    champ = fiche.get("cout")
    if not isinstance(champ, dict):
        return None
    if champ.get("statut") != "disponible":
        return f"Coût : non disponible ({champ.get('raison')})"
    v = champ["valeur"]
    source = champ["source"]["id"]
    if source == "code_travail_l6211_1":
        return (
            f"Coût de la formation en apprentissage (Code du travail, article L6211-1) : « {v.get('texte_source')} » "
            "Cette phrase porte sur la formation seulement ; elle ne dit rien des autres frais (logement, "
            "transport, équipement)"
        )
    if source.startswith("onisep"):
        morceaux = []
        if v.get("scolarite_total_eur") is not None:
            morceaux.append(f"{_eur(v['scolarite_total_eur'])} pour l'ensemble de la formation")
        if v.get("fourchette_eur"):
            bas, haut = v["fourchette_eur"]
            morceaux.append(f"de {_eur(bas)} à {_eur(haut)} selon la situation")
        if v.get("scolarite_annuel_eur") is not None:
            morceaux.append(f"soit {_eur(v['scolarite_annuel_eur'])} par an")
        if v.get("gratuit_en_apprentissage"):
            morceaux.append("gratuit en apprentissage")
        if v.get("gratuit_boursiers"):
            morceaux.append("gratuit pour les boursiers")
        texte = v.get("texte_source") or ""
        # Onisep publie un « coût de scolarité » ; s'il ne cite ni droits d'inscription ni CVEC,
        # on ne sait pas s'ils s'y ajoutent, et le texte le dit plutôt que de laisser lire « gratuit ».
        reserve = (
            "" if re.search(r"droit|cvec", texte, re.IGNORECASE)
            else ". Le texte Onisep ne dit pas si des droits d'inscription ou la CVEC s'y ajoutent"
        )
        # Règle « même famille » : Onisep publie ce coût pour toutes les formations de ce type au même
        # lieu, pas nommément pour celle-ci ; le texte le dit.
        famille = (
            ". Ce coût est celui que l'Onisep publie pour toutes les formations de ce type dans cet établissement"
            if champ.get("rattachement") == "onisep_uai_famille" else ""
        )
        return (
            f"Coût de scolarité (Onisep, tarif {v.get('annee_tarif')}) : " + ", ".join(morceaux)
            + f". Texte publié par l'Onisep : « {texte} »" + famille + reserve
        )
    morceaux = []
    droits = v.get("droits_inscription_eur")
    if droits == 0:
        morceaux.append("pas de droits d'inscription dans un BTS public")
    elif droits is not None:
        morceaux.append(f"droits d'inscription {_eur(droits)} par an (taux normal fixé par l'État)")
    if v.get("cvec_eur") is not None:
        morceaux.append(f"contribution vie étudiante et de campus (CVEC) {_eur(v['cvec_eur'])}")
    else:
        morceaux.append("CVEC non disponible")
    return f"Coût (établissement public, année {v.get('annee_tarif')}, {_source_courte(champ)}) : " + " ; ".join(morceaux)


# Au-delà de ce nombre d'établissements, le texte résume au lieu de lister (demande de Jarvis du
# 23/09/2026 : une liste de 27 formations pour un BTS SIO à Paris noyait le reste de la fiche).
MAX_ETABLISSEMENTS_LISTES = 5


def _places(formations: list[dict]) -> str:
    connues = [f["capacite"] for f in formations if f.get("capacite") is not None]
    if not connues:
        return "capacité non publiée"
    total = sum(connues)
    manque = len(formations) - len(connues)
    return f"{total} places" + (f" (capacité non publiée pour {manque})" if manque else "")


def _variante(f: dict) -> str:
    """Ce qui distingue une formation d'une autre du même établissement."""
    if f.get("cfa_partenaire") and f.get("precision"):
        return f"avec {f['cfa_partenaire']}, {f['precision']}"
    if f.get("cfa_partenaire"):
        return f"avec {f['cfa_partenaire']}"
    if f.get("precision"):
        return f["precision"]
    return f"formation Parcoursup n° {f['cod_aff_form']}"


def _etablissement(nom_lieu: str, formations: list[dict]) -> str:
    if len(formations) == 1:
        f = formations[0]
        detail = [x for x in (f.get("cfa_partenaire") and f"avec {f['cfa_partenaire']}", f.get("precision")) if x]
        return f"{nom_lieu} ({', '.join(detail + [_places(formations)])})"
    variantes = [f"{_variante(f)} : {_places([f])}" for f in formations]
    # Deux formations que rien ne distingue dans le jeu ouvert restent deux formations : elles sont
    # nommées par leur numéro Parcoursup, et le texte dit que la différence n'est pas publiée.
    muettes = all(v.startswith("formation Parcoursup n°") for v in variantes)
    reserve = ", le jeu ouvert ne dit pas ce qui les distingue" if muettes else ""
    return f"{nom_lieu} ({len(formations)} formations{reserve}, {_places(formations)} : " + " / ".join(variantes) + ")"


def _alternance(fiche: dict) -> str | None:
    champ = fiche.get("alternance")
    if not isinstance(champ, dict):
        return None
    if champ.get("statut") != "disponible":
        return f"Alternance : non disponible ({champ.get('raison')})"
    formations = champ["valeur"]["formations"]
    entete = f"Alternance (Parcoursup apprentissage, {champ.get('millesime')})"
    if not formations:
        return (
            f"{entete} : aucune formation en apprentissage du même diplôme dans le même établissement "
            "ou la même commune"
        )
    groupes: dict[str, list[dict]] = {}
    for f in formations:
        groupes.setdefault(f"{f.get('etablissement')} à {f.get('ville')}", []).append(f)
    if len(groupes) <= MAX_ETABLISSEMENTS_LISTES:
        return (
            f"{entete} : ce diplôme existe aussi en apprentissage, même établissement ou même commune : "
            + " ; ".join(_etablissement(lieu, fs) for lieu, fs in groupes.items())
        )
    villes = sorted({f.get("ville") for f in formations if f.get("ville")})
    resume = (
        f"{entete} : {len(formations)} formations en apprentissage du même diplôme dans "
        f"{len(groupes)} établissements de la même commune ({', '.join(villes)}), {_places(formations)} au total"
    )
    memes = {lieu: fs for lieu, fs in groupes.items() if any(f.get("rattachee_par") == "uai" for f in fs)}
    if memes:
        resume += " ; dans le même établissement : " + " ; ".join(_etablissement(lieu, fs) for lieu, fs in memes.items())
    return resume


def _ligne_insertion(ligne: dict, dispositif: str) -> str:
    p = ligne["perimetre"]
    ind = ligne["indicateurs"]
    bits = []
    if dispositif == "InserSup":
        for cle, mots in (("taux_emploi_salarie_fr_6m", "6 mois"), ("taux_emploi_salarie_fr_12m", "12 mois"),
                          ("taux_emploi_salarie_fr_18m", "18 mois")):
            t = _taux_fr(ind.get(cle))
            if t:
                bits.append(f"taux d'emploi salarié en France à {mots} {t}")
        if ind.get("salaire_median_net_12m_eur") is not None:
            bits.append(f"salaire net médian à 12 mois {ind['salaire_median_net_12m_eur']} euros par mois")
        if ligne.get("effectif_sortants") is not None:
            bits.append(f"{ligne['effectif_sortants']} diplômés sortis des études")
        return f"{p['diplome']}, {p['etablissement']} (tous sites de l'établissement) : " + ", ".join(bits)
    for cle, mots in (("taux_emploi_6m", "taux d'emploi à 6 mois"), ("taux_emploi_12m", "taux d'emploi à 12 mois"),
                      ("taux_poursuite_etudes", "taux de poursuite d'études")):
        t = _taux_fr(ind.get(cle))
        if t:
            bits.append(f"{mots} {t}")
    return f"{p['diplome']} : " + (", ".join(bits) if bits else "taux non diffusés")


def _insertion(fiche: dict) -> list[str]:
    champ = fiche.get("insertion")
    if not isinstance(champ, dict):
        return []
    if champ.get("statut") != "disponible":
        return [f"Insertion professionnelle : non disponible ({champ.get('raison')})"]
    v = champ["valeur"]
    dispositif = v["dispositif"]
    promo = v["promotion"].replace(",", " et ")
    entete = (
        f"Insertion professionnelle ({dispositif}, promotion {promo}, ensemble des régimes)"
        if dispositif == "InserSup" else f"Insertion professionnelle ({dispositif}, {promo}, voie scolaire)"
    )
    lignes = " ; ".join(_ligne_insertion(ligne, dispositif) for ligne in v["lignes"])
    if dispositif == "InserSup":
        avec_salaire = any(l["indicateurs"].get("salaire_median_net_12m_eur") is not None for l in v["lignes"])
        cles = ("taux_emploi_salarie_fr",) + (("salaire_median",) if avec_salaire else ()) + ("sortants",)
    else:
        cles = ("inserjeunes_taux_emploi", "inserjeunes_poursuite")
    return [f"{entete} : {lignes}", "Définitions (libellés officiels) : " + " ; ".join(DEFINITIONS_INSERTION[k] for k in cles)]


# ── Étape B-2 : accès aux études de santé (contrat, section 10) ─────────────────────────────
# Le chiffre national vient avant celui de l'université, et chaque phrase qui porte un taux dit sa
# portée (« au niveau national », « publié par l'université ») : demande de Jarvis du 23/09/2026.
_FILIERES_MMOPK = (("medecine", "médecine"), ("pharmacie", "pharmacie"), ("odontologie", "odontologie"),
                   ("maieutique", "maïeutique"), ("kinesitherapie", "kinésithérapie"))
_MMOPK = "MMOPK (médecine, maïeutique, odontologie, pharmacie ou kinésithérapie)"


def _sante_national(champ: dict) -> str | None:
    if champ.get("statut") != "disponible":
        return None
    v = champ["valeur"]
    voie = v["voie"]
    filieres = ", ".join(
        f"{mot} {_taux_fr(v['par_filiere_1_ou_2_ans_pct'][cle])}"
        for cle, mot in _FILIERES_MMOPK if v["par_filiere_1_ou_2_ans_pct"].get(cle) is not None
    )
    return (
        f"Accès aux études de santé, chiffre national : au niveau national (SIES, Note Flash n°31 de "
        f"novembre 2025, session {v['session_resultats']}, {v['cohorte']}), "
        f"{_taux_fr(v['admis_mmopk_1_ou_2_ans_pct'])} des néo-bacheliers inscrits en {voie} sont admis en "
        f"{_MMOPK} en 1 ou 2 ans, dont {_taux_fr(v['admis_mmopk_1_an_pct'])} dès la première année ; "
        f"au niveau national, par filière : {filieres} ; ce chiffre national ne décrit pas cette "
        f"université en particulier"
    )


def _sante_universite(champ: dict) -> str | None:
    if champ.get("statut") != "disponible":
        return f"Taux de passage en MMOPK propre à l'université : non disponible ({champ.get('raison')})"
    v = champ["valeur"]
    voie = "PASS et LAS confondus" if v["voie"] == "PASS+LAS" else v["voie"]
    definition = v.get("definition_publiee") or "définition non publiée par l'université"
    return (
        f"Taux de passage en MMOPK publié par l'université : l'{v['universite']} publie pour sa part "
        f"{_taux_fr(v['taux_pct'])} ({voie}, année {v['annee']}, publié par l'université ; {definition})"
        if v["universite"].startswith("Université") else
        f"Taux de passage en MMOPK publié par l'université : {v['universite']} publie pour sa part "
        f"{_taux_fr(v['taux_pct'])} ({voie}, année {v['annee']}, publié par l'université ; {definition})"
    )


def _places_filiere(d: dict) -> str:
    voies = [f"{mot} {d[cle]}" for cle, mot in (("PASS", "PASS"), ("LAS", "LAS"), ("passerelles", "passerelles"),
                                                   ("autres", "autres voies")) if d.get(cle) is not None]
    total = d.get("total")
    if total is not None:
        return f"{total}" + (f" (dont {', '.join(voies)})" if voies else "")
    return ", ".join(voies)


def _sante_capacites(champ: dict, voie_fiche: str) -> str:
    if champ.get("statut") != "disponible":
        return f"Places en MMOPK de l'université : non disponible ({champ.get('raison')})"
    v = champ["valeur"]
    filieres = [
        f"{mot} {_places_filiere(d)}" + (f" (rentrée {d['rentree']})" if d.get("rentree") and d["rentree"] != v["rentree"] else "")
        for cle, mot in _FILIERES_MMOPK if (d := v["par_filiere"].get(cle))
    ]
    phrase = (
        f"Places en MMOPK, {v['universite']}, rentrée {v['rentree']} (publiées par l'université) : "
        + " ; ".join(filieres)
        + (f" ; total {v['total']} places" if v.get("total") is not None else "")
    )
    if voie_fiche == "LAS" and "LAS" in v.get("voies_publiees", []):
        phrase += " ; les places LAS sont ouvertes aux étudiants de LAS de l'université, toutes mentions confondues"
    if v.get("note"):
        phrase += f" ; précision : {v['note']}"
    return phrase


def _sante_reforme(champ: dict) -> str | None:
    if champ.get("statut") != "disponible":
        return None
    j = champ["valeur"]["verifie_le"].split("-")
    return (
        "Réforme : une voie unique remplaçant PASS et LAS a été annoncée par le gouvernement le 17/04/2026 "
        "pour la rentrée 2027 ; aucun décret ni arrêté publié au Journal officiel à la date du "
        f"{j[2]}/{j[1]}/{j[0]} (voir la fiche « Réforme de l'accès aux études de santé »)"
    )


def _sante(fiche: dict) -> list[str]:
    champ = fiche.get("sante")
    if not isinstance(champ, dict):
        return []
    voie = "PASS" if fiche.get("fili_code") == "PASS" else "LAS"
    sortie = [
        _sante_national(champ.get("passage_national") or {}),
        _sante_universite(champ.get("passage_universite") or {}),
        _sante_capacites(champ.get("capacites_universite") or {}, voie),
        _sante_reforme(champ.get("reforme_2027") or {}),
    ]
    return [x for x in sortie if x]


def blocs_complements(fiche: dict) -> list[str]:
    """Coût, alternance et insertion d'une fiche (étape B-1), puis accès santé (étape B-2)."""
    sortie = [x for x in (_cout(fiche), _alternance(fiche)) if x]
    sortie.extend(_insertion(fiche))
    sortie.extend(_sante(fiche))
    return sortie


# Libellés officiels du jeu fr-esr-parcoursup-apprentissage (API, métadonnées lues le 23/09/2026).
DEFINITIONS_APPRENTISSAGE = {
    "capacite": "capacité : capacité de l'établissement par formation",
    "candidats": "candidats : effectif total des candidats pour la formation",
    "propositions": (
        "propositions : effectif total des candidats ayant reçu une proposition d'admission de la "
        "part de l'établissement"
    ),
    "recherche_contrat": "vœux en recherche de contrat : nombre de vœux placés en « Recherche de contrat » par la formation",
}


def blocs_apprentissage(fiche: dict) -> list[str]:
    """Chiffres d'une formation en apprentissage : pas de taux d'accès (non publié)."""
    a = fiche.get("apprentissage") or {}
    morceaux, definis = [], []
    for cle, gabarit, definition in (
        ("capacite", "{} places", "capacite"), ("candidats", "{} candidats", "candidats"),
        ("propositions", "{} propositions d'admission", "propositions"),
        ("voeux_recherche_contrat", "{} vœux en recherche de contrat", "recherche_contrat"),
    ):
        n = _nombre(a.get(cle))
        if n is not None:
            morceaux.append(gabarit.format(n))
            definis.append(definition)
    sortie = ["Voie : apprentissage (formation en alternance, inscrite sur Parcoursup apprentissage)"]
    if morceaux:
        sortie.append(f"Admission (Parcoursup apprentissage, session {a.get('session', SESSION)}) : " + " ; ".join(morceaux))
        sortie.append("Définitions (libellés officiels Parcoursup apprentissage) : " + " ; ".join(DEFINITIONS_APPRENTISSAGE[k] for k in definis))
    sortie.append("Taux d'accès : non publié pour les formations en apprentissage")
    return sortie


SOURCE_APPRENTISSAGE = (
    f"Parcoursup apprentissage, session {SESSION} : jeu open data fr-esr-parcoursup-apprentissage "
    "du ministère de l'Enseignement supérieur (SIES)"
)
