"""Capacités MMOPK et taux de passage publiés par les 10 universités du panel (étape B-2).

Chaque nombre est recopié à la main du document de l'université (page ou PDF), téléchargé dans
`data/raw/sante/` et verrouillé (`src.collect.sources_officielles`, clés `univ_*`). `extraits`
reprend les lignes du document qui portent les nombres, telles que `pdftotext -layout` les rend
(espaces réduits) ; `src.eval.donnee.audit_sante` les y cherche.

Deux documents n'ont pas de couche texte exploitable : Nantes (scan, aucune couche texte) et
Lyon 1 MMOP (couche texte corrompue : « 202 -202 », « 27 8 16 2 5 0 » là où l'image porte
« 2026-2027 » et « 275 82 165 28 550 »). Leurs extraits sont transcrits de l'image, relue par
Claudette le 23/09/2026 ; `LECTURE_VISUELLE` les signale à l'audit, qui les rend NON MESURÉ au
lieu de les compter verts.

Clés de `par_filiere.<filière>` : `total`, `PASS`, `LAS`, `passerelles`, `autres` (valeurs telles
que publiées ; une clé absente = non publiée), `detail` (ventilation publiée, libellés du
document), `somme_de` (quand `LAS` ou `total` est une somme de lignes publiées, les lignes
additionnées, chemin dans `detail` séparé par « > »), `rentree` et `source_id` quand la filière vient d'un autre document que le reste.
"""
from __future__ import annotations

from src.collect.sante import Capacites, PassageUniversite, Recherche  # noqa: F401

LUE_LE = "2026-09-23"

# Sources dont les extraits ne peuvent pas être cherchés dans une couche texte (voir en-tête).
LECTURE_VISUELLE = {"univ_nantes_mmopk_2026_2027", "univ_lyon1_mmop_2026_2027"}

RECHERCHES: dict[str, Recherche] = {}


def _ajouter(r: Recherche) -> None:
    RECHERCHES[r.universite] = r


# ── Université de Bordeaux ────────────────────────────────────────────────────────────────
# PDF daté du 25/11/2025. Couvre Bordeaux et Pau (« Université de Bordeaux et PAU ») ; les
# sections « Pacifique sud » et « Accueil sur conventions » (places réservées à d'autres
# universités) ne sont pas reprises. La kinésithérapie est dans un autre document, dont le plus
# récent publié porte sur 2025/2026.
_ajouter(Recherche(
    universite="Université de Bordeaux",
    urls=(
        "https://sante.u-bordeaux.fr/scolarite-demarches-administratives/candidater/pass-las-modalites-dacces-mmopk",
        "https://sante.u-bordeaux.fr/formations/pass-l/pass",
        "https://www.u-bordeaux.fr/formation/accompagnement-et-reussite-des-etudes/enquetes-et-statistiques",
    ),
    date=LUE_LE,
    constat="capacités publiées (PDF 2026/27, kinésithérapie 2025/2026) ; aucun taux de passage MMOPK publié sur ces pages",
    capacites=Capacites(
        universite="Université de Bordeaux",
        source_id="univ_bordeaux_mmop_2026_2027",
        rentree="2026/27",
        total=None,
        par_filiere={
            "medecine": {"total": 425, "PASS": 195, "LAS": 195, "passerelles": 30, "autres": 5,
                         "detail": {"LAS 60 ECTS Université de Bordeaux et PAU": 15,
                                    "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU": 180,
                                    "Passerelles tardives": 30, "Candidats internationaux": 5},
                         "somme_de": {"LAS": ["LAS 60 ECTS Université de Bordeaux et PAU",
                                              "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU"]}},
            "pharmacie": {"total": 165, "PASS": 70, "LAS": 70, "passerelles": 20, "autres": 5,
                          "detail": {"LAS 60 ECTS Université de Bordeaux et PAU": 8,
                                     "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU": 62,
                                     "Passerelles tardives": 20, "Candidats internationaux": 5},
                          "somme_de": {"LAS": ["LAS 60 ECTS Université de Bordeaux et PAU",
                                               "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU"]}},
            "odontologie": {"total": 82, "PASS": 35, "LAS": 36, "passerelles": 9, "autres": 2,
                            "detail": {"LAS 60 ECTS Université de Bordeaux et PAU": 4,
                                       "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU": 32,
                                       "Passerelles tardives": 9, "Candidats internationaux": 2},
                            "somme_de": {"LAS": ["LAS 60 ECTS Université de Bordeaux et PAU",
                                                 "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU"]}},
            "maieutique": {"total": 31, "PASS": 12, "LAS": 13, "passerelles": 5, "autres": 1,
                           "detail": {"LAS 60 ECTS Université de Bordeaux et PAU": 4,
                                      "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU": 9,
                                      "Passerelles tardives": 5, "Candidats internationaux": 1},
                           "somme_de": {"LAS": ["LAS 60 ECTS Université de Bordeaux et PAU",
                                                "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU"]}},
            "kinesitherapie": {"total": 110, "PASS": 54, "LAS": 54, "autres": 2,
                               "detail": {"PASS / Université de Bordeaux et partenaires": 54,
                                          "LAS-licences / Université de Bordeaux et partenaires": 54,
                                          "Université de la Nouvelle-Calédonie": 2,
                                          "Sportifs de haut niveau (hors quota)": 2},
                               "rentree": "2025/2026", "source_id": "univ_bordeaux_kine_2025_2026"},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "BORDEAUX rentrée universitaire 2026/27 : capacité d'accueil en vue d'admission en 2e ou 3e année de médecine, maïeutique,",
            "Médecine 425", "PASS 195", "LAS 60 ECTS Université de Bordeaux et PAU 15",
            "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU 180", "Passerelles tardives 30",
            "Candidats internationaux 5",
            "Pharmacie 165", "PASS 70", "LAS 60 ECTS Université de Bordeaux et PAU 8",
            "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU 62", "Passerelles tardives 20",
            "Odontologie 82", "PASS 35", "LAS 60 ECTS Université de Bordeaux et PAU 4",
            "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU 32", "Passerelles tardives 9",
            "Candidats internationaux 2",
            "Maïeutique 31", "PASS 12", "LAS 120 ECTS et Licences 2 et 3 Université de Bordeaux et PAU 9",
            "Passerelles tardives 5", "Candidats internationaux 1",
        ),
        note="places du site Bordeaux et Pau ; kinésithérapie : rentrée 2025/2026, dernier document publié "
             "(« QUOTA 110 étudiants ») ; hors places réservées au Pacifique sud et aux universités sous convention",
    ),
))
EXTRAITS_AUTRES_SOURCES = {
    "univ_bordeaux_kine_2025_2026": (
        "BORDEAUX année universitaire 2025/2026 : capacité d'accueil en",
        "QUOTA 110 étudiants", "PASS / Université de Bordeaux et partenaires 54",
        "LAS-licences / Université de Bordeaux et partenaires 54", "Université de la Nouvelle-Calédonie 2",
        "Sportifs de haut niveau 2",
    ),
    "univ_lyon1_kine_2026_2027": (
        "Groupe de parcours 1 : 37 places", "Groupe de parcours 2 : 17 places", "Groupe de parcours 3 : 21 places",
        "masseur-kinésithérapeute, dans la limite des places disponibles, pour l'année 2026-2027, les",
        "Groupe de parcours 2 : Etudiants issus de LAS 1 (UCBL, Université Lyon 3, Institut Catholique de",
    ),
}

# ── Nantes Université ─────────────────────────────────────────────────────────────────────
# Délibération n°CAC_250919-05 du Conseil académique (19/09/2025), PDF scanné (lecture visuelle).
_ajouter(Recherche(
    universite="Nantes Université",
    urls=(
        "https://medecine.univ-nantes.fr/formation-initiale/presentation-generale/parcours-dacces-specifique-sante-pass",
        "https://www.univ-nantes.fr/universite/vision-strategie-et-grands-projets/observatoire-de-la-reussite-universitaire",
    ),
    date=LUE_LE,
    constat="capacités publiées (délibération 2026-2027, 5 filières) ; aucun taux de passage MMOPK publié sur ces pages "
            "(l'observatoire de la réussite couvre la licence générale)",
    capacites=Capacites(
        universite="Nantes Université",
        source_id="univ_nantes_mmopk_2026_2027",
        rentree="2026-2027",
        total=604,
        par_filiere={
            "medecine": {"total": 263, "PASS": 110, "LAS": 139, "passerelles": 14,
                         "detail": {"LAS 1": 60, "LAS 2 et 3": 79, "Total": 249, "Passerelles": 14, "Total général": 263},
                         "somme_de": {"LAS": ["LAS 1", "LAS 2 et 3"]}},
            "pharmacie": {"total": 130, "PASS": 54, "LAS": 68, "passerelles": 7, "autres": 1,
                          "detail": {"LAS 1": 29, "LAS 2 et 3": 39, "Universités extérieures": 1, "Total": 123,
                                     "Passerelles": 7, "Total général": 130},
                          "somme_de": {"LAS": ["LAS 1", "LAS 2 et 3"]}},
            "odontologie": {"total": 89, "PASS": 19, "LAS": 25, "passerelles": 4, "autres": 41,
                            "detail": {"LAS 1": 10, "LAS 2 et 3": 15, "Universités extérieures": 41, "Total": 85,
                                       "Passerelles": 4, "Total général": 89},
                            "somme_de": {"LAS": ["LAS 1", "LAS 2 et 3"]}},
            "maieutique": {"total": 30, "PASS": 12, "LAS": 16, "passerelles": 2,
                           "detail": {"LAS 1": 6, "LAS 2 et 3": 10, "Total": 28, "Passerelles": 2, "Total général": 30},
                           "somme_de": {"LAS": ["LAS 1", "LAS 2 et 3"]}},
            "kinesitherapie": {"total": 92, "PASS": 25, "LAS": 67,
                               "detail": {"LAS 1": 39, "LAS 2 et 3": 28, "Total": 92, "Total général": 92},
                               "somme_de": {"LAS": ["LAS 1", "LAS 2 et 3"]}},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "Capacités d'accueil 2026-2027 pour MMOP-K 1er cycle (2ème et 3ème année)",
            "Médecine 110 60 79 249 14 263",
            "Pharmacie 54 29 39 1 123 7 130",
            "Odontologie 19 10 15 41 85 4 89",
            "Maïeutique 12 6 10 28 2 30",
            "Kinésithérapie 25 39 28 92 92",
            "Total 220 144 171 42 577 27 604",
        ),
        note="« Universités extérieures » : places réservées aux étudiants d'universités conventionnées",
    ),
))

# ── Université de Lille ───────────────────────────────────────────────────────────────────
# PDF « Capacités d'accueil en 2ème année ... pour la rentrée universitaire 2026 », signé le
# 1er octobre 2024 par la présidente du jury (seule version 2026 trouvée en ligne le 23/09/2026).
_ajouter(Recherche(
    universite="Université de Lille",
    urls=(
        "https://ufr3s.univ-lille.fr/formation-initiale/pass",
        "https://ufr3s.univ-lille.fr/formation-initiale/las-mineure-sante",
        "https://pass.univ-lille.fr",
    ),
    date=LUE_LE,
    constat="capacités publiées (rentrée 2026) ; aucun taux de passage MMOPK publié sur ces pages",
    capacites=Capacites(
        universite="Université de Lille",
        source_id="univ_lille_mmopk_2026",
        rentree="2026",
        total=None,
        par_filiere={
            "medecine": {"total": 560, "PASS": 276, "LAS": 244, "passerelles": 34, "autres": 6,
                         "detail": {"L-AS 1": 69, "L-AS 2/3": 175, "Candidats intra UE": 0, "Candidats hors UE": 6},
                         "somme_de": {"LAS": ["L-AS 1", "L-AS 2/3"], "autres": ["Candidats intra UE", "Candidats hors UE"]}},
            "maieutique": {"total": 53, "PASS": 25, "LAS": 22, "passerelles": 4, "autres": 2,
                           "detail": {"L-AS 1": 6, "L-AS 2/3": 16, "Candidats intra UE": 1, "Candidats hors UE": 1},
                           "somme_de": {"LAS": ["L-AS 1", "L-AS 2/3"], "autres": ["Candidats intra UE", "Candidats hors UE"]}},
            "odontologie": {"total": 90, "PASS": 44, "LAS": 39, "passerelles": 6, "autres": 1,
                            "detail": {"L-AS 1": 11, "L-AS 2/3": 28, "Candidats intra UE": 0, "Candidats hors UE": 1},
                            "somme_de": {"LAS": ["L-AS 1", "L-AS 2/3"], "autres": ["Candidats intra UE", "Candidats hors UE"]}},
            "pharmacie": {"total": 220, "PASS": 108, "LAS": 96, "passerelles": 11, "autres": 5,
                          "detail": {"L-AS 1": 30, "L-AS 2/3": 66, "Candidats intra UE": 3, "Candidats hors UE": 2},
                          "somme_de": {"LAS": ["L-AS 1", "L-AS 2/3"], "autres": ["Candidats intra UE", "Candidats hors UE"]}},
            "kinesitherapie": {"total": 230, "PASS": 62, "LAS": 168,
                               "detail": {"L-AS 1": 99, "L-AS 2/3": 69},
                               "somme_de": {"LAS": ["L-AS 1", "L-AS 2/3"]}},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "Capacités d'accueil en 2ème année des études de Médecine, Maïeutique, Odontologie, Pharmacie et",
            "Masso-Kinésithérapie à l'Université de Lille pour la rentrée universitaire 2026",
            "MEDECINE MAIEUTIQUE ODONTOLOGIE PHARMACIE KINE",
            "TOTAL dont : 560 53 90 220 230",
            "Passerelles 34 4 6 11 -",
            "Candidats intra UE 0 1 0 3 -",
            "Candidats hors UE 6 1 1 2 -",
            "PASS 276 25 44 108 62",
            "L-AS 1 69 6 11 30 99",
            "L-AS 2/3 175 16 28 66 69",
            "Lille, le 1er octobre 2024,",
        ),
    ),
))

# ── Université Claude Bernard Lyon 1 ──────────────────────────────────────────────────────
# Délibération du CA (23/09/2025), 2026-2027 ; lecture visuelle (couche texte corrompue). Les
# lignes « par convention de partenariat » (places réservées aux étudiants de Saint-Étienne et de
# Grenoble) ne sont pas des places de Lyon 1 : non reprises. Médecine = somme des deux facultés.
_ajouter(Recherche(
    universite="Université Claude Bernard Lyon 1",
    urls=(
        "https://lyon-est.univ-lyon1.fr/formation/medecine/pass",
        "https://lyon-sud.univ-lyon1.fr/formation/medecine/pass-las",
    ),
    date=LUE_LE,
    constat="capacités publiées (délibérations 2026-2027 MMOP et kinésithérapie) ; aucun taux de passage MMOPK publié "
            "par la faculté sur ces pages (sites de tutorat étudiant non retenus comme source de l'université)",
    capacites=Capacites(
        universite="Université Claude Bernard Lyon 1",
        source_id="univ_lyon1_mmop_2026_2027",
        rentree="2026-2027",
        total=None,
        par_filiere={
            "medecine": {"total": 950, "PASS": 475, "LAS": 427, "passerelles": 48,
                         "detail": {"Faculté de médecine Lyon Est": {"PASS": 275, "LAS1": 82, "LAS2/LAS3": 165,
                                                                     "Admission directe (passerelle)": 28, "Capacités d'accueil totales": 550},
                                    "Faculté de médecine Lyon Sud": {"PASS": 200, "LAS1": 60, "LAS2/LAS3": 120,
                                                                     "Admission directe (passerelle)": 20, "Capacités d'accueil totales": 400}},
                         "somme_de": {"total": ["Faculté de médecine Lyon Est > Capacités d'accueil totales", "Faculté de médecine Lyon Sud > Capacités d'accueil totales"],
                                      "PASS": ["Faculté de médecine Lyon Est > PASS", "Faculté de médecine Lyon Sud > PASS"],
                                      "LAS": ["Faculté de médecine Lyon Est > LAS1", "Faculté de médecine Lyon Est > LAS2/LAS3", "Faculté de médecine Lyon Sud > LAS1", "Faculté de médecine Lyon Sud > LAS2/LAS3"],
                                      "passerelles": ["Faculté de médecine Lyon Est > Admission directe (passerelle)", "Faculté de médecine Lyon Sud > Admission directe (passerelle)"]}},
            "maieutique": {"total": 50, "PASS": 25, "LAS": 20, "passerelles": 5,
                           "detail": {"LAS1": 5, "LAS2/LAS3": 15}, "somme_de": {"LAS": ["LAS1", "LAS2/LAS3"]}},
            "odontologie": {"total": 62, "PASS": 31, "LAS": 26, "passerelles": 5,
                            "detail": {"LAS1": 7, "LAS2/LAS3": 19}, "somme_de": {"LAS": ["LAS1", "LAS2/LAS3"]}},
            "pharmacie": {"total": 203, "PASS": 96, "LAS": 88, "passerelles": 19,
                          "detail": {"LAS1": 28, "LAS2/LAS3": 60}, "somme_de": {"LAS": ["LAS1", "LAS2/LAS3"]}},
            "kinesitherapie": {"total": 75, "PASS": 37, "LAS": 38,
                               "detail": {"Groupe de parcours 1 (PASS Lyon-Sud et Lyon-Est)": 37,
                                          "Groupe de parcours 2 (LAS 1 UCBL, Lyon 3, Institut Catholique de Lyon)": 17,
                                          "Groupe de parcours 3 (LAS 2 et LAS 3 UCBL, Lyon 2, Lyon 3, Institut Catholique de Lyon)": 21},
                               "somme_de": {"total": ["Groupe de parcours 1 (PASS Lyon-Sud et Lyon-Est)", "Groupe de parcours 2 (LAS 1 UCBL, Lyon 3, Institut Catholique de Lyon)", "Groupe de parcours 3 (LAS 2 et LAS 3 UCBL, Lyon 2, Lyon 3, Institut Catholique de Lyon)"],
                                            "LAS": ["Groupe de parcours 2 (LAS 1 UCBL, Lyon 3, Institut Catholique de Lyon)", "Groupe de parcours 3 (LAS 2 et LAS 3 UCBL, Lyon 2, Lyon 3, Institut Catholique de Lyon)"]},
                               "rentree": "2026-2027", "source_id": "univ_lyon1_kine_2026_2027"},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "pharmacie, d'odontologie, et de maïeutique pour l'année universitaire 2026-2027.",
            "Faculté de médecine Lyon Est 275 82 165 28 550",
            "Faculté de médecine Lyon Sud 200 60 120 20 400",
            "Maïeutique UCBL - Lyon 1 25 5 15 5 50",
            "Odontologie UCBL - Lyon 1 31 7 19 5 62",
            "Pharmacie UCBL - Lyon 1 96 28 60 19 203",
            "Fait à Villeurbanne, le 23 septembre 2025",
        ),
        note="médecine : Lyon Est 550 et Lyon Sud 400 ; kinésithérapie : les groupes LAS comprennent aussi des "
             "étudiants de Lyon 2, Lyon 3 et de l'Institut Catholique de Lyon, et une place parmi les 75 va à un "
             "sportif de haut niveau ; hors places réservées par convention aux universités de Saint-Étienne et Grenoble",
    ),
))

# ── Université de Montpellier ─────────────────────────────────────────────────────────────
# PDF « Répartition des capacités d'accueil par filière MMOP », colonne « Places ouvertes en DFGS2
# en 2026-2027 ». Colonnes attribuées sur l'image (la couche texte perd l'en-tête) : PASS UM, LAS1,
# LAS 2 et LAS 3, DE auxiliaire médical, Passerelles, Étudiants ayant validé le 1er cycle (EUE ou
# transfert), puis, datées 2025-2026 dans l'en-tête : Candidature hors UE, Places extérieures,
# Total des places. Seule la colonne 2026-2027 et sa ventilation sont reprises. Pas de
# kinésithérapie dans ce document. La page de 2021 de la faculté (« minimum pass rate 5.8% ») est
# un minimum théorique (places / inscrits PASS) pour 2021-22, pas un taux de passage constaté.
_ajouter(Recherche(
    universite="Université de Montpellier",
    urls=(
        "https://facmedecine.umontpellier.fr/en/2021/vie-etudiante/pass-las-le-point-sur-les-places-offertes-en-medecine-pour-2021-22/",
        "https://www.umontpellier.fr/wp-content/uploads/2025/12/Livret-PASS-LAS-2026-2027.pdf",
    ),
    date=LUE_LE,
    constat="capacités publiées (DFGS2 2026-2027, sans kinésithérapie) ; aucun taux de passage constaté publié : le seul "
            "chiffre trouvé (5,8 %, 2021-22) est un minimum théorique, écarté",
    capacites=Capacites(
        universite="Université de Montpellier",
        source_id="univ_montpellier_mmop_2026_2027",
        rentree="2026-2027",
        total=None,
        par_filiere={
            "medecine": {"total": 393, "PASS": 196, "LAS": 172, "passerelles": 25, "autres": 0,
                         "detail": {"LAS1": 44, "LAS 2 et LAS 3": 128, "DE auxiliaire médical": 0,
                                    "Etudiants ayant validé le 1er cycle": 0,
                                    "site Montpellier": {"total": 245, "PASS": 131, "LAS1": 29, "LAS 2 et LAS 3": 85},
                                    "site Nîmes": {"total": 123, "PASS": 65, "LAS1": 15, "LAS 2 et LAS 3": 43}},
                         "somme_de": {"LAS": ["LAS1", "LAS 2 et LAS 3"],
                                      "autres": ["DE auxiliaire médical", "Etudiants ayant validé le 1er cycle"]}},
            "maieutique": {"total": 71, "PASS": 35, "LAS": 30, "passerelles": 6, "autres": 0,
                           "detail": {"LAS1": 7, "LAS 2 et LAS 3": 23, "DE auxiliaire médical": 0,
                                      "Etudiants ayant validé le 1er cycle": 0,
                                      "site Montpellier": {"total": 33, "PASS": 18, "LAS1": 3, "LAS 2 et LAS 3": 9, "Passerelles": 3},
                                      "site Nîmes": {"total": 38, "PASS": 17, "LAS1": 4, "LAS 2 et LAS 3": 14, "Passerelles": 3}},
                           "somme_de": {"LAS": ["LAS1", "LAS 2 et LAS 3"],
                                        "autres": ["DE auxiliaire médical", "Etudiants ayant validé le 1er cycle"]}},
            "odontologie": {"total": 63, "PASS": 29, "LAS": 28, "passerelles": 6, "autres": 0,
                            "detail": {"LAS1": 9, "LAS 2 et LAS 3": 19, "DE auxiliaire médical": 0,
                                       "Etudiants ayant validé le 1er cycle": 0},
                            "somme_de": {"LAS": ["LAS1", "LAS 2 et LAS 3"],
                                         "autres": ["DE auxiliaire médical", "Etudiants ayant validé le 1er cycle"]}},
            "pharmacie": {"total": 221, "PASS": 108, "LAS": 99, "passerelles": 13, "autres": 1,
                          "detail": {"LAS1": 32, "LAS 2 et LAS 3": 67, "DE auxiliaire médical": 0,
                                     "Etudiants ayant validé le 1er cycle": 1},
                          "somme_de": {"LAS": ["LAS1", "LAS 2 et LAS 3"],
                                       "autres": ["DE auxiliaire médical", "Etudiants ayant validé le 1er cycle"]}},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "Répartition des capacités d'accueil par filière MMOP",
            "DFGS2 en 2026-2027",
            "Médecine 393 196 44 128 0 25 0 7 0 0 0 400",
            "site Montpellier 245 131 29 85",
            "site Nîmes 123 65 15 43",
            "Maïeutique 71 35 7 23 0 6 0 1 2 0 1 75",
            "site Montpellier 33 18 3 9 3 1",
            "site Nîmes 38 17 4 14 3",
            "Odontologie 63 29 9 19 0 6 0 2 8 0 0 73",
            "Pharmacie 221 108 32 67 0 13 1 1 1 1 1 225",
        ),
        note="places ouvertes en DFGS2 en 2026-2027 ; les places LAS comprennent les LAS des universités partenaires "
             "(Montpellier 3, Perpignan, Nîmes, Mayotte) ; kinésithérapie non publiée dans ce document",
    ),
))

# ── Université Paris Cité ─────────────────────────────────────────────────────────────────
# Diaporama officiel « Accès Santé PASS/L.AS » de la Faculté de Santé, journée portes ouvertes du
# 7 février 2026 (u-paris.fr), diapositives « Accès aux filières de santé - capacités et
# répartition, pour la rentrée universitaire en filière en 2026-2027 ». Le tableau ne publie pas
# de places de passerelle. Les 23 places de maïeutique « réservées pour UVSQ » figurent dans un
# encadré séparé : rien ne dit si elles sont comprises dans les 46 ; elles ne sont pas reprises.
# La fiche du catalogue (« environ 50% des étudiants admis en filière de santé provenaient du
# PASS ») est une répartition des admis par origine, pas un taux de passage : écartée.
_ajouter(Recherche(
    universite="Université Paris Cité",
    urls=(
        "https://u-paris.fr/sante/pass-parcours-dacces-specifique-sante/",
        "https://u-paris.fr/sante/rentree-2026-2027/",
        "https://odf.u-paris.fr/fr/offre-de-formation/parcours-specifique-et-licence-acces-sante-pass-las-PASS/sciences-technologies-sante-STS/parcours-d-acces-specifique-sante-pass-K5P2ML11.html",
    ),
    date=LUE_LE,
    constat="capacités publiées (diaporama officiel du 07/02/2026, rentrée 2026-2027) ; aucun taux de passage MMOPK publié "
            "(seule une répartition des admis par origine, écartée)",
    capacites=Capacites(
        universite="Université Paris Cité",
        source_id="univ_paris_cite_jpo_2026",
        rentree="2026-2027",
        total=None,
        par_filiere={
            "medecine": {"total": 702, "PASS": 375, "LAS": 327,
                         "detail": {"L.AS 1": 64, "L.AS 2/3, Master": 263}, "somme_de": {"LAS": ["L.AS 1", "L.AS 2/3, Master"]}},
            "pharmacie": {"total": 234, "PASS": 125, "LAS": 109,
                          "detail": {"L.AS 1": 21, "L.AS 2/3, Master": 88}, "somme_de": {"LAS": ["L.AS 1", "L.AS 2/3, Master"]}},
            "odontologie": {"total": 74, "PASS": 37, "LAS": 37,
                            "detail": {"L.AS 1": 10, "L.AS 2/3, Master": 27}, "somme_de": {"LAS": ["L.AS 1", "L.AS 2/3, Master"]}},
            "maieutique": {"total": 46, "PASS": 26, "LAS": 20,
                           "detail": {"L.AS 1": 3, "L.AS 2/3, Master": 17}, "somme_de": {"LAS": ["L.AS 1", "L.AS 2/3, Master"]}},
            "kinesitherapie": {"total": 61, "PASS": 37, "LAS": 24,
                               "detail": {"EFOM (privé)": {"PASS": 8, "L.A.S": 4}, "EKP (ADERF) (privé)": {"PASS": 8, "L.A.S": 8},
                                          "ASSAS (privé)": {"PASS": 4, "L.A.S": 7}, "ENKRE (public)": {"PASS": 12, "L.A.S": 4},
                                          "APHP (public)": {"PASS": 5, "L.A.S": 1}},
                               "somme_de": {"total": ["PASS", "LAS"]}},
        },
        voies_publiees=("PASS", "LAS"),
        extraits=(
            "Pour la rentrée universitaire en filière en 2026-2027",
            "Médecine Pharmacie Odontologie Maïeutique Total",
            "PASS 375 125 37 26 563",
            "L.AS 1 64 21 10 3 98",
            "L.AS 2/3, Master 263 88 27 17 395",
            "Total 702 234 74 46 1056",
            "Capacités d'accueil en filière Kinésithérapie",
            "EFOM privé 8 4", "EKP (ADERF) privé 8 8", "ASSAS privé 4 7", "ENKRE public 12 4", "APHP public 5 1",
            "TOTAL 37 24",
        ),
        note="source : diaporama de la journée portes ouvertes de la Faculté de Santé (07/02/2026) ; le tableau ne publie "
             "pas de places de passerelle ; kinésithérapie : places dans 5 instituts partenaires (IFMK) ; hors 23 places de "
             "maïeutique réservées à l'UVSQ",
    ),
))

# ── Université Sorbonne Paris Nord ────────────────────────────────────────────────────────
# PDF de l'UFR SMBH « Capacités d'accueil en 2e année ... pour l'année 2026-2027 ». Places pour
# les étudiants de l'USPN et de ses universités partenaires (CY Cergy Paris Université, Paris 8).
_ajouter(Recherche(
    universite="Université Sorbonne Paris Nord",
    urls=(
        "https://smbh.univ-paris13.fr/fr/formations-accueil.html",
        "https://odf.univ-spn.fr",
    ),
    date=LUE_LE,
    constat="capacités publiées (2026-2027, sans kinésithérapie) ; aucun taux de passage MMOPK publié sur ces pages",
    capacites=Capacites(
        universite="Université Sorbonne Paris Nord",
        source_id="univ_spn_mmop_2026_2027",
        rentree="2026-2027",
        total=None,
        par_filiere={
            "medecine": {"total": 215, "PASS": 66, "LAS": 134, "passerelles": 11, "autres": 4,
                         "detail": {"LAS 1": 69, "LAS 2-3": 65, "Passerelles (y compris auxiliaires médicaux)": 11,
                                    "Médecins hors-UE": 4},
                         "somme_de": {"LAS": ["LAS 1", "LAS 2-3"]}},
            "maieutique": {"total": 14, "PASS": 4, "LAS": 10,
                           "detail": {"LAS 1": 6, "LAS 2-3": 4}, "somme_de": {"LAS": ["LAS 1", "LAS 2-3"]}},
            "pharmacie": {"total": 58, "PASS": 28, "LAS": 30,
                          "detail": {"LAS 1": 10, "LAS 2-3": 20}, "somme_de": {"LAS": ["LAS 1", "LAS 2-3"]}},
            "odontologie": {"total": 15, "PASS": 7, "LAS": 8,
                            "detail": {"LAS 1": 3, "LAS 2-3": 5}, "somme_de": {"LAS": ["LAS 1", "LAS 2-3"]}},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "maïeutique et odontologie pour l'année 2026-2027",
            "Nord et de ses universités partenaires (Cergy Université et Université Paris 8) :",
            "PASS 66 4 28 7", "LAS 1 69 6 10 3", "LAS 2-3 65 4 20 5", "Passerelles (y 11 * * *",
            "Médecins 4 * * *", "Total 215 14 58 15",
            "*passerelle gérée par l'université réceptrice.",
        ),
        note="places ouvertes aux étudiants de l'USPN et de ses universités partenaires (CY Cergy Paris Université, "
             "Paris 8) ; passerelles de maïeutique, pharmacie et odontologie gérées par l'université réceptrice ; "
             "kinésithérapie non publiée dans ce document",
    ),
))

# ── Université Paris-Saclay ───────────────────────────────────────────────────────────────
# Aucune capacité MMOPK chiffrée trouvée sur les domaines de l'université le 23/09/2026. Le
# document de procédure d'accès direct (session 2026, mis à jour le 05/01/2026) annonce que « le
# nombre de place seront communiqué sur le site de la faculté de Médecine Paris-Saclay
# ultérieurement ». Les chiffres qui circulent viennent de sites de prépa sans lien vers un
# document de l'université : non repris.
_ajouter(Recherche(
    universite="Université Paris-Saclay",
    urls=(
        "https://www.medecine.universite-paris-saclay.fr/sites/default/files/2026-01/deroulement_de_la_procedure_dacces_direct-1.pdf",
        "https://www.sciences.universite-paris-saclay.fr/admission/candidater-en-pass",
        "https://www.universite-paris-saclay.fr/admission/lyceens-entrer-luniversite/lecole-universitaire-de-premier-cycle-paris-saclay",
        "https://www.universite-paris-saclay.fr/luniversite/textes-statutaires-et-actes-reglementaires/actes-administratifs/deliberations-des-instances",
    ),
    date=LUE_LE,
    constat="aucune capacité MMOPK ni aucun taux de passage publiés sur les pages consultées de l'université ; la page des "
            "délibérations des instances refuse la lecture automatique (HTTP 403)",
))

# ── Aix-Marseille Université ──────────────────────────────────────────────────────────────
# Le document le plus récent trouvé sur les pages de l'université est la délibération pour la
# rentrée 2024 (avis CFVU du 14/09/2023, CA du 19/09/2023) ; le site des délibérations indique
# ne plus être mis à jour, et les M3C 2025-2026 renvoient aux capacités « fixées par l'université »
# sans les chiffrer. Pas de kinésithérapie dans ce document.
_ajouter(Recherche(
    universite="Aix-Marseille Université",
    urls=(
        "https://daji.univ-amu.fr/sites/daji.univ-amu.fr/files/ca_deliberations/ca2023_09_18_05_capacites_daccueil_0.pdf",
        "https://smpm.univ-amu.fr",
        "https://www.univ-amu.fr/fr/public/observatoire-de-la-vie-etudiante",
    ),
    date=LUE_LE,
    constat="capacités publiées, dernière rentrée trouvée : 2024 ; aucun taux de passage MMOPK publié sur ces pages",
    capacites=Capacites(
        universite="Aix-Marseille Université",
        source_id="univ_amu_mmop_rentree_2024",
        rentree="2024",
        total=789,
        par_filiere={
            "medecine": {"total": 507, "PASS": 253, "LAS": 221, "passerelles": 33,
                         "detail": {"GROUPE 2 - LAS1": 61, "GROUPE 1 LAS2-LAS3": 160},
                         "somme_de": {"LAS": ["GROUPE 2 - LAS1", "GROUPE 1 LAS2-LAS3"]}},
            "maieutique": {"total": 38, "PASS": 19, "LAS": 16, "passerelles": 3,
                           "detail": {"GROUPE 2 - LAS1": 3, "GROUPE 1 LAS2-LAS3": 13},
                           "somme_de": {"LAS": ["GROUPE 2 - LAS1", "GROUPE 1 LAS2-LAS3"]}},
            "odontologie": {"total": 72, "PASS": 36, "LAS": 28, "passerelles": 8,
                            "detail": {"GROUPE 2 - LAS1": 5, "GROUPE 1 LAS2-LAS3": 23},
                            "somme_de": {"LAS": ["GROUPE 2 - LAS1", "GROUPE 1 LAS2-LAS3"]}},
            "pharmacie": {"total": 172, "PASS": 86, "LAS": 69, "passerelles": 17,
                          "detail": {"GROUPE 2 - LAS1": 17, "GROUPE 1 LAS2-LAS3": 52},
                          "somme_de": {"LAS": ["GROUPE 2 - LAS1", "GROUPE 1 LAS2-LAS3"]}},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "médecine, maïeutique, odontologie, pharmacie (MMOP) pour un total de 789 places pour la rentrée 2024 est fixée comme suit sur la base de la délibération",
            "MEDECINE MAIEUTIQUE ODONTOLOGIE PHARMACIE TOTAL %",
            "GROUPE 1 - PASS 253 19 36 86 394",
            "GROUPE 2 - LAS1 61 3 5 17 86",
            "GROUPE 1 LAS2-LAS3 160 13 23 52 248",
            "PASSERELLES 33 3 8 17 61 8% ≥ 5%",
            "Capacités d'accueil 507 38 72 172 789 100%",
        ),
        note="rentrée 2024 : c'est la dernière délibération publiée trouvée sur les pages de l'université ; "
             "kinésithérapie non publiée dans ce document",
    ),
))

# ── Université Toulouse III (Université de Toulouse, Faculté de santé) ─────────────────────
# PDF « NUMERUS APERTUS PASS-LAS 2025/2026 », daté du 21/07/2025. Le document ne dit pas si
# « 2025/2026 » est l'année d'inscription en PASS/LAS ou l'année d'entrée en 2e année ; la page
# « passerelle santé » du même site affiche les mêmes places de passerelle sous « 2026/2027 ».
# Les « Etudiants diplômés étrangers hors UE » sont publiés entre parenthèses, hors des totaux.
_ajouter(Recherche(
    universite="Université Toulouse III",
    urls=(
        "https://sante.utoulouse.fr/parcours-dacces-specifique-a-la-sante-pass",
        "https://sante.utoulouse.fr/passerelle-sante",
    ),
    date=LUE_LE,
    constat="capacités publiées (numerus apertus 2025/2026, 5 filières) ; aucun taux de passage MMOPK publié sur ces pages",
    capacites=Capacites(
        universite="Université Toulouse III",
        source_id="univ_toulouse_mmopk_2025_2026",
        rentree="2025/2026",
        total=None,
        par_filiere={
            "medecine": {"total": 410, "PASS": 196, "LAS": 193, "passerelles": 21,
                         "detail": {"LAS-2+3": 122, "LAS-1": 71, "2025-2026 PASS/LAS": 389},
                         "somme_de": {"LAS": ["LAS-2+3", "LAS-1"]}},
            "maieutique": {"total": 30, "PASS": 11, "LAS": 15, "passerelles": 4,
                           "detail": {"LAS-2+3": 9, "LAS-1": 6, "2025-2026 PASS/LAS": 26,
                                      "Etudiants diplômés étrangers hors UE (entre parenthèses)": 2},
                           "somme_de": {"LAS": ["LAS-2+3", "LAS-1"]}},
            "odontologie": {"total": 106, "PASS": 48, "LAS": 52, "passerelles": 6,
                            "detail": {"LAS-2+3": 34, "LAS-1": 18, "2025-2026 PASS/LAS": 100},
                            "somme_de": {"LAS": ["LAS-2+3", "LAS-1"]}},
            "pharmacie": {"total": 144, "PASS": 52, "LAS": 72, "passerelles": 20,
                          "detail": {"LAS-2+3": 43, "LAS-1": 29, "2025-2026 PASS/LAS": 124,
                                     "Etudiants diplômés étrangers hors UE (entre parenthèses)": 5},
                          "somme_de": {"LAS": ["LAS-2+3", "LAS-1"]}},
            "kinesitherapie": {"total": 28, "PASS": 23, "LAS": 5,
                               "detail": {"PASS Toulouse": 18, "PASS Rodez": 5, "LAS-2+3 Toulouse": 5}},
        },
        voies_publiees=("PASS", "LAS", "passerelles"),
        extraits=(
            "NUMERUS APERTUS PASS-LAS 2025/2026",
            "2025-2026 TOTAL 410 30 106 144 690",
            "Passerelles (7.4%) 21 4 6 20 51",
            "Etudiants diplômés étrangers hors UE (2) (5) (7)",
            "2025-2026 PASS/LAS 389 26 100 124 639 28 23",
            "PASS (44.5%) 196 11 48 52 307 Tlse : 18",
            "Rodez : 5",
            "LAS-2+3 (30.1%) 122 9 34 43 208 5 Tlse",
            "LAS-1 (18%) 71 6 18 29 124",
            "Le 21/07/2025",
        ),
        note="document « NUMERUS APERTUS PASS-LAS 2025/2026 » du 21/07/2025, dernier publié ; il ne précise pas si "
             "2025/2026 est l'année d'inscription en PASS/LAS ou l'année d'entrée en 2e année",
    ),
))
