"""Tests génération sectionnée MODE RÉCIT (R1 1d, ordre #137).

Couvre :
- composition de SYSTEM_PROMPT_NARRATIVE : réutilise le contrat factuel v4 strict
  (R1-R3/R5/R7 verbatim), remplace R6 (cap 250 mots) par 4 sections.
- branche `narrative_mode` de `_build_chat_kwargs` : prompt sectionné, max_tokens
  relevé, few-shot récit injecté côté user ; v4/v3.2 strictement inchangés.
- `_prepare_narrative` propage `narrative_mode=True` + le few-shot dédié.
- R02 fix : la règle négation est câblée dans le prompt du clarifier récit.

Pas d'appel Mistral : tout est offline/déterministe (validation comportementale =
boucle de jugement humain, hors tests). _retrieve_and_filter stubbé.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.agent.tools.profile_clarifier import (
    NARRATIVE_CLARIFIER_SYSTEM_PROMPT,
    Profile,
    dedup_sector_vs_eviter,
)
from src.prompt.system_narrative import NARRATIVE_FEW_SHOT_PREFIX, SYSTEM_PROMPT_NARRATIVE
from src.prompt.system_v4_strict import SYSTEM_PROMPT_V4_STRICT
from src.rag.generator import NARRATIVE_MAX_TOKENS, _build_chat_kwargs
from src.rag.pipeline import OrientIAPipeline, _PreparedGenContext


_RETRIEVED = [
    {
        "fiche": {
            "nom": "BUT Informatique",
            "etablissement": "IUT de Lille",
            "ville": "Villeneuve d'Ascq",
            "region": "Hauts-de-France",
            "domain": "formation",
            "lien_form_psup": "https://dossierappel.parcoursup.fr/x",
            "admission": {"taux_acces": 40, "places": 30},
        },
        "score": 0.9,
    }
]


def _kwargs(**over):
    base = dict(
        model="m",
        temperature=0.3,
        inject_user_level=False,
        system_prompt_override=None,
        golden_qa_prefix=None,
        history=None,
        hint_block="",
        use_strict_v4=False,
        hardlock_block="",
    )
    base.update(over)
    return _build_chat_kwargs(_RETRIEVED, "Mon long récit d'orientation...", **base)


class TestNarrativeSystemPrompt:
    def test_reuses_v4_factual_contract_verbatim(self):
        # R1-R3/R5/R7 viennent du slicing du prompt v4 -> présents tels quels.
        for marker in (
            "### R1 — Chiffres",
            "### R2 — Identité des formations",
            "### R3 — Citations sources",
            "R3.bis",
            "### R5 — Posture",
            "### R7 — CONTRAINTES HARDLOCK",
        ):
            assert marker in SYSTEM_PROMPT_NARRATIVE, marker

    def test_replaces_r6_length_cap_with_sections(self):
        # Le cap 250 mots de R6 doit avoir disparu...
        assert "MAX 250 mots" not in SYSTEM_PROMPT_NARRATIVE
        assert "LONGUEUR (NON-NÉGOCIABLE)" not in SYSTEM_PROMPT_NARRATIVE
        # ...remplacé par les 4 sections obligatoires.
        for section in (
            "**1. Ta situation**",
            "**2. Les pistes qui collent**",
            "**3. Points de vigilance**",
            "**4. Prochaine étape**",
        ):
            assert section in SYSTEM_PROMPT_NARRATIVE, section

    def test_a_eviter_visible_requirement_present(self):
        # Exigence Jarvis : l'à-éviter doit apparaître dans la reformulation.
        assert "ÉVITER" in SYSTEM_PROMPT_NARRATIVE

    def test_v4_strict_prompt_untouched(self):
        # Isolation : le prompt v4 garde son R6 et son cap (banc 100q/497q intact).
        assert "MAX 250 mots" in SYSTEM_PROMPT_V4_STRICT
        assert "LONGUEUR (NON-NÉGOCIABLE)" in SYSTEM_PROMPT_V4_STRICT


class TestNarrativeFewShot:
    def test_comment_quoi_separation(self):
        assert "SÉPARATION STRICTE COMMENT vs QUOI" in NARRATIVE_FEW_SHOT_PREFIX
        assert "FICTIFS" in NARRATIVE_FEW_SHOT_PREFIX

    def test_demonstrates_four_sections(self):
        for section in (
            "**1. Ta situation**",
            "**2. Les pistes qui collent**",
            "**3. Points de vigilance**",
            "**4. Prochaine étape**",
        ):
            assert section in NARRATIVE_FEW_SHOT_PREFIX, section


class TestBuildChatKwargsNarrativeBranch:
    def test_narrative_uses_sectioned_prompt_and_raised_cap(self):
        kw = _kwargs(use_strict_v4=True, narrative_mode=True, golden_qa_prefix="FEWSHOT_X")
        sys_msg = kw["messages"][0]["content"]
        user_msg = kw["messages"][-1]["content"]
        assert kw["max_tokens"] == NARRATIVE_MAX_TOKENS == 1500
        assert "**1. Ta situation**" in sys_msg
        assert "MAX 250 mots" not in sys_msg
        # Few-shot injecté côté user (canal golden_qa_prefix), attaché au fact.
        assert "FEWSHOT_X" in user_msg
        assert "<sources>" in user_msg

    def test_narrative_takes_precedence_over_strict_v4(self):
        # narrative_mode prime même avec use_strict_v4=True (cas prod réel).
        kw = _kwargs(use_strict_v4=True, narrative_mode=True)
        assert kw["max_tokens"] == 1500  # pas 800

    def test_strict_v4_unchanged_when_not_narrative(self):
        kw = _kwargs(use_strict_v4=True, narrative_mode=False)
        assert kw["max_tokens"] == 800
        assert "250 mots" in kw["messages"][0]["content"]

    def test_legacy_v3_2_unchanged(self):
        kw = _kwargs(use_strict_v4=False, narrative_mode=False)
        assert "max_tokens" not in kw


class TestPrepareNarrativePropagatesFlag:
    def _pipeline(self, profile):
        clar = MagicMock()
        clar.clarify_narrative.return_value = profile
        p = OrientIAPipeline(
            client=MagicMock(),
            fiches=[],
            enable_narrative_mode=True,
            narrative_clarifier=clar,
            enable_geo_coherence=False,
        )
        p._retrieve_and_filter = lambda **kw: [{"id": "F.1", "text": "x", "score": 1.0}]  # type: ignore[assignment]
        return p

    def test_prepared_context_carries_narrative_mode_and_fewshot(self):
        prof = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="decouverte_filieres",
            sector_interest=["sciences"],
            a_eviter=["médecine"],
        )
        p = self._pipeline(prof)
        # >=300 chars : seuil de narrative_detect (sinon branche récit non prise).
        recit = (
            "Salut, je suis en terminale generale a Bordeaux avec les specialites "
            "maths et SVT. J'ai de bons resultats mais aucune idee de ce que je veux "
            "faire. J'aime les sciences, comprendre comment marchent les choses, mais "
            "je ne veux surtout pas faire medecine : les concours et les etudes trop "
            "longues ne me tentent pas du tout. Tu aurais des pistes scientifiques "
            "qui pourraient me correspondre ?"
        )
        prepared = p._prepare_for_generation(recit, k=30, top_k_sources=10, criteria=None, history=None)
        assert isinstance(prepared, _PreparedGenContext)
        assert prepared.narrative_mode is True
        # Forme adaptative (ordre 1926) : le récit « aucune idée » route en
        # EXPLORATOIRE -> few-shot MATCHÉ au format (plus le few-shot CONSEIL fixe).
        from src.rag.narrative_format import EXPLORATOIRE
        from src.prompt.system_narrative import narrative_few_shot
        assert prepared.format_decision is not None
        assert prepared.format_decision.format == EXPLORATOIRE
        assert prepared.golden_qa_prefix == narrative_few_shot(EXPLORATOIRE)

    def test_non_narrative_context_defaults_flag_false(self):
        # Garde-fou : le chemin classique ne doit jamais activer narrative_mode.
        ctx = _PreparedGenContext(
            top=[], effective_top_k=5, golden_qa_prefix=None, intent_label=None,
            hardlock_block="", criteria=None, route_decision=None,
        )
        assert ctx.narrative_mode is False

    def test_flag_off_keeps_generation_classic_on_long_recit(self):
        # 1e — non-régression LOCK : flag OFF, même sur un récit long (>=300
        # chars), la génération reste classique (narrative_mode jamais propagé
        # -> v4/v3.2 byte-identique, banc 100q/serving intact).
        clar = MagicMock()
        p = OrientIAPipeline(
            client=MagicMock(), fiches=[],
            enable_narrative_mode=False,           # flag OFF
            narrative_clarifier=clar,
            enable_geo_coherence=False,
        )
        p._retrieve_and_filter = lambda **kw: [{"id": "F.1", "text": "x", "score": 1.0}]  # type: ignore[assignment]
        recit = (
            "Bonjour, je suis en terminale et je raconte ici un long récit "
            "d'orientation détaillé avec mon parcours, mes envies, mes doutes et "
            "ce que je veux éviter, bien au-delà de trois cents caractères pour "
            "franchir le seuil de détection narrative et vérifier que, flag OFF, "
            "rien ne bascule sur le mode récit. Quelles pistes pour moi ?"
        )
        prepared = p._prepare_for_generation(recit, k=30, top_k_sources=10, criteria=None, history=None)
        assert isinstance(prepared, _PreparedGenContext)
        assert prepared.narrative_mode is False
        clar.clarify_narrative.assert_not_called()


class TestR02NegationRuleWired:
    def test_clarifier_prompt_has_negation_rule(self):
        prompt = NARRATIVE_CLARIFIER_SYSTEM_PROMPT
        assert "RÈGLE NÉGATION" in prompt
        # Le coeur de la règle : un rejet va dans a_eviter, jamais en secteur.
        assert "a_eviter" in prompt and "sector_interest" in prompt
        # L'exemple médecine (R02) est encodé.
        assert "médecine" in prompt
        # Distinction domaine-distinct vs activité-au-sein-d'un-champ (anti-R09).
        assert "RESTE" in prompt


class TestDedupSectorVsEviter:
    """Prédicat déterministe (code, pas prompt) : un domaine rejeté ne reste
    pas en secteur. Cf fix R02 (médecine listée en secteur ET rejetée)."""

    def _p(self, sector, a_eviter):
        return Profile(
            age_group="lyceen_terminale", education_level="terminale",
            intent_type="decouverte_filieres", sector_interest=sector, a_eviter=a_eviter,
        )

    def test_r02_removes_rejected_domain_from_sector(self):
        p = dedup_sector_vs_eviter(self._p(["sciences", "médecine"], ["médecine", "concours médicaux"]))
        assert p.sector_interest == ["sciences"]

    def test_r09_keeps_field_when_only_activity_rejected(self):
        # informatique attire ; seul coder est rejeté -> informatique RESTE.
        p = dedup_sector_vs_eviter(self._p(["informatique"], ["programmation", "écrire du code"]))
        assert p.sector_interest == ["informatique"]

    def test_substring_match_removes(self):
        # « médecine » ⊂ « études de médecine ».
        p = dedup_sector_vs_eviter(self._p(["médecine", "biologie"], ["études de médecine"]))
        assert p.sector_interest == ["biologie"]

    def test_accent_insensitive(self):
        p = dedup_sector_vs_eviter(self._p(["Médecine"], ["medecine"]))
        assert p.sector_interest == []

    def test_no_eviter_is_noop(self):
        p = dedup_sector_vs_eviter(self._p(["sciences", "médecine"], []))
        assert p.sector_interest == ["sciences", "médecine"]

    def test_conservative_short_terms_need_exact_match(self):
        # « data » (4 car., <5) ne doit PAS être purgé par substring dans « database ».
        p = dedup_sector_vs_eviter(self._p(["data"], ["database admin"]))
        assert p.sector_interest == ["data"]

    def test_does_not_remove_unrelated(self):
        p = dedup_sector_vs_eviter(self._p(["marketing", "communication"], ["comptabilité", "finance"]))
        assert p.sector_interest == ["marketing", "communication"]
