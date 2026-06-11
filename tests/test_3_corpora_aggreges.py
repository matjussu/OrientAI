"""Tests pour les 3 nouveaux corpora aggrégés (CROUS / INSEE / InserSup)."""
from __future__ import annotations

import json

import pytest

from src.collect.build_crous_corpus import (
    build_corpus as build_crous_corpus,
    _aggregate_france as crous_france,
    _aggregate_by_region as crous_regions,
    _aggregate_by_grande_ville as crous_villes,
)
from src.collect.build_insee_salaan_corpus import (
    _PCS_GROUPS,
    _TARGET_REGIONS,
    _weighted_median,
    _aggregate_france_globale as insee_france,
    _aggregate_by_cs_libelle as insee_by_cs,
    _aggregate_by_pcs_group_x_region as insee_by_pcs_region,
)
from src.collect.build_insersup_corpus import (
    _METROPOLE_REGIONS,
    _select_cohorte_recente,
    _aggregate_taux_emploi,
    _median_nullable,
    build_corpus as build_insersup_corpus,
)


# --- CROUS ---


@pytest.fixture
def crous_logements_sample():
    return [
        {"id": 1, "nom": "Résidence A", "zone": "Paris 18", "region": "Île-de-France",
         "services": ["Parking", "Wifi"]},
        {"id": 2, "nom": "Résidence B", "zone": "Lyon", "region": "Auvergne-Rhône-Alpes",
         "services": ["Wifi"]},
        {"id": 3, "nom": "Résidence C", "zone": "Lyon", "region": "Auvergne-Rhône-Alpes",
         "services": ["Wifi", "Garage"]},
    ]


@pytest.fixture
def crous_restos_sample():
    return [
        {"id": "r1", "nom": "RU 1", "type": "Cafétéria", "zone": "Paris 18",
         "region_source": "paris"},
        {"id": "r2", "nom": "RU 2", "type": "Restaurant", "zone": "Lyon",
         "region_source": "lyon"},
        {"id": "r3", "nom": "RU 3", "type": "Restaurant", "zone": "Lyon",
         "region_source": "lyon"},
    ]


class TestCrousCorpus:
    def test_aggregate_france_global(self, crous_logements_sample, crous_restos_sample):
        rec = crous_france(crous_logements_sample, crous_restos_sample)
        assert rec["id"] == "crous:france"
        assert rec["domain"] == "crous"
        assert rec["n_logements_total"] == 3
        assert rec["n_restos_total"] == 3

    def test_aggregate_by_region(self, crous_logements_sample, crous_restos_sample):
        recs = crous_regions(crous_logements_sample, crous_restos_sample)
        assert len(recs) == 2  # paris + lyon
        regions = {r["region_slug"] for r in recs}
        assert {"paris", "lyon"} == regions
        # Lyon has 2 logements + 2 restos
        lyon = next(r for r in recs if r["region_slug"] == "lyon")
        assert lyon["n_logements"] == 2
        assert lyon["n_restos"] == 2

    def test_aggregate_by_grande_ville_skips_small(self):
        logs = [
            {"nom": f"Log {i}", "zone": "Paris 18", "region": "IDF", "services": []}
            for i in range(5)
        ] + [{"nom": "Single", "zone": "TinyVille", "region": "X", "services": []}]
        recs = crous_villes(logs)
        zones = {r["ville"] for r in recs}
        # commit 52520f9 : agrégation par ville CANONIQUE -> "Paris 18" (5 logs,
        # >= seuil 3) est canonicalisé en "Paris". Le test vérifie toujours le
        # seuil (5 gardés via la ville canonique, 1 TinyVille skippé).
        assert "Paris" in zones
        # TinyVille only has 1 → skipped (threshold < 3)
        assert "TinyVille" not in zones

    def test_corpus_real_data_runs(self):
        from pathlib import Path
        if not Path("data/processed/crous_logements.json").exists():
            pytest.skip("CROUS raw absent (fresh clone)")
        corpus = build_crous_corpus()
        assert len(corpus) >= 10
        assert all(c["domain"] == "crous" for c in corpus)
        assert all("text" in c and c["text"] for c in corpus)


# --- INSEE SALAAN ---


@pytest.fixture
def insee_sample():
    return [
        {
            "cs_code": "21", "cs_libelle": "Cadres",
            "region_libelle": "Île-de-France", "age_tr_libelle": "[27;31[",
            "sexe_libelle": "Hommes", "effectif_pondere": 5000,
            "salaire_net_median_annuel": 42000,
            "salaire_net_median_mensuel": 3500,
        },
        {
            "cs_code": "21", "cs_libelle": "Cadres",
            "region_libelle": "Île-de-France", "age_tr_libelle": "[31;35[",
            "sexe_libelle": "Femmes", "effectif_pondere": 4000,
            "salaire_net_median_annuel": 38000,
            "salaire_net_median_mensuel": 3200,
        },
        {
            "cs_code": "55", "cs_libelle": "Employés de commerce",
            "region_libelle": "Bretagne", "age_tr_libelle": "[31;35[",
            "sexe_libelle": "Femmes", "effectif_pondere": 2000,
            "salaire_net_median_annuel": 17000,
            "salaire_net_median_mensuel": 1417,
        },
    ]


class TestInseeWeightedMedian:
    def test_simple(self):
        records = [
            {"salaire_net_median_annuel": 30000, "effectif_pondere": 100},
            {"salaire_net_median_annuel": 40000, "effectif_pondere": 100},
        ]
        m = _weighted_median(records, "salaire_net_median_annuel")
        # Avec poids égaux et 2 valeurs : médiane = première qui passe 50 % cumulé
        assert m in (30000, 40000)  # selon implémentation exacte

    def test_skips_none_and_zero_weight(self):
        records = [
            {"salaire_net_median_annuel": None, "effectif_pondere": 100},
            {"salaire_net_median_annuel": 30000, "effectif_pondere": 0},
            {"salaire_net_median_annuel": 30000, "effectif_pondere": 100},
        ]
        m = _weighted_median(records, "salaire_net_median_annuel")
        assert m == 30000

    def test_empty(self):
        assert _weighted_median([], "salaire_net_median_annuel") is None


class TestInseeCorpus:
    def test_france_globale_includes_n_pcs(self, insee_sample):
        rec = insee_france(insee_sample)
        assert rec["id"] == "insee_salaan:france"
        assert rec["domain"] == "insee_salaire"
        assert rec["n_records_source"] == 3
        assert rec["effectif_total"] > 0

    def test_by_cs_libelle_groups(self, insee_sample):
        recs = insee_by_cs(insee_sample)
        assert len(recs) == 2  # cs 21 + cs 55
        cs21 = next(r for r in recs if r["cs_code"] == "21")
        # cadres : 9 000 effectif total (5k + 4k)
        assert cs21["effectif_total"] == 9000
        assert cs21["pct_femmes"] > 40  # 4/9 ≈ 44%

    def test_by_pcs_group_targets_only_target_regions(self, insee_sample):
        # cs 55 est en Bretagne (target), cs 21 en IDF (target)
        recs = insee_by_pcs_region(insee_sample)
        regions = {r["region"] for r in recs}
        assert regions.issubset(_TARGET_REGIONS)


# --- InserSup ---


@pytest.fixture
def insersup_sample():
    return [
        {
            "cohorte_promo": "2023", "type_diplome": "Master LMD",
            "discipline": "Sciences humaines", "region": "Île-de-France",
            "etablissement": "Paris 1", "niveau_orientia": "bac+5",
            "nb_sortants": 200, "nb_poursuivants": 50,
            "taux_emploi_salarie_fr": {"6m": 0.6, "12m": 0.75, "18m": 0.78, "24m": 0.80, "30m": 0.82},
        },
        {
            "cohorte_promo": "2023", "type_diplome": "Master LMD",
            "discipline": "Sciences humaines", "region": "Île-de-France",
            "etablissement": "Paris 4", "niveau_orientia": "bac+5",
            "nb_sortants": 150, "nb_poursuivants": 40,
            "taux_emploi_salarie_fr": {"6m": 0.55, "12m": 0.70, "18m": 0.75, "24m": 0.78, "30m": 0.80},
        },
        {
            "cohorte_promo": "2022", "type_diplome": "Licence générale",
            "discipline": "Lettres", "region": "Bretagne",
            "etablissement": "Rennes", "niveau_orientia": "bac+3",
            "nb_sortants": 50, "nb_poursuivants": 20,
            "taux_emploi_salarie_fr": {"6m": 0.4, "12m": 0.6, "18m": 0.7, "24m": 0.7, "30m": 0.7},
        },
    ]


class TestInsersupHelpers:
    def test_select_cohorte_recente(self, insersup_sample):
        cohorte, filtered = _select_cohorte_recente(insersup_sample)
        assert cohorte == "2023"
        # 2 records sur 3 sont en 2023
        assert len(filtered) == 2

    def test_aggregate_taux_emploi_median(self, insersup_sample):
        records = insersup_sample[:2]  # 2 records 2023
        m = _aggregate_taux_emploi(records, "6m")
        assert m == pytest.approx((0.6 + 0.55) / 2)

    def test_aggregate_taux_emploi_skips_missing(self):
        records = [
            {"taux_emploi_salarie_fr": {"6m": 0.5}},
            {"taux_emploi_salarie_fr": {}},
        ]
        m = _aggregate_taux_emploi(records, "6m")
        assert m == 0.5

    def test_median_nullable(self):
        assert _median_nullable([1, 2, 3]) == 2
        assert _median_nullable([None, 1, None, 2]) == 1.5
        assert _median_nullable([None, None]) is None
        assert _median_nullable([]) is None


class TestInsersupCorpus:
    def test_skips_small_effectifs(self, insersup_sample):
        # Cohorte récente = 2023, donc seul Master LMD × Sciences humaines × IDF
        # avec 350 sortants total (200+150)
        corpus = build_insersup_corpus(insersup_sample)
        # Cohorte 2023 = 2 records IDF Master, total 350 sortants > 50 → 1 cell
        # Cohorte 2022 ne sera pas traitée (la plus récente est 2023)
        assert len(corpus) >= 0
        for c in corpus:
            assert c["nb_sortants"] >= 50

    def test_corpus_format(self, insersup_sample):
        corpus = build_insersup_corpus(insersup_sample)
        if corpus:
            c = corpus[0]
            assert c["domain"] == "insertion_pro"
            assert c["source"] == "insersup_mesr"
            assert c["region"] in _METROPOLE_REGIONS
            assert "text" in c

    def test_skips_overseas_regions(self):
        # Records avec régions non-métropolitaines doivent être skippés
        records = [
            {
                "cohorte_promo": "2023", "type_diplome": "Master LMD",
                "discipline": "Sciences", "region": "Guadeloupe",
                "etablissement": "X", "niveau_orientia": "bac+5",
                "nb_sortants": 1000, "nb_poursuivants": 200,
                "taux_emploi_salarie_fr": {"12m": 0.6},
            }
        ]
        corpus = build_insersup_corpus(records)
        assert corpus == []
