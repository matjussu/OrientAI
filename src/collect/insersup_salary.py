"""InserSup salary attach (C2b, order 2026-06-11) — salaire net médian par formation.

Alimente `insertion_pro.salaire_median_embauche` (net mensuel, valeur SOURCE,
ZÉRO agrégation maison) depuis le CSV InserSup local (`data/raw/insersup.csv`),
qui porte le "Salaire mensuel net médian en équivalent temps plein" par
établissement × type de diplôme × domaine disciplinaire.

Pourquoi un module à part de `insersup_attach.py` : ce dernier joint les TAUX
d'emploi via les fichiers processés (issus de l'API, qui n'expose PAS le salaire).
Le salaire n'existe QUE dans le CSV local -> chemin dédié.

Join (exact-match normalisé, zéro fuzzy pour rester sûr) :
- MonMaster (masters, sans UAI) -> par (nom établissement, "master", discipline).
- Parcoursup supérieur (avec UAI) -> par (UAI, type dérivé du nom).

Net étiqueté source (RÈGLE 6). Le salaire formation réel prime sur le proxy PCS.
"""
from __future__ import annotations

import collections
import csv
import re
import unicodedata
from pathlib import Path
from typing import Any

# Colonnes CSV InserSup (cf src/collect/insersup.py)
COL_ETAB = "Établissement"
COL_UAI = "Code UAI de l'établissement"
COL_TYPE = "type_diplome"
COL_DISC = "Domaine disciplinaire"
COL_LIBELLE = "Libellé du diplôme"
COL_GENRE, COL_NAT, COL_REGIME, COL_OBT = (
    "Genre", "Nationalité", "Régime d'inscription", "Obtention du diplôme",
)
COL_PROMO = "Promotion"
COL_SAL12 = "12-Salaire mensuel net médian en équivalent temps plein - 12 mois après le diplôme"
COL_SAL30 = "30-Salaire mensuel net médian en équivalent temps plein - 30 mois après le diplôme"

INSERSUP_DATASET_URL = (
    "https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/"
)
_NULL_TOKENS = {"", "ns", "nd", ".", "secret", "na", "n/a"}


def _norm(s: Any) -> str:
    s = str(s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s)


# Strip d'un préfixe de type de diplôme en tête de libellé (symétrique fiche/InserSup).
_LEADING_TYPE_RE = re.compile(
    r"^(but|bachelor universitaire de technologie|licence professionnelle|"
    r"licence pro|licence|master meef|master lmd|master|diplome national|"
    r"dn made|tout)\s*[-:]?\s+"
)


def _canon_formation(s: Any) -> str:
    """Forme canonique d'un libellé de formation pour le join par-formation :
    minuscule sans accents -> strip du suffixe parcours ('— B', '- option X')
    -> strip d'un préfixe de type ('Master ', 'BUT '). Appliqué SYMÉTRIQUEMENT
    au nom de fiche et au libellé InserSup pour matcher la mention exacte."""
    c = _norm(s)
    c = re.split(r"\s[-—]\s", c)[0].strip()      # suffixe parcours/option
    c = _LEADING_TYPE_RE.sub("", c).strip()       # préfixe de type éventuel
    return c


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        f = float(str(val).replace(",", ".").replace(" ", ""))
        if f != f:  # NaN
            return None
        return int(round(f))
    except (ValueError, TypeError):
        return None


def _type_bucket(type_label: str) -> str | None:
    """Réduit un libellé de type de diplôme à un bucket de join sûr.

    On garde des buckets DISTINCTS pour éviter les matchs sémantiquement faux
    (un Master ne doit pas matcher un 'Diplôme visé management'). Retourne None
    pour les types non pris en charge (pas de match).
    """
    t = _norm(type_label)
    if not t:
        return None
    if t.startswith("master") or t == "master lmd" or "master meef" in t:
        return "master"
    if "licence professionnelle" in t or t == "licence_pro" or t == "licence pro":
        return "licence_pro"
    if "bachelor universitaire de technologie" in t or t == "but":
        return "but"
    if t.startswith("licence"):  # licence générale (après licence pro ci-dessus)
        return "licence"
    if "ingenieur" in t:
        return "ingenieur"
    return None


def _derive_fiche_bucket(fiche: dict) -> str | None:
    """Bucket de type pour une fiche. MonMaster = master implicite ; sinon on
    dérive du `type_diplome` puis, en fallback, du `nom`."""
    if fiche.get("source") == "monmaster":
        return "master"
    b = _type_bucket(fiche.get("type_diplome"))
    if b:
        return b
    return _bucket_from_nom(fiche.get("nom"))


def _bucket_from_nom(nom: str) -> str | None:
    n = _norm(nom)
    if "master" in n:
        return "master"
    if "licence professionnelle" in n or "licence pro" in n:
        return "licence_pro"
    if "bachelor universitaire de technologie" in n or re.search(r"\bbut\b", n):
        return "but"
    if "ingenieur" in n:
        return "ingenieur"
    if "licence" in n:
        return "licence"
    return None


def _fiche_uai(fiche: dict) -> str | None:
    for k in ("cod_uai", "uai", "code_uai"):
        v = fiche.get(k)
        if v:
            return str(v).strip().upper()
    return None


def _promo_key(promo: Any) -> int:
    """Année la plus récente d'une promo ('2022' ou '2021,2022')."""
    s = str(promo or "")
    years = re.findall(r"\d{4}", s)
    return max((int(y) for y in years), default=0)


def build_salary_index(csv_path: str | Path) -> dict[str, Any]:
    """Index salaire depuis le CSV InserSup (lignes ensemble × salaire non-null).

    Retourne :
      {
        "by_name_disc": {(nom_norm, bucket, disc_norm): record},
        "by_uai_type":  {(uai, bucket): record},
        "metrics": {...},
      }
    record = {salaire, salaire_30m, cohorte, etab, type, discipline, horizon}
    Sur collision de clé : on garde la promo la plus récente. Les collisions à
    salaire DIFFÉRENT sur même promo sont comptées (ambiguïté).
    """
    by_name_disc: dict[tuple, dict] = {}
    by_uai_type: dict[tuple, dict] = {}
    n_rows = 0
    ambiguities = 0
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if (row.get(COL_GENRE) != "ensemble" or row.get(COL_NAT) != "ensemble"
                    or row.get(COL_REGIME) != "ensemble" or row.get(COL_OBT) != "ensemble"):
                continue
            sal12 = _safe_int(row.get(COL_SAL12)) if (row.get(COL_SAL12) or "").strip().lower() not in _NULL_TOKENS else None
            sal30 = _safe_int(row.get(COL_SAL30)) if (row.get(COL_SAL30) or "").strip().lower() not in _NULL_TOKENS else None
            salaire = sal12 if sal12 is not None else sal30
            if salaire is None:
                continue
            bucket = _type_bucket(row.get(COL_TYPE))
            if not bucket:
                continue
            libelle_canon = _canon_formation(row.get(COL_LIBELLE))
            if not libelle_canon:
                continue  # pas de libellé exploitable -> pas de join par-formation
            n_rows += 1
            etab = _norm(row.get(COL_ETAB))
            uai = (row.get(COL_UAI) or "").strip().upper()
            promo = _promo_key(row.get(COL_PROMO))
            rec = {
                "salaire": salaire, "salaire_30m": sal30, "horizon": "12m" if sal12 is not None else "30m",
                "cohorte": str(row.get(COL_PROMO) or "").strip() or None,
                "_promo": promo, "etab": row.get(COL_ETAB), "type": row.get(COL_TYPE),
                "discipline": row.get(COL_DISC), "libelle": row.get(COL_LIBELLE), "uai": uai,
            }

            def _insert(idx: dict, key: tuple) -> None:
                nonlocal ambiguities
                prev = idx.get(key)
                if prev is None or promo > prev["_promo"]:
                    # freshest-promo : on garde l'année de cohorte la plus récente
                    idx[key] = rec
                elif promo == prev["_promo"] and prev["salaire"] != salaire:
                    ambiguities += 1  # vraie ambiguïté résiduelle : même clé + même promo, salaires divergents

            # Clé par-formation : (établissement|UAI, bucket de type, libellé canonique)
            if etab:
                _insert(by_name_disc, (etab, bucket, libelle_canon))
            if uai:
                _insert(by_uai_type, (uai, bucket, libelle_canon))
    return {
        "by_name_disc": by_name_disc,
        "by_uai_type": by_uai_type,
        "metrics": {
            "rows_with_salary": n_rows,
            "keys_name_libelle": len(by_name_disc),
            "keys_uai_libelle": len(by_uai_type),
            "ambiguities_same_key_same_promo": ambiguities,
        },
    }


def match_fiche_salary(fiche: dict, index: dict[str, Any]) -> tuple[dict | None, str]:
    """Tente un match salaire pour une fiche. Retourne (record | None, méthode).

    méthode ∈ {"name_disc", "uai_type", "none"}.
    Priorité au match le plus précis (nom+discipline pour MonMaster, UAI+type
    pour les fiches à UAI).
    """
    bucket = _derive_fiche_bucket(fiche)
    if not bucket:
        return None, "none"
    formation = _canon_formation(fiche.get("nom"))
    if not formation:
        return None, "none"
    # MonMaster (sans UAI) : nom établissement + libellé canonique
    if fiche.get("source") == "monmaster":
        rec = index["by_name_disc"].get((_norm(fiche.get("etablissement")), bucket, formation))
        if rec:
            return rec, "name_libelle"
        return None, "none"
    # Fiches à UAI (parcoursup supérieur) : UAI + libellé canonique
    uai = _fiche_uai(fiche)
    if uai:
        rec = index["by_uai_type"].get((uai, bucket, formation))
        if rec:
            return rec, "uai_libelle"
    return None, "none"


def attach_insersup_salaries(fiches: list[dict], index: dict[str, Any]) -> dict[str, Any]:
    """Enrichit `insertion_pro.salaire_median_embauche` (net source) sur les
    fiches matchées. Idempotent (n'écrase pas un salaire déjà présent). Retourne
    des métriques de jointure (pour audit)."""
    by_method = collections.Counter()
    by_source = collections.Counter()
    examples: list[dict] = []
    for f in fiches:
        if not isinstance(f, dict):
            continue
        ip = f.get("insertion_pro")
        if isinstance(ip, dict) and ip.get("salaire_median_embauche") is not None:
            continue  # déjà un salaire, on ne clobber pas
        rec, method = match_fiche_salary(f, index)
        if not rec:
            continue
        if not isinstance(f.get("insertion_pro"), dict):
            f["insertion_pro"] = {}
        f["insertion_pro"]["salaire_median_embauche"] = rec["salaire"]
        f["insertion_pro"]["salaire_net"] = True
        f["insertion_pro"]["salaire_horizon"] = rec["horizon"]
        f["insertion_pro"]["salaire_source"] = "insersup"
        f["insertion_pro"]["salaire_cohorte"] = rec["cohorte"]
        f["insertion_pro"].setdefault("source", "insersup_mesr")
        f["insertion_pro"].setdefault("url_source", INSERSUP_DATASET_URL)
        by_method[method] += 1
        by_source[f.get("source")] += 1
        if len(examples) < 8:
            examples.append({
                "fiche_nom": (f.get("nom") or "")[:60], "fiche_source": f.get("source"),
                "fiche_etab": f.get("etablissement"), "fiche_discipline": f.get("discipline"),
                "method": method, "salaire": rec["salaire"], "horizon": rec["horizon"],
                "insersup_etab": rec["etab"], "insersup_type": rec["type"],
                "insersup_discipline": rec["discipline"], "cohorte": rec["cohorte"],
            })
    return {
        "n_enriched": sum(by_method.values()),
        "by_method": dict(by_method),
        "by_source": dict(by_source),
        "examples": examples,
    }
