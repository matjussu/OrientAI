from __future__ import annotations

import csv
import io
import zipfile
from functools import lru_cache
from pathlib import Path

import pandas as pd


# --- D3 extension (2026-04-19) : accès enrichi au référentiel ROME 4.0 ---
# Le zip téléchargé contient 30 CSV. On expose ici un accès mémoïsé
# à unix_referentiel_code_rome_v460_utf8.csv pour enrichir les fiches
# avec : libellé officiel, transition éco/num/démo, emploi cadre/réglementé,
# hiérarchie (code_rome_parent). Pas besoin d'API live pour ces champs.

ROME_ZIP_PATH = Path("data/raw/rome_4_0.zip")
_REF_CSV_NAME = "unix_referentiel_code_rome_v460_utf8.csv"


@lru_cache(maxsize=1)
def _load_rome_ref_from_zip() -> dict[str, dict]:
    """Parse unix_referentiel_code_rome CSV depuis le zip ROME 4.0.
    Mémoïsé — charge une seule fois par process."""
    ref: dict[str, dict] = {}
    if not ROME_ZIP_PATH.exists():
        return ref
    with zipfile.ZipFile(ROME_ZIP_PATH) as z:
        with z.open(_REF_CSV_NAME) as f:
            text = f.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = row.get("code_rome", "").strip()
        if not code:
            continue
        ref[code] = {
            "code_rome": code,
            "libelle": row.get("libelle_rome", "").strip(),
            "transition_eco_label": row.get("transition_eco", "").strip(),
            "transition_num": row.get("transition_num", "").strip() == "Y",
            "transition_demo": row.get("transition_demo", "").strip() == "Y",
            "emploi_reglemente": row.get("emploi_reglemente", "").strip() == "Y",
            "emploi_cadre": row.get("emploi_cadre", "").strip() == "Y",
            "code_rome_parent": row.get("code_rome_parent", "").strip(),
        }
    return ref


def get_rome_info(code_rome: str) -> dict | None:
    """Retourne les infos référentielles pour un code ROME 4.0, ou None.

    Champs retournés : libelle, transition_eco_label (texte),
    transition_num (bool), transition_demo (bool), emploi_reglemente
    (bool), emploi_cadre (bool), code_rome_parent."""
    if not code_rome:
        return None
    ref = _load_rome_ref_from_zip()
    return ref.get(code_rome.strip())


def list_all_rome_codes() -> list[str]:
    """Liste tous les codes ROME du référentiel v460 (~1584 codes)."""
    return list(_load_rome_ref_from_zip().keys())


def is_emploi_cadre(code_rome: str) -> bool:
    info = get_rome_info(code_rome)
    return bool(info and info.get("emploi_cadre"))


def is_transition_numerique(code_rome: str) -> bool:
    info = get_rome_info(code_rome)
    return bool(info and info.get("transition_num"))


# --- Anciennes fonctions (stables, alimentent les tests existants) ---


# ROME 4.0 codes relevant to OrientIA's two domains.
# Verified against France Travail ROME 4.0 open data (2026-04 release,
# 1584 codes total). These are the codes that will show up as "débouchés"
# for formations in each domain.
RELEVANT_ROME_CODES = {
    # Cybersécurité — 9 direct codes
    "M1812": "Responsable de la Sécurité des Systèmes d'Information (RSSI)",
    "M1817": "Administrateur / Administratrice sécurité informatique",
    "M1819": "Ingénieur / Ingénieure sécurité informatique",
    "M1844": "Analyste en cybersécurité",
    "M1846": "Ingénieur / Ingénieure Cybersécurité Datacenter",
    "M1856": "Expert / Experte en cybersécurité",
    "M1863": "Evaluateur / Evaluatrice sécurité des systèmes et produits informatiques",
    "M1882": "Architecte sécurité informatique",
    "M1884": "Ingénieur / Ingénieure systèmes, réseaux et sécurité informatique",
    # Data / IA — 6 direct codes
    "M1405": "Data scientist",
    "M1419": "Data analyst",
    "M1423": "Chief Data Officer",
    "M1811": "Data engineer",
    "M1868": "Architecte base de données",
    "M1894": "Gestionnaire de base de données",
    # Santé — 10 codes J1xxx couvrant les principaux métiers paramédicaux
    # et médicaux (source : Pôle Emploi / France Travail ROME 4.0, 2026).
    # Intentionally broad so a "santé" fiche Parcoursup (qu'elle soit PASS,
    # IFSI, ou formation paramédicale spécifique) surface une gamme réaliste
    # de métiers accessibles après la formation.
    "J1102": "Médecin généraliste / Médecin spécialiste",
    "J1103": "Médecin de prévention et santé publique",
    "J1104": "Sage-femme",
    "J1201": "Professions paramédicales (aide-soignant, auxiliaire de puériculture)",
    "J1304": "Pharmacien / Préparateur en pharmacie",
    "J1401": "Audioprothésiste / Opticien / Orthoptiste / Podologue",
    "J1501": "Infirmier / Infirmière diplômé(e) d'État",
    "J1502": "Cadre de santé / Directeur de soins",
    "J1505": "Kinésithérapeute / Ergothérapeute",
    "J1506": "Orthophoniste",
    # Travail social — 8 codes K1xxx/K2xxx (NSF 332). Famille ROME DISTINCTE de
    # la santé : un Accompagnant Educatif et Social, un CESF ou un éducateur
    # spécialisé n'a AUCUN débouché médical. Vérifiés contre France Travail
    # ROME 4.0 (2026-04, via get_rome_info). Fix order 2026-06-11 : ces
    # formations héritaient à tort des 10 débouchés médicaux J11xx via
    # domaine=sante (NSF 332 collapsé sur "sante"). cf detresse-prec-007.
    "K1201": "Assistant / Assistante de service social",
    "K1202": "Éducateur / Éducatrice de jeunes enfants",
    "K1204": "Médiateur social / Médiatrice sociale",
    "K1207": "Éducateur spécialisé / Éducatrice spécialisée",
    "K1305": "Technicien / Technicienne d'intervention sociale et familiale (TISF)",
    "K1306": "Accompagnant éducatif et social (AES)",
    "K1403": "Directeur / Directrice de structure sociale ou médico-sociale",
    "K2112": "Conseiller / Conseillère d'orientation / d'insertion",
}


_DOMAIN_CODES = {
    "cyber": ["M1812", "M1817", "M1819", "M1844", "M1846", "M1856", "M1863", "M1882", "M1884"],
    "data_ia": ["M1405", "M1419", "M1423", "M1811", "M1868", "M1894"],
    "sante": ["J1102", "J1103", "J1104", "J1201", "J1304", "J1401",
              "J1501", "J1502", "J1505", "J1506"],
    # Travail social (NSF 332) — débouchés ROME K*, jamais médicaux (cf supra).
    "social": ["K1201", "K1202", "K1204", "K1207", "K1305", "K1306", "K1403", "K2112"],
}


def load_rome_job_titles(path: str | Path) -> dict[str, str]:
    """Load the ROME 4.0 canonical code→libellé mapping.

    Expects the unix_referentiel_code_rome_v460_utf8.csv file from the
    official France Travail ROME 4.0 open data ZIP. CSV uses comma
    separator and the canonical column name is `libelle_rome`.
    """
    df = pd.read_csv(path, sep=",", encoding="utf-8")
    return dict(zip(df["code_rome"], df["libelle_rome"]))


def get_debouches_for_domain(domain: str) -> list[dict]:
    """Return the list of ROME codes and canonical labels for a domain.

    Uses the hard-coded RELEVANT_ROME_CODES mapping (verified against ROME 4.0)
    rather than filtering the full CSV at runtime. This keeps the debouches
    stable and reproducible across benchmark runs.
    """
    codes = _DOMAIN_CODES[domain]
    return [{"code_rome": c, "libelle": RELEVANT_ROME_CODES[c]} for c in codes]
