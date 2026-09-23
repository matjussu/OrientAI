"""Alternance (étape B-1, champ `alternance` et fiches `parcoursup_apprentissage`).

Forme : `results/donnee_etape_b/CONTRACT.md`, section 4.

Fait mesuré qui fixe la forme (23/09/2026) : les 11 536 formations du jeu
`fr-esr-parcoursup-apprentissage` (session 2025) ont leurs propres `cod_aff_form`, et aucun n'est
dans le jeu principal `fr-esr-parcoursup` 2025. Une formation en apprentissage est donc une autre
formation Parcoursup, pas un attribut d'une fiche scolaire. D'où deux sorties :

- des fiches `source: "parcoursup_apprentissage"`, une par formation d'apprentissage des domaines
  de la démo (table de domaines de l'étape A) ;
- sur chaque fiche scolaire, le champ `alternance` : les formations d'apprentissage du même
  diplôme (même filière agrégée, même spécialité) au même lieu (même UAI ou même commune INSEE).

Le rattachement ne s'étend jamais à la région : « ce BTS existe en apprentissage à 300 km » n'est
pas une information sur la fiche.
"""
from __future__ import annotations

import re
from collections import defaultdict

from src.collect.communes import ReferentielCommunes
from src.collect.domaines import classer
from src.collect.parcoursup import _infer_statut
from src.collect.types_formation import decrire, niveau_vise
from src.collect.valeur_sourcee import Referentiel

SOURCE_ID = "parcoursup_apprentissage_2025"
MILLESIME = "session 2025"
RATTACHEMENT = "meme_diplome_meme_uai_ou_meme_commune"

# Domaines de la démo (table `data/reference/domaines_parcoursup.csv`) pour lesquels une fiche
# d'apprentissage est créée. Les autres formations d'apprentissage servent seulement au
# rattachement des fiches scolaires.
DOMAINES_DEMO = frozenset({"informatique", "cyber", "data_ia", "sante", "sciences_fondamentales"})

# Filière très agrégée du jeu apprentissage -> vocabulaire `fili_code` des fiches de l'étape A.
# Les autres filières du jeu (formation professionnelle, certificat de spécialisation, DEUST, DCG,
# EFTS...) n'ont pas d'équivalent exact : elles sont « Autre formation », comme à l'étape A.
FILI_APPRENTISSAGE = {"1_BTS": "BTS", "2_BUT": "BUT"}

_SUFFIXE = re.compile(r"\s*-\s*en apprentissage\s*$", re.IGNORECASE)


def _norme(texte: str | None) -> str:
    return " ".join(_SUFFIXE.sub("", texte or "").lower().split())


def cle_diplome(filiere_agregee: str | None, filiere_detaillee: str | None) -> tuple[str, str]:
    """Même diplôme = même filière agrégée (« BTS - Services ») et même spécialité, sans le
    suffixe « - en apprentissage » que le jeu apprentissage ajoute à la spécialité."""
    return _norme(filiere_agregee), _norme(filiere_detaillee)


def _entier(v) -> int | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _texte(v) -> str | None:
    s = " ".join(str(v).split()) if v is not None else ""
    return s or None


class Alternance:
    """`lignes` : lignes du CSV apprentissage session 2025 (dict par colonne, valeurs texte)."""

    def __init__(self, lignes: list[dict], communes: ReferentielCommunes, referentiel: Referentiel) -> None:
        self.ref = referentiel
        self.communes = communes
        self.lignes = [dict(ligne) for ligne in lignes]  # copies : les lignes reçues restent intactes
        self.par_diplome: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for ligne in self.lignes:
            commune = communes.resoudre(ligne.get("ville_etab"), ligne.get("dep"))
            ligne["_code_insee"] = commune.code_insee
            ligne["_ville"] = commune.ville
            self.par_diplome[cle_diplome(ligne.get("form_lib_voe_acc"), ligne.get("fil_lib_voe_acc"))].append(ligne)

    # ── champ `alternance` d'une fiche scolaire ─────────────────────────────────────────────
    def rattacher(self, fiche: dict) -> dict:
        cle = cle_diplome(fiche.get("form_lib_voe_acc"), fiche.get("filiere_detaillee"))
        if not all(cle):
            return self.ref.non_disponible(
                "filière ou spécialité de la formation absente : rattachement impossible",
                SOURCE_ID, MILLESIME, RATTACHEMENT,
            )
        uai, insee = fiche.get("cod_uai"), fiche.get("code_insee")
        formations = []
        for ligne in self.par_diplome.get(cle, []):
            if uai and ligne.get("cod_uai") == uai:
                par = "uai"
            elif insee and ligne.get("_code_insee") == insee:
                par = "commune"
            else:
                continue
            formations.append({
                "cod_aff_form": str(ligne["cod_aff_form"]),
                "etablissement": _texte(ligne.get("g_ea_lib_vx")),
                "ville": ligne.get("_ville"),
                "capacite": _entier(ligne.get("capa_fin")),
                "rattachee_par": par,
            })
        formations.sort(key=lambda f: (f["rattachee_par"] != "uai", f["cod_aff_form"]))
        valeur = {"existe_en_apprentissage": bool(formations), "formations": formations}
        return self.ref.disponible(valeur, SOURCE_ID, MILLESIME, RATTACHEMENT)

    # ── fiches des formations d'apprentissage ───────────────────────────────────────────────
    def fiches(self, regles: list) -> list[dict]:
        """Fiches `parcoursup_apprentissage` des domaines de la démo, dans l'ordre du jeu."""
        source, collecte = self.ref.source(SOURCE_ID)
        sortie = []
        for ligne in self.lignes:
            fili = FILI_APPRENTISSAGE.get(ligne.get("fili") or "", "Autre formation")
            nom = _texte(ligne.get("lib_for_voe_ins")) or ""
            filiere_detaillee = _texte(ligne.get("fil_lib_voe_acc"))
            intitule = " ".join(x for x in (nom, _texte(ligne.get("detail_forma"))) if x)
            classe = classer(regles, fili, ligne.get("form_lib_voe_acc"), intitule)
            if not classe or classe[0] not in DOMAINES_DEMO:
                continue
            type_formation = decrire(fili, nom, None, _SUFFIXE.sub("", filiere_detaillee or ""))
            niveau, niveau_origine = niveau_vise(fili, nom)
            commune = self.communes.resoudre(ligne.get("ville_etab"), ligne.get("dep"))
            sortie.append({
                "source": "parcoursup_apprentissage",
                "cod_aff_form": str(ligne["cod_aff_form"]),
                "cod_uai": _texte(ligne.get("cod_uai")),
                "fili_code": fili,
                "nom": nom,
                "detail": _texte(ligne.get("detail_forma")),
                "etablissement": _texte(ligne.get("g_ea_lib_vx")) or "",
                "statut": _infer_statut(ligne.get("contrat_etab")),
                "statut_detaille": _texte(ligne.get("contrat_etab")),
                "ville_source": _texte(ligne.get("ville_etab")),
                "ville": commune.ville,
                "code_insee": commune.code_insee,
                "arrondissement": commune.arrondissement,
                "code_insee_arrondissement": commune.code_insee_arrondissement,
                "code_departement": _texte(ligne.get("dep")),
                "departement": _texte(ligne.get("dep_lib")),
                "region": _texte(ligne.get("region_etab_aff")),
                "academie": _texte(ligne.get("acad_mies")),
                "form_lib_voe_acc": _texte(ligne.get("form_lib_voe_acc")),
                "filiere_detaillee": filiere_detaillee,
                "type_formation": type_formation.libelle if type_formation else None,
                "precision_formation": type_formation.precision if type_formation else None,
                "niveau": niveau,
                "niveau_origine": niveau_origine,
                "phase": "initial",
                "domaine": classe[0],
                "domaine_regle": classe[1],
                "selectivite_code": "formation sélective" if str(ligne.get("select_form")).lower() == "true"
                else "formation non sélective",
                "lien_form_psup": _texte(ligne.get("lien_form_psup")),
                # Absent du jeu apprentissage, jamais recalculé (propositions / candidats n'est pas
                # un taux d'accès : définition officielle à l'étape A).
                "taux_acces_parcoursup_2025": None,
                "nombre_places": _entier(ligne.get("capa_fin")),
                "apprentissage": {
                    "session": 2025,
                    "capacite": _entier(ligne.get("capa_fin")),
                    "candidats": _entier(ligne.get("voe_tot")),
                    "propositions": _entier(ligne.get("prop_tot")),
                    "voeux_recherche_contrat": _entier(ligne.get("nb_rech_con")),
                    "refus_apres_examen": _entier(ligne.get("nb_ref_classe")),
                    "refus_faute_de_place": _entier(ligne.get("nb_ref_place")),
                },
                "provenance": {"apprentissage": SOURCE_ID},
                "collected_at": {"parcoursup_apprentissage": collecte},
                "source_detail": source,
                "retrieval_eligible": True,
                "url_canonical": _texte(ligne.get("lien_form_psup")),
                "url_type": "direct_parcoursup" if ligne.get("lien_form_psup") else None,
            })
        return sortie
