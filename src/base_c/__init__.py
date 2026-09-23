"""Base structurée de l'étape C : schéma, distance et normalisations partagés.

Contrat : `results/donnee_etape_c/CONTRACT.md` (v1.1). La base est construite par
`src.collect.base_etape_c`, interrogée par `src.base_c.outils`, auditée par
`src.eval.audit_base_c`.
"""
from __future__ import annotations

import math
import re

# Rayon terrestre moyen utilisé par la distance haversine (contrat §5).
RAYON_TERRE_KM = 6371.0

# Espaces d'identifiants convenus avec Jarvis (message gate-format-fige du 23/09/2026).
ESPACES = ("psup", "psup_app", "mm")

# Session d'une valeur qui n'est pas une observation Parcoursup ou MonMaster (coût, santé...).
SANS_SESSION = "-"

# Noms officiels des régions par code INSEE (Code officiel géographique 2025, liste des
# 18 régions). Recopiés ici parce que le COG verrouillé ne porte que les codes ; l'audit
# vérifie qu'ils concordent avec le libellé Parcoursup de chaque fiche.
REGIONS = {
    "01": "Guadeloupe", "02": "Martinique", "03": "Guyane", "04": "La Réunion", "06": "Mayotte",
    "11": "Île-de-France", "24": "Centre-Val de Loire", "27": "Bourgogne-Franche-Comté",
    "28": "Normandie", "32": "Hauts-de-France", "44": "Grand Est", "52": "Pays de la Loire",
    "53": "Bretagne", "75": "Nouvelle-Aquitaine", "76": "Occitanie",
    "84": "Auvergne-Rhône-Alpes", "93": "Provence-Alpes-Côte d'Azur", "94": "Corse",
}
# Variantes de libellés de région trouvées dans le corpus B-2 (mesure du 23/09/2026 : 291
# « Ile-de-France », 87 « Pays-de-la-Loire », 64 « Nouvelle Aquitaine », 43 « Grand-Est »,
# 24 « Centre », 23 « Réunion »). Servent seulement quand la commune n'a pas de code INSEE.
ALIAS_REGIONS = {
    "Ile-de-France": "Île-de-France", "Pays-de-la-Loire": "Pays de la Loire",
    "Nouvelle Aquitaine": "Nouvelle-Aquitaine", "Grand-Est": "Grand Est",
    "Centre": "Centre-Val de Loire", "Réunion": "La Réunion",
}

SCHEMA = """
CREATE TABLE source (
    source_id TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    url TEXT,
    licence TEXT,
    collecte TEXT,
    sha256 TEXT,
    lignes INTEGER
);
CREATE TABLE champ (
    champ TEXT PRIMARY KEY,
    espaces TEXT NOT NULL,
    types TEXT NOT NULL,
    sessions TEXT NOT NULL,
    parent TEXT NOT NULL,
    unite TEXT NOT NULL,
    type_valeur TEXT NOT NULL,
    portee TEXT NOT NULL,
    nom_officiel TEXT NOT NULL,
    chemin_corpus TEXT NOT NULL,
    libelle TEXT NOT NULL,
    definition TEXT NOT NULL,
    ne_dit_pas TEXT NOT NULL
);
CREATE TABLE formation (
    id TEXT PRIMARY KEY,
    espace TEXT NOT NULL CHECK (espace IN ('psup', 'psup_app', 'mm')),
    identifiant_source TEXT NOT NULL,
    intitule TEXT NOT NULL,
    etablissement TEXT,
    uai TEXT,
    statut TEXT,
    statut_detaille TEXT,
    type TEXT NOT NULL,
    type_libelle TEXT,
    filiere TEXT,
    specialite TEXT,
    apprentissage INTEGER NOT NULL CHECK (apprentissage IN (0, 1)),
    selectivite TEXT,
    domaine TEXT NOT NULL,
    domaine_regle TEXT,
    region_academique TEXT,
    lien_officiel TEXT,
    derniere_session TEXT NOT NULL
);
CREATE TABLE lieu (
    id TEXT NOT NULL REFERENCES formation(id),
    rang INTEGER NOT NULL,
    libelle TEXT,
    commune TEXT,
    code_insee TEXT,
    arrondissement TEXT,
    code_departement TEXT,
    departement TEXT,
    region TEXT,
    academie TEXT,
    lat REAL,
    lon REAL,
    precision_geo TEXT NOT NULL CHECK (precision_geo IN ('formation', 'commune', 'non_disponible')),
    source_id TEXT REFERENCES source(source_id),
    PRIMARY KEY (id, rang),
    CHECK ((precision_geo = 'non_disponible') = (lat IS NULL)),
    CHECK ((lat IS NULL) = (lon IS NULL))
);
CREATE TABLE valeur (
    id TEXT NOT NULL REFERENCES formation(id),
    champ TEXT NOT NULL REFERENCES champ(champ),
    session TEXT NOT NULL,
    valeur_num NUMERIC,
    valeur_texte TEXT,
    unite TEXT,
    statut TEXT NOT NULL CHECK (statut IN ('disponible', 'non_disponible')),
    raison TEXT,
    source_id TEXT REFERENCES source(source_id),
    millesime TEXT,
    identifiant_source TEXT,
    rattachement TEXT,
    portee TEXT NOT NULL CHECK (portee IN ('formation', 'etablissement', 'universite', 'nationale', 'regionale')),
    PRIMARY KEY (id, champ, session),
    CHECK ((statut = 'disponible') = (valeur_num IS NOT NULL OR valeur_texte IS NOT NULL)),
    CHECK (statut = 'disponible' OR (raison IS NOT NULL AND raison <> '')),
    CHECK (statut = 'non_disponible' OR source_id IS NOT NULL),
    CHECK (source_id IS NOT NULL OR identifiant_source IS NULL)
);
CREATE TABLE insertion_ligne (
    id TEXT NOT NULL REFERENCES formation(id),
    rang INTEGER NOT NULL,
    dispositif TEXT,
    promotion TEXT,
    regime TEXT,
    granularite TEXT,
    etablissement TEXT,
    diplome TEXT,
    effectif_sortants NUMERIC,
    taux_emploi_6m NUMERIC,
    taux_emploi_12m NUMERIC,
    taux_emploi_18m NUMERIC,
    taux_emploi_24m NUMERIC,
    taux_emploi_30m NUMERIC,
    taux_poursuite_etudes NUMERIC,
    non_diffuse TEXT,
    perimetre_json TEXT,
    source_id TEXT NOT NULL REFERENCES source(source_id),
    PRIMARY KEY (id, rang)
);
CREATE TABLE alternance_lien (
    id TEXT NOT NULL REFERENCES formation(id),
    id_apprentissage TEXT NOT NULL,
    etablissement TEXT,
    commune TEXT,
    capacite NUMERIC,
    cfa_partenaire TEXT,
    precision TEXT,
    rattachee_par TEXT,
    PRIMARY KEY (id, id_apprentissage)
);
CREATE TABLE concept (
    concept_id TEXT PRIMARY KEY,
    titre TEXT NOT NULL,
    texte TEXT NOT NULL,
    statut_reglementaire TEXT,
    verifie_le TEXT,
    sources_json TEXT NOT NULL
);
CREATE TABLE commune (
    code_insee TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    cle TEXT NOT NULL,
    code_departement TEXT,
    region TEXT,
    lat REAL,
    lon REAL
);
CREATE TABLE meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
CREATE INDEX valeur_champ ON valeur(champ, session);
CREATE INDEX lieu_insee ON lieu(code_insee);
CREATE INDEX commune_cle ON commune(cle);
"""

# Clés primaires par table : ordre d'insertion et empreinte canonique.
CLES = {
    "source": ("source_id",), "champ": ("champ",), "formation": ("id",), "lieu": ("id", "rang"),
    "valeur": ("id", "champ", "session"), "insertion_ligne": ("id", "rang"),
    "alternance_lien": ("id", "id_apprentissage"), "concept": ("concept_id",),
    "commune": ("code_insee",), "meta": ("cle",),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance à vol d'oiseau entre deux points, en kilomètres (sphère de rayon 6 371 km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAYON_TERRE_KM * math.asin(math.sqrt(min(1.0, h)))


_DEP_TROIS_CHIFFRES = re.compile(r"0(\d\d|2[AB])")


def normaliser_departement(code: str | None) -> str | None:
    """Code département au format du COG : « 044 » -> « 44 », « 1 » -> « 01 », « 974 » inchangé.

    Le jeu Parcoursup apprentissage écrit la métropole sur trois chiffres (mesure du 23/09/2026 :
    442 fiches d'apprentissage sur 526 sans code INSEE à cause de cette forme).
    """
    if code is None:
        return None
    d = str(code).strip()
    if _DEP_TROIS_CHIFFRES.fullmatch(d):
        return d[1:]
    if d.isdigit() and len(d) == 1:
        return d.zfill(2)
    return d or None
