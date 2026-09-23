"""Étape C : base structurée SQLite, dérivée du corpus B-2 (contrat results/donnee_etape_c/CONTRACT.md).

Une commande, déterministe, jamais éditée à la main :
- chiffres post-bac lus dans le corpus B-2 (décision Q6 = B de Matteo, 23/09/2026) ;
- coordonnées lues dans les bruts Parcoursup verrouillés (le corpus n'en porte pas) ;
- masters lus dans le brut MonMaster 2025 verrouillé (décision Q1) ;
- centres des communes lus dans le brut geo.api.gouv.fr verrouillé.

Sorties (hors git) : `data/processed/base_etape_c.sqlite`, son manifeste, l'export de
l'explorateur et le CSV pour tableur. Copie du manifeste dans `results/donnee_etape_c/`.

Levier de sabotage (audit, jamais en usage normal) : `ORIENTIA_SABOTAGE_C=<nom>`, voir
`SABOTAGES`. Un sabotage suffixe les sorties par `.sabote-<nom>` et n'écrase rien.

Usage :
    python -m src.collect.base_etape_c [--corpus data/processed/formations_etape_b2.json] [--sortie DIR]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from src.base_c import (
    ALIAS_REGIONS, CLES, REGIONS, SANS_SESSION, SCHEMA, normaliser_departement,
)
from src.collect.communes import ReferentielCommunes, cle_nom
from src.collect.sources_officielles import RACINE, charger_verrou, chemin_verifie
from src.collect.valeur_sourcee import SOURCES_LUES

CORPUS_DEFAUT = RACINE / "data/processed/formations_etape_b2.json"
SORTIE_DEFAUT = RACINE / "data/processed"
RESULTATS = RACINE / "results/donnee_etape_c"
TABLE_DOMAINES = RACINE / "data/reference/domaines_parcoursup.csv"
TABLE_TYPES = RACINE / "data/reference/types_etape_c.csv"
TABLE_CHAMPS = RACINE / "data/reference/champs_etape_c.csv"

# ── Périmètre (contrat §2, décisions Q2 et Q3 de Matteo) ─────────────────────────────────────
DOMAINES_DIRECTS = {"informatique", "cyber", "data_ia", "sante"}
REGLES_MATHS = {"M01", "M02", "M03"}
# Exclusion écrite et comptée (contrat v0.1 §2) : la règle M01 de la table A range dans les prépas
# scientifiques une préparation « ENS Paris-Saclay arts et design » (5 fiches le 23/09/2026).
# Défaut de la table A, à corriger dans la table ; en attendant, exclu ici.
EXCLUSIONS = (
    {"regle": "M01", "filiere_commence_par": "Ecole normale supérieure Paris Saclay",
     "motif": "préparation ENS arts et design classée en prépa scientifique par la règle M01 (défaut de la table A)"},
)
SECTEURS_MASTERS = {
    "Informatique": "informatique", "Mathématique et informatique": "informatique",
    "Mathématiques": "sciences_fondamentales", "Mathématiques appliquées et sciences sociales": "sciences_fondamentales",
}
SUFFIXE_APPRENTISSAGE = " - en apprentissage"

# ── Leviers de sabotage de l'audit (contrat §11.6) ─────────────────────────────────────────
SABOTAGES = {
    "valeur": "deux taux d'accès 2025 modifiés (+1) : psup:7596 (témoin) et psup:11236 (gate C05)",
    "source": "la source d'une valeur disponible effacée de la table source",
    "portee": "un taux national de santé présenté comme propre à l'université",
    "geo": "une coordonnée décalée d'un degré de latitude (environ 111 km)",
    "perimetre": "périmètre remplacé par le classement par mots-clés de l'explorateur",
    "absent": "une ligne non disponible supprimée",
    "insee": "normalisation « 0NN » des départements d'apprentissage retirée",
    "null_muet": "une valeur NULL sans raison insérée (doit être refusée par les contraintes)",
    "insertion": "un taux d'emploi InserSup à 6 mois modifié (+1) : psup:7596, ligne 1",
    "indicateur_inconnu": "un indicateur d'insertion sans colonne ajouté (doit être refusé à la construction)",
    "alternance": "un lien d'alternance supprimé",
    "table_orpheline": "une table que l'audit ne connaît pas ajoutée à la base",
}

# Noms officiels des enveloppes d'insertion du corpus (contrat B v1.2) : InserJeunes (lycée pro, BTS) et
# InserSup (supérieur) ne partagent pas leurs définitions, chaque indicateur garde sa colonne.
# Inventaire mesuré le 23/09 sur formations_etape_b2.json : 3 102 lignes InserJeunes, 2 097 InserSup.
INDICATEURS_INSERTION = {
    "taux_emploi_6m", "taux_emploi_12m", "taux_poursuite_etudes",  # InserJeunes
    "taux_emploi_salarie_fr_6m", "taux_emploi_salarie_fr_12m", "taux_emploi_salarie_fr_18m",  # InserSup
    "taux_emploi_stable_12m", "salaire_median_net_12m_eur",  # InserSup
}
CLES_LIGNE_INSERTION = {"perimetre", "effectif_sortants", "effectif_poursuivants", "indicateurs", "non_diffuse"}


def _maintenant() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Paris")).isoformat(timespec="seconds")


def sha256_fichier(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lire_csv(p: Path, delim: str = ";") -> list[dict]:
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delim))


def coord(texte: str | None) -> tuple[float, float] | None:
    try:
        la, lo = (float(x) for x in (texte or "").split(","))
    except ValueError:
        return None
    return la, lo


def chemin(obj, chemin_pointe: str):
    """Valeur à un chemin pointé (« a.b.c », « a.0 » pour un élément de liste) ; None si un maillon manque."""
    for morceau in chemin_pointe.split("."):
        if isinstance(obj, list) and morceau.isdigit() and int(morceau) < len(obj):
            obj = obj[int(morceau)]  # « fourchette_eur.0 » : borne basse d'une fourchette publiée
        elif isinstance(obj, dict) and morceau in obj:
            obj = obj[morceau]
        else:
            return None
    return obj


def par_espace(texte: str) -> dict[str, str]:
    """« psup=a|psup_app=b » -> {"psup": "a", "psup_app": "b"} ; texte sans « = » -> {"*": texte}."""
    if not texte:
        return {}
    if "=" not in texte:
        return {"*": texte}
    return dict(part.split("=", 1) for part in texte.split("|"))


# ── Tables de référence ────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RegleType:
    regle: str
    fili: str
    motif_type: re.Pattern | None
    type: str


def charger_types(p: Path = TABLE_TYPES) -> list[RegleType]:
    regles = []
    for r in lire_csv(p):
        motif = None if r["type_formation"] == "*" else re.compile(r["type_formation"])
        regles.append(RegleType(r["regle"], r["fili"], motif, r["type"]))
    return regles


def type_court(regles: list[RegleType], fili: str | None, type_formation: str | None) -> str:
    for r in regles:
        if r.fili != "*" and r.fili != fili:
            continue
        if r.motif_type is not None and not r.motif_type.search(type_formation or ""):
            continue
        return r.type
    raise ValueError(f"aucune règle de type pour {fili!r} / {type_formation!r}")  # T99 attrape tout


def charger_champs(p: Path = TABLE_CHAMPS) -> dict[str, dict]:
    return {r["champ"]: r for r in lire_csv(p)}


def champ_s_applique(c: dict, espace: str, type_: str) -> bool:
    if espace not in c["espaces"].split(","):
        return False
    return not c["types"] or type_ in c["types"].split(",")


def sessions_du_champ(c: dict, espace: str) -> list[str]:
    s = c["sessions"]
    if s == SANS_SESSION:
        return [SANS_SESSION]
    return par_espace(s).get(espace, "").split(",")


# ── Accumulateur de lignes ─────────────────────────────────────────────────────────────────
@dataclass
class Lignes:
    formation: list[dict] = field(default_factory=list)
    lieu: list[dict] = field(default_factory=list)
    valeur: list[dict] = field(default_factory=list)
    insertion_ligne: list[dict] = field(default_factory=list)
    alternance_lien: list[dict] = field(default_factory=list)
    concept: list[dict] = field(default_factory=list)
    commune: list[dict] = field(default_factory=list)
    sources_citees: dict[str, dict] = field(default_factory=dict)
    comptes: dict = field(default_factory=dict)

    def compte(self, cle: str, n: int = 1) -> None:
        self.comptes[cle] = self.comptes.get(cle, 0) + n


def _v(id_, champ, session, *, num=None, texte=None, unite=None, statut="disponible", raison=None,
       source_id=None, millesime=None, identifiant=None, rattachement=None, portee="formation") -> dict:
    return {"id": id_, "champ": champ, "session": session, "valeur_num": num, "valeur_texte": texte,
            "unite": unite, "statut": statut, "raison": raison, "source_id": source_id,
            "millesime": millesime, "identifiant_source": identifiant, "rattachement": rattachement,
            "portee": portee}


def _num(x):
    """Nombre tel que publié : int garde int, float garde float ; bool -> 0/1 ; le reste -> None."""
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return x
    return None


# ── Construction ───────────────────────────────────────────────────────────────────────────
class Constructeur:
    def __init__(self, corpus: list[dict], sabotage: str | None = None, avec_verrou: bool = True):
        self.corpus = corpus
        self.sabotage = sabotage
        self.types = charger_types()
        self.champs = charger_champs()
        self.l = Lignes()
        self.verrou = charger_verrou() if avec_verrou else {}
        self._charger_bruts()

    # Bruts verrouillés : un sha divergent lève avant toute écriture.
    def _charger_bruts(self) -> None:
        self.geo_psup = {r["cod_aff_form"]: coord(r["g_olocalisation_des_formations"])
                         for r in lire_csv(chemin_verifie("parcoursup_2025"))}
        self.geo_app = {r["cod_aff_form"]: coord(r["g_olocalisation_des_formations"])
                        for r in lire_csv(chemin_verifie("parcoursup_apprentissage_2025"))}
        self.masters_bruts = json.loads(chemin_verifie("monmaster_2025").read_bytes())
        self.communes_geo = json.loads(chemin_verifie("geo_api_communes").read_bytes())
        self.ref_communes = ReferentielCommunes(chemin_verifie("insee_cog_communes_2025"),
                                                chemin_verifie("insee_cog_comer_2025"))
        self.centres = {c["code"]: c for c in self.communes_geo}
        self.par_cle = {}
        for c in self.communes_geo:
            self.par_cle.setdefault((c.get("codeDepartement"), cle_nom(c["nom"])), c)

    # ── périmètre
    def dans_perimetre(self, f: dict) -> bool:
        if f.get("source") not in ("parcoursup", "parcoursup_apprentissage"):
            return False
        dom = f.get("domaine")
        return dom in DOMAINES_DIRECTS or (dom == "sciences_fondamentales" and f.get("domaine_regle") in REGLES_MATHS)

    def exclusion(self, f: dict) -> dict | None:
        for e in EXCLUSIONS:
            if f.get("domaine_regle") == e["regle"] and (f.get("filiere_detaillee") or "").startswith(e["filiere_commence_par"]):
                return e
        return None

    def selection(self) -> list[dict]:
        if self.sabotage == "perimetre":
            return self._selection_explorateur()
        retenues = []
        for f in self.corpus:
            if not self.dans_perimetre(f):
                continue
            e = self.exclusion(f)
            if e:
                self.l.compte(f"exclues:{e['regle']}:{e['filiere_commence_par']}")
                continue
            retenues.append(f)
        return retenues

    def _selection_explorateur(self) -> list[dict]:
        """Sabotage « perimetre » : le classement par mots-clés de l'explorateur (export_data.py, 23/09)."""
        dom = {
            "informatique": (r"(?i:informatiq|cyber|science des données|\bdata\b|réseaux et télécom|MIASHS|intelligence artificielle|développeur|MP2I|MPII)", ()),
            "sante": (r"\bPASS\b|(?i:accès santé|infirmi|kiné|masso|orthophon|ergothér|psychomot|manipulateur|pédicur|orthopt|audioprothé|sage-femme|maïeut)", ("PASS", "Licence_Las", "IFSI")),
            "maths": (r"(?i:math|MPSI|MP2I|MPII|MIASHS)", ()),
        }
        exclu = {"informatique": r"information[- ]communication|information et communication|génie électrique et informatique industrielle",
                 "maths": r"avec (la|2) spécialit|\bECG\b"}
        out = []
        for f in self.corpus:
            if "fili_code" not in f:
                continue
            txt = " ".join(str(f.get(k) or "") for k in ("nom", "detail", "fili_code"))
            for nom, (pat, filis) in dom.items():
                champ = (f.get("nom") or "") if nom == "maths" else txt
                if (re.search(pat, champ) or f.get("fili_code") in filis) and not (nom in exclu and re.search(exclu[nom], txt, re.I)):
                    out.append(f)
                    break
        return out

    # ── une fiche post-bac
    def fiche_postbac(self, f: dict) -> None:
        espace = "psup" if f["source"] == "parcoursup" else "psup_app"
        cod = f["cod_aff_form"]
        id_ = f"{espace}:{cod}"
        type_ = type_court(self.types, f.get("fili_code"), f.get("type_formation"))
        filiere = (f.get("filiere_detaillee") or "")
        apprentissage = 1 if espace == "psup_app" else 0
        if filiere.endswith(SUFFIXE_APPRENTISSAGE):
            filiere = filiere[: -len(SUFFIXE_APPRENTISSAGE)]
        self.l.formation.append({
            "id": id_, "espace": espace, "identifiant_source": cod, "intitule": f.get("nom") or "",
            "etablissement": f.get("etablissement"), "uai": f.get("cod_uai"), "statut": f.get("statut"),
            "statut_detaille": f.get("statut_detaille"), "type": type_, "type_libelle": f.get("type_formation"),
            "filiere": filiere or None, "specialite": f.get("precision_formation"), "apprentissage": apprentissage,
            "selectivite": f.get("selectivite_code"), "domaine": f.get("domaine"),
            "domaine_regle": f.get("domaine_regle"), "region_academique": None,
            "lien_officiel": f.get("lien_form_psup"), "derniere_session": "2025",
        })
        self.lieu_postbac(f, id_, espace)
        self.admission(f, id_, espace, type_)
        self.enveloppe("cout", f.get("cout"), id_, espace, type_)
        if espace == "psup":
            self.alternance(f, id_)
        self.insertion(f, id_)
        if type_ in ("pass", "las"):
            self.sante(f, id_)

    def lieu_postbac(self, f: dict, id_: str, espace: str) -> None:
        dep = f.get("code_departement")
        dep_norm = dep if self.sabotage == "insee" else normaliser_departement(dep)
        code_insee, commune, arr = f.get("code_insee"), f.get("ville"), f.get("arrondissement")
        if code_insee:
            self.l.compte(f"insee_du_corpus:{espace}")
        else:
            res = self.ref_communes.resoudre(f.get("ville"), dep_norm)
            if res.code_insee:
                code_insee, commune, arr = res.code_insee, res.ville, res.arrondissement
                self.l.compte(f"insee_resolus_etape_c:{espace}")
            else:
                self.l.compte(f"insee_non_resolus:{espace}")
        centre = self.centres.get(code_insee) if code_insee else None
        region = REGIONS.get(centre.get("codeRegion")) if centre else None
        if region is None:
            region = ALIAS_REGIONS.get(f.get("region"), f.get("region"))
        gps = (self.geo_psup if espace == "psup" else self.geo_app).get(f["cod_aff_form"])
        if gps:
            lat, lon, precision = gps[0], gps[1], "formation"
            src = "parcoursup_2025" if espace == "psup" else "parcoursup_apprentissage_2025"
        elif centre and centre.get("centre"):
            lon, lat = centre["centre"]["coordinates"]
            precision, src = "commune", "geo_api_communes"
            self.l.compte("lieux_au_centre_de_commune")
        else:
            lat = lon = None
            precision, src = "non_disponible", None
            self.l.compte("lieux_sans_coordonnees")
        if self.sabotage == "geo" and id_ == "psup:7596" and lat is not None:
            lat += 1.0
        self.l.lieu.append({
            "id": id_, "rang": 1, "libelle": f.get("etablissement"), "commune": commune, "code_insee": code_insee,
            "arrondissement": arr, "code_departement": dep_norm, "departement": f.get("departement"),
            "region": region, "academie": f.get("academie"), "lat": lat, "lon": lon,
            "precision_geo": precision, "source_id": src,
        })

    # Chiffres Parcoursup : 2025 lus dans les champs principaux, 2023-2024 dans l'historique.
    CHEMINS_2025 = {
        "taux_acces": "taux_acces_parcoursup_2025", "places": "nombre_places",
        "voeux_totaux": "admission.volumes.voeux_totaux", "voeux_phase_principale": "admission.volumes.voeux_phase_principale",
        "classes_phase_principale": "admission.volumes.classes_phase_principale",
        "admis_total": "admission.volumes.admis_total", "propositions": "propositions_totales",
        "part_admis_debut_pp": "pct_acceptes_debut_pp",
        "part_bac_general": "profil_admis.bac_type_pct.general", "part_bac_techno": "profil_admis.bac_type_pct.techno",
        "part_bac_pro": "profil_admis.bac_type_pct.pro",
        "part_mention_tb": "profil_admis.mentions_pct.tb", "part_mention_b": "profil_admis.mentions_pct.b",
        "part_mention_ab": "profil_admis.mentions_pct.ab", "part_mention_sans_mention": "profil_admis.mentions_pct.sans",
        "part_mention_tbf": "profil_admis.mentions_pct.tbf", "part_boursiers": "profil_admis.boursiers_pct",
        "part_femmes": "profil_admis.femmes_pct", "part_neobacheliers": "profil_admis.neobacheliers_pct",
        "part_meme_academie": "profil_admis.origine_academique_idf_pct",
        "part_acces_general": "profil_admis.acces_pct.general", "part_acces_techno": "profil_admis.acces_pct.techno",
        "part_acces_pro": "profil_admis.acces_pct.pro",
    }
    CHEMINS_HISTORIQUE = {
        "taux_acces": "taux_acces", "places": "places", "voeux_totaux": "voeux_totaux",
        "voeux_phase_principale": "voeux_phase_principale", "part_bac_general": "pct_bg",
        "part_bac_techno": "pct_bt", "part_bac_pro": "pct_bp", "part_mention_tb": "pct_tb",
        "part_mention_b": "pct_b", "part_boursiers": "pct_bours", "part_femmes": "pct_f",
    }
    CHEMINS_APPRENTISSAGE = {
        "places": "apprentissage.capacite", "voeux_totaux": "apprentissage.candidats",
        "propositions": "apprentissage.propositions", "voeux_recherche_contrat": "apprentissage.voeux_recherche_contrat",
        "refus_apres_examen": "apprentissage.refus_apres_examen", "refus_faute_de_place": "apprentissage.refus_faute_de_place",
    }

    def admission(self, f: dict, id_: str, espace: str, type_: str) -> None:
        cod = f["cod_aff_form"]
        src = "parcoursup_2025" if espace == "psup" else "parcoursup_apprentissage_2025"
        hist = (f.get("admission") or {}).get("historique") or {}
        for nom, c in self.champs.items():
            if c["parent"] or c["type_valeur"] in ("groupe", "booleen") or not champ_s_applique(c, espace, type_):
                continue
            officiel = par_espace(c["nom_officiel"]).get(espace, "")
            for s in sessions_du_champ(c, espace):
                source_s = src if s == "2025" else f"parcoursup_{s}"
                ident = f"cod_aff_form={cod};champ={officiel}"
                if espace == "psup_app":
                    v = chemin(f, self.CHEMINS_APPRENTISSAGE[nom])
                    present = True
                elif s == "2025":
                    v = chemin(f, self.CHEMINS_2025[nom])
                    present = True
                else:
                    present = s in hist
                    v = hist.get(s, {}).get(self.CHEMINS_HISTORIQUE[nom]) if present else None
                v = _num(v)
                if v is None:
                    # Formation absente du jeu de la session : aucune ligne source ne porte ce chiffre,
                    # donc pas d'identifiant (sinon il pointerait vers une ligne qui n'existe pas).
                    raison = (f"formation absente du jeu Parcoursup {s}" if not present
                              else "la source ne publie pas cette valeur pour cette formation (champ vide)")
                    self.l.valeur.append(_v(id_, nom, s, unite=c["unite"], statut="non_disponible", raison=raison,
                                            source_id=source_s, millesime=f"session {s}",
                                            identifiant=ident if present else None))
                    continue
                # Deux cibles : le témoin de l'audit (psup:7596) et un chiffre vérifié par le gate (C05).
                if self.sabotage == "valeur" and id_ in ("psup:7596", "psup:11236") and nom == "taux_acces" and s == "2025":
                    v = v + 1
                self.l.valeur.append(_v(id_, nom, s, num=v, unite=c["unite"], source_id=source_s,
                                        millesime=f"session {s}", identifiant=ident))

    def _source_enveloppe(self, env: dict) -> str | None:
        src = env.get("source")
        if not src:
            return None
        sid = src.get("id")
        self.l.sources_citees.setdefault(sid, src)
        return sid

    def enveloppe(self, groupe: str, env: dict | None, id_: str, espace: str, type_: str, portee: str = "formation") -> None:
        """Champ groupe de l'étape B (cout, insertion...) : une ligne groupe + une ligne par détail publié."""
        if env is None:
            self.l.valeur.append(_v(id_, groupe, SANS_SESSION, statut="non_disponible", portee=portee,
                                    raison="champ absent de la fiche du corpus (défaut de pipeline)"))
            self.l.compte(f"enveloppe_absente:{groupe}")
            return
        sid = self._source_enveloppe(env)
        commun = {"source_id": sid, "millesime": env.get("millesime"), "rattachement": env.get("rattachement"),
                  "portee": env.get("portee") or portee}
        if env.get("statut") != "disponible":
            self.l.valeur.append(_v(id_, groupe, SANS_SESSION, statut="non_disponible",
                                    raison=env.get("raison") or "non disponible", **commun))
            return
        valeur = env.get("valeur") or {}
        details = []
        for nom, c in self.champs.items():
            if c["parent"] != groupe or not champ_s_applique(c, espace, type_):
                continue
            chemin_detail = par_espace(c["chemin_corpus"]).get("*", "")
            sous = chemin_detail.split(".valeur.", 1)[1] if ".valeur." in chemin_detail else None
            brut = chemin(valeur, sous) if sous else None
            if brut is None:
                continue
            ligne = dict(commun)
            if nom == "cout.cvec_eur" and valeur.get("cvec_source"):
                ligne["source_id"] = valeur["cvec_source"]
                self.l.sources_citees.setdefault(valeur["cvec_source"], {"id": valeur["cvec_source"]})
            if c["type_valeur"] == "texte":
                details.append(_v(id_, nom, SANS_SESSION, texte=str(brut), unite=c["unite"] or None, identifiant=self._ident(groupe, valeur), **ligne))
            else:
                n = _num(brut)
                if n is None:
                    continue
                details.append(_v(id_, nom, SANS_SESSION, num=n, unite=c["unite"] or None, identifiant=self._ident(groupe, valeur), **ligne))
        self.l.valeur.append(_v(id_, groupe, SANS_SESSION, num=len(details), unite="détails",
                                identifiant=self._ident(groupe, valeur), **commun))
        self.l.valeur.extend(details)

    @staticmethod
    def _ident(groupe: str, valeur: dict) -> str | None:
        if groupe == "cout" and valeur.get("onisep_action"):
            return f"onisep_action={valeur['onisep_action']}"
        if groupe == "sante.capacites_universite":
            return f"universite={valeur.get('universite')};rentree={valeur.get('rentree')}"
        if groupe == "sante.passage_national":
            return f"voie={valeur.get('voie')};cohorte={valeur.get('cohorte')}"
        return None

    def alternance(self, f: dict, id_: str) -> None:
        env = f.get("alternance")
        if not env or env.get("statut") != "disponible":
            self.l.valeur.append(_v(id_, "alternance", SANS_SESSION, statut="non_disponible",
                                    raison=(env or {}).get("raison") or "champ absent de la fiche du corpus",
                                    source_id=self._source_enveloppe(env) if env else None,
                                    millesime=(env or {}).get("millesime")))
            return
        val = env["valeur"]
        sid = self._source_enveloppe(env)
        self.l.valeur.append(_v(id_, "alternance", SANS_SESSION, num=1 if val.get("existe_en_apprentissage") else 0,
                                unite="0/1", source_id=sid, millesime=env.get("millesime"),
                                rattachement=env.get("rattachement")))
        for form in val.get("formations") or []:
            self.l.alternance_lien.append({
                "id": id_, "id_apprentissage": f"psup_app:{form['cod_aff_form']}", "etablissement": form.get("etablissement"),
                "commune": form.get("ville"), "capacite": form.get("capacite"), "cfa_partenaire": form.get("cfa_partenaire"),
                "precision": form.get("precision"), "rattachee_par": form.get("rattachee_par"),
            })

    def insertion(self, f: dict, id_: str) -> None:
        env = f.get("insertion")
        if not env:
            self.l.valeur.append(_v(id_, "insertion", SANS_SESSION, statut="non_disponible",
                                    raison="champ absent de la fiche du corpus (défaut de pipeline)"))
            return
        sid = self._source_enveloppe(env)
        commun = {"source_id": sid, "millesime": env.get("millesime"), "rattachement": env.get("rattachement")}
        if env.get("statut") != "disponible":
            self.l.valeur.append(_v(id_, "insertion", SANS_SESSION, statut="non_disponible",
                                    raison=env.get("raison") or "non disponible", **commun))
            return
        val = env["valeur"]
        lignes = val.get("lignes") or []
        self.l.valeur.append(_v(id_, "insertion", SANS_SESSION, num=len(lignes), unite="lignes",
                                texte=val.get("dispositif"), **commun))
        for rang, lg in enumerate(lignes, 1):
            ind = dict(lg.get("indicateurs") or {})
            if self.sabotage == "indicateur_inconnu" and id_ == "psup:7596" and rang == 1:
                ind["taux_emploi_inconnu_6m"] = 50.0
            per = lg.get("perimetre") or {}
            # Une clé que la table ne sait pas porter arrête la construction : le 23/09, les 5 indicateurs
            # InserSup étaient lus sous les noms InserJeunes et perdus sans erreur sur 108 lignes.
            inconnues = sorted(set(lg) - CLES_LIGNE_INSERTION) + sorted(set(ind) - INDICATEURS_INSERTION)
            if inconnues:
                raise ValueError(f"{id_} insertion ligne {rang} : clés sans colonne {inconnues}")
            ligne = {
                "id": id_, "rang": rang, "dispositif": val.get("dispositif"), "promotion": val.get("promotion"),
                "regime": val.get("regime"), "granularite": per.get("granularite"), "etablissement": per.get("etablissement"),
                "diplome": per.get("diplome"), "effectif_sortants": _num(lg.get("effectif_sortants")),
                "effectif_poursuivants": _num(lg.get("effectif_poursuivants")),
                **{k: _num(ind.get(k)) for k in sorted(INDICATEURS_INSERTION)},
                "non_diffuse": json.dumps(lg.get("non_diffuse") or [], ensure_ascii=False),
                "perimetre_json": json.dumps(per, ensure_ascii=False, sort_keys=True), "source_id": sid,
            }
            if self.sabotage == "insertion" and id_ == "psup:7596" and rang == 1 and ligne["taux_emploi_salarie_fr_6m"] is not None:
                ligne["taux_emploi_salarie_fr_6m"] += 1
            self.l.insertion_ligne.append(ligne)

    def sante(self, f: dict, id_: str) -> None:
        s = f.get("sante") or {}
        for groupe, cle in (("sante.passage_national", "passage_national"), ("sante.capacites_universite", "capacites_universite"),
                            ("sante.passage_universite", "passage_universite")):
            env = s.get(cle)
            if self.sabotage == "portee" and groupe == "sante.passage_national" and id_ == "psup:27163" and env:
                env = {**env, "portee": "universite"}
            self.enveloppe(groupe, env, id_, "psup", "pass" if f.get("fili_code") == "PASS" else "las",
                           portee="nationale" if cle == "passage_national" else "universite")
        env = s.get("reforme_2027")
        if env and env.get("statut") == "disponible":
            self.l.valeur.append(_v(id_, "sante.reforme_2027", SANS_SESSION, texte=env["valeur"]["concept_id"],
                                    source_id=self._source_enveloppe(env), millesime=env.get("millesime"),
                                    rattachement=env.get("rattachement"), portee="nationale",
                                    identifiant=f"concept:{env['valeur']['concept_id']}"))
        else:
            self.l.valeur.append(_v(id_, "sante.reforme_2027", SANS_SESSION, statut="non_disponible",
                                    raison=(env or {}).get("raison") or "champ absent de la fiche du corpus", portee="nationale"))

    # ── masters (brut MonMaster 2025 verrouillé)
    def masters(self) -> None:
        for m in self.masters_bruts:
            dom = SECTEURS_MASTERS.get(m.get("secteur_disci_lib"))
            if dom is None:
                continue
            id_ = f"mm:{m['ifc']}"
            self.l.formation.append({
                "id": id_, "espace": "mm", "identifiant_source": m["ifc"],
                "intitule": " - ".join(x for x in (m.get("mention"), m.get("parcours")) if x),
                "etablissement": m.get("eta_nom"), "uai": m.get("eta_uai"), "statut": None, "statut_detaille": None,
                "type": "master", "type_libelle": "Master", "filiere": m.get("mention"), "specialite": m.get("parcours"),
                "apprentissage": 1 if m.get("alternance") == "1" else 0, "selectivite": None, "domaine": dom,
                "domaine_regle": f"MM:{m.get('secteur_disci_lib')}", "region_academique": m.get("acad_reg_lib"),
                "lien_officiel": None, "derniere_session": "2025",
            })
            self.lieux_master(m, id_)
            ident = f"ifc={m['ifc']}"
            for nom, c in self.champs.items():
                if "mm" not in c["espaces"].split(",") or c["parent"] or c["type_valeur"] == "groupe":
                    continue
                officiel = par_espace(c["nom_officiel"]).get("mm", "")
                brut = m.get(officiel)
                if isinstance(brut, str):
                    try:
                        brut = float(brut) if "." in brut else int(brut)
                    except ValueError:
                        brut = None
                if brut is None:
                    self.l.valeur.append(_v(id_, nom, "2025", unite=c["unite"], statut="non_disponible",
                                            raison="la source ne publie pas cette valeur pour ce master (champ vide)",
                                            source_id="monmaster_2025", millesime="session 2025", identifiant=f"{ident};champ={officiel}"))
                    continue
                self.l.valeur.append(_v(id_, nom, "2025", num=brut, unite=c["unite"], source_id="monmaster_2025",
                                        millesime="session 2025", identifiant=f"{ident};champ={officiel}"))
            for groupe, raison in (("cout", "coût des masters non collecté (l'étape B-1 couvre le post-bac)"),
                                   ("insertion", "insertion des masters non collectée (l'étape B-1 couvre le post-bac)")):
                self.l.valeur.append(_v(id_, groupe, SANS_SESSION, statut="non_disponible", raison=raison))

    _LIEU_MASTER = re.compile(r"^(?P<lib>.*) - (?P<commune>[^()]+?) \((?P<dep>[0-9AB]{2,3})\)$")

    def lieux_master(self, m: dict, id_: str) -> None:
        vus = []
        for morceau in (m.get("lieux") or "").split("|"):
            r = self._LIEU_MASTER.match(morceau.strip())
            if not r:
                continue
            dep = normaliser_departement(r["dep"])
            cle = (dep, cle_nom(r["commune"]))
            if cle in vus:
                continue
            vus.append(cle)
            c = self.par_cle.get(cle) or self._commune_par_nom(r["commune"], dep)
            rang = len(vus)
            if c and c.get("centre"):
                lon, lat = c["centre"]["coordinates"]
                self.l.lieu.append({"id": id_, "rang": rang, "libelle": r["lib"], "commune": c["nom"], "code_insee": c["code"],
                                    "arrondissement": None, "code_departement": c.get("codeDepartement"), "departement": None,
                                    "region": REGIONS.get(c.get("codeRegion")), "academie": m.get("lieu_acad_lib"),
                                    "lat": lat, "lon": lon, "precision_geo": "commune", "source_id": "geo_api_communes"})
            else:
                self.l.compte("lieux_masters_non_resolus")
                self.l.lieu.append({"id": id_, "rang": rang, "libelle": r["lib"], "commune": r["commune"], "code_insee": None,
                                    "arrondissement": None, "code_departement": dep, "departement": None, "region": None,
                                    "academie": m.get("lieu_acad_lib"), "lat": None, "lon": None,
                                    "precision_geo": "non_disponible", "source_id": None})
        if not vus:
            self.l.compte("masters_sans_lieu")

    def _commune_par_nom(self, nom: str, dep: str | None):
        """Lieu MonMaster qui ne tombe pas du premier coup sur une commune (mesure du 23/09/2026 : 29 lieux).

        Dans l'ordre : CEDEX retiré (MonMaster écrit aussi « CÉDEX »), numéro final retiré
        (« LYON 07 ») ; outre-mer écrit « 97 » essayé en 971 à 976 ; puis le résolveur de l'étape A,
        qui connaît les communes déléguées (Évry) et la Corse (« 20 »). Rien n'est deviné au-delà :
        un lieu qui ne se résout pas reste sans coordonnées, compté.
        """
        propre = re.sub(r"\s+C[EÉ]DEX(\s*\d+)?$", "", nom.strip(), flags=re.I)
        propre = re.sub(r"\s+\d{1,2}(ER|E)?$", "", propre, flags=re.I)
        deps = [f"97{i}" for i in range(1, 7)] if dep == "97" else [dep]
        for d in deps:
            c = self.par_cle.get((d, cle_nom(propre)))
            if c:
                return c
        for d in deps:
            res = self.ref_communes.resoudre(propre, d)
            if res.code_insee and res.code_insee in self.centres:
                return self.centres[res.code_insee]
        return None

    # ── tables annexes
    def communes(self) -> None:
        for c in self.communes_geo:
            ctr = (c.get("centre") or {}).get("coordinates") or [None, None]
            self.l.commune.append({"code_insee": c["code"], "nom": c["nom"], "cle": cle_nom(c["nom"]),
                                   "code_departement": c.get("codeDepartement"), "region": REGIONS.get(c.get("codeRegion")),
                                   "lat": ctr[1], "lon": ctr[0]})

    def concepts(self) -> None:
        for f in self.corpus:
            if f.get("source") != "concept":
                continue
            self.l.concept.append({
                "concept_id": f["id"], "titre": f.get("nom") or f.get("subject") or f["id"], "texte": f.get("text") or "",
                "statut_reglementaire": f.get("statut_reglementaire"), "verifie_le": f.get("verifie_le"),
                "sources_json": json.dumps({"annonce": f.get("annonce"), "recherches": f.get("recherches")},
                                           ensure_ascii=False, sort_keys=True),
            })

    def table_sources(self) -> list[dict]:
        ids = {v["source_id"] for v in self.l.valeur if v["source_id"]} | {x["source_id"] for x in self.l.lieu if x["source_id"]}
        lignes = []
        for sid in sorted(ids):
            if self.sabotage == "source" and sid == "parcoursup_2024":
                continue
            if sid in self.verrou:
                v = self.verrou[sid]
                lignes.append({"source_id": sid, "libelle": v["producteur"], "url": v["url"], "licence": v["licence"],
                               "collecte": v["telecharge_le"], "sha256": v["sha256"], "lignes": v.get("lignes")})
            elif sid in SOURCES_LUES:
                s = SOURCES_LUES[sid]
                lignes.append({"source_id": sid, "libelle": s.libelle, "url": s.url, "licence": s.licence,
                               "collecte": s.lue_le, "sha256": None, "lignes": None})
            else:
                s = self.l.sources_citees.get(sid) or {}
                lignes.append({"source_id": sid, "libelle": s.get("libelle") or sid, "url": s.get("url"),
                               "licence": s.get("licence"), "collecte": None, "sha256": None, "lignes": None})
        return lignes

    # ── tout
    def construire(self) -> Lignes:
        retenues = self.selection()
        for f in sorted(retenues, key=lambda x: (x["source"], x["cod_aff_form"])):
            self.fiche_postbac(f)
        self.l.compte("fiches_postbac", len(retenues))
        self.masters()
        self.communes()
        self.concepts()
        if self.sabotage == "absent":
            cible = next(i for i, v in enumerate(self.l.valeur) if v["statut"] == "non_disponible")
            del self.l.valeur[cible]
        if self.sabotage == "null_muet":
            self.l.valeur.append(_v(self.l.formation[0]["id"], "taux_acces", "1999", statut="non_disponible"))
        if self.sabotage == "alternance":
            del self.l.alternance_lien[0]
        return self.l


# ── Écriture ───────────────────────────────────────────────────────────────────────────────
def ecrire_sqlite(l: Lignes, sources: list[dict], champs: dict[str, dict], meta: dict, cible: Path) -> None:
    if cible.exists():
        cible.unlink()
    con = sqlite3.connect(cible)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    tables = {
        "source": sources, "champ": list(champs.values()), "formation": l.formation, "lieu": l.lieu,
        "valeur": l.valeur, "insertion_ligne": l.insertion_ligne, "alternance_lien": l.alternance_lien,
        "concept": l.concept, "commune": l.commune,
        "meta": [{"cle": k, "valeur": json.dumps(v, ensure_ascii=False, sort_keys=True)} for k, v in meta.items()],
    }
    with con:
        for table in ("source", "champ", "formation", "lieu", "valeur", "insertion_ligne", "alternance_lien",
                      "concept", "commune", "meta"):
            lignes = sorted(tables[table], key=lambda r: tuple(str(r[k]) for k in CLES[table]))
            if not lignes:
                continue
            cols = list(lignes[0].keys())
            con.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                            [tuple(r[c] for c in cols) for r in lignes])
    con.execute("PRAGMA foreign_key_check")
    fautes = con.execute("PRAGMA foreign_key_check").fetchall()
    con.close()
    if fautes:
        raise sqlite3.IntegrityError(f"{len(fautes)} clés étrangères orphelines, ex. {fautes[:3]}")


def empreinte_canonique(base: Path, sauf=("meta",)) -> tuple[str, dict]:
    """sha256 du contenu, table par table, lignes triées par clé ; indépendant de la disposition du fichier."""
    con = sqlite3.connect(base)
    h = hashlib.sha256()
    comptes = {}
    for table, cles in CLES.items():
        if table in sauf:
            continue
        cur = con.execute(f"SELECT * FROM {table} ORDER BY {', '.join(cles)}")
        cols = [d[0] for d in cur.description]
        n = 0
        h.update(table.encode())
        for row in cur:
            h.update(json.dumps(dict(zip(cols, row)), ensure_ascii=False, sort_keys=True).encode())
            n += 1
        comptes[table] = n
    con.close()
    return h.hexdigest(), comptes


# ── Exports ────────────────────────────────────────────────────────────────────────────────
CLE_IDENTIFIANT = {"psup": "cod_aff_form", "psup_app": "cod_aff_form", "mm": "ifc"}


def identifiant_deduit(id_: str, espace: str, nom_officiel: str) -> str:
    """Identifiant qu'un chiffre porte par défaut ; l'export v1.3 l'écrit null et l'écran le reconstruit."""
    return f"{CLE_IDENTIFIANT[espace]}={id_.split(':', 1)[1]};champ={par_espace(nom_officiel).get(espace, '')}"


def exporter(base: Path, json_sortie: Path, csv_sortie: Path, meta: dict) -> dict:
    con = sqlite3.connect(base)
    con.row_factory = sqlite3.Row
    champs = {r["champ"]: {k: r[k] for k in ("libelle", "definition", "ne_dit_pas", "unite", "portee", "parent", "type_valeur",
                                              "nom_officiel", "sessions", "espaces", "types")}
              for r in con.execute("SELECT * FROM champ ORDER BY champ")}
    sources = {r["source_id"]: {k: r[k] for k in ("libelle", "url", "licence", "collecte")}
               for r in con.execute("SELECT * FROM source ORDER BY source_id")}
    lieux, valeurs, insertions, liens = {}, {}, {}, {}
    for r in con.execute("SELECT * FROM lieu ORDER BY id, rang"):
        lieux.setdefault(r["id"], []).append({k: r[k] for k in ("libelle", "commune", "code_insee", "code_departement", "region", "lat", "lon", "precision_geo")})
    # Contrat v1.3 §9 : chaînes répétées remplacées par un indice dans « dico » ; identifiant
    # laissé à null quand il vaut « <clé>=<identifiant de la formation>;champ=<nom officiel> ».
    dico = {"sources": [], "millesimes": [], "raisons": [], "portees": []}
    index = {k: {} for k in dico}

    def indice(bloc: str, texte: str | None) -> int | None:
        if texte is None:
            return None
        if texte not in index[bloc]:
            index[bloc][texte] = len(dico[bloc])
            dico[bloc].append(texte)
        return index[bloc][texte]

    espace_de = {r["id"]: r["espace"] for r in con.execute("SELECT id, espace FROM formation")}
    n_valeurs = 0
    for r in con.execute("SELECT * FROM valeur ORDER BY id, champ, session"):
        cle = r["champ"] if r["session"] == SANS_SESSION else f"{r['champ']}@{r['session']}"
        val = r["valeur_num"] if r["valeur_num"] is not None else r["valeur_texte"]
        # v1.3.1 : null = identifiant déduit par la règle ; "" = aucune ligne source ne porte ce chiffre.
        ident = r["identifiant_source"]
        if ident is None:
            ident = ""
        elif ident == identifiant_deduit(r["id"], espace_de[r["id"]], champs[r["champ"]]["nom_officiel"]):
            ident = None
        valeurs.setdefault(r["id"], {})[cle] = [val, indice("sources", r["source_id"]), indice("millesimes", r["millesime"]),
                                                ident, indice("raisons", r["raison"]), indice("portees", r["portee"])]
        n_valeurs += 1
    for r in con.execute("SELECT * FROM insertion_ligne ORDER BY id, rang"):
        insertions.setdefault(r["id"], []).append({k: r[k] for k in r.keys() if k not in ("id", "perimetre_json")})
    for r in con.execute("SELECT * FROM alternance_lien ORDER BY id, id_apprentissage"):
        liens.setdefault(r["id"], []).append({k: r[k] for k in r.keys() if k != "id"})
    formations = []
    for r in con.execute("SELECT * FROM formation ORDER BY id"):
        d = {k: r[k] for k in r.keys() if k not in ("identifiant_source",)}
        d["lieux"] = lieux.get(r["id"], [])
        d["v"] = valeurs.get(r["id"], {})
        if r["id"] in insertions:
            d["insertion"] = insertions[r["id"]]
        if r["id"] in liens:
            d["alternance_liens"] = liens[r["id"]]
        formations.append(d)
    concepts = [dict(r) for r in con.execute("SELECT * FROM concept ORDER BY concept_id")]
    communes = [[r["code_insee"], r["nom"], r["code_departement"], r["lat"], r["lon"]]
                for r in con.execute("SELECT * FROM commune ORDER BY code_insee")]
    con.close()
    # Témoin de complétude pour l'écran (demande de Jarvis, v1.3) : il recompte après décompression.
    meta = {**meta, "n_formations": len(formations), "n_valeurs": n_valeurs, "n_communes": len(communes),
            "format": "contrat v1.3.1 section 9"}
    doc = {"meta": meta, "dico": dico, "champs": champs, "sources": sources, "formations": formations,
           "concepts": concepts, "communes": {"cols": ["code_insee", "nom", "departement", "lat", "lon"], "rows": communes}}
    json_sortie.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=False), encoding="utf-8")
    ecrire_csv(formations, champs, dico, csv_sortie)
    return {"json_octets": json_sortie.stat().st_size, "json_sha256": sha256_fichier(json_sortie),
            "csv_octets": csv_sortie.stat().st_size, "csv_sha256": sha256_fichier(csv_sortie)}


COLONNES_CSV = (
    ("id", "Identifiant"), ("type", "Type"), ("filiere", "Filière"), ("intitule", "Intitulé"),
    ("etablissement", "Établissement"), ("statut", "Public / privé"), ("apprentissage", "Apprentissage (0/1)"),
    ("domaine", "Domaine"),
)
CHIFFRES_CSV = ("taux_acces@2025", "taux_acces@2024", "taux_acces@2023", "places@2025", "voeux_totaux@2025",
                "part_bac_general@2025", "part_bac_techno@2025", "part_bac_pro@2025", "part_boursiers@2025",
                "capacite@2025", "candidats_pp@2025", "alternance", "alternance@2025", "cout.droits_inscription_eur",
                "cout.scolarite_annuel_eur", "cout.fourchette_min_eur", "cout.fourchette_max_eur",
                "passage_mmopk_1_ou_2_ans_national", "capacites_mmopk_total")


def ecrire_csv(formations: list[dict], champs: dict, dico: dict, cible: Path) -> None:
    with cible.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        entetes = [lib for _, lib in COLONNES_CSV] + ["Commune", "Département", "Région", "Latitude", "Longitude"]
        for c in CHIFFRES_CSV:
            nom, _, s = c.partition("@")
            lib = champs.get(nom, {}).get("libelle", nom)
            entetes += [f"{lib}{' ' + s if s else ''}", f"{lib}{' ' + s if s else ''} : source"]
        entetes.append("Lien officiel")
        w.writerow(entetes)
        for f in formations:
            lieu = (f["lieux"] or [{}])[0]
            ligne = [f.get(k) for k, _ in COLONNES_CSV] + [lieu.get("commune"), lieu.get("code_departement"),
                                                           lieu.get("region"), lieu.get("lat"), lieu.get("lon")]
            for c in CHIFFRES_CSV:
                v = f["v"].get(c)
                if not v:
                    ligne += ["", ""]
                    continue
                raison = dico["raisons"][v[4]] if v[4] is not None else ""
                source = dico["sources"][v[1]] if v[1] is not None else ""
                ligne += [v[0] if v[0] is not None else f"non disponible : {raison}", source]
            ligne.append(f.get("lien_officiel"))
            w.writerow(ligne)


# ── Commande ───────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=CORPUS_DEFAUT)
    ap.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    ap.add_argument("--sans-copie-resultats", action="store_true", help="ne recopie pas le manifeste dans results/")
    args = ap.parse_args(argv)

    sabotage = os.environ.get("ORIENTIA_SABOTAGE_C") or None
    if sabotage and sabotage not in SABOTAGES:
        print(f"ORIENTIA_SABOTAGE_C={sabotage!r} inconnu ; connus : {', '.join(SABOTAGES)}", file=sys.stderr)
        return 2
    suffixe = f".sabote-{sabotage}" if sabotage else ""
    args.sortie.mkdir(parents=True, exist_ok=True)
    base = args.sortie / f"base_etape_c{suffixe}.sqlite"
    manifeste = args.sortie / f"base_etape_c{suffixe}.manifest.json"

    corpus_octets = args.corpus.read_bytes()
    corpus = json.loads(corpus_octets)
    c = Constructeur(corpus, sabotage=sabotage)
    lignes = c.construire()
    sources = c.table_sources()
    entrees = {
        "corpus": {"chemin": str(args.corpus), "sha256": hashlib.sha256(corpus_octets).hexdigest(), "fiches": len(corpus)},
        "verrou": {"sha256": sha256_fichier(RACINE / "data/reference/sources_officielles.json")},
        "table_domaines": {"sha256": sha256_fichier(TABLE_DOMAINES)},
        "table_types": {"sha256": sha256_fichier(TABLE_TYPES)},
        "table_champs": {"sha256": sha256_fichier(TABLE_CHAMPS)},
        "bruts": {k: c.verrou[k]["sha256"] for k in ("parcoursup_2025", "parcoursup_apprentissage_2025",
                                                     "monmaster_2025", "geo_api_communes", "insee_cog_communes_2025")},
    }
    meta = {"commande": "python -m src.collect.base_etape_c", "contrat": "results/donnee_etape_c/CONTRACT.md v1.2",
            "sabotage": sabotage, "entrees": entrees, "comptes_construction": dict(sorted(lignes.comptes.items())),
            "exclusions": list(EXCLUSIONS)}
    ecrire_sqlite(lignes, sources, c.champs, meta, base)
    if sabotage == "table_orpheline":
        with sqlite3.connect(base) as con:
            con.execute("CREATE TABLE fantome (cle TEXT PRIMARY KEY, valeur NUMERIC)")
            con.execute("INSERT INTO fantome VALUES ('psup:7596', 42)")
    empreinte, comptes = empreinte_canonique(base)
    export_meta = {"genere_le": _maintenant(), "corpus_sha256": entrees["corpus"]["sha256"][:12],
                   "base_empreinte": empreinte[:12], "commande": meta["commande"], "sabotage": sabotage,
                   "perimetre": "post-bac Parcoursup et apprentissage des domaines informatique, cyber, data/IA, santé "
                                "et maths (règles M01-M03), masters info et maths MonMaster 2025"}
    exports = exporter(base, args.sortie / f"base_etape_c{suffixe}.explorateur.json",
                       args.sortie / f"base_etape_c{suffixe}_formations.csv", export_meta)
    doc = {"genere_le": export_meta["genere_le"], **meta,
           "sortie": {"chemin": str(base), "sha256_fichier": sha256_fichier(base), "empreinte_canonique": empreinte,
                      "lignes": comptes}, "exports": exports}
    manifeste.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not sabotage and not args.sans_copie_resultats:
        RESULTATS.mkdir(parents=True, exist_ok=True)
        (RESULTATS / "manifest_base.json").write_text(manifeste.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"{base}  empreinte {empreinte[:12]}  {comptes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
