"""Étape B-2 de la donnée verticale : accès aux études de santé (MMOPK) des fiches PASS et LAS.

Contrat : `results/donnee_etape_b/CONTRACT.md`, section 10 (v1.3). Chaque fiche Parcoursup
`PASS` ou `Licence_Las` reçoit `sante`, quatre sous-champs à l'enveloppe commune, chacun avec sa
`portee` (`nationale` | `universite`) :
- `passage_national` : SIES, Note Flash n°31 (novembre 2025), ligne de la voie de la fiche ;
- `passage_universite` : taux publié par l'université elle-même, sinon `non_disponible` ;
- `capacites_universite` : places MMOPK publiées par l'université (panel de 10), sinon `non_disponible` ;
- `reforme_2027` : renvoi vers la fiche concept `reforme_sante_2027`.

Les chiffres sont recopiés à la main des documents sources ; chaque valeur porte l'extrait qui la
contient, et `src.eval.donnee.audit_sante` vérifie que l'extrait figure dans le fichier brut
verrouillé (`data/raw/sante/`, empreinte au verrou `data/reference/sources_officielles.json`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.collect.valeur_sourcee import Referentiel

FILIERES_SANTE = ("PASS", "Licence_Las")
VOIE = {"PASS": "PASS", "Licence_Las": "LAS"}
FILIERES_MMOPK = ("medecine", "pharmacie", "odontologie", "maieutique", "kinesitherapie")
LIBELLE_FILIERE = {
    "medecine": "médecine", "pharmacie": "pharmacie", "odontologie": "odontologie",
    "maieutique": "maïeutique", "kinesitherapie": "kinésithérapie",
}

# ── a) passage national : SIES, Note Flash n°31, novembre 2025 ──────────────────────────────
# PDF lu le 23/09/2026 (sha256 bd4e38d26f30..., verrou `sies_nf_2025_31`). Tableau « Taux de
# passage en 2ème année de MMOPK des néo-bacheliers après un ou deux ans d'études par filière
# (en %) », colonnes PASS 2022 et L.AS 2022. Chaque ligne du tableau est recopiée telle que
# `pdftotext -layout` la rend (espaces réduits), toutes cohortes comprises : l'audit la cherche
# dans le PDF, ce qui vérifie aussi la colonne. Le PDF ne donne pas de taux « en 1 an » par
# filière : il n'est pas écrit (contrat, section 10 a).
SIES_SOURCE_ID = "sies_nf_2025_31"
SIES_MILLESIME = "session 2024 (néo-bacheliers inscrits en 2022)"
SIES_DEFINITION = (
    "taux de passage en 2ème année de MMOPK des néo-bacheliers après un ou deux ans d'études ; "
    "champ : néo-bacheliers inscrits en 1ère année de santé, France (hors Polynésie française et "
    "Nouvelle-Calédonie) ; source MESRE-SIES, Système d'information sur le suivi de l'étudiant (SISE)"
)
# Ligne du tableau -> (PASS 2022, L.AS 2022), dans l'ordre des colonnes du PDF.
SIES_LIGNES = {
    "medecine": ("Médecine 22,7 24,7 24,2 29,4 14,1", (29.4, 14.1)),
    "maieutique": ("Maïeutique 1,3 1,9 2,0 2,4 1,2", (2.4, 1.2)),
    "odontologie": ("Odontologie 2,5 3,1 3,1 3,6 2,2", (3.6, 2.2)),
    "pharmacie": ("Pharmacie 4,8 6,2 6,5 7,9 3,9", (7.9, 3.9)),
    "kinesitherapie": ("Kinésithérapie 3,2 4,5 4,2 4,2 4,4", (4.2, 4.4)),
    "ensemble": ("en 2ème année de 34,5 40,4 40,1 47,5 25,7", (47.5, 25.7)),
    "un_an": ("dont admis en 1 an 25,3 30,3 28,9 33,8 19,5", (33.8, 19.5)),
    "deux_ans": ("admis en 2 ans 9,2 10,1 11,2 13,8 6,3", (13.8, 6.3)),
}
# PASS et L.AS confondus, cohorte 2022 : colonne « 2022 » de la ligne « Ensemble des admis ».
SIES_ENSEMBLE_PASS_LAS = 40.1
# Effectifs de la cohorte, texte de la page 1 (« 34 200 néo-bacheliers », « 22 500 », « 11 700 »).
SIES_EFFECTIFS = {"ensemble": 34200, "PASS": 22500, "LAS": 11700}
SIES_EXTRAITS_TEXTE = (
    "34 200 néo-bacheliers s'engagent dans",
    "ils sont 22 500 (soit 66 % d'entre eux) à",
    "en L.AS (Licence accès santé - annexe 1).",
    "Le taux de néo-bacheliers 2022 admis à poursuivre des études",
    "de santé en un ou deux ans est de 40,1 %",
)


def passage_national(voie: str) -> dict:
    """Valeur `passage_national` d'une voie (`PASS` | `LAS`), lue dans le tableau SIES."""
    i = 0 if voie == "PASS" else 1
    return {
        "voie": voie,
        "cohorte": "néo-bacheliers inscrits en 2022",
        "session_resultats": 2024,
        "effectif_cohorte": SIES_EFFECTIFS[voie],
        "admis_mmopk_1_ou_2_ans_pct": SIES_LIGNES["ensemble"][1][i],
        "admis_mmopk_1_an_pct": SIES_LIGNES["un_an"][1][i],
        "admis_mmopk_2_ans_pct": SIES_LIGNES["deux_ans"][1][i],
        "par_filiere_1_ou_2_ans_pct": {f: SIES_LIGNES[f][1][i] for f in FILIERES_MMOPK},
        "ensemble_pass_las_pct": SIES_ENSEMBLE_PASS_LAS,
        "definition": SIES_DEFINITION,
    }


# ── normalisation des établissements et panel ───────────────────────────────────────────────
# Libellé d'établissement Parcoursup -> université qui publie les capacités MMOPK. Ordre = priorité
# (« Université de Versailles » avant « Saclay » : l'EUPC de Guyancourt va à l'UVSQ, Q3 du contrat,
# accord de Jarvis le 23/09). Motifs mesurés sur les 800 fiches PASS/LAS du corpus B-1 le 23/09/2026.
NORMALISATION: tuple[tuple[str, str], ...] = (
    (r"Paris Cité", "Université Paris Cité"),
    (r"Sorbonne Paris Nord", "Université Sorbonne Paris Nord"),
    (r"^Sorbonne université", "Sorbonne Université"),
    (r"Versailles", "Université de Versailles Saint-Quentin-en-Yvelines"),
    (r"Saclay", "Université Paris-Saclay"),
    (r"^Université de Lille", "Université de Lille"),
    (r"Aix-Marseille", "Aix-Marseille Université"),
    (r"Lyon ?1|Claude Bernard", "Université Claude Bernard Lyon 1"),
    (r"Toulouse III", "Université Toulouse III"),
    (r"^Université de Montpellier", "Université de Montpellier"),
    (r"^Université de Bordeaux", "Université de Bordeaux"),
    (r"^Nantes Université", "Nantes Université"),
    (r"Lorraine", "Université de Lorraine"),
    (r"^Université de Rennes(?! 2)", "Université de Rennes"),
    (r"Jean Monnet", "Université Jean Monnet Saint-Étienne"),
    (r"Grenoble Alpes", "Université Grenoble Alpes"),
)

# Les 10 universités qui reçoivent le plus de vœux PASS + LAS (somme de
# `admission.volumes.voeux_totaux`, 800 fiches, 1 618 000 vœux, corpus B-1 sha256
# 9863d2b40d3f..., mesure du 23/09/2026, validée par Jarvis le même jour). Figé : le panel ne
# bouge pas quand le corpus change, il se remesure par décision.
PANEL = (
    "Université Paris Cité",
    "Université Sorbonne Paris Nord",
    "Université de Lille",
    "Université Claude Bernard Lyon 1",
    "Université de Montpellier",
    "Aix-Marseille Université",
    "Université Paris-Saclay",
    "Université Toulouse III",
    "Université de Bordeaux",
    "Nantes Université",
)


def universite_de(etablissement: str) -> str:
    """Université d'un libellé d'établissement Parcoursup (le libellé avant « - » à défaut)."""
    for motif, universite in NORMALISATION:
        if re.search(motif, etablissement or ""):
            return universite
    return re.split(r"\s+-\s+", (etablissement or "").strip())[0]


# ── b), c) données des universités (renseignées dans `src.collect.sante_universites`) ──────
@dataclass(frozen=True)
class Capacites:
    """Places MMOPK d'une université, telles que publiées sur ses pages."""

    universite: str
    source_id: str          # clé du verrou (page ou PDF de l'université)
    rentree: str            # telle que la page la date
    total: int | None
    # filière -> {"total", "PASS", "LAS", "passerelles", "autres", "detail"} ; valeurs publiées
    par_filiere: dict
    voies_publiees: tuple[str, ...]
    extraits: tuple[str, ...]   # lignes du document qui portent les nombres (audit)
    note: str | None = None


@dataclass(frozen=True)
class PassageUniversite:
    """Taux de passage en MMOPK publié par l'université elle-même."""

    universite: str
    source_id: str
    voie: str               # "PASS" | "LAS" | "PASS+LAS"
    annee: str
    taux_pct: float
    definition_publiee: str | None
    extraits: tuple[str, ...]


@dataclass(frozen=True)
class Recherche:
    """Pages consultées pour une université (preuve de l'absence quand rien n'est publié)."""

    universite: str
    urls: tuple[str, ...]
    date: str
    constat: str
    capacites: Capacites | None = None
    passages: tuple[PassageUniversite, ...] = field(default_factory=tuple)


# ── d) réforme 2027 ─────────────────────────────────────────────────────────────────────────
REFORME_ID = "reforme_sante_2027"
REFORME_VERIFIEE_LE = "2026-09-23"
REFORME_STATUT = "annonce"   # "annonce" | "texte_publie"


def fiche_reforme() -> dict:
    """Fiche concept « réforme 2027 : voie unique », datée, avec les recherches faites."""
    texte = (
        "Réforme de l'accès aux études de santé (médecine, maïeutique, odontologie, pharmacie, "
        "kinésithérapie : MMOPK). Le gouvernement a annoncé le 17/04/2026 la fin de PASS et de "
        "LAS et une voie unique d'accès à partir de la rentrée 2027 (annonce confirmée par "
        "Service-Public, actualité A18890 du 29/04/2026). Une proposition de loi relative aux "
        "formations en santé, qui prévoit une voie d'accès unique au plus tard le 1er septembre "
        "2027, a été adoptée en première lecture au Sénat le 20/10/2025 ; déposée à l'Assemblée "
        "nationale le 21/10/2025 (n° 1981), elle n'y a connu aucune autre étape à ce jour. "
        f"Aucun décret ni arrêté instituant cette voie unique n'est publié au Journal officiel à la "
        f"date du {_date_fr(REFORME_VERIFIEE_LE)}. Pour les étudiants qui entrent en première année à la rentrée "
        "2026, PASS et LAS restent la règle ; les chiffres de réussite PASS/LAS décrivent ce "
        "système et deviendront historiques avec la réforme."
    )
    return {
        "source": "concept",
        "id": REFORME_ID,
        "domain": "concept_sante",
        "subject": "Réforme 2027 de l'accès aux études de santé (voie unique, fin de PASS et LAS)",
        "nom": "Réforme de l'accès aux études de santé : voie unique annoncée pour la rentrée 2027",
        "text": texte,
        "statut_reglementaire": REFORME_STATUT,
        "texte_publie": None,
        "verifie_le": REFORME_VERIFIEE_LE,
        "annonce": {
            "date": "2026-04-17",
            "par": "Philippe Baptiste (Enseignement supérieur) et Stéphanie Rist (Santé)",
            "sources": [
                {"libelle": "L'Etudiant, « Le gouvernement annonce la fin des filières Pass/LAS et le retour à une voie unique »",
                 "url": "https://www.letudiant.fr/etudes/medecine-sante/le-gouvernement-annonce-la-fin-des-filieres-pass-las-et-le-retour-a-une-voie-unique.html",
                 "lue_le": "2026-09-23"},
                {"libelle": "Service-Public, actualité A18890 du 29/04/2026, « Réforme des études de santé : ce qui changera à partir de 2027 »",
                 "url": "https://www.service-public.gouv.fr/particuliers/actualites/A18890",
                 "lue_le": "2026-09-23"},
            ],
        },
        "recherches": [
            {"lieu": "Sénat, dossier législatif ppl24-868 (« la loi en clair »)",
             "url": "https://www.senat.fr/travaux-parlementaires/textes-legislatifs/la-loi-en-clair/proposition-de-loi-formations-en-sante.html",
             "resultat": "proposition de loi adoptée en première lecture le 20/10/2025, transmise à l'Assemblée nationale ; "
                         "« la voie d'accès unique aux études de santé doit entrer en vigueur au plus tard le 1er septembre 2027 »"},
            {"lieu": "Assemblée nationale, dossier DLR5L17N52601",
             "url": "https://www.assemblee-nationale.fr/dyn/17/dossiers/DLR5L17N52601",
             "resultat": "dernière étape : dépôt le 21/10/2025 (n° 1981), renvoi en commission des affaires sociales ; aucune étape ultérieure affichée"},
            {"lieu": "Légifrance, recherche JORF « portail santé », tri par date",
             "url": "https://www.legifrance.gouv.fr/search/jorf?query=%22portail%20sant%C3%A9%22&sortValue=PUBLICATION_DATE_DESC",
             "resultat": "0 texte"},
            {"lieu": "Légifrance, recherche JORF « études de santé », tri par date",
             "url": "https://www.legifrance.gouv.fr/search/jorf?query=%22%C3%A9tudes%20de%20sant%C3%A9%22&sortValue=PUBLICATION_DATE_DESC",
             "resultat": "248 textes, aucun n'institue une voie unique ni ne supprime PASS et LAS"},
            {"lieu": "Légifrance, témoin positif : recherche JORF « accès aux formations de médecine », tri par date",
             "url": "https://www.legifrance.gouv.fr/search/jorf?query=%22acc%C3%A8s%20aux%20formations%20de%20m%C3%A9decine%22&sortValue=PUBLICATION_DATE_DESC",
             "resultat": "75 textes, le plus récent : arrêté du 27/07/2026 (JORF n°0182 du 06/08/2026, JORFTEXT000054621889) "
                         "fixant la liste des établissements autorisés à reporter les places non pourvues des parcours "
                         "mentionnés au I de l'article R. 631-1 du code de l'éducation au titre de l'année 2025-2026. "
                         "La recherche voit donc les textes de 2026. Cet arrêté règle l'année 2025-2026 du système "
                         "PASS/LAS en vigueur : hors sujet pour la réforme 2027."},
            {"lieu": "presse spécialisée, AEF info, dépêche 753755",
             "url": "https://www.aefinfo.fr/depeche/753755-etudes-de-sante-le-systeme-passlas-sera-remplace-par-une-licence-portail-sante-en-2027-projets-de-decret-et-arrete",
             "resultat": "projets de décret et d'arrêté « licence portail santé » examinés au CNESER le 07/07/2026 : "
                         "presse, non vérifiée en source primaire (dépêche payante), non écrite dans le texte"},
        ],
    }


def _date_fr(iso: str) -> str:
    a, m, j = iso.split("-")
    return f"{j}/{m}/{a}"


# ── calcul du champ `sante` d'une fiche ─────────────────────────────────────────────────────
RAISON_HORS_PANEL = "hors du panel de 10 universités dont les pages ont été collectées à la main"
RAISON_SANS_FACULTE = "faculté partenaire non identifiée dans les données ouvertes"
RAISON_PASSAGE_NON_PUBLIE = "l'université ne publie pas de taux de passage sur les pages consultées"


class CalculSante:
    def __init__(self, ref: Referentiel, recherches: dict[str, Recherche], universites_avec_pass: set[str]) -> None:
        self.ref = ref
        self.recherches = recherches
        # Universités qui portent au moins une fiche PASS : elles ont une faculté de santé. Une
        # LAS d'une autre université a ses places chez une faculté partenaire (Q1 du contrat).
        self.universites_avec_pass = universites_avec_pass

    @staticmethod
    def concernee(fiche: dict) -> bool:
        return fiche.get("source") == "parcoursup" and fiche.get("fili_code") in FILIERES_SANTE

    def calculer(self, fiche: dict) -> dict:
        voie = VOIE[fiche["fili_code"]]
        universite = universite_de(fiche.get("etablissement") or "")
        return {
            "passage_national": self._national(voie),
            "passage_universite": self._passage_universite(voie, universite),
            "capacites_universite": self._capacites(voie, universite),
            "reforme_2027": self._reforme(),
        }

    def _national(self, voie: str) -> dict:
        champ = self.ref.disponible(passage_national(voie), SIES_SOURCE_ID, SIES_MILLESIME, "voie_nationale")
        return {**champ, "portee": "nationale"}

    def _hors(self, voie: str, universite: str) -> str | None:
        if universite in self.recherches:
            return None
        if voie == "LAS" and universite not in self.universites_avec_pass:
            return RAISON_SANS_FACULTE
        return RAISON_HORS_PANEL

    def _passage_universite(self, voie: str, universite: str) -> dict:
        raison = self._hors(voie, universite)
        if raison:
            return {**self.ref.non_disponible(raison), "portee": "universite"}
        r = self.recherches[universite]
        # Un taux publié pour la voie de la fiche, sinon un taux publié toutes voies confondues.
        choix = [p for p in r.passages if p.voie == voie] or [p for p in r.passages if p.voie == "PASS+LAS"]
        if not choix:
            return {**self._non_disponible_recherche(r, RAISON_PASSAGE_NON_PUBLIE), "portee": "universite"}
        p = max(choix, key=lambda x: x.annee)
        valeur = {
            "universite": universite, "voie": p.voie, "annee": p.annee, "taux_pct": p.taux_pct,
            "definition_publiee": p.definition_publiee, "texte_source": " ".join(p.extraits),
        }
        champ = self.ref.disponible(valeur, p.source_id, p.annee, "universite_de_la_fiche")
        return {**self._empreinte(champ, p.source_id), "portee": "universite"}

    def _capacites(self, voie: str, universite: str) -> dict:
        raison = self._hors(voie, universite)
        if raison:
            return {**self.ref.non_disponible(raison), "portee": "universite"}
        r = self.recherches[universite]
        c = r.capacites
        if c is None:
            return {**self._non_disponible_recherche(r, "l'université ne publie pas ses capacités MMOPK sur les pages consultées"),
                    "portee": "universite"}
        valeur = {
            "universite": universite, "rentree": c.rentree, "total": c.total,
            "par_filiere": {f: c.par_filiere.get(f) for f in FILIERES_MMOPK},
            "voies_publiees": list(c.voies_publiees), "texte_source": " ".join(c.extraits), "note": c.note,
            # Filières publiées dans un autre document (kinésithérapie à Bordeaux et à Lyon 1).
            "sources_complementaires": [
                {**self.ref.source(sid)[0], "sha256": self.ref.verrou[sid]["sha256"], "filieres": fs}
                for sid, fs in sorted(self._autres_sources(c).items())
            ],
        }
        champ = self.ref.disponible(valeur, c.source_id, f"rentrée {c.rentree}", "universite_de_la_fiche")
        return {**self._empreinte(champ, c.source_id), "portee": "universite"}

    @staticmethod
    def _autres_sources(c: Capacites) -> dict[str, list[str]]:
        autres: dict[str, list[str]] = {}
        for nom, f in c.par_filiere.items():
            if f.get("source_id") and f["source_id"] != c.source_id:
                autres.setdefault(f["source_id"], []).append(nom)
        return autres

    def _empreinte(self, champ: dict, source_id: str) -> dict:
        """Ajoute au bloc `source` l'empreinte du document lu (verrou), exigée par le contrat."""
        return {**champ, "source": {**champ["source"], "sha256": self.ref.verrou[source_id]["sha256"]}}

    def _non_disponible_recherche(self, r: Recherche, raison: str) -> dict:
        return {
            "statut": "non_disponible", "raison": raison,
            "source": {"id": None, "libelle": f"pages consultées ({r.universite})", "url": r.urls[0] if r.urls else None,
                       "urls_consultees": list(r.urls), "licence": None},
            "millesime": None, "collecte": r.date, "rattachement": "universite_de_la_fiche",
        }

    def _reforme(self) -> dict:
        return {
            "statut": "disponible",
            "valeur": {"concept_id": REFORME_ID, "statut_reglementaire": REFORME_STATUT, "verifie_le": REFORME_VERIFIEE_LE},
            "raison": None,
            "source": {"id": REFORME_ID, "libelle": "fiche concept du corpus (sources dans la fiche)", "url": None, "licence": None},
            "millesime": REFORME_VERIFIEE_LE,
            "collecte": REFORME_VERIFIEE_LE,
            "rattachement": "concept_national",
            "portee": "nationale",
        }
