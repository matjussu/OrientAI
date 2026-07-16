"""Tests pour `src/experimental/fact_checker.py` (StatFactChecker LLM-based).

Couvre l'extension Sprint 7 Action 1 — verdict `verified_by_official_source`
pour le pattern anti-hallu défensif (chiffre approximatif `~X` + URL
officielle inline).

Préserve la non-régression : tous les anciens verdicts (`verified`,
`unsourced_with_disclaimer`, `unsourced_unsafe`) restent comptés
identiquement.
"""
from __future__ import annotations

from src.experimental.fact_checker import (
    OFFICIAL_SOURCE_URL_PATTERNS,
    OFFICIAL_SOURCE_REGEX,
    StatVerification,
    VerificationReport,
    VERIFIED_VERDICTS,
    _extract_has_official_source,
)


class TestVerifiedVerdictsConst:
    def test_includes_strict_verified(self):
        assert "verified" in VERIFIED_VERDICTS

    def test_includes_verified_by_official_source(self):
        """Sprint 7 Action 1 : nouveau verdict ajouté à la famille verified."""
        assert "verified_by_official_source" in VERIFIED_VERDICTS

    def test_excludes_disclaimer_and_unsafe(self):
        """Non-régression : les autres verdicts NE doivent PAS être verified."""
        assert "unsourced_with_disclaimer" not in VERIFIED_VERDICTS
        assert "unsourced_unsafe" not in VERIFIED_VERDICTS


class TestOfficialSourceRegex:
    def test_etudiant_gouv_recognized(self):
        text = "Source : https://www.etudiant.gouv.fr/fr/les-bourses-2317"
        assert _extract_has_official_source(text)

    def test_insee_recognized(self):
        text = "Voir insee.fr/fr/statistiques?geo=DEP-973 pour le détail"
        assert _extract_has_official_source(text)

    def test_moncompteformation_recognized(self):
        text = "Compte personnel sur moncompteformation.gouv.fr"
        assert _extract_has_official_source(text)

    def test_service_public_recognized(self):
        text = "https://www.service-public.fr/particuliers/vosdroits/F1010"
        assert _extract_has_official_source(text)

    def test_francetravail_recognized(self):
        text = "statistiques.francetravail.fr"
        assert _extract_has_official_source(text)

    def test_agefiph_recognized(self):
        text = "Site agefiph.fr pour les RQTH"
        assert _extract_has_official_source(text)

    def test_random_url_not_recognized(self):
        """Contre-exemple : URL non officielle ne doit PAS upgrader."""
        text = "Voir https://example.com pour plus de détails"
        assert not _extract_has_official_source(text)

    def test_empty_or_none(self):
        assert not _extract_has_official_source("")
        assert not _extract_has_official_source(None)

    def test_glassdoor_not_recognized(self):
        """Anti-pattern Sprint 5 : sources fabriquées type Glassdoor restent
        non reconnues comme officielles."""
        text = "Selon Glassdoor le salaire moyen est..."
        assert not _extract_has_official_source(text)

    def test_pattern_count_matches_constant(self):
        """Sanity : la liste des patterns matche le regex compilé."""
        # Au moins 15 sources officielles attendues (Sprint 7 Action 1)
        assert len(OFFICIAL_SOURCE_URL_PATTERNS) >= 15


class TestVerificationReportNewProperties:
    def _make_report_with_mix_verdicts(self) -> VerificationReport:
        return VerificationReport(stats_extracted=[
            StatVerification(stat_text="85%", verdict="verified"),
            StatVerification(stat_text="500€/an", verdict="verified_by_official_source"),
            StatVerification(stat_text="~2500€", verdict="verified_by_official_source"),
            StatVerification(stat_text="1500€ (estim)", verdict="unsourced_with_disclaimer"),
            StatVerification(stat_text="90% (CEREQ 2023)", verdict="unsourced_unsafe"),
        ])

    def test_stats_verified_includes_both_strict_and_by_source(self):
        """Sprint 7 : stats_verified inclut désormais les 2 sous-catégories."""
        report = self._make_report_with_mix_verdicts()
        verified = report.stats_verified
        assert len(verified) == 3
        # 1 strict + 2 by_source
        assert sum(1 for s in verified if s.verdict == "verified") == 1
        assert sum(1 for s in verified if s.verdict == "verified_by_official_source") == 2

    def test_stats_verified_strict_only(self):
        """Distinction Sprint 7 : strict seulement (verdict == 'verified')."""
        report = self._make_report_with_mix_verdicts()
        strict = report.stats_verified_strict
        assert len(strict) == 1
        assert strict[0].stat_text == "85%"

    def test_stats_verified_by_source_only(self):
        """Distinction Sprint 7 : verified par URL officielle uniquement."""
        report = self._make_report_with_mix_verdicts()
        by_source = report.stats_verified_by_source
        assert len(by_source) == 2
        assert all(s.verdict == "verified_by_official_source" for s in by_source)

    def test_stats_with_disclaimer_unchanged(self):
        """Non-régression : disclaimer reste séparé."""
        report = self._make_report_with_mix_verdicts()
        disc = report.stats_with_disclaimer
        assert len(disc) == 1
        assert disc[0].stat_text == "1500€ (estim)"

    def test_stats_hallucinated_unchanged(self):
        """Non-régression : hallucination reste séparée."""
        report = self._make_report_with_mix_verdicts()
        halluc = report.stats_hallucinated
        assert len(halluc) == 1
        assert halluc[0].stat_text == "90% (CEREQ 2023)"


class TestSummaryStructure:
    def test_summary_has_n_verified_total(self):
        """Sprint 7 : n_verified inclut strict + by_source."""
        report = VerificationReport(stats_extracted=[
            StatVerification(stat_text="a", verdict="verified"),
            StatVerification(stat_text="b", verdict="verified_by_official_source"),
            StatVerification(stat_text="c", verdict="verified_by_official_source"),
            StatVerification(stat_text="d", verdict="unsourced_unsafe"),
        ])
        s = report.summary
        # Sprint 7 : n_verified inclut les 2 sous-catégories
        assert s["n_verified"] == 3
        assert s["n_verified_strict"] == 1
        assert s["n_verified_by_source"] == 2

    def test_summary_preserves_old_keys(self):
        """Non-régression : les clés summary anciennes restent présentes."""
        report = VerificationReport(stats_extracted=[
            StatVerification(stat_text="x", verdict="verified"),
            StatVerification(stat_text="y", verdict="unsourced_with_disclaimer"),
            StatVerification(stat_text="z", verdict="unsourced_unsafe"),
        ])
        s = report.summary
        # Anciennes clés (ne pas casser callers existants)
        assert "n_stats_total" in s
        assert "n_verified" in s
        assert "n_with_disclaimer" in s
        assert "n_hallucinated" in s
        assert "error" in s

    def test_summary_old_caller_pattern_preserved(self):
        """Non-régression contractuelle : un caller qui faisait
        `report.summary["n_verified"]` doit toujours obtenir le bon nombre.
        Sprint 7 ajoute simplement les by_source au compte."""
        # Cas pré-Sprint-7 (aucun verified_by_official_source)
        report = VerificationReport(stats_extracted=[
            StatVerification(stat_text="a", verdict="verified"),
            StatVerification(stat_text="b", verdict="verified"),
            StatVerification(stat_text="c", verdict="unsourced_unsafe"),
        ])
        s = report.summary
        # Comportement Sprint 5/6 préservé : 2 verified
        assert s["n_verified"] == 2
        assert s["n_verified_strict"] == 2
        assert s["n_verified_by_source"] == 0

    def test_summary_n_total_includes_all_verdicts(self):
        report = VerificationReport(stats_extracted=[
            StatVerification(stat_text="a", verdict="verified"),
            StatVerification(stat_text="b", verdict="verified_by_official_source"),
            StatVerification(stat_text="c", verdict="unsourced_with_disclaimer"),
            StatVerification(stat_text="d", verdict="unsourced_unsafe"),
        ])
        s = report.summary
        assert s["n_stats_total"] == 4


class TestBackwardCompatibility:
    """Garde-fou Sprint 7 : aucun caller existant ne doit casser."""

    def test_default_verdict_unchanged(self):
        """Non-régression : la valeur par défaut reste unsourced_unsafe."""
        sv = StatVerification(stat_text="x")
        assert sv.verdict == "unsourced_unsafe"

    def test_only_verified_in_old_data_still_counts(self):
        """Cas baseline figée Sprint 5/6 (avant Action 1) : pct_verified
        identique au comportement antérieur."""
        report = VerificationReport(stats_extracted=[
            StatVerification(stat_text="a", verdict="verified"),
            StatVerification(stat_text="b", verdict="verified"),
            StatVerification(stat_text="c", verdict="unsourced_with_disclaimer"),
            StatVerification(stat_text="d", verdict="unsourced_unsafe"),
        ])
        s = report.summary
        # Comportement attendu Sprint 5/6 : 2/4 = 50% verified
        # Sprint 7 ne change PAS ce résultat (no verified_by_source dans le mix)
        assert s["n_verified"] == 2
        assert s["n_stats_total"] == 4
