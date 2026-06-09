"""Tests src/rag/fact_card.py — extraction structurée fiches pour contrat v4."""
from __future__ import annotations

import json

from src.rag.fact_card import (
    FactCard,
    FactChiffres,
    FactProvenance,
    SOURCE_TO_TIER,
    SOURCE_LABEL_MAP,
    fiche_to_fact_card,
    format_sources_for_llm,
    has_any_chiffres,
)


# ─────────────── Fixtures de fiches réalistes ───────────────


def fiche_parcoursup_riche() -> dict:
    """Fiche typique sous-corpus Parcoursup (21.5%) avec tous les chiffres."""
    return {
        "source": "parcoursup",
        "domaine": "cyber",
        "nom": "Bachelor Cybersécurité des systèmes industriels",
        "etablissement": "Lycée Emmanuel d'Alzon",
        "ville": "Nîmes",
        "region": "Occitanie",
        "niveau": "bac+3",
        "statut": "Privé",
        "type_diplome": "formation d'école spécialisée",
        "duree": "3 ans",
        "taux_acces_parcoursup_2025": 52.0,
        "nombre_places": 25,
        "propositions_totales": 53,
        "pct_acceptes_debut_pp": 0.0,
        "selectivite_code": "formation sélective",
        "lien_form_psup": "https://dossierappel.parcoursup.fr/?g_ta_cod=39320",
        "url_onisep": "https://www.onisep.fr/.../FOR.9891",
        "admission": {
            "session": 2025,
            "taux_acces": 52.0,
            "places": 25,
        },
        "insertion_pro": {
            "taux_emploi_3ans": 0.86,
            "taux_emploi_6ans": 0.91,
            "taux_cdi": 0.83,
            "salaire_median_embauche": 1740,
            "source": "cereq",
        },
        "debouches": [
            {"code_rome": "M1812", "libelle": "RSSI"},
            {"code_rome": "M1817", "libelle": "Administrateur sécurité"},
            {"code_rome": "M1819", "libelle": "Ingénieur sécurité"},
        ],
        "collected_at": {"parcoursup": "2026-04-24"},
    }


def fiche_monmaster_simple() -> dict:
    """Fiche MonMaster (master) sans chiffres Parcoursup, juste insertion_pro."""
    return {
        "source": "monmaster",
        "phase": "master",
        "nom": "DROIT DES AFFAIRES — Juriste d'affaires fiscaliste",
        "etablissement": "Université Paris Cité",
        "ville": "MALAKOFF",
        "niveau": "bac+5",
        "insertion_pro": {
            "taux_emploi_3ans": 0.85,
            "salaire_median_embauche": 2570,
        },
        "url_onisep": "https://www.onisep.fr/.../FOR.10535",
    }


def fiche_rncp_minimal() -> dict:
    """Fiche RNCP nationale sans école nommée — cas des fiches multi-corpus."""
    return {
        "source": "rncp",
        "nom": "Cybersécurité",
        "rncp": "RNCP12345",
        "niveau": "bac+5",
        "text": "Titre RNCP de niveau 7 en cybersécurité. Compétences : audit, "
                "pentest, gouvernance SSI, conformité. Reconnu par l'État.",
    }


def fiche_corrupted() -> dict:
    """Fiche avec champs corrompus (None, NaN, strings vides)."""
    return {
        "nom": "  Test Formation  ",  # whitespace à trim
        "etablissement": "",
        "ville": "non renseigné",
        "niveau": None,
        "taux_acces_parcoursup_2025": "abc",  # non parsable
        "nombre_places": "25",  # str → int OK
        "insertion_pro": {
            "taux_emploi_3ans": "0.86",  # str → float OK
            "salaire_median_embauche": float("nan"),  # NaN → None
        },
        "debouches": [
            {"libelle": ""},  # vide → skip
            {"libelle": "Métier valide"},
            "non-dict-item",  # type wrong → skip
        ],
    }


# ─────────────── Tests fiche_to_fact_card ───────────────


class TestFicheToFactCardParcoursupRiche:
    def test_extracts_identity(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.id == "S1"
        assert card.formation == "Bachelor Cybersécurité des systèmes industriels"
        assert card.etablissement == "Lycée Emmanuel d'Alzon"
        assert card.ville == "Nîmes"
        assert card.region == "Occitanie"
        assert card.niveau == "bac+3"
        assert card.statut == "Privé"

    def test_extracts_chiffres_parcoursup(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.chiffres.taux_acces_parcoursup_2025 == 52.0
        assert card.chiffres.nombre_places == 25
        assert card.chiffres.duree == "3 ans"
        assert card.chiffres.propositions_totales == 53

    def test_extracts_chiffres_insertion_pro(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.chiffres.taux_emploi_3ans == 0.86
        assert card.chiffres.taux_emploi_6ans == 0.91
        assert card.chiffres.taux_cdi == 0.83
        assert card.chiffres.salaire_median_embauche == 1740

    def test_extracts_debouches_libelles(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert "RSSI" in card.debouches
        assert "Administrateur sécurité" in card.debouches
        assert len(card.debouches) == 3

    def test_picks_parcoursup_url_in_priority(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.url == "https://dossierappel.parcoursup.fr/?g_ta_cod=39320"

    def test_picks_annee_from_admission_session(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.annee_donnees == 2025


class TestFicheToFactCardMonMaster:
    def test_extracts_identity_without_parcoursup_chiffres(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.formation == "DROIT DES AFFAIRES — Juriste d'affaires fiscaliste"
        assert card.etablissement == "Université Paris Cité"
        assert card.niveau == "bac+5"

    def test_chiffres_parcoursup_are_none(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.chiffres.taux_acces_parcoursup_2025 is None
        assert card.chiffres.nombre_places is None

    def test_chiffres_insertion_pro_present(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.chiffres.taux_emploi_3ans == 0.85
        assert card.chiffres.salaire_median_embauche == 2570

    def test_url_falls_back_to_onisep(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.url == "https://www.onisep.fr/.../FOR.10535"


class TestFicheToFactCardRNCPMinimal:
    def test_extracts_text_libre_when_no_etab(self):
        card = fiche_to_fact_card(fiche_rncp_minimal(), "S1")
        assert card.formation == "Cybersécurité"
        assert card.etablissement is None
        assert card.text_libre is not None
        assert "audit" in card.text_libre.lower()

    def test_no_chiffres_disponibles(self):
        card = fiche_to_fact_card(fiche_rncp_minimal(), "S1")
        assert not has_any_chiffres(card)


class TestFicheToFactCardCorrupted:
    def test_trims_whitespace(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.formation == "Test Formation"

    def test_empty_strings_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.etablissement is None  # was ""

    def test_non_renseigne_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.ville is None  # was "non renseigné"

    def test_unparseable_int_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.taux_acces_parcoursup_2025 is None  # was "abc"

    def test_str_int_parsed(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.nombre_places == 25  # was "25"

    def test_str_float_parsed(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.taux_emploi_3ans == 0.86

    def test_nan_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.salaire_median_embauche is None

    def test_bad_debouches_filtered(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.debouches == ["Métier valide"]

    def test_no_url_returns_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.url is None


# ─────────────── Tests has_any_chiffres ───────────────


class TestHasAnyChiffres:
    def test_parcoursup_riche_has_chiffres(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert has_any_chiffres(card)

    def test_monmaster_with_insertion_has_chiffres(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert has_any_chiffres(card)

    def test_rncp_minimal_no_chiffres(self):
        card = fiche_to_fact_card(fiche_rncp_minimal(), "S1")
        assert not has_any_chiffres(card)


# ─────────────── Tests format_sources_for_llm (sérialisation JSON) ───────────────


class TestFormatSourcesForLLM:
    def test_handles_list_of_score_fiche_dicts(self):
        """Format pipeline : list[{score: float, fiche: dict}]."""
        sources = [
            {"score": 0.9, "fiche": fiche_parcoursup_riche()},
            {"score": 0.7, "fiche": fiche_monmaster_simple()},
        ]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert len(parsed) == 2
        assert parsed[0]["id"] == "S1"
        assert parsed[1]["id"] == "S2"
        assert parsed[0]["formation"].startswith("Bachelor Cyber")

    def test_handles_list_of_raw_fiches(self):
        """Format alternatif : la liste contient les fiches directement."""
        sources = [fiche_parcoursup_riche(), fiche_monmaster_simple()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert len(parsed) == 2

    def test_caps_at_max_sources(self):
        sources = [fiche_parcoursup_riche()] * 15
        out = format_sources_for_llm(sources, max_sources=10)
        parsed = json.loads(out)
        assert len(parsed) == 10
        # IDs séquentiels S1..S10
        assert parsed[0]["id"] == "S1"
        assert parsed[-1]["id"] == "S10"

    def test_chiffres_block_always_present_even_if_all_null(self):
        """Le LLM doit voir les `null` explicites pour décider 'info non disponible'."""
        sources = [fiche_rncp_minimal()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        # `chiffres` doit être présent, avec tous les champs null
        assert "chiffres" in parsed[0]
        for v in parsed[0]["chiffres"].values():
            assert v is None

    def test_none_fields_stripped_except_chiffres(self):
        """Les champs None hors `chiffres` ne polluent pas le JSON."""
        sources = [fiche_rncp_minimal()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        # etablissement absent (was None) ; chiffres présent (block conservé)
        assert "etablissement" not in parsed[0]
        assert "chiffres" in parsed[0]

    def test_skips_non_dict_sources(self):
        """Items malformés ne crashent pas, sont skippés silencieusement."""
        sources = [
            {"score": 0.9, "fiche": fiche_parcoursup_riche()},
            "not-a-dict",
            None,
            {"fiche": "not-a-dict-either"},
        ]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        # Seule la 1re carte est valide
        assert len(parsed) == 1

    def test_caps_debouches_per_card(self):
        f = fiche_parcoursup_riche()
        f["debouches"] = [{"libelle": f"Métier {i}"} for i in range(20)]
        sources = [f]
        out = format_sources_for_llm(sources, max_debouches_per_card=3)
        parsed = json.loads(out)
        assert len(parsed[0]["debouches"]) == 3


# ─────────────── Tests provenance / tier ADR-055 ───────────────


class TestProvenanceInference:
    """Vérifie l'inférence du tier 1/2/3 depuis le champ source de la fiche."""

    def test_parcoursup_inferred_as_tier_1(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_1"
        assert card.provenance.source_label == "Parcoursup"

    def test_monmaster_inferred_as_tier_1(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_1"

    def test_rncp_inferred_as_tier_1(self):
        card = fiche_to_fact_card(fiche_rncp_minimal(), "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_1"

    def test_unknown_source_returns_none(self):
        """Source non listée dans SOURCE_TO_TIER → provenance None (conservatif)."""
        fiche = {"nom": "X", "source": "totally_unknown_source"}
        card = fiche_to_fact_card(fiche, "S1")
        assert card.provenance is None

    def test_missing_source_returns_none(self):
        fiche = {"nom": "X"}  # pas de champ `source`
        card = fiche_to_fact_card(fiche, "S1")
        assert card.provenance is None

    def test_apec_inferred_as_tier_2(self):
        fiche = {"nom": "Marché cadre Bretagne", "source": "apec", "domain": "apec_region"}
        card = fiche_to_fact_card(fiche, "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_2"
        assert card.provenance.source_label == "APEC"

    def test_secnumedu_inferred_as_tier_2(self):
        fiche = {"nom": "X", "source": "secnumedu"}
        card = fiche_to_fact_card(fiche, "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_2"

    def test_site_etablissement_inferred_as_tier_3(self):
        """Préfixe site_etablissement_<slug> → tier_3 (info pratique uniquement)."""
        fiche = {"nom": "HEC Paris", "source": "site_etablissement_hec"}
        card = fiche_to_fact_card(fiche, "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_3"

    def test_explicit_provenance_block_overrides_source(self):
        """Si la fiche contient déjà un bloc provenance explicite, l'utiliser."""
        fiche = {
            "nom": "X",
            "source": "parcoursup",  # serait inféré tier_1 sinon
            "provenance": {
                "tier": "tier_2",  # override explicite
                "source_label": "Custom Label",
                "source_url": "https://example.org",
                "last_updated": "2026-01-15",
            },
        }
        card = fiche_to_fact_card(fiche, "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_2"
        assert card.provenance.source_label == "Custom Label"
        assert card.provenance.source_url == "https://example.org"
        assert card.provenance.last_updated == "2026-01-15"

    def test_explicit_provenance_with_invalid_tier_falls_back_to_source_inference(self):
        """tier invalide dans provenance explicite → fallback sur inférence source."""
        fiche = {
            "nom": "X",
            "source": "parcoursup",
            "provenance": {"tier": "tier_42_oups"},  # invalide
        }
        card = fiche_to_fact_card(fiche, "S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_1"  # fallback inféré depuis source


class TestProvenanceSerialization:
    """Vérifie la sérialisation propre dans le JSON LLM."""

    def test_provenance_present_in_json_when_inferred(self):
        sources = [fiche_parcoursup_riche()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert "provenance" in parsed[0]
        assert parsed[0]["provenance"]["tier"] == "tier_1"
        assert parsed[0]["provenance"]["source_label"] == "Parcoursup"

    def test_provenance_absent_when_unknown_source(self):
        """Source inconnue → pas de champ provenance dans le JSON (silent)."""
        fiche = {"nom": "Test", "source": "agregateur_prive_quelconque"}
        out = format_sources_for_llm([fiche])
        parsed = json.loads(out)
        assert "provenance" not in parsed[0]

    def test_provenance_subfields_none_omitted(self):
        """Les sous-champs None de provenance ne sont pas dans le JSON (propreté)."""
        sources = [fiche_parcoursup_riche()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        # source_url + last_updated sont None par défaut → omis
        assert "source_url" not in parsed[0]["provenance"]
        assert "last_updated" not in parsed[0]["provenance"]

    def test_provenance_explicit_subfields_serialized(self):
        """Les sous-champs explicites (URL, date) apparaissent dans le JSON."""
        fiche = {
            "nom": "Test",
            "source": "dares",
            "provenance": {
                "tier": "tier_1",
                "source_label": "DARES Métiers 2030",
                "source_url": "https://dares.travail-emploi.gouv.fr/...",
                "last_updated": "2026-04-15",
            },
        }
        out = format_sources_for_llm([fiche])
        parsed = json.loads(out)
        prov = parsed[0]["provenance"]
        assert prov["tier"] == "tier_1"
        assert prov["source_label"] == "DARES Métiers 2030"
        assert prov["source_url"] == "https://dares.travail-emploi.gouv.fr/..."
        assert prov["last_updated"] == "2026-04-15"


# ─────────────── Tests FactChiffres extension ADR-054 ───────────────


class TestFactChiffresInsertionGranularite:
    """Vérifie les nouveaux champs `insertion_pro_granularite` + `nombre_sortants`
    (populés par insersup_attach Phase A.3 — pour Phase A.1 ils restent None).
    """

    def test_default_granularite_is_none(self):
        """Par défaut, granularité absente (sera populée par insersup_attach)."""
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.chiffres.insertion_pro_granularite is None
        assert card.chiffres.nombre_sortants is None

    def test_granularite_in_json_when_populated(self):
        """Quand FactChiffres porte une granularité, elle apparaît dans le JSON."""
        # Simulate ce que fera insersup_attach en Phase A.3
        from src.rag.fact_card import FactChiffres
        chiffres = FactChiffres(
            taux_emploi_3ans=0.85,
            insertion_pro_granularite="discipline_region",
            nombre_sortants=128,
        )
        from src.rag.fact_card import FactCard
        card = FactCard(id="S1", formation="Test", chiffres=chiffres)
        d = card.to_dict()
        assert d["chiffres"]["insertion_pro_granularite"] == "discipline_region"
        assert d["chiffres"]["nombre_sortants"] == 128


# ─────────────── Tests rétrocompat (le contrat strict v4 doit rester valide) ───────────────


class TestBackwardCompatStrictV4Contract:
    """Garantit que les contrats R1/R2/R3 du SYSTEM_PROMPT_V4_STRICT restent
    respectés après l'ajout de provenance/tier (ADR-055).
    """

    def test_chiffres_block_still_always_present(self):
        """R1 : le LLM doit toujours voir `chiffres` même si tous null."""
        sources = [fiche_rncp_minimal()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert "chiffres" in parsed[0]

    def test_id_format_preserved(self):
        """R3 : citations [source SX] — le format S1, S2... reste intact."""
        sources = [fiche_parcoursup_riche(), fiche_monmaster_simple()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert parsed[0]["id"] == "S1"
        assert parsed[1]["id"] == "S2"

    def test_formation_required(self):
        """R2 : identité formation toujours présente (jamais omise)."""
        sources = [fiche_rncp_minimal()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert "formation" in parsed[0]
        assert parsed[0]["formation"] == "Cybersécurité"


# ─────────────── Tests SOURCE_TO_TIER mapping ───────────────


class TestSourceToTierMapping:
    """Sanity checks sur le mapping ADR-055 lui-même."""

    def test_all_tier_values_are_valid(self):
        for source, tier in SOURCE_TO_TIER.items():
            assert tier in ("tier_1", "tier_2", "tier_3"), (
                f"source '{source}' has invalid tier '{tier}'"
            )

    def test_tier_1_majority(self):
        """Tier 1 (officiel État) doit être largement majoritaire."""
        n_t1 = sum(1 for t in SOURCE_TO_TIER.values() if t == "tier_1")
        n_total = len(SOURCE_TO_TIER)
        assert n_t1 / n_total >= 0.6, "tier_1 doit être ≥60% des sources listées"

    def test_critical_sources_listed(self):
        """Les sources critiques d'OrientIA sont bien dans la liste blanche."""
        required = ["parcoursup", "monmaster", "onisep", "rncp", "insersup",
                    "dares", "apec", "crous", "france_travail"]
        for src in required:
            assert src in SOURCE_TO_TIER, f"source critique manquante : {src}"


# ─────────────── Bloc A (2026-06-09) — champs présents-non-exposés ───────────────
#
# Généralisation d'A2 : des champs factuels EXISTENT dans les fiches mais ne sont
# pas mappés à la FactCard, donc le générateur ne peut pas les citer (faux-refus).
# C0 a inventorié ces champs ; la re-vérification data a montré 3 pièges :
#   1. taux_admission (monmaster) = ratio 0-1, PAS un % 0-100 -> normaliser ×100
#   2. profil_admis = dict imbriqué POLYSÉMIQUE (schéma monmaster ≠ parcoursup)
#   3. mention = polysémique (spécialité master sur monmaster) -> EXCLU de Bloc A


def fiche_monmaster_bloc_a() -> dict:
    """MonMaster réelle (schéma observé dans formations.json 2026-06-09)."""
    return {
        "source": "monmaster",
        "phase": "master",
        "nom": "MEEF Acoustique et musicologie",
        "etablissement": "Sorbonne Université",
        "ville": "PARIS",
        "niveau": "bac+5",
        "taux_admission": 0.1935483870967742,   # ratio 0-1 (≈ 19,4 %)
        "capacite": 12,
        "n_candidats_pp": 62,
        "n_acceptes_total": 12,
        "rang_dernier_appele": 20,
        "alternance": False,                      # bool valide (≠ None)
        "profil_admis": {                         # schéma MonMaster = origine parcours
            "pct_lg3": 50.0, "pct_lp3": 0.0, "pct_but3": 16.7,
            "pct_master": 0.0, "pct_autre": 8.3, "pct_femme": 0.0,
            "pct_etab": 16.7, "pct_lieu_acad": 16.7,
        },
        "mention": "ACOUSTIQUE ET MUSICOLOGIE",   # NOM de spécialité, PAS une stat
    }


def fiche_parcoursup_bloc_a() -> dict:
    """Parcoursup réelle avec trends + profil_admis (schéma observé)."""
    return {
        "source": "parcoursup",
        "nom": "BUT Informatique",
        "etablissement": "IUT Lyon 1",
        "ville": "Villeurbanne",
        "niveau": "bac+3",
        "taux_acces_parcoursup_2025": 43.0,
        "trends": {
            "taux_acces": {
                "direction": "stable", "delta_pp": 6.0,
                "start_year": 2023, "end_year": 2025,
                "start_value": 37.0, "end_value": 43.0,
                "interpretation": "taux d'accès stable 2023→2025 (37% → 43%)",
            },
            "places": {"direction": "stable", "delta": 0, "interpretation": None},
        },
        "profil_admis": {                         # schéma Parcoursup = mentions au bac
            "mentions_pct": {"tb": 10.0, "b": 21.0, "ab": 44.0, "sans": 26.0},
            "bac_type_pct": {"general": 85.0, "techno": 15.0, "pro": 0.0},
            "boursiers_pct": 16.0, "femmes_pct": 49.0,
            "neobacheliers_pct": 95.0,
        },
    }


class TestFicheToFactCardBlocA:
    """Mappings Bloc A : taux_admission, sélectivité master, alternance,
    tendance d'accès, profil_admis source-aware. mention reste exclue."""

    # --- taux_admission : ratio 0-1 -> % 0-100 ---
    def test_taux_admission_normalise_en_pourcent(self):
        card = fiche_to_fact_card(fiche_monmaster_bloc_a(), "S1")
        # 0.1935… -> 19.4 (et SURTOUT pas 0.19, sinon le LLM cite « 0,19 % »)
        assert card.chiffres.taux_admission == 19.4

    def test_taux_admission_un_devient_cent(self):
        f = fiche_monmaster_bloc_a(); f["taux_admission"] = 1.0
        assert fiche_to_fact_card(f, "S1").chiffres.taux_admission == 100.0

    def test_taux_admission_absent_reste_none(self):
        f = fiche_monmaster_bloc_a(); del f["taux_admission"]
        assert fiche_to_fact_card(f, "S1").chiffres.taux_admission is None

    # --- scalaires de sélectivité master ---
    def test_selectivite_scalaires_master(self):
        c = fiche_to_fact_card(fiche_monmaster_bloc_a(), "S1").chiffres
        assert c.capacite == 12
        assert c.nombre_candidats == 62
        assert c.nombre_admis == 12
        assert c.rang_dernier_appele == 20

    # --- alternance booléen (False doit être préservé, ≠ None) ---
    def test_alternance_false_preservee(self):
        card = fiche_to_fact_card(fiche_monmaster_bloc_a(), "S1")
        assert card.chiffres.alternance_possible is False

    def test_alternance_true(self):
        f = fiche_monmaster_bloc_a(); f["alternance"] = True
        assert fiche_to_fact_card(f, "S1").chiffres.alternance_possible is True

    def test_alternance_absente_reste_none(self):
        f = fiche_monmaster_bloc_a(); del f["alternance"]
        assert fiche_to_fact_card(f, "S1").chiffres.alternance_possible is None

    # --- tendance d'accès depuis trends.taux_acces.interpretation ---
    def test_tendance_acces_depuis_trends(self):
        card = fiche_to_fact_card(fiche_parcoursup_bloc_a(), "S1")
        assert card.tendance_acces == "taux d'accès stable 2023→2025 (37% → 43%)"

    def test_tendance_acces_absente_reste_none(self):
        card = fiche_to_fact_card(fiche_monmaster_bloc_a(), "S1")
        assert card.tendance_acces is None

    # --- profil_admis SOURCE-AWARE (2 schémas distincts) ---
    def test_profil_admis_parcoursup_mentions(self):
        p = fiche_to_fact_card(fiche_parcoursup_bloc_a(), "S1").profil_admis
        assert p is not None
        assert "mention" in p.lower()        # schéma parcoursup = mentions au bac
        assert "44" in p                     # AB 44 %
        assert "boursier" in p.lower() and "16" in p

    def test_profil_admis_monmaster_origine(self):
        p = fiche_to_fact_card(fiche_monmaster_bloc_a(), "S1").profil_admis
        assert p is not None
        assert "origine" in p.lower()        # schéma monmaster = origine parcours
        assert "50" in p                     # 50 % L3 générale
        assert "mention" not in p.lower()    # NE PAS inventer des mentions au bac

    def test_profil_admis_schema_inconnu_reste_none(self):
        f = fiche_monmaster_bloc_a(); f["profil_admis"] = {"clef_inconnue": 42}
        assert fiche_to_fact_card(f, "S1").profil_admis is None

    # --- mention EXCLUE de Bloc A (garde anti-contresens factuel) ---
    def test_mention_non_exposee(self):
        d = fiche_to_fact_card(fiche_monmaster_bloc_a(), "S1").to_dict()
        assert "mention" not in d
        assert "mention" not in d.get("chiffres", {})


# ─────────────── C2a — voies_acces -> dispositifs reconversion ───────────────
#
# Généralisation d'A2/Bloc A : `voies_acces` (vocabulaire RNCP fermé de 6 valeurs,
# 10072 fiches rncp + rncp_blocs) encode les dispositifs de reconversion (VAE,
# formation continue, alternance) mais n'est PAS exposé à la FactCard -> le
# générateur refuse à tort les questions reconversion alors que la donnée existe.
# Champ de citation pur (zéro re-embed). Mapping déterministe, source-aware.
#
# Garde-fous (audit data réelle 2026-06-09 + consigne Jarvis) :
#   1. "Par expérience" = la voie VAE (libellé France Compétences standard) -> SÛR.
#   2. PAS d'éligibilité CPF / financement déduite de voies_acces (c'est C2b, différé).
#   3. "sous statut d'élève ou d'étudiant" = voie INITIALE, NON reconversion -> non mappé.
#   4. "Par candidature individuelle" = pas un dispositif de reconversion -> non mappé.
#   5. Apostrophe typographique U+2019 dans la data ("d'apprentissage") -> normaliser.

# Les 6 chaînes EXACTES observées dans formations.json (apostrophes U+2019 préservées).
VA_VAE = "Par expérience"
VA_FC = "Après un parcours de formation continue"
VA_PRO = "En contrat de professionnalisation"
VA_APP = "En contrat d’apprentissage"                       # U+2019
VA_INIT = "Après un parcours de formation sous statut d’élève ou d’étudiant"  # U+2019 x2
VA_CAND = "Par candidature individuelle"


def fiche_rncp_voies_acces(voies: list[str]) -> dict:
    """Fiche RNCP réelle (schéma observé) avec une liste voies_acces donnée."""
    return {
        "source": "rncp",
        "nom": "Accompagnant éducatif et social",
        "niveau": "bac",
        "voies_acces": list(voies),
    }


class TestFicheToFactCardVoiesAccesC2a:
    """C2a : mapping voies_acces -> dispositifs_reconversion (citation, source-aware)."""

    # --- VAE depuis "Par expérience" (mapping le plus important : 9834 fiches) ---
    def test_vae_depuis_par_experience(self):
        card = fiche_to_fact_card(fiche_rncp_voies_acces([VA_VAE]), "S1")
        d = card.dispositifs_reconversion
        assert d is not None
        assert "VAE" in d
        assert "expérience" in d.lower()

    # --- formation continue ---
    def test_formation_continue(self):
        card = fiche_to_fact_card(fiche_rncp_voies_acces([VA_FC]), "S1")
        assert card.dispositifs_reconversion is not None
        assert "formation continue" in card.dispositifs_reconversion.lower()

    # --- alternance : apprentissage + contrat pro regroupés ---
    def test_alternance_groupee(self):
        card = fiche_to_fact_card(fiche_rncp_voies_acces([VA_APP, VA_PRO]), "S1")
        d = card.dispositifs_reconversion
        assert d is not None
        assert "alternance" in d.lower()
        assert "apprentissage" in d.lower()
        assert "professionnalisation" in d.lower()

    # --- piège Unicode : apostrophe typographique U+2019 doit matcher ---
    def test_apostrophe_typographique_matchee(self):
        # VA_APP contient bien U+2019, pas l'apostrophe droite
        assert "’" in VA_APP
        card = fiche_to_fact_card(fiche_rncp_voies_acces([VA_APP]), "S1")
        assert card.dispositifs_reconversion is not None
        assert "alternance" in card.dispositifs_reconversion.lower()

    # --- les 6 valeurs réelles : 3 dispositifs présents, ordre reconversion-first ---
    def test_complet_ordre_reconversion(self):
        toutes = [VA_VAE, VA_FC, VA_PRO, VA_APP, VA_INIT, VA_CAND]
        d = fiche_to_fact_card(fiche_rncp_voies_acces(toutes), "S1").dispositifs_reconversion
        assert d is not None
        assert "VAE" in d
        assert "formation continue" in d.lower()
        assert "alternance" in d.lower()
        # ordre : VAE avant alternance (reconversion-first)
        assert d.index("VAE") < d.lower().index("alternance")

    # --- voie INITIALE seule (statut élève/étudiant) = NON reconversion -> None ---
    def test_statut_eleve_etudiant_seul_non_mappe(self):
        card = fiche_to_fact_card(fiche_rncp_voies_acces([VA_INIT]), "S1")
        assert card.dispositifs_reconversion is None

    # --- candidature individuelle seule = pas un dispositif reconversion -> None ---
    def test_candidature_individuelle_seule_non_mappe(self):
        card = fiche_to_fact_card(fiche_rncp_voies_acces([VA_CAND]), "S1")
        assert card.dispositifs_reconversion is None

    # --- voies initiales mélangées : seules les reconversion remontent ---
    def test_init_et_cand_ignorees_si_vae_present(self):
        card = fiche_to_fact_card(fiche_rncp_voies_acces([VA_INIT, VA_CAND, VA_VAE]), "S1")
        d = card.dispositifs_reconversion
        assert d is not None
        assert "VAE" in d
        # la voie initiale ne doit PAS apparaître comme dispositif reconversion
        assert "initial" not in d.lower()
        assert "statut" not in d.lower()

    # --- absence / vide -> None ---
    def test_voies_acces_absente_reste_none(self):
        f = fiche_rncp_voies_acces([VA_VAE]); del f["voies_acces"]
        assert fiche_to_fact_card(f, "S1").dispositifs_reconversion is None

    def test_voies_acces_liste_vide_reste_none(self):
        assert fiche_to_fact_card(fiche_rncp_voies_acces([]), "S1").dispositifs_reconversion is None

    # --- valeur inconnue (hors vocab fermé) seule -> None (ne rien inventer) ---
    def test_valeur_inconnue_seule_reste_none(self):
        card = fiche_to_fact_card(fiche_rncp_voies_acces(["Par téléportation"]), "S1")
        assert card.dispositifs_reconversion is None

    # --- garde-fou : JAMAIS de claim CPF/financement depuis voies_acces (C2b différé) ---
    def test_pas_de_claim_cpf_ni_financement(self):
        toutes = [VA_VAE, VA_FC, VA_PRO, VA_APP, VA_INIT, VA_CAND]
        d = fiche_to_fact_card(fiche_rncp_voies_acces(toutes), "S1").dispositifs_reconversion
        assert d is not None
        low = d.lower()
        assert "cpf" not in low
        assert "financ" not in low
        assert "éligible" not in low and "eligible" not in low

    # --- sérialisation to_dict ---
    def test_present_dans_to_dict(self):
        d = fiche_to_fact_card(fiche_rncp_voies_acces([VA_VAE]), "S1").to_dict()
        assert "dispositifs_reconversion" in d

    def test_absent_de_to_dict_si_none(self):
        d = fiche_to_fact_card(fiche_rncp_voies_acces([VA_INIT]), "S1").to_dict()
        assert "dispositifs_reconversion" not in d
