import re
from pathlib import Path
import pandas as pd
from src.collect.niveau import infer_niveau


DOMAIN_KEYWORDS = {
    "cyber": [
        "cyber",
        "cybersécurité", "cyber sécurité", "cyber-sécurité", "cybersecurity",
        "sécurité informatique", "sécurité des systèmes", "sécurité numérique",
        r"\bSSI\b", r"\bSecNumEdu\b",
    ],
    "data_ia": [
        "intelligence artificielle", "data science", "données", "data",
        "machine learning", "apprentissage automatique", "big data",
        r"\bIA\b", "science des données", "data analyst", "data engineer",
    ],
    # Vague santé — filières médicales et paramédicales
    # Mots-clés choisis pour capturer les formations santé spécifiques sans
    # faux positifs trop larges. "Santé" seul pourrait capturer "santé
    # environnementale" ou "santé publique" en fac de sciences — volontaire
    # (ces parcours sont légitimement dans le scope orientation lycéen).
    "sante": [
        # Études médicales (PASS / L.AS / médecine / maïeutique / dentaire / pharmacie)
        r"\bPASS\b", r"\bL\.?\s?AS\b",
        "médecine", "médical", "médicale",
        "maïeutique", "sage-femme", "sage femme",
        "odontologie", "dentaire",
        "pharmacie", "pharmac", "pharmaceutique",
        # Paramédical & soins
        "infirmier", "infirmière", r"\bIFSI\b", r"\bIFPS\b",
        "aide-soignant", "aide soignant",
        "kinésithér", r"\bkiné\b", r"\bDEMK\b",
        "ergothérap",
        "orthophon", "orthoptie", "orthopt",
        "psychomotricien", "psychomotricité",
        "audioprothèse", "audiologie",
        "opticien", "optique-lunetterie", "optométrie",
        "podolog", "pédicurie",
        "diététique", "diététicien", "nutrition",
        r"manipulateur\s+(?:en\s+|d['']\s*)?radio", "imagerie médicale",
        "puéricult",
        # Autres métiers santé & paramed
        "ostéopath",
        "santé publique",
        "biologie médicale", "laboratoire médical",
    ],
    # Travail social (NSF 332) — DISTINCT de la santé. Fix order 2026-06-11 :
    # CESF / AES / éducateurs spécialisés -> domaine "social" (débouchés ROME K*,
    # PAS les J11xx médicaux). Mots-clés professionnels spécifiques : on évite
    # "social" nu / "sciences sociales" (disciplines, classées sciences_humaines).
    "social": [
        r"travail\s+social", r"travailleur\s+social",
        r"économie\s+sociale\s+et\s+familiale", r"\bCESF\b",
        r"éducateur\s+spécialisé", r"éducateur\s+de\s+jeunes\s+enfants",
        r"éducateur\s+technique\s+spécialisé", r"moniteur[-\s]éducateur",
        r"accompagnant\s+éducatif\s+et\s+social", r"\bAES\b",
        r"assistant\w*\s+(?:de\s+)?service\s+social",
        r"intervention\s+sociale", r"\bTISF\b",
        r"médiateur\s+social", r"médiation\s+sociale",
        r"carrières\s+sociales", r"secteur\s+social",
        # Petite enfance + insertion (résidu audit #131). "sante" est testé AVANT
        # "social" (ordre EXTENDED_DOMAINS first-wins) -> "auxiliaire de
        # puériculture" matche puéricult en santé d'abord et n'est pas capté ici.
        r"petite\s+enfance", r"transition\s+professionnelle",
    ],
    # === Extension scope élargi (ADR-041, 2026-04-23) — tous secteurs 17-25 ans ===
    "droit": [
        "droit", r"\bjurid", "science politique", "sciences politiques",
        r"\bSciences?\s+Po\b", "notariat", "administration publique",
    ],
    "eco_gestion": [
        "économie", "économique", "gestion", "finance", "comptabilité",
        "banque", "assurance", "management", "commerce", "marketing",
        "ressources humaines", r"\bRH\b", "audit", "contrôle de gestion",
        "entrepreneuriat", "business",
    ],
    "sciences_humaines": [
        "sociologie", "psychologie", "anthropologie", "ethnologie",
        "histoire", "géographie", "philosophie", "archéologie",
        "sciences sociales", "sciences humaines",
    ],
    "langues": [
        "langues", "langue", r"\bLLCE\b", r"\bLEA\b",
        "anglais", "espagnol", "allemand", "italien", "chinois", "arabe",
        "linguistique", "interprétariat", "traduction",
        "français langue étrangère",
    ],
    "lettres_arts": [
        "lettres", "littérature", "beaux-arts", "arts plastiques",
        "arts appliqués", "design", "architecture", "musique",
        "théâtre", "cinéma", "audiovisuel", "patrimoine",
        "arts du spectacle", "création", "danse",
    ],
    "sport": [
        r"\bSTAPS\b", "sport", "sportif", "sportive",
        "éducation physique", "entraînement sportif",
        "management du sport",
    ],
    "sciences_fondamentales": [
        "mathématique", "physique", "chimie", "biologie", "géologie",
        "sciences de la terre", "sciences de la vie", "astronomie",
        r"\bSVT\b", "écologie", "environnement", "biodiversité",
    ],
    "ingenierie_industrielle": [
        "ingénieur", "ingénierie", "mécanique", "électronique", "électrotechnique",
        "génie civil", "génie industriel", "génie mécanique", "génie électrique",
        "matériaux", "aéronautique", "automobile", "robotique",
        "industrie", "BTP", r"\bCPI\b",
    ],
    "communication": [
        "communication", "journalisme", "médias", "relations publiques",
        "publicité", "marketing digital", "webmarketing",
    ],
    "education": [
        "enseignement", "éducation", r"\bMEEF\b", "professeur des écoles",
        "sciences de l'éducation", "formation des enseignants",
    ],
    "agriculture": [
        "agriculture", "agronomie", "agroalimentaire", "viticulture",
        "horticulture", "forêt", "élevage", "œnologie",
    ],
    "tourisme_hotellerie": [
        "tourisme", "hôtellerie", "restauration", "cuisine",
        "gastronomie", "loisirs",
    ],
}

# Ensembles de domaines — utilisés par `collect_parcoursup_fiches(domains=...)`.
# Les 3 domaines legacy restent le défaut pour backward-compat tests.
LEGACY_DOMAINS = ["cyber", "data_ia", "sante"]
EXTENDED_DOMAINS = list(DOMAIN_KEYWORDS.keys())  # 15 domaines post-ADR-041

# Resolved column names from the real Parcoursup 2025 export
# (inspected by controller on 2026-04-10; Parcoursup open data has no RNCP column)
FORMATION_COLUMN = "lib_for_voe_ins"
ETABLISSEMENT_COLUMN = "g_ea_lib_vx"
COD_UAI_COLUMN = "cod_uai"  # official MEN establishment id (joins InserSup etc.)
VILLE_COLUMN = "ville_etab"
TAUX_ACCES_COLUMN = "taux_acces_ens"
PLACES_COLUMN = "capa_fin"
CONTRAT_COLUMN = "contrat_etab"
REGION_COLUMN = "region_etab_aff"
DEPARTEMENT_COLUMN = "dep_lib"
DETAIL_COLUMN = "detail_forma"

# Mention-level breakdown of admitted candidates (useful for realism scoring)
PCT_TB_COLUMN = "pct_tb"               # % admis avec mention Très Bien
PCT_B_COLUMN = "pct_b"                 # % admis avec mention Bien
PCT_AB_COLUMN = "pct_ab"               # % admis avec mention Assez Bien
PCT_SANSMENTION_COLUMN = "pct_sansmention"

# Bac-type breakdown of admitted candidates (profile signal)
PCT_BG_COLUMN = "pct_bg"               # % admis bac général
PCT_BT_COLUMN = "pct_bt"               # % admis bac techno
PCT_BP_COLUMN = "pct_bp"               # % admis bac pro

# Access share by bac type (realism: can someone from bac techno get in?)
PART_ACCES_GEN_COLUMN = "part_acces_gen"
PART_ACCES_TEC_COLUMN = "part_acces_tec"
PART_ACCES_PRO_COLUMN = "part_acces_pro"

PCT_BOURS_COLUMN = "pct_bours"         # % boursiers (social mix)

# Vague A — extensions (data foundation)
COD_AFF_FORM_COLUMN = "cod_aff_form"       # unique Parcoursup id per formation×etab
LIEN_FORM_PSUP_COLUMN = "lien_form_psup"   # official Parcoursup URL
VOE_TOT_COLUMN = "voe_tot"                 # total voeux formulés
NB_VOE_PP_COLUMN = "nb_voe_pp"             # voeux phase principale
NB_CLA_PP_COLUMN = "nb_cla_pp"             # classes phase principale (ranked)
ACC_INTERNAT_COLUMN = "acc_internat"       # count of internat accepted — 0 or NaN = pas d'internat
PCT_F_COLUMN = "pct_f"                     # % women admitted
PCT_NEOBAC_COLUMN = "pct_neobac"           # % néobacheliers admitted
PCT_ACA_ORIG_IDF_COLUMN = "pct_aca_orig_idf"   # % admis originaires IDF

# === ADR-041 extension champs P0 (2026-04-23) — gap analysis 75% champs non-utilisés ===
PROP_TOT_COLUMN = "prop_tot"               # propositions totales envoyées (≠ acceptés)
PCT_ACC_DEBUTPP_COLUMN = "pct_acc_debutpp" # % acceptés dès début phase principale (sélectivité timing)
FILI_COLUMN = "fili"                       # code filière officiel Parcoursup (classification structurée)
LIB_GRP1_COLUMN = "lib_grp1"               # groupe de formations — famille cohérente
SELECT_FORM_COLUMN = "select_form"         # code sélectivité formation officiel Parcoursup
FORM_LIB_VOE_ACC_COLUMN = "form_lib_voe_acc"  # libellé type+champ ("BTS - Services", "D.E secteur social")


# === C1 (2026-06-09) — cascade domaine pour ré-ingestion élargie ===
# Mapping form_lib_voe_acc -> domaine thématique (validé Jarvis). Fallback de la
# cascade quand le nom ne matche aucun keyword. Tout libellé ABSENT de cette
# table (type trop large type "BTS - Services", multi-domaine type
# "Droit-économie-gestion") -> "autre" : mieux vaut "autre" qu'un faux domaine.
# Clés normalisées (whitespace collapsé + lowercase) — les données réelles ont
# des doubles espaces sur certains libellés.
FORM_LIB_VOE_ACC_TO_DOMAINE = {
    # — thématique clair —
    "formations des écoles d'ingénieurs": "ingenierie_industrielle",
    "c.m.i - cursus master en ingénierie": "ingenierie_industrielle",
    "formation des écoles de commerce et de management": "eco_gestion",
    "classe préparatoire économique et commerciale": "eco_gestion",
    "licence - sciences humaines et sociales": "sciences_humaines",
    "lp - sciences humaines et sociales": "sciences_humaines",
    "sciences politiques": "sciences_humaines",
    "d.e secteur social": "social",   # Fix order 2026-06-11 : travail social ≠ santé
    "d.e secteur sanitaire": "sante",
    "bts - agricole": "agriculture",
    "licence - staps": "sport",
    "bpjeps": "sport",
    "dn made": "lettres_arts",
    "diplôme national d'art": "lettres_arts",
    "formation des écoles supérieures d'art": "lettres_arts",
    "formation des écoles supérieures de cuisine": "tourisme_hotellerie",
    # — jugement (validé Jarvis) —
    "licence - sciences - technologies - santé": "sciences_fondamentales",
    "lp - sciences - technologies - santé": "sciences_fondamentales",
    "cupge - sciences, technologie, santé": "sciences_fondamentales",
    "classe préparatoire scientifique": "sciences_fondamentales",
    "licence - arts-lettres-langues": "lettres_arts",
    "classe préparatoire littéraire": "lettres_arts",
    "formations des écoles vétérinaires": "sante",
}


def _norm_ws(s) -> str:
    """Collapse whitespace + lowercase pour le lookup du mapping form_lib_voe_acc."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _domaine_from_name(nom) -> str | None:
    """Step 1 cascade : 1er domaine EXTENDED dont un keyword matche le NOM.

    Même logique regex que `filter_domain` (case-insensitive, alternation des
    keywords), itérée dans l'ordre EXTENDED_DOMAINS = first-wins (cohérent avec
    la classification des fiches déjà ingérées)."""
    n = str(nom or "")
    if not n:
        return None
    for domain in EXTENDED_DOMAINS:
        pattern = "|".join(DOMAIN_KEYWORDS[domain])
        if re.search(pattern, n, flags=re.IGNORECASE):
            return domain
    return None


def domaine_cascade(row: pd.Series) -> str:
    """Assigne un domaine à une formation Parcoursup hors taxonomie keyword (C1).

    Cascade :
      1. keyword sur le NOM (filter_domain par-ligne) -> domaine thématique ;
      2. sinon mapping form_lib_voe_acc -> domaine thématique (validé Jarvis) ;
      3. sinon "autre" (mieux vaut "autre" qu'un faux domaine).
    """
    d = _domaine_from_name(row.get(FORMATION_COLUMN))
    if d:
        return d
    d = FORM_LIB_VOE_ACC_TO_DOMAINE.get(_norm_ws(row.get(FORM_LIB_VOE_ACC_COLUMN)))
    if d:
        return d
    return "autre"


def load_parcoursup(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(Path(path), sep=";", encoding="utf-8", low_memory=False)


def filter_domain(df: pd.DataFrame, domain: str, name_column: str) -> pd.DataFrame:
    if domain not in DOMAIN_KEYWORDS:
        raise ValueError(f"Unknown domain: {domain}")
    pattern = "|".join(DOMAIN_KEYWORDS[domain])
    mask = df[name_column].fillna("").str.contains(pattern, case=False, regex=True)
    return df[mask].copy()


def _safe_float(val) -> float | None:
    try:
        f = float(val)
    except (ValueError, TypeError):
        return None
    # NaN / inf : cellules CSV vides lues par pandas -> ne PAS laisser fuiter
    # (JSON invalide + violerait la borne [0,100] du contrat data / GE).
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _infer_statut(contrat: str) -> str:
    if not isinstance(contrat, str):
        return "Inconnu"
    c = contrat.lower()
    if c.startswith("public"):
        return "Public"
    if "privé" in c or "prive" in c:
        return "Privé"
    return "Inconnu"


def _internat_disponible(row: pd.Series) -> bool | None:
    """Return True if at least one candidate was accepted with internat, False if
    explicitly 0, None if not renseigné. Source: acc_internat (count, not %).
    """
    val = _safe_int(row.get(ACC_INTERNAT_COLUMN))
    if val is None:
        return None
    return val > 0


def _clean_str(val) -> str | None:
    """Normalize a pandas-read field: '', 'nan', NaN → None; else stripped str.

    pandas returns NaN for missing CSV cells, which str() turns into 'nan'
    (the literal three-letter string). That leaks into the generator context
    as 'Détail: nan'. This helper neutralises the leak.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def _infer_phase(niveau: str | None) -> str:
    """Infère la phase ADR-039 depuis le niveau.

    Parcoursup couvre essentiellement post-bac (phase initial) mais expose
    parfois des masters/bac+5 qui tombent en phase master.
    """
    if niveau in ("bac+5", "bac+8"):
        return "master"
    return "initial"


def extract_fiche(row: pd.Series) -> dict:
    nom = _clean_str(row.get(FORMATION_COLUMN)) or ""
    cod_aff_form = _clean_str(row.get(COD_AFF_FORM_COLUMN))
    cod_uai = _clean_str(row.get(COD_UAI_COLUMN))
    lien_psup = _clean_str(row.get(LIEN_FORM_PSUP_COLUMN))
    taux_acces = _safe_float(row.get(TAUX_ACCES_COLUMN))
    nombre_places = _safe_int(row.get(PLACES_COLUMN))
    niveau = infer_niveau(nom)

    return {
        "source": "parcoursup",
        "phase": _infer_phase(niveau),  # ADR-039 : phase explicite (initial/master)
        "nom": nom,
        "etablissement": _clean_str(row.get(ETABLISSEMENT_COLUMN)) or "",
        "ville": _clean_str(row.get(VILLE_COLUMN)) or "",
        "region": _clean_str(row.get(REGION_COLUMN)),
        "departement": _clean_str(row.get(DEPARTEMENT_COLUMN)),
        "rncp": None,
        # Official MEN id of the establishment — join key for InserSup + other
        # open-data datasets (ESR effectifs, insertion pro, etc.)
        "cod_uai": cod_uai,
        # Vague A — unique Parcoursup id + official link (for citation)
        "cod_aff_form": cod_aff_form,
        "lien_form_psup": lien_psup,
        # Legacy fields kept for backward compat (index FAISS + tests existants)
        "taux_acces_parcoursup_2025": taux_acces,
        "nombre_places": nombre_places,
        "statut": _infer_statut(row.get(CONTRAT_COLUMN, "")),
        "niveau": niveau,
        # Enriched fields for realism & discovery scoring
        "detail": _clean_str(row.get(DETAIL_COLUMN)),
        # Vague A — structured admission block (taux/places + volumes + internat)
        "admission": {
            "session": 2025,
            "taux_acces": taux_acces,
            "places": nombre_places,
            "volumes": {
                "voeux_totaux": _safe_int(row.get(VOE_TOT_COLUMN)),
                "voeux_phase_principale": _safe_int(row.get(NB_VOE_PP_COLUMN)),
                "classes_phase_principale": _safe_int(row.get(NB_CLA_PP_COLUMN)),
            },
            "internat_disponible": _internat_disponible(row),
        },
        "profil_admis": {
            "mentions_pct": {
                "tb": _safe_float(row.get(PCT_TB_COLUMN)),
                "b": _safe_float(row.get(PCT_B_COLUMN)),
                "ab": _safe_float(row.get(PCT_AB_COLUMN)),
                "sans": _safe_float(row.get(PCT_SANSMENTION_COLUMN)),
            },
            "bac_type_pct": {
                "general": _safe_float(row.get(PCT_BG_COLUMN)),
                "techno": _safe_float(row.get(PCT_BT_COLUMN)),
                "pro": _safe_float(row.get(PCT_BP_COLUMN)),
            },
            "acces_pct": {
                "general": _safe_float(row.get(PART_ACCES_GEN_COLUMN)),
                "techno": _safe_float(row.get(PART_ACCES_TEC_COLUMN)),
                "pro": _safe_float(row.get(PART_ACCES_PRO_COLUMN)),
            },
            "boursiers_pct": _safe_float(row.get(PCT_BOURS_COLUMN)),
            # Vague A — diversité démographique + origine géographique
            "femmes_pct": _safe_float(row.get(PCT_F_COLUMN)),
            "neobacheliers_pct": _safe_float(row.get(PCT_NEOBAC_COLUMN)),
            "origine_academique_idf_pct": _safe_float(row.get(PCT_ACA_ORIG_IDF_COLUMN)),
        },
        # === ADR-041 — champs P0 enrichissement ===
        # prop_tot = propositions totales envoyées (≠ acceptations). Signal de
        # "convertibilité" voeux → admission, plus granulaire que taux_acces.
        "propositions_totales": _safe_int(row.get(PROP_TOT_COLUMN)),
        # pct_acc_debutpp = % acceptés dès le début PP. Mesure la sélectivité
        # timing : formation prise d'assaut vs places restées dispo longtemps.
        "pct_acceptes_debut_pp": _safe_float(row.get(PCT_ACC_DEBUTPP_COLUMN)),
        # Classification structurée Parcoursup (complément des keywords DOMAIN_KEYWORDS
        # basés sur le nom). Utile pour désambiguïser (ex: "Master Psychologie" →
        # fili précis). Nom humain dans `lib_grp1`.
        "fili_code": _clean_str(row.get(FILI_COLUMN)),
        "fili_groupe": _clean_str(row.get(LIB_GRP1_COLUMN)),
        "selectivite_code": _clean_str(row.get(SELECT_FORM_COLUMN)),
    }


def collect_parcoursup_fiches(
    path: str | Path, domains: list[str] | None = None
) -> list[dict]:
    """Extrait les fiches Parcoursup filtrées par domaines (mot-clé keyword match).

    Arguments :
    - `path` : CSV Parcoursup OpenData (parcoursup_2025.csv typiquement)
    - `domains` : liste des domaines à extraire. None = LEGACY_DOMAINS
      (cyber + data_ia + sante) pour backward-compat. Passer EXTENDED_DOMAINS
      pour scope élargi 17-25 ans (ADR-041 Axe a).

    L'ordre d'itération des domaines détermine le first-wins pour les fiches
    multi-domaines (une fiche qui match cyber + eco_gestion est classée cyber
    si cyber apparaît avant dans la liste).
    """
    df = load_parcoursup(path)
    target_domains = domains if domains is not None else LEGACY_DOMAINS
    all_fiches = []
    # De-dup par cod_aff_form : même row dédoublonné si keyword liste overlap.
    seen_codes: set[str] = set()
    for domain in target_domains:
        if domain not in DOMAIN_KEYWORDS:
            raise ValueError(
                f"Domain {domain!r} absent de DOMAIN_KEYWORDS. "
                f"Options disponibles : {sorted(DOMAIN_KEYWORDS.keys())}"
            )
        filtered = filter_domain(df, domain, FORMATION_COLUMN)
        for _, row in filtered.iterrows():
            fiche = extract_fiche(row)
            cod = fiche.get("cod_aff_form")
            if cod and cod in seen_codes:
                continue
            if cod:
                seen_codes.add(cod)
            fiche["domaine"] = domain
            all_fiches.append(fiche)
    return all_fiches


def collect_parcoursup_all_sectors(path: str | Path) -> list[dict]:
    """Alias pour `collect_parcoursup_fiches(path, domains=EXTENDED_DOMAINS)`.

    Raccourci explicite pour le scope élargi ADR-041. Attendu 8k-12k fiches
    (vs 1.4k avec les 3 domaines legacy).
    """
    return collect_parcoursup_fiches(path, domains=EXTENDED_DOMAINS)


def collect_parcoursup_all_cascade(path: str | Path) -> list[dict]:
    """Ingestion ÉLARGIE C1 (2026-06-09) : TOUTES les formations du CSV Parcoursup,
    pas seulement celles dont le nom matche la taxonomie keyword.

    Contraste avec `collect_parcoursup_fiches` (filtre par DOMAIN_KEYWORDS, ~8k
    fiches) : ici on prend chaque ligne et on assigne le domaine par CASCADE
    (`domaine_cascade` : keyword nom -> mapping form_lib_voe_acc -> "autre").
    Comble les ~6000 formations hors taxonomie (BTS, D.E social/sanitaire, etc.).

    Dédup par `cod_aff_form` (un id Parcoursup = une fiche). Conserve
    `form_lib_voe_acc` en métadonnée (info type/champ, même si domaine="autre").

    NB : la dédup CROSS-SOURCE (vs ONISEP/MonMaster) n'est PAS faite ici — elle
    est gérée en aval par run_merge_v3 (fuzzy-merge + dedup exact). Cette fonction
    ne fait que produire les fiches Parcoursup ; le merge canonique dédoublonne.
    """
    df = load_parcoursup(path)
    all_fiches: list[dict] = []
    seen_codes: set[str] = set()
    for _, row in df.iterrows():
        fiche = extract_fiche(row)
        cod = fiche.get("cod_aff_form")
        if cod and cod in seen_codes:
            continue
        if cod:
            seen_codes.add(cod)
        fiche["domaine"] = domaine_cascade(row)
        fiche[FORM_LIB_VOE_ACC_COLUMN] = _clean_str(row.get(FORM_LIB_VOE_ACC_COLUMN))
        all_fiches.append(fiche)
    return all_fiches
