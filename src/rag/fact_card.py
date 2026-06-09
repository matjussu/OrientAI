"""FactCard — extraction structurée des fiches pour le contrat strict v4.0.

Étape 2 refonte WHAT/HOW (2026-05-06). L'idée : au lieu de passer la prose
libre des fiches au LLM (qui mélange chiffres et description), on extrait
les champs typés en JSON tabulaire explicite. Le LLM voit alors clairement
"ce que je peux citer" vs "ce que je n'ai pas".

## 2 modes de fiches

Le corpus formations.json contient 47 220 fiches de 2 natures (vérifié
2026-06-09 contre data/processed/formations.json) :

1. **Parcoursup riches** (17.3%, 8 191 fiches) : ont `taux_acces_parcoursup_2025`,
   `nombre_places`, `admission` (nested avec historique 2023-2025), `profil_admis`
   (schéma mentions au bac), `selectivite_code`, `debouches`. Sous-corpus "or".
   MonMaster (7 573, 16%) ajoute la sélectivité master : `taux_admission` (ratio
   0-1), `capacite`, `rang_dernier_appele`, `alternance`, `profil_admis` (schéma
   origine de diplôme, distinct du schéma Parcoursup) — exposés via Bloc A.

2. **Multi-corpus / RNCP / ONISEP / etc.** (~67%, ~31k fiches) : ont `nom`,
   `etablissement`, `niveau`, ~31% ont `insertion_pro`, souvent un `text` libre
   ou `detail` mais pas les stats Parcoursup.

`fiche_to_fact_card()` gère les 2 cas : extrait ce qui est disponible,
laisse `None` ailleurs. Le LLM décide de citer ou de dire "info non disponible".

## Format JSON pour le prompt LLM

`format_sources_for_llm(top_sources)` produit un tableau JSON sérialisé :

    [
      {
        "id": "S1",
        "formation": "Bachelor Cybersécurité ...",
        "etablissement": "Lycée Emmanuel d'Alzon",
        "ville": "Nîmes",
        "region": "Occitanie",
        "niveau": "bac+3",
        "statut": "Privé",
        "type_diplome": "formation d'école spécialisée",
        "chiffres": {
          "taux_acces_parcoursup_2025": 52.0,
          "nombre_places": 25,
          "duree": "3 ans",
          "taux_emploi_3ans": 0.86,
          "taux_cdi": 0.83,
          "salaire_median_embauche": 1740,
          "frais_annuels": null
        },
        "selectivite_code": "formation sélective",
        "debouches": ["RSSI", "Administrateur sécurité", "Ingénieur sécurité"],
        "url": "https://dossierappel.parcoursup.fr/.../?g_ta_cod=39320..."
      },
      ...
    ]

Le LLM lit ce JSON, sait quels chiffres citer, voit explicitement les `null`
qui doivent déclencher "info non disponible".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


# ─────────────── ADR-055 — Liste blanche tier 1/2/3 ───────────────
#
# Mapping source → tier de confiance pour exposer dans la provenance.
# Voir docs/DECISION_LOG.md ADR-055 pour le périmètre complet.
#
# - tier_1 : officiel État (Parcoursup, ONISEP, INSEE, DARES, France Travail, etc.)
# - tier_2 : paritaire / agence officielle (APEC, AGEFIPH, ANSSI, CTI, CGE, FESIC)
# - tier_3 : sites officiels d'établissements pour info pratique uniquement
#            (préfixe `site_etablissement_<slug>` dans le champ source)

SOURCE_TO_TIER: dict[str, str] = {
    # ── Tier 1 — Officiel État ──
    # Plateformes Parcoursup / MonMaster / ONISEP
    "parcoursup": "tier_1",
    "parcoursup_extended": "tier_1",
    "monmaster": "tier_1",
    "onisep": "tier_1",
    "onisep_extended": "tier_1",
    "onisep_formations_extended": "tier_1",
    "onisep_metiers": "tier_1",
    "ideo_onisep": "tier_1",
    "onisep_ideo_fiches": "tier_1",
    # Certifications RNCP / France Compétences
    "rncp": "tier_1",
    "rncp_blocs": "tier_1",
    "france_competences": "tier_1",
    # France Travail / ROME 4.0
    "rome_api_v4": "tier_1",
    "france_travail": "tier_1",
    "ft_marche": "tier_1",
    "ft_offres": "tier_1",
    "ft_sortants": "tier_1",
    # Insertion / formation (MESR + DEPP + Cereq)
    "insersup": "tier_1",
    "insersup_mesr": "tier_1",
    "cereq": "tier_1",  # collectée mais non utilisée pour citation par formation (ADR-054)
    "dares": "tier_1",
    "dares_metiers_2030": "tier_1",
    "drees": "tier_1",
    "france_strategie": "tier_1",
    "inserjeunes": "tier_1",
    "inserjeunes_cfa": "tier_1",
    "inserjeunes_depp": "tier_1",
    "inserjeunes_lycee_pro": "tier_1",
    "ip_doc_doctorat": "tier_1",
    "mesri_parcours_bacheliers_licence": "tier_1",
    "parcours_bacheliers": "tier_1",
    # La Bonne Alternance / France Travail
    "labonnealternance": "tier_1",
    "lba": "tier_1",
    # Vie étudiante / CROUS
    "crous": "tier_1",
    "crous_combine_logements_restos": "tier_1",
    # INSEE
    "insee": "tier_1",
    "insee_salaan": "tier_1",
    "insee_salaan_2023": "tier_1",
    # Ultramarins
    "ladom": "tier_1",
    "domtom_curated": "tier_1",  # curated à partir de sources officielles DROM
    # Curated officiels (sources État aggregées par OrientIA)
    "financement_dispositifs_curated": "tier_1",
    "corrections_factuelles_curated": "tier_1",  # corrections factuelles curées par audit user-test
    # ── Tier 2 — Paritaire / agence officielle ──
    "apec": "tier_2",
    "apec_observatoire_emploi_cadre_2026": "tier_2",
    "agefiph": "tier_2",
    "fiphfp": "tier_2",
    "anssi": "tier_2",
    "secnumedu": "tier_2",
    "cge": "tier_2",
    "cti": "tier_2",
    "fesic": "tier_2",
}

# Libellés humains pour `provenance.source_label` (exposés au LLM dans le JSON).
SOURCE_LABEL_MAP: dict[str, str] = {
    "parcoursup": "Parcoursup",
    "parcoursup_extended": "Parcoursup (étendu)",
    "monmaster": "MonMaster",
    "onisep": "ONISEP",
    "onisep_extended": "ONISEP (étendu)",
    "onisep_formations_extended": "ONISEP — formations étendues",
    "onisep_metiers": "ONISEP — métiers",
    "ideo_onisep": "ONISEP IDEO",
    "onisep_ideo_fiches": "ONISEP IDEO — fiches métiers",
    "rncp": "RNCP",
    "rncp_blocs": "France Compétences — blocs RNCP",
    "france_competences": "France Compétences",
    "rome_api_v4": "France Travail ROME 4.0",
    "france_travail": "France Travail",
    "ft_marche": "France Travail — marché du travail",
    "ft_offres": "France Travail — offres d'emploi",
    "ft_sortants": "France Travail — sortants de formation",
    "insersup": "InserSup MESR",
    "insersup_mesr": "InserSup MESR",
    "cereq": "Cereq Enquête Génération",
    "dares": "DARES",
    "dares_metiers_2030": "DARES Métiers 2030",
    "drees": "DREES",
    "france_strategie": "France Stratégie",
    "inserjeunes": "Inserjeunes DEPP",
    "inserjeunes_cfa": "Inserjeunes DEPP — CFA",
    "inserjeunes_depp": "Inserjeunes DEPP",
    "inserjeunes_lycee_pro": "Inserjeunes DEPP — lycée pro",
    "labonnealternance": "La Bonne Alternance",
    "lba": "La Bonne Alternance",
    "crous": "CROUS / CNOUS",
    "crous_combine_logements_restos": "CROUS — logements + restos U",
    "insee": "INSEE",
    "insee_salaan": "INSEE — salaires PCS",
    "insee_salaan_2023": "INSEE Salaan 2023",
    "ladom": "LADOM",
    "domtom_curated": "Curated DROM-COM (sources État)",
    "ip_doc_doctorat": "MESR — insertion doctorat",
    "parcours_bacheliers": "MESR — parcours bacheliers",
    "mesri_parcours_bacheliers_licence": "MESR — parcours bacheliers en licence",
    "financement_dispositifs_curated": "Curated dispositifs financement (sources État)",
    "corrections_factuelles_curated": "Corrections factuelles curées (audit user-test)",
    "apec": "APEC",
    "apec_observatoire_emploi_cadre_2026": "APEC Observatoire emploi cadre 2026",
    "agefiph": "AGEFIPH",
    "fiphfp": "FIPHFP",
    "anssi": "ANSSI",
    "secnumedu": "ANSSI label SecNumEdu",
    "cge": "Conférence des Grandes Écoles",
    "cti": "Commission des Titres d'Ingénieur",
    "fesic": "FESIC",
}


@dataclass
class FactProvenance:
    """Provenance d'une fiche selon ADR-055 (liste blanche tier 1/2/3).

    Exposée dans le JSON LLM pour traçabilité côté reviewer / utilisateur :
    chaque source a un tier explicite et un libellé humain. Les sites
    établissements (tier 3) portent un préfixe `site_etablissement_<slug>`
    dans `source` côté fiche brute.
    """
    tier: str  # "tier_1" | "tier_2" | "tier_3"
    source_label: str | None = None  # ex: "Parcoursup", "DARES Métiers 2030"
    source_url: str | None = None  # URL canonique de la source officielle (datasets, fiches)
    last_updated: str | None = None  # date YYYY-MM-DD si disponible

    def to_dict(self) -> dict[str, Any]:
        """Sérialise sans les champs None pour limiter le bruit JSON."""
        d = {"tier": self.tier}
        if self.source_label:
            d["source_label"] = self.source_label
        if self.source_url:
            d["source_url"] = self.source_url
        if self.last_updated:
            d["last_updated"] = self.last_updated
        return d


@dataclass
class FactChiffres:
    """Sous-bloc 'chiffres' de la FactCard. Tous les champs sont None par
    défaut — le contrat strict v4 dit au LLM 'si null → info non disponible'."""
    taux_acces_parcoursup_2025: float | None = None
    nombre_places: int | None = None
    duree: str | None = None
    frais_annuels: float | None = None
    taux_emploi_3ans: float | None = None
    taux_emploi_6ans: float | None = None
    # A2 (2026-06-09) — insertion court-terme InserSup/InserJeunes. Ces champs
    # EXISTENT dans insertion_pro du corpus mais n'etaient pas exposes a la
    # FactCard -> le generateur refusait a tort "pas d'info sur l'insertion a
    # 6 mois" alors que la donnee etait presente (faux refus, audit 2026-06-09).
    taux_emploi_6m: float | None = None
    taux_emploi_12m: float | None = None
    taux_emploi_18m: float | None = None
    taux_emploi_24m: float | None = None
    part_emploi_6m: float | None = None
    part_poursuite_etudes: float | None = None
    taux_cdi: float | None = None
    salaire_median_embauche: int | None = None
    pct_acceptes_debut_pp: float | None = None
    propositions_totales: int | None = None
    # ADR-054 — granularité du matching InserSup pour transparence.
    # Populé par src/collect/insersup_attach.py (Phase A.3) :
    #   "etablissement_x_discipline" (best, score 1.0)
    #   "discipline_region"          (score 0.7)
    #   "discipline_nationale"       (score 0.4, last resort)
    #   None                         (pas de match — `insertion_pro` absent)
    insertion_pro_granularite: str | None = None
    # Taille échantillon InserSup (transparence statistique).
    nombre_sortants: int | None = None
    # Bloc A (2026-06-09) — sélectivité MASTER (MonMaster), présente dans les
    # fiches mais non exposée -> faux-refus sur "quel taux d'admission en master".
    # taux_admission est NORMALISÉ en % (le brut est un ratio 0-1, cf
    # _norm_taux_admission) pour rester cohérent avec taux_acces_parcoursup_2025.
    taux_admission: float | None = None        # % 0-100
    capacite: int | None = None                # places offertes (master)
    nombre_candidats: int | None = None        # candidats phase principale
    nombre_admis: int | None = None            # acceptés au total
    rang_dernier_appele: int | None = None     # rang du dernier appelé
    alternance_possible: bool | None = None    # alternance offerte (bool, ≠ None)


@dataclass
class FactCard:
    """Structure une fiche corpus pour le LLM en mode strict v4.

    L'identité (formation/etab/ville/niveau) est obligatoire si présente — le
    LLM ne peut citer que les formations dont l'identité figure ici.
    Les chiffres sont scopés dans `chiffres` pour clarté visuelle dans le JSON.
    """
    id: str  # "S1", "S2", ... pour citations [source SX]
    formation: str
    etablissement: str | None = None
    ville: str | None = None
    region: str | None = None
    niveau: str | None = None
    statut: str | None = None  # "Public" | "Privé"
    type_diplome: str | None = None
    selectivite_code: str | None = None  # "formation sélective" | "formation non sélective"
    chiffres: FactChiffres = field(default_factory=FactChiffres)
    debouches: list[str] = field(default_factory=list)  # libellés métiers (depuis ROME)
    url: str | None = None  # url_parcoursup ou url_onisep prioritairement
    annee_donnees: int | None = None  # session Parcoursup ex 2025
    text_libre: str | None = None  # detail / text pour fiches non-Parcoursup
    domain: str | None = None  # "formation" | "metier" | "apec_region" | etc.
    # Bloc A (2026-06-09) — champs qualitatifs présents-non-exposés :
    tendance_acces: str | None = None  # évolution du taux d'accès (depuis trends)
    profil_admis: str | None = None    # résumé source-aware (mentions OU origine)
    # C2a (2026-06-09) — dispositifs de reconversion depuis voies_acces (RNCP).
    # Résumé source-aware des voies reconversion (VAE, formation continue,
    # alternance). None si aucune voie reconversion (ex : voie initiale seule).
    dispositifs_reconversion: str | None = None
    # ADR-055 — provenance avec tier de confiance, exposée au LLM via JSON.
    # None si la source de la fiche est inconnue ou hors liste blanche.
    provenance: FactProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        """Sérialise pour injection dans le user prompt LLM."""
        d = asdict(self)
        # Retire les champs None pour ne pas polluer le prompt avec du bruit
        # MAIS conserve `chiffres` même si tous null (le LLM doit voir
        # explicitement quels chiffres sont absents → "info non disponible").
        d_clean = {k: v for k, v in d.items() if k == "chiffres" or v not in (None, "", [])}
        # Sérialisation custom de provenance (omet sub-fields None pour propreté).
        if self.provenance is not None:
            d_clean["provenance"] = self.provenance.to_dict()
        elif "provenance" in d_clean:
            # asdict aurait pu produire un dict avec `tier=None` par mégarde.
            del d_clean["provenance"]
        return d_clean


def _safe_int(value: Any) -> int | None:
    """Convertit en int ou None (pas d'exception)."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    """Convertit en float ou None (pas d'exception)."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
        # NaN/inf check
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    """Convertit en str non-vide ou None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("none", "null", "n/a", "nan", "non renseigné", "non renseignee"):
        return None
    return s


def _safe_bool(value: Any) -> bool | None:
    """Convertit en bool ou None. Indispensable car `_safe_int(False)` vaut 0
    (isinstance(False, int) est True en Python) : on perdrait False -> 0 falsy."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "oui", "1"):
            return True
        if v in ("false", "non", "0"):
            return False
    return None


def _norm_taux_admission(value: Any) -> float | None:
    """Normalise le taux d'admission MonMaster (ratio 0-1) en pourcentage 0-100.

    Bloc A — piège data : `taux_admission` est un ratio (ex 0.1935), alors que
    `taux_acces_parcoursup_2025` déjà exposé est un % (ex 52.0). Sans ×100 le LLM
    citerait « 0,19 % d'admission ». On normalise au format % cohérent avec le
    reste de la FactCard. Une valeur >1 est supposée déjà en %, on la laisse.
    """
    ratio = _safe_float(value)
    if ratio is None:
        return None
    if 0 <= ratio <= 1:
        return round(ratio * 100, 1)
    return round(ratio, 1)


def _fmt_pct(value: Any) -> str | None:
    """Formate un pourcentage factuel : entier si rond, sinon 1 décimale."""
    v = _safe_float(value)
    if v is None:
        return None
    return f"{v:.0f}%" if v == int(v) else f"{v:.1f}%"


def _summarize_profil_admis(profil: Any) -> str | None:
    """Résume `profil_admis` en une phrase factuelle, SOURCE-AWARE.

    Bloc A — piège data : `profil_admis` est un dict imbriqué de schéma DIFFÉRENT
    selon la source :
      - Parcoursup : `mentions_pct` / `bac_type_pct` / `boursiers_pct`...
        = mentions AU BAC des admis + type de bac.
      - MonMaster : `pct_lg3` / `pct_but3` / `pct_master`...
        = ORIGINE (diplôme antérieur) des admis, PAS des mentions au bac.
    Confondre les deux serait un contresens factuel. On détecte le schéma par
    présence de clés et on étiquette correctement. Aucune inférence individuelle
    (conforme au non-pronostic) : on ne fait que restituer des proportions.
    """
    if not isinstance(profil, dict) or not profil:
        return None

    # Schéma Parcoursup — mentions au bac
    if "mentions_pct" in profil or "bac_type_pct" in profil:
        parts: list[str] = []
        mentions = profil.get("mentions_pct")
        if isinstance(mentions, dict):
            labels = {"tb": "très bien", "b": "bien", "ab": "assez bien", "sans": "sans mention"}
            items = [f"{labels.get(k, k)} {_fmt_pct(v)}"
                     for k, v in mentions.items() if _fmt_pct(v) is not None]
            if items:
                parts.append("mentions au bac : " + ", ".join(items))
        bac = profil.get("bac_type_pct")
        if isinstance(bac, dict):
            labels = {"general": "général", "techno": "technologique", "pro": "professionnel"}
            items = [f"{labels.get(k, k)} {_fmt_pct(v)}"
                     for k, v in bac.items() if _fmt_pct(v) is not None]
            if items:
                parts.append("type de bac : " + ", ".join(items))
        bours = _fmt_pct(profil.get("boursiers_pct"))
        if bours:
            parts.append(f"boursiers {bours}")
        femmes = _fmt_pct(profil.get("femmes_pct"))
        if femmes:
            parts.append(f"femmes {femmes}")
        return "Profil des admis (" + " ; ".join(parts) + ")" if parts else None

    # Schéma MonMaster — origine (diplôme antérieur) des admis
    if any(k in profil for k in ("pct_lg3", "pct_lp3", "pct_but3", "pct_master")):
        labels = [
            ("pct_lg3", "licence générale"),
            ("pct_lp3", "licence pro"),
            ("pct_but3", "BUT"),
            ("pct_master", "master"),
            ("pct_autre", "autre diplôme"),
        ]
        items = [f"{lib} {_fmt_pct(profil.get(k))}"
                 for k, lib in labels if _fmt_pct(profil.get(k)) is not None]
        if not items:
            return None
        out = "Origine des admis : " + ", ".join(items)
        femmes = _fmt_pct(profil.get("pct_femme"))
        if femmes:
            out += f" ; femmes {femmes}"
        return out

    # Schéma inconnu : on ne risque aucun contresens.
    return None


def _summarize_voies_acces(voies: Any) -> str | None:
    """Résume `voies_acces` (RNCP) en dispositifs de RECONVERSION, source-aware.

    C2a — `voies_acces` est un vocabulaire RNCP FERMÉ de 6 valeurs (vérifié sur
    formations.json 2026-06-09, 10072 fiches rncp/rncp_blocs). On ne mappe QUE
    les voies de reconversion adulte ; on ignore les voies initiales.

    Mapping (vocabulaire contrôlé, déterministe — pas de NLP) :
      - "Par expérience"                         -> VAE (libellé France Compétences)
      - "Après un parcours de formation continue"-> formation continue
      - "En contrat d'apprentissage"             -> alternance (apprentissage)
      - "En contrat de professionnalisation"     -> alternance (contrat pro)

    NON mappées (ne sont PAS des dispositifs de reconversion, consigne Jarvis) :
      - "...sous statut d'élève ou d'étudiant"   = voie INITIALE
      - "Par candidature individuelle"

    Garde-fous (leçon A2/Bloc A) :
      - aucune éligibilité CPF / financement déduite ici (c'est C2b, différé) ;
      - apostrophe typographique U+2019 normalisée (sinon match silencieux raté) ;
      - None si aucune voie reconversion -> "info non disponible" côté LLM.
    """
    if not isinstance(voies, list) or not voies:
        return None

    # Normalise apostrophe typographique U+2019 -> droite pour matcher le vocab.
    normalized = {
        str(v).replace("’", "'").strip().lower()
        for v in voies if isinstance(v, str)
    }

    vae = "par expérience" in normalized
    formation_continue = "après un parcours de formation continue" in normalized
    apprentissage = "en contrat d'apprentissage" in normalized
    contrat_pro = "en contrat de professionnalisation" in normalized

    parts: list[str] = []
    if vae:
        parts.append("VAE (validation des acquis de l'expérience)")
    if formation_continue:
        parts.append("formation continue")
    alt_formes = []
    if apprentissage:
        alt_formes.append("apprentissage")
    if contrat_pro:
        alt_formes.append("contrat de professionnalisation")
    if alt_formes:
        parts.append("alternance (" + ", ".join(alt_formes) + ")")

    if not parts:
        return None
    return "Dispositifs de reconversion (certification RNCP) : " + ", ".join(parts)


def _extract_debouches_libelles(debouches: Any) -> list[str]:
    """Extrait les libellés métiers depuis le champ debouches (list de dicts ROME)."""
    if not isinstance(debouches, list):
        return []
    out = []
    for d in debouches:
        if isinstance(d, dict):
            lib = _safe_str(d.get("libelle"))
            if lib:
                out.append(lib)
    return out


def _pick_url(fiche: dict) -> str | None:
    """Sélectionne l'URL la plus authoritative.

    Priorité : Parcoursup (lien direct fiche officielle) > ONISEP > url générique.

    Vague 3.8 fix (2026-05-08) — fallback sur `url_canonical` qui contient
    soit l'URL native soit un fallback ONISEP search construit par le merger
    Stage 5 NORMALIZE (cf `_resolve_fiche_url` dans run_merge_v3.py). Sans ce
    fallback, 21 946 fiches sans URL native (MonMaster 7 573, RNCP 5 181,
    inserjeunes_cfa 4 065, LBA 4 008, etc.) étaient invisibles côté LLM.
    Couverture URL côté user-facing : 33% → ~79%.
    """
    for key in ("lien_form_psup", "url_onisep", "url"):
        url = _safe_str(fiche.get(key))
        if url and url.startswith(("http://", "https://")):
            return url
    # Fallback Vague 3.8 — url_canonical (potentiellement ONISEP search fallback)
    url_canonical = _safe_str(fiche.get("url_canonical"))
    if url_canonical and url_canonical.startswith(("http://", "https://")):
        return url_canonical
    return None


def _pick_annee(fiche: dict) -> int | None:
    """Récupère l'année des données. Priorité : admission.session > annee > collected_at year."""
    admission = fiche.get("admission")
    if isinstance(admission, dict):
        annee = _safe_int(admission.get("session"))
        if annee:
            return annee
    annee = _safe_int(fiche.get("annee"))
    if annee:
        return annee
    # collected_at peut être un dict source -> date "YYYY-MM-DD"
    ca = fiche.get("collected_at")
    if isinstance(ca, dict):
        for v in ca.values():
            if isinstance(v, str) and len(v) >= 4 and v[:4].isdigit():
                year = _safe_int(v[:4])
                if year:
                    return year
    return None


def _pick_text_libre(fiche: dict, max_chars: int = 400) -> str | None:
    """Pour les fiches sans chiffres Parcoursup, récupère un texte court."""
    for key in ("text", "detail"):
        t = _safe_str(fiche.get(key))
        if t:
            return t[:max_chars]
    return None


def _pick_formation_name(fiche: dict) -> str:
    """Cascade pour récupérer le nom à exposer dans `FactCard.formation`.

    Schémas supportés (ordre de priorité) :

    **1. Champs nom directs** (formations classiques + métiers + blocs) :
    - `nom` : formations classiques (Parcoursup, MonMaster, ONISEP, RNCP, LBA)
    - `libelle_metier` : ROME 4.0 (build_rome_corpus.py, domain="metier_detail")
    - `nom_metier` : IDEO ONISEP (build_metiers_corpus.py, domain="metier")
    - `libelle` : ONISEP métiers (build via onisep_metiers.py)
    - `intitule` : France Compétences blocs (build_france_comp_blocs_corpus.py)
    - `libelle_diplome`, `libelle_formation` : autres corpora annexes
    - `fap_libelle` : DARES Métiers 2030 (Famille Activité Professionnelle)
    - `subject` : Corrections factuelles curées

    **2. Composition contextuelle** (pour les corpora discipline-based) :
    - `type_diplome` + `discipline` : InserSup ("Master LMD en Droit, sciences politiques")
    - `type_diplome` + `domaine` : Voie pré-bac ("BAC PRO en agriculture")
    - `grande_discipline` + `bac` + `mention` : Parcours bacheliers
      ("Parcours licence en Droit — bac ES mention Assez bien")

    **3. Fallback id-based** (pour APEC, CROUS, INSEE — pas d'identité formation) :
    - Extrait la partie significative de `id` (après le dernier `:`), formate.

    Fallback `(formation sans nom)` uniquement si vraiment rien n'est trouvé.
    """
    # Étape 1 — cascade champs nom directs
    for key in ("nom", "libelle_metier", "nom_metier", "libelle",
                "intitule", "libelle_diplome", "libelle_formation",
                "fap_libelle", "subject"):
        candidate = _safe_str(fiche.get(key))
        if candidate:
            return candidate

    # Étape 1.5 — fallback établissement (Inserjeunes CFA, autres stats par étab)
    # Quand un record n'a pas de nom de formation propre mais représente une
    # stat aggregée pour un établissement, on expose l'étab comme identifiant.
    # Le merger v3 attache typiquement ces records via UAI à des fiches existantes,
    # donc ce fallback n'est utilisé que si le record reste autonome.
    etab = _safe_str(fiche.get("etablissement"))
    if etab and not _safe_str(fiche.get("type_diplome")) and not _safe_str(fiche.get("discipline")):
        # Étab seul (pas de discipline ni type_diplome) → cas Inserjeunes CFA
        return etab

    # Étape 2 — compositions contextuelles
    type_dip = _safe_str(fiche.get("type_diplome"))
    discipline = _safe_str(fiche.get("discipline"))
    grande_discipline = _safe_str(fiche.get("grande_discipline"))
    domaine = _safe_str(fiche.get("domaine"))
    bac = _safe_str(fiche.get("bac"))
    mention = _safe_str(fiche.get("mention"))

    # Parcours bacheliers : "Parcours licence en {grande_discipline} — bac {bac} mention {mention}"
    if grande_discipline and bac:
        composed = f"Parcours licence en {grande_discipline} — bac {bac}"
        if mention:
            composed = f"{composed} mention {mention}"
        return composed

    # InserSup : "{type_diplome} en {discipline}"
    if type_dip and discipline:
        return f"{type_dip} en {discipline}"

    # Voie pré-bac : "{type_diplome} en {domaine}"
    if type_dip and domaine:
        return f"{type_dip} en {domaine}"

    # Discipline ou type_diplome seul
    if discipline:
        return discipline
    if type_dip:
        return type_dip

    # Étape 3 — fallback id-based (APEC, CROUS, INSEE, autres corpora identifiés par id)
    id_val = _safe_str(fiche.get("id"))
    if id_val:
        # Extrait la queue après le dernier ':' (ex "apec_region:auvergne-rhone-alpes" → "auvergne-rhone-alpes")
        tail = id_val.rsplit(":", 1)[-1] if ":" in id_val else id_val
        # Format : "auvergne-rhone-alpes" → "Auvergne Rhone Alpes"
        formatted = tail.replace("-", " ").replace("_", " ").strip()
        if formatted:
            return formatted

    return "(formation sans nom)"


def _infer_provenance(fiche: dict) -> FactProvenance | None:
    """Infère la provenance (tier + label) selon ADR-055.

    Stratégie :
      1. Si la fiche contient un dict `provenance` explicite avec `tier` valide,
         utilise-le (le merger v3 / les builders peuvent populer ce champ).
      2. Sinon, regarde `fiche['source']` et lookup dans SOURCE_TO_TIER.
         Cas spécial : préfixe `site_etablissement_<slug>` → tier_3.
      3. Si source absente/inconnue → None (la provenance ne sera pas exposée
         au LLM, choix conservatif pour éviter de mentir sur le tier).
    """
    # 1) Bloc provenance explicite déjà dans la fiche
    explicit = fiche.get("provenance")
    if isinstance(explicit, dict):
        tier = _safe_str(explicit.get("tier"))
        if tier in ("tier_1", "tier_2", "tier_3"):
            return FactProvenance(
                tier=tier,
                source_label=_safe_str(explicit.get("source_label")),
                source_url=_safe_str(explicit.get("source_url")),
                last_updated=_safe_str(explicit.get("last_updated")),
            )

    # 2) Inférence depuis fiche['source']
    raw_source = fiche.get("source")
    if not isinstance(raw_source, str):
        return None
    source = raw_source.lower().strip()
    if not source:
        return None

    # 2.a) Tier 3 — sites d'établissements (préfixe explicite)
    if source.startswith("site_etablissement_"):
        slug = source[len("site_etablissement_"):]
        label = SOURCE_LABEL_MAP.get(source) or slug.replace("_", " ").title()
        return FactProvenance(
            tier="tier_3",
            source_label=label,
            source_url=None,
            last_updated=None,
        )

    # 2.b) Tier 1 / 2 lookup
    tier = SOURCE_TO_TIER.get(source)
    if tier is None:
        return None

    return FactProvenance(
        tier=tier,
        source_label=SOURCE_LABEL_MAP.get(source),
        source_url=None,
        last_updated=None,
    )


def fiche_to_fact_card(fiche: dict, fact_id: str) -> FactCard:
    """Mappe une fiche corpus (dict JSON) vers une FactCard structurée.

    Args:
        fiche: dict (depuis formations.json). Tolérant aux champs absents.
        fact_id: identifiant court "S1", "S2", ... pour citations LLM.

    Returns:
        FactCard. Garantie : `formation` non vide. Tous les autres champs
        peuvent être None — le contrat v4 dit au LLM "si None, info non
        disponible".
    """
    nom = _pick_formation_name(fiche)

    # CHIFFRES PARCOURSUP (sous-corpus 21.5%)
    chiffres = FactChiffres(
        taux_acces_parcoursup_2025=_safe_float(fiche.get("taux_acces_parcoursup_2025")),
        nombre_places=_safe_int(fiche.get("nombre_places")),
        duree=_safe_str(fiche.get("duree")),
        frais_annuels=_safe_float(fiche.get("frais_annuels")),
        propositions_totales=_safe_int(fiche.get("propositions_totales")),
        pct_acceptes_debut_pp=_safe_float(fiche.get("pct_acceptes_debut_pp")),
        # Bloc A — sélectivité master (MonMaster). taux_admission normalisé ×100.
        taux_admission=_norm_taux_admission(fiche.get("taux_admission")),
        capacite=_safe_int(fiche.get("capacite")),
        nombre_candidats=_safe_int(fiche.get("n_candidats_pp")),
        nombre_admis=_safe_int(fiche.get("n_acceptes_total")),
        rang_dernier_appele=_safe_int(fiche.get("rang_dernier_appele")),
        alternance_possible=_safe_bool(fiche.get("alternance")),
    )
    # CHIFFRES INSERTION PRO (90% du corpus, sous insertion_pro nested)
    ip = fiche.get("insertion_pro")
    if isinstance(ip, dict):
        chiffres.taux_emploi_3ans = _safe_float(ip.get("taux_emploi_3ans"))
        chiffres.taux_emploi_6ans = _safe_float(ip.get("taux_emploi_6ans"))
        # A2 — exposer l'insertion court-terme presente dans le corpus
        chiffres.taux_emploi_6m = _safe_float(ip.get("taux_emploi_6m"))
        chiffres.taux_emploi_12m = _safe_float(ip.get("taux_emploi_12m"))
        chiffres.taux_emploi_18m = _safe_float(ip.get("taux_emploi_18m"))
        chiffres.taux_emploi_24m = _safe_float(ip.get("taux_emploi_24m"))
        chiffres.part_emploi_6m = _safe_float(ip.get("part_emploi_6m"))
        chiffres.part_poursuite_etudes = _safe_float(ip.get("part_poursuite_etudes"))
        chiffres.taux_cdi = _safe_float(ip.get("taux_cdi"))
        chiffres.salaire_median_embauche = _safe_int(ip.get("salaire_median_embauche"))

    # Bloc A — tendance d'accès : phrase pré-calculée dans trends.taux_acces.
    tendance_acces = None
    trends = fiche.get("trends")
    if isinstance(trends, dict):
        ta = trends.get("taux_acces")
        if isinstance(ta, dict):
            tendance_acces = _safe_str(ta.get("interpretation"))

    return FactCard(
        id=fact_id,
        formation=nom,
        etablissement=_safe_str(fiche.get("etablissement")),
        ville=_safe_str(fiche.get("ville")),
        region=_safe_str(fiche.get("region")),
        niveau=_safe_str(fiche.get("niveau")),
        statut=_safe_str(fiche.get("statut")),
        type_diplome=_safe_str(fiche.get("type_diplome")),
        selectivite_code=_safe_str(fiche.get("selectivite_code")),
        chiffres=chiffres,
        debouches=_extract_debouches_libelles(fiche.get("debouches")),
        url=_pick_url(fiche),
        annee_donnees=_pick_annee(fiche),
        text_libre=_pick_text_libre(fiche),
        domain=_safe_str(fiche.get("domain")) or _safe_str(fiche.get("domaine")),
        tendance_acces=tendance_acces,
        profil_admis=_summarize_profil_admis(fiche.get("profil_admis")),
        dispositifs_reconversion=_summarize_voies_acces(fiche.get("voies_acces")),
        provenance=_infer_provenance(fiche),
    )


def format_sources_for_llm(
    top_sources: list[dict],
    max_sources: int = 10,
    max_debouches_per_card: int = 5,
) -> str:
    """Sérialise les top_sources retrievées en JSON tabulaire pour le user prompt v4.

    Args:
        top_sources: liste retournée par retrieve_top_k + rerank. Chaque item
            est soit `{score, fiche}`, soit la fiche elle-même.
        max_sources: cap pour éviter prompt trop long (top-10 par défaut).
        max_debouches_per_card: cap par carte pour éviter explosion.

    Returns:
        String JSON formaté (indent=2) prêt à injecter dans le user message.
    """
    cards = []
    for i, s in enumerate(top_sources[:max_sources], 1):
        fiche = s.get("fiche") if isinstance(s, dict) and "fiche" in s else s
        if not isinstance(fiche, dict):
            continue
        card = fiche_to_fact_card(fiche, fact_id=f"S{i}")
        # Tronque debouches pour cap
        if card.debouches and len(card.debouches) > max_debouches_per_card:
            card.debouches = card.debouches[:max_debouches_per_card]
        cards.append(card.to_dict())
    return json.dumps(cards, ensure_ascii=False, indent=2)


def has_any_chiffres(card: FactCard) -> bool:
    """Vrai si la FactCard contient AU MOINS un chiffre exploitable."""
    c = card.chiffres
    return any(
        v is not None for v in (
            c.taux_acces_parcoursup_2025,
            c.nombre_places,
            c.duree,
            c.frais_annuels,
            c.taux_emploi_3ans,
            c.taux_emploi_6ans,
            c.taux_cdi,
            c.salaire_median_embauche,
        )
    )
