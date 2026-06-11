"""IP Doc — Insertion professionnelle des doctorants (MESR).

Source : https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insertion-professionnelle-doctorat-par-discipline/
Licence : Etalab 2.0.
API : Opendatasoft v2.1 (même pattern que InserSup / MonMaster).

**Apports OrientIA** (ADR-039 phase c, scope 22-25 ans) :

- **Angle mort comblé** : toutes les autres sources OrientIA s'arrêtent
  au master (bac+5). InserSup couvre Master + Licence. IP Doc est la
  seule source sur la **trajectoire doctorale** (bac+8 + R&D).
- Pertinence narrative INRIA : "parcours recherche" est une voie
  légitime d'orientation à 22-25 ans (post-master, entrée en thèse).
- Taille raisonnable : 240 records (petit dataset, ingestion immédiate).

**Contenu des records** :

- Enquête annuelle par `disca` (discipline agrégée) × `discipline_principale`
- Horizons à 12 et 36 mois post-diplôme
- Taux d'insertion + part femmes + répartition secteurs :
  - `part_secteur_academique` : reste dans la recherche publique
  - `part_public_hors_secteur_academique` : fonction publique hors académie
  - `part_r_d_privee` : R&D industrie privée
  - `part_prive_hors_secteur_academique_et_r_d` : privé hors R&D
- Part emploi à l'étranger
- Salaires q1 / médian / q3 mensuel + brut annuel
- Part emploi stable (CDI / fonctionnaire)
- Part cadre + temps plein

**Stratégie** : fetch bulk via `/exports/json` (comme InserSup).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import requests


EXPORT_URL = (
    "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/"
    "catalog/datasets/fr-esr-insertion-professionnelle-doctorat-par-discipline/"
    "exports/json"
)
PROCESSED_PATH = Path("data/processed/ip_doc_doctorat.json")


# --- Mapping disca (discipline agrégée) → domaine OrientIA ---

DISCA_TO_DOMAINE: dict[str, str] = {
    "Sciences de la société": "sciences_humaines",
    "Droit, économie, gestion": "eco_gestion",
    "Sciences humaines et humanités": "sciences_humaines",
    "Sciences, technologies, santé": "sciences_fondamentales",
    "Sciences et techniques": "sciences_fondamentales",
    "Sciences de l'environnement": "sciences_fondamentales",
    "Biologie, médecine, santé": "sante",
    "Mathématiques et leurs interactions": "sciences_fondamentales",
    "Physique": "sciences_fondamentales",
    "Chimie": "sciences_fondamentales",
    "Sciences pour l'ingénieur": "ingenierie_industrielle",
    "Sciences et technologies de l'information et de la communication": "data_ia",
    "Sciences agronomiques et écologiques": "agriculture",
    "Milieux, ressources et sociétés du passé": "sciences_humaines",
    "Sciences de la terre et de l'univers, espace": "sciences_fondamentales",
    "Sciences juridiques et politiques": "eco_gestion",
    "Sciences économiques et de gestion": "eco_gestion",
    "Sciences de l'homme et humanités": "sciences_humaines",
    "Arts, lettres et langues": "sciences_humaines",
    "Langues et littératures": "langues",
}


def disca_to_domaine(disca: Optional[str]) -> Optional[str]:
    if not disca:
        return None
    if disca in DISCA_TO_DOMAINE:
        return DISCA_TO_DOMAINE[disca]
    # Fallback substring
    low = disca.lower()
    if "informat" in low or "numérique" in low:
        return "data_ia"
    if "santé" in low or "médec" in low or "biolog" in low:
        return "sante"
    if "ingéni" in low:
        return "ingenierie_industrielle"
    if "droit" in low or "écono" in low or "gestion" in low:
        return "eco_gestion"
    if "sciences" in low:
        return "sciences_fondamentales"
    if "lettre" in low or "langue" in low or "human" in low:
        return "sciences_humaines"
    if "agro" in low or "écolo" in low:
        return "agriculture"
    return None


# --- Fetch ---


class IpDocFetchError(Exception):
    """Erreur réseau ou réponse API inattendue."""


def fetch_ip_doc_records(
    max_records: Optional[int] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """Fetch via `/exports/json` du dataset IP Doc."""
    sess = session or requests.Session()
    params: dict[str, Any] = {}
    if max_records is not None:
        params["limit"] = max_records
    resp = sess.get(EXPORT_URL, params=params, timeout=timeout)
    if resp.status_code != 200:
        raise IpDocFetchError(
            f"IP Doc API {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    if not isinstance(data, list):
        raise IpDocFetchError(
            f"Réponse inattendue (attendu list, obtenu {type(data).__name__})"
        )
    return data


# --- Safe parsers ---


def _safe_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        # Accepte "1 851,5" (FR) / "1 851.5" / "38\u202f000" (espace insécable)
        s = str(val).replace("\u202f", "").replace(" ", "").replace(",", ".")
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _safe_ratio(val: Any) -> Optional[float]:
    """Convertit en ratio [0,1]. Valeur >1 = pourcentage à diviser par 100."""
    if val is None or val == "":
        return None
    try:
        f = float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None
    return f / 100.0 if f > 1.0 else f


# --- Normalize ---


def build_doctorat_insertion_pro(fiche: dict[str, Any]) -> dict[str, Any] | None:
    """Construit le bloc `insertion_pro` d'une fiche doctorat depuis ses champs
    salaire/insertion top-level.

    Fix order 2026-06-11 (C2b) : les fiches ip_doc_doctorat portent un salaire net
    médian mensuel RÉEL (source enquête IP Doc) au top-level mais `insertion_pro`
    était absent -> ni `_format_insertion_pro` ni `FactChiffres.salaire_median_embauche`
    (fact_card lit `insertion_pro.salaire_median_embauche`) ne le surfaçaient.
    On expose le salaire net étiqueté source (RÈGLE 6), zéro agrégation maison.

    Retourne None si pas de salaire net médian exploitable.
    """
    sal = fiche.get("salaire_net_median_mensuel")
    if sal is None:
        return None
    return {
        "source": "ip_doc_doctorat",
        "salaire_median_embauche": sal,                  # net mensuel, valeur source
        "salaire_net": True,
        "salaire_horizon": fiche.get("situation"),       # "12m" / "36m" après le doctorat
        "salaire_brut_median_annuel": fiche.get("salaire_brut_median_annuel"),
        "taux_insertion": fiche.get("taux_insertion"),
        # Année de cohorte d'enquête, tracée pour citation (cf détresse-006).
        # Le corpus servi porte `annee_cohorte` ; le normalize_record produit `annee`.
        "cohorte": fiche.get("annee_cohorte") or fiche.get("annee"),
    }


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise un record IP Doc en fiche OrientIA.

    Schéma de sortie :
        source, annee, situation (12m/36m), discipline_agregee,
        discipline_principale, domaine_orientia, niveau_orientia (bac+8),
        genre, nb_repondants, part_femmes, taux_insertion, part_stable,
        part_cadre, part_temps_plein, part_secteur_academique,
        part_public_hors_academique, part_rd_privee,
        part_prive_hors_rd, part_emploi_etranger,
        salaire_net_q1 / q3 / median_mensuel, salaire_brut_median_annuel.
    """
    disca = record.get("disca")
    fiche = {
        "source": "ip_doc_doctorat",
        "annee": record.get("annee"),
        "situation": record.get("situation"),
        "discipline_agregee": disca,
        "discipline_principale": record.get("discipline_principale"),
        "domaine_orientia": disca_to_domaine(disca),
        "niveau_orientia": "bac+8",  # Tous docs → bac+8
        "genre": record.get("genre"),
        "nb_repondants": _safe_int(record.get("nbre_de_repondants")),
        "part_femmes": _safe_ratio(record.get("part_femmes")),
        "taux_insertion": _safe_ratio(record.get("taux_insertion")),
        "part_stable": _safe_ratio(record.get("part_stable")),
        "part_cadre": _safe_ratio(record.get("part_cadre")),
        "part_temps_plein": _safe_ratio(record.get("part_temps_plein")),
        "part_secteur_academique": _safe_ratio(record.get("part_secteur_academique")),
        "part_public_hors_academique": _safe_ratio(
            record.get("part_public_hors_secteur_academique")
        ),
        "part_rd_privee": _safe_ratio(record.get("part_r_d_privee")),
        "part_prive_hors_rd": _safe_ratio(
            record.get("part_prive_hors_secteur_academique_et_r_d")
        ),
        "part_emploi_etranger": _safe_ratio(record.get("part_en_emploi_a_l_etranger")),
        "salaire_net_q1_mensuel": _safe_int(record.get("sal_net_q1_mensuel")),
        "salaire_net_median_mensuel": _safe_int(record.get("sal_net_med_mensuel")),
        "salaire_net_q3_mensuel": _safe_int(record.get("sal_net_q3_mensuel")),
        "salaire_brut_median_annuel": _safe_int(record.get("sal_brut_med_annuel")),
    }
    ip = build_doctorat_insertion_pro(fiche)
    if ip is not None:
        fiche["insertion_pro"] = ip
    return fiche


def normalize_all(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_record(r) for r in raw]


def save_processed(
    entries: list[dict[str, Any]], path: Path = PROCESSED_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def collect_ip_doc_doctorat(
    max_records: Optional[int] = None, save: bool = True
) -> list[dict[str, Any]]:
    """Pipeline complet : fetch → normalize → save."""
    t0 = time.time()
    print("  [ip_doc] Fetch via /exports/json…")
    raw = fetch_ip_doc_records(max_records=max_records)
    print(f"  [ip_doc] {len(raw)} records en {time.time()-t0:.1f}s")
    normalized = normalize_all(raw)
    if save:
        p = save_processed(normalized)
        print(f"  [ip_doc] {len(normalized)} fiches → {p}")
    return normalized


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion IP Doc doctorat MESR")
    parser.add_argument("--max", type=int, default=None)
    args = parser.parse_args()
    fiches = collect_ip_doc_doctorat(max_records=args.max)
    print(f"  [ip_doc] total : {len(fiches)} fiches")
