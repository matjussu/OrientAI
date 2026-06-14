"""Dérivation déterministe de champs corpus — type_diplome + région (Phase 1a fill).

Ordre 2026-06-14-1230-claudette-orientai-data-phase1a-fill-typage-region.

Principe : PRÉCISION > RAPPEL. On ne remplit un champ que sur un signal ancré
certain ; au moindre doute, VIDE. Une fiche mal typée dégrade le modèle plus
qu'une fiche vide (le refus honnête repose sur des null explicites).

Câblé dans run_merge_v3 (après reclassify_social_health) -> reproductible à
chaque régénération du corpus, comme le fix ROME J11 (#146).

Deux passes :

1. derive_type_diplome : monmaster -> "Master" (100 % bac+5 vérifié) ;
   parcoursup -> mapping du champ STRUCTURÉ `fili_code` (BTS/BUT/Licence/CPGE/
   Ecole d'Ingénieur/IFSI). Les codes ambigus (Autre formation, EFTS, Ecole de
   Commerce, PASS) restent VIDE. Le champ structuré Parcoursup est bien plus
   fiable qu'un regex sur l'intitulé : ex. le piège "DE" (Diplôme d'État) qui
   matche la préposition française "de" dans 31 % des intitulés.

2. geocode_region : departement -> région, APPRIS du corpus (un departement qui
   ne mappe qu'à UNE région observée) + supplément overseas pour les COM
   (Polynésie...) jamais labellisées ailleurs. Les fiches NATIONALES
   (RNCP/ONISEP/ROME) n'ont pas de departement -> restent SANS région : c'est
   correct sémantiquement (une certification nationale n'a pas de région), PAS
   un trou de données. On ne fabrique jamais une région.
"""
from __future__ import annotations


# fili_code (champ structuré Parcoursup) -> type_diplome canonique.
# Seuls les codes NON AMBIGUS sont mappés. Absent de la table = laissé vide.
TYPE_FROM_FILI_CODE: dict[str, str] = {
    "BTS": "BTS",
    "BUT": "BUT",
    "Licence": "Licence",
    "Licence_Las": "Licence",            # L.AS = licence option accès santé
    "CPGE": "CPGE",
    "Ecole d'Ingénieur": "Diplôme d'ingénieur",
    "IFSI": "Diplôme d'État infirmier",  # institut de formation en soins infirmiers
    # Volontairement NON mappés (ambigus -> vide) : "Autre formation",
    # "EFTS" (DE travail social multiples : DEASS/DEES/DEEJE...), "Ecole de
    # Commerce" (bachelor/PGE/master indistincts), "PASS" (année d'accès santé,
    # pas un diplôme).
}

# Supplément overseas : COM qui se nomment elles-mêmes comme région et ne sont
# jamais présentes avec une `region` dans le corpus (donc absentes de la map
# apprise). Mapping administratif sûr.
_OVERSEAS_DEPARTEMENT_TO_REGION: dict[str, str] = {
    "Polynésie française": "Polynésie française",
    "Nouvelle-Calédonie": "Nouvelle-Calédonie",
    "Saint-Pierre-et-Miquelon": "Saint-Pierre-et-Miquelon",
    "Wallis-et-Futuna": "Wallis-et-Futuna",
    "Saint-Martin": "Saint-Martin",
    "Saint-Barthélemy": "Saint-Barthélemy",
}


def _nonempty(v) -> bool:
    return bool(v and str(v).strip())


def derive_type_diplome(fiches: list[dict]) -> list[dict]:
    """Remplit type_diplome (vide uniquement) pour parcoursup + monmaster.

    Mutates in place et retourne la liste (convention reclassify_social_health).
    N'écrase JAMAIS une valeur existante.
    """
    for f in fiches:
        if not isinstance(f, dict) or _nonempty(f.get("type_diplome")):
            continue
        source = f.get("source")
        if source == "monmaster":
            f["type_diplome"] = "Master"
        elif source == "parcoursup":
            fili = f.get("fili_code")
            mapped = TYPE_FROM_FILI_CODE.get(fili)
            if fili == "Ecole d'Ingénieur":
                # Ce code conflate le cycle prépa intégré (bac+1-3) et le cycle
                # ingénieur (bac+5). Seul le bac+5 délivre le diplôme d'ingénieur ;
                # un "Formation Bac + 3" est une entrée de cycle prépa -> vide.
                mapped = mapped if f.get("niveau") == "bac+5" else None
            elif mapped == "Licence":
                nom = (f.get("nom") or "").lower()
                if "licence pro" in nom or "licence professionnelle" in nom:
                    mapped = "Licence professionnelle"
            if mapped:
                f["type_diplome"] = mapped
    return fiches


# Valeur À PART (ordre 1305 Option A, GO Matteo) : ne se mélange pas aux diplômes
# formels (BTS/BUT/Licence/Master...) pour ne pas polluer le filtrage par diplôme.
RNCP_PROFESSIONAL_TITLE = "Titre professionnel (RNCP)"


def derive_rncp_professional_title(fiches: list[dict]) -> list[dict]:
    """Type les certifications RNCP "Enregistrement sur demande" (vide uniquement).

    Signal AUTORITAIRE : `type_enregistrement == "Enregistrement sur demande"`
    (certifs professionnelles : CQP, titres pros — pas de diplôme formel). Les
    certifs "Enregistrement de droit" sans abrégé capturé (37 cas) NE sont PAS
    touchées : ce sont des diplômes formels, on les laisse vides plutôt que de les
    mal-étiqueter. N'écrase jamais une valeur existante.
    """
    for f in fiches:
        if not isinstance(f, dict) or _nonempty(f.get("type_diplome")):
            continue
        if (f.get("source") == "rncp"
                and f.get("type_enregistrement") == "Enregistrement sur demande"):
            f["type_diplome"] = RNCP_PROFESSIONAL_TITLE
    return fiches


# lycée_pro : les stats d'emploi vivent au top-level (_moyen) et NON dans un bloc
# insertion_pro -> invisibles à fact_card. On les remappe vers les noms de champs
# que fact_card lit (taux_emploi_12m/24m, part_poursuite_etudes). Valeurs = fractions
# [0,1] (format attendu par _safe_pct/_safe_float). Source étiquetée pour l'attribution.
_LYCEEPRO_INSERTION_MAP = {
    "taux_emploi_12m_moyen": "taux_emploi_12m",
    "taux_emploi_24m_moyen": "taux_emploi_24m",
    "taux_poursuite_etudes_moyen": "part_poursuite_etudes",
}


def derive_lyceepro_insertion(fiches: list[dict]) -> list[dict]:
    """Construit un bloc insertion_pro pour les fiches lycée_pro (vide uniquement).

    Les stats d'emploi étaient présentes mais hors bloc structuré -> non citables par
    fact_card. N'écrase jamais un insertion_pro existant. Ne crée le bloc que si au
    moins une stat est présente (sinon pas de bloc tout-à-null).
    """
    for f in fiches:
        if not isinstance(f, dict) or f.get("source") != "inserjeunes_lycee_pro":
            continue
        if f.get("insertion_pro"):
            continue
        block = {}
        for src_key, ip_key in _LYCEEPRO_INSERTION_MAP.items():
            v = f.get(src_key)
            if v is not None:
                block[ip_key] = v
        if block:
            block["source"] = "inserjeunes_lycee_pro"
            f["insertion_pro"] = block
    return fiches


# niveau_certification ONISEP -> niveau. Échelle INVERSÉE non-RNCP, mapping APPRIS
# du corpus (fiches ayant niveau ET niveau_certification, ≥98% purity, ≥360 ex) :
#   '1'->bac+5 (100%/1422), '2'->bac+3 (99%/787), '3'->bac+2 (98%/362).
# Exclus VOLONTAIREMENT : '0' (ambigu, 38% purity), '4' (3 ex, insuffisant),
# '5' (0 ex labellisé) -> restent vides (précision > rappel).
_ONISEP_CERT_TO_NIVEAU = {"1": "bac+5", "2": "bac+3", "3": "bac+2"}


def derive_onisep_niveau(fiches: list[dict]) -> list[dict]:
    """Dérive niveau depuis niveau_certification pour les fiches onisep (vide uniquement)."""
    for f in fiches:
        if not isinstance(f, dict) or f.get("source") != "onisep":
            continue
        if _nonempty(f.get("niveau")):
            continue
        niv = _ONISEP_CERT_TO_NIVEAU.get(str(f.get("niveau_certification") or "").strip())
        if niv:
            f["niveau"] = niv
    return fiches


def _build_departement_region_map(fiches: list[dict]) -> dict[str, str]:
    """Apprend departement -> région depuis les fiches qui ont LES DEUX.

    Ne garde QUE les départements NON AMBIGUS (une seule région observée).
    Retourne {departement: region_display} en conservant le format d'affichage
    exact du corpus (pas de normalisation).
    """
    observed: dict[str, set[str]] = {}
    for f in fiches:
        if not isinstance(f, dict):
            continue
        dep, reg = f.get("departement"), f.get("region")
        if _nonempty(dep) and _nonempty(reg):
            observed.setdefault(str(dep).strip(), set()).add(str(reg).strip())
    return {dep: next(iter(regs)) for dep, regs in observed.items() if len(regs) == 1}


def geocode_region(fiches: list[dict]) -> list[dict]:
    """Remplit region (vide uniquement) depuis le departement.

    Source de vérité : map apprise du corpus (departement non ambigu -> région)
    + supplément overseas. Aucune fabrication : sans departement résoluble, vide.
    """
    learned = _build_departement_region_map(fiches)
    for f in fiches:
        if not isinstance(f, dict) or _nonempty(f.get("region")):
            continue
        dep = f.get("departement")
        if not _nonempty(dep):
            continue
        dep = str(dep).strip()
        region = learned.get(dep) or _OVERSEAS_DEPARTEMENT_TO_REGION.get(dep)
        if region:
            f["region"] = region
    return fiches
