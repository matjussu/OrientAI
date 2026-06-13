"""Tests src/agent/tools/profile_clarifier.py — Profile + tool func + clarifier (mocked)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.agent.tools.profile_clarifier import (
    Profile,
    ProfileClarifier,
    PROFILE_CLARIFIER_TOOL,
    NARRATIVE_PROFILE_TOOL,
    VALID_AGE_GROUPS,
    VALID_EDUCATION_LEVELS,
    VALID_INTENT_TYPES,
    _profile_clarifier_tool_func,
    _narrative_profile_tool_func,
)


# --- Profile dataclass ---


class TestProfile:
    def test_minimal_construction(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=["informatique"],
        )
        assert p.is_valid()
        assert p.region is None
        assert p.urgent_concern is False
        assert p.confidence == 0.5

    def test_full_construction(self):
        p = Profile(
            age_group="adulte_25_45",
            education_level="bac+5",
            intent_type="reconversion_pro",
            sector_interest=["sante", "education"],
            region="Bretagne",
            urgent_concern=True,
            confidence=0.85,
            notes="Reconversion post-burn-out",
        )
        assert p.is_valid()
        assert p.region == "Bretagne"
        assert p.urgent_concern is True

    def test_invalid_age_group(self):
        p = Profile(
            age_group="alien_visitor",
            education_level="bac+3",
            intent_type="orientation_initiale",
            sector_interest=[],
        )
        assert not p.is_valid()

    def test_invalid_education(self):
        p = Profile(
            age_group="etudiant_l1_l3",
            education_level="bac+42",
            intent_type="orientation_initiale",
            sector_interest=[],
        )
        assert not p.is_valid()

    def test_invalid_intent(self):
        p = Profile(
            age_group="etudiant_l1_l3",
            education_level="bac+2",
            intent_type="something_random",
            sector_interest=[],
        )
        assert not p.is_valid()

    def test_invalid_confidence_above_1(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            confidence=1.5,
        )
        assert not p.is_valid()

    def test_invalid_sector_not_list(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest="informatique",  # string instead of list
        )
        assert not p.is_valid()

    def test_to_dict_roundtrip(self):
        p = Profile(
            age_group="bachelier_general",
            education_level="bac_obtenu",
            intent_type="comparaison_options",
            sector_interest=["droit"],
            region="Île-de-France",
            urgent_concern=False,
            confidence=0.7,
            notes=None,
        )
        d = p.to_dict()
        p2 = Profile(**d)
        assert p == p2


# --- Tool func wrapper ---


class TestProfileClarifierToolFunc:
    def test_valid_call(self):
        result = _profile_clarifier_tool_func(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=["numerique"],
            region="La Réunion",
            urgent_concern=False,
            confidence=0.8,
            notes=None,
        )
        assert result["valid"] is True
        assert result["profile"]["age_group"] == "lyceen_terminale"
        assert result["profile"]["region"] == "La Réunion"

    def test_invalid_enum_returns_error(self):
        result = _profile_clarifier_tool_func(
            age_group="invalid_xxx",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            urgent_concern=False,
            confidence=0.5,
        )
        assert "error" in result

    def test_missing_required_uses_defaults(self):
        # Le wrapper utilise des defaults sécurisés ('other_or_unknown'
        # / 'unknown' / 'other') quand le LLM omet un champ — pour ne
        # pas crasher. Le profile peut quand même être valid si tous
        # les enums sont valides.
        result = _profile_clarifier_tool_func(sector_interest=[])
        assert result.get("valid") is True
        assert result["profile"]["age_group"] == "other_or_unknown"
        assert result["profile"]["education_level"] == "unknown"
        assert result["profile"]["intent_type"] == "other"

    def test_empty_sector_list(self):
        result = _profile_clarifier_tool_func(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            urgent_concern=False,
            confidence=0.5,
        )
        assert result["valid"] is True
        assert result["profile"]["sector_interest"] == []


# --- Mistral PROFILE_CLARIFIER_TOOL definition ---


class TestProfileClarifierToolDefinition:
    def test_tool_name(self):
        assert PROFILE_CLARIFIER_TOOL.name == "extract_user_profile"

    def test_tool_description_clear(self):
        # Description doit mentionner ce qu'extrait le tool
        d = PROFILE_CLARIFIER_TOOL.description.lower()
        assert "profil" in d or "profile" in d

    def test_tool_required_fields(self):
        required = set(PROFILE_CLARIFIER_TOOL.parameters["required"])
        assert "age_group" in required
        assert "education_level" in required
        assert "intent_type" in required
        assert "sector_interest" in required

    def test_tool_enums_valid(self):
        props = PROFILE_CLARIFIER_TOOL.parameters["properties"]
        assert set(props["age_group"]["enum"]) == VALID_AGE_GROUPS
        assert set(props["education_level"]["enum"]) == VALID_EDUCATION_LEVELS
        assert set(props["intent_type"]["enum"]) == VALID_INTENT_TYPES

    def test_to_mistral_schema_format(self):
        schema = PROFILE_CLARIFIER_TOOL.to_mistral_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "extract_user_profile"


# --- ProfileClarifier (mocked Mistral) ---


def _mock_mistral_response(args_dict):
    """Construit un mock de réponse Mistral avec un tool_call sur extract_user_profile."""
    tool_call = MagicMock()
    tool_call.function.name = "extract_user_profile"
    tool_call.function.arguments = json.dumps(args_dict)

    msg = MagicMock()
    msg.tool_calls = [tool_call]
    msg.content = ""

    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


class TestProfileClarifier:
    def test_clarify_simple_query(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_mistral_response({
            "age_group": "lyceen_terminale",
            "education_level": "terminale",
            "intent_type": "orientation_initiale",
            "sector_interest": ["informatique"],
            "region": "Île-de-France",
            "urgent_concern": False,
            "confidence": 0.9,
            "notes": "Query explicite avec niveau et région",
        })
        clarifier = ProfileClarifier(client=client)
        profile = clarifier.clarify("Je suis en terminale à Paris, j'aime l'informatique")
        assert profile.age_group == "lyceen_terminale"
        assert profile.region == "Île-de-France"
        assert profile.confidence == 0.9

    def test_clarify_no_tool_call_raises(self):
        client = MagicMock()
        msg = MagicMock()
        msg.tool_calls = None
        msg.content = "Je ne sais pas extraire ce profil"
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="n'a pas appelé le tool"):
            clarifier.clarify("???")

    def test_clarify_wrong_tool_raises(self):
        client = MagicMock()
        tool_call = MagicMock()
        tool_call.function.name = "some_other_tool"
        tool_call.function.arguments = "{}"
        msg = MagicMock()
        msg.tool_calls = [tool_call]
        msg.content = ""
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="tool inattendu"):
            clarifier.clarify("test")

    def test_clarify_invalid_json_raises(self):
        client = MagicMock()
        tool_call = MagicMock()
        tool_call.function.name = "extract_user_profile"
        tool_call.function.arguments = "{invalid json"
        msg = MagicMock()
        msg.tool_calls = [tool_call]
        msg.content = ""
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="JSON parse failed"):
            clarifier.clarify("test")

    def test_clarify_invalid_profile_data_raises(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_mistral_response({
            "age_group": "invalid_xxx",  # not in VALID_AGE_GROUPS
            "education_level": "terminale",
            "intent_type": "orientation_initiale",
            "sector_interest": [],
            "urgent_concern": False,
            "confidence": 0.5,
        })
        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="returned error"):
            clarifier.clarify("test")


# --- 1b mode récit : champs étendus du Profile (additifs, backward-compat) ---


class TestProfileExtendedFields:
    """Le mode récit extrait a_eviter / contraintes / mobilite + spans.

    Contrainte dure : additif. Un Profile construit "à l'ancienne" (les
    callers existants, la pipeline agentique, le banc 100q) ne doit PAS
    casser et doit recevoir des defaults sûrs.
    """

    def test_base_profile_has_empty_extended_defaults(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=["informatique"],
        )
        assert p.a_eviter == []
        assert p.contraintes == []
        assert p.mobilite is None
        assert p.spans == {}
        assert p.is_valid()

    def test_extended_construction(self):
        p = Profile(
            age_group="adulte_25_45",
            education_level="professionnel_actif",
            intent_type="reconversion_pro",
            sector_interest=["numerique"],
            a_eviter=["etudes longues sans revenu"],
            contraintes=["alternance", "remunere"],
            mobilite="Lyon, pas mobile",
            spans={"a_eviter": "je ne peux pas reprendre des etudes sans rentree d'argent"},
        )
        assert p.is_valid()
        assert p.a_eviter == ["etudes longues sans revenu"]
        assert p.contraintes == ["alternance", "remunere"]
        assert p.mobilite == "Lyon, pas mobile"
        assert p.spans["a_eviter"].startswith("je ne peux pas")

    def test_to_dict_roundtrip_with_extended(self):
        p = Profile(
            age_group="etudiant_master",
            education_level="bac+5",
            intent_type="info_metier_specifique",
            sector_interest=[],
            mobilite="mobile en France",
            a_eviter=["backend"],
            contraintes=[],
            spans={"cible": "data analyst"},
        )
        d = p.to_dict()
        assert {"a_eviter", "contraintes", "mobilite", "spans"} <= set(d.keys())
        p2 = Profile(**d)
        assert p == p2

    def test_is_valid_false_when_a_eviter_not_list(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            a_eviter="commercial",  # string au lieu de list
        )
        assert not p.is_valid()

    def test_is_valid_false_when_spans_not_dict(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            spans=["not", "a", "dict"],
        )
        assert not p.is_valid()


# --- 1b mode récit : NARRATIVE_PROFILE_TOOL (définition + func) ---


class TestNarrativeProfileTool:
    def test_tool_name(self):
        assert NARRATIVE_PROFILE_TOOL.name == "extract_narrative_profile"

    def test_tool_has_extended_properties(self):
        props = NARRATIVE_PROFILE_TOOL.parameters["properties"]
        for key in ("a_eviter", "contraintes", "mobilite", "spans"):
            assert key in props, f"propriété étendue manquante: {key}"

    def test_tool_reuses_base_enums(self):
        # Enums core synchronisés avec le tool de base (DRY, pas de drift).
        props = NARRATIVE_PROFILE_TOOL.parameters["properties"]
        assert set(props["age_group"]["enum"]) == VALID_AGE_GROUPS
        assert set(props["intent_type"]["enum"]) == VALID_INTENT_TYPES

    def test_tool_required_is_core_only(self):
        # Les champs étendus sont best-effort : jamais requis.
        required = set(NARRATIVE_PROFILE_TOOL.parameters["required"])
        assert "a_eviter" not in required
        assert "mobilite" not in required
        assert "spans" not in required
        assert "age_group" in required

    def test_func_extracts_extended(self):
        result = _narrative_profile_tool_func(
            age_group="adulte_25_45",
            education_level="professionnel_actif",
            intent_type="reconversion_pro",
            sector_interest=["numerique"],
            urgent_concern=False,
            confidence=0.7,
            a_eviter=["vente", "commercial"],
            contraintes=["alternance"],
            mobilite="Lyon",
            spans={"cible": "me reconvertir dans le numerique"},
        )
        assert result["valid"] is True
        prof = result["profile"]
        assert prof["a_eviter"] == ["vente", "commercial"]
        assert prof["contraintes"] == ["alternance"]
        assert prof["mobilite"] == "Lyon"
        assert prof["spans"]["cible"] == "me reconvertir dans le numerique"

    def test_func_extended_defaults_when_omitted(self):
        result = _narrative_profile_tool_func(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            urgent_concern=False,
            confidence=0.5,
        )
        assert result["valid"] is True
        assert result["profile"]["a_eviter"] == []
        assert result["profile"]["contraintes"] == []
        assert result["profile"]["mobilite"] is None
        assert result["profile"]["spans"] == {}

    def test_func_coerces_bad_spans_to_empty(self):
        # spans best-effort : un type inattendu ne plante pas, il est ignoré.
        result = _narrative_profile_tool_func(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            urgent_concern=False,
            confidence=0.5,
            spans="pas un dict",
        )
        assert result["valid"] is True
        assert result["profile"]["spans"] == {}


# --- 1b mode récit : ProfileClarifier.clarify_narrative (mocked, fallback) ---


def _mock_narrative_response(args_dict):
    """Mock réponse Mistral avec un tool_call sur extract_narrative_profile."""
    tool_call = MagicMock()
    tool_call.function.name = "extract_narrative_profile"
    tool_call.function.arguments = json.dumps(args_dict)
    msg = MagicMock()
    msg.tool_calls = [tool_call]
    msg.content = ""
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


class TestClarifyNarrative:
    def _full_args(self, **over):
        base = {
            "age_group": "etudiant_l1_l3",
            "education_level": "bac+2",
            "intent_type": "reorientation_etude",
            "sector_interest": ["informatique", "data"],
            "region": "Hauts-de-France",
            "urgent_concern": False,
            "confidence": 0.8,
            "notes": None,
            "a_eviter": ["commercial", "vente"],
            "contraintes": [],
            "mobilite": None,
            "spans": {"a_eviter": "je ne veux surtout pas finir dans un metier commercial"},
        }
        base.update(over)
        return base

    def test_extracts_extended_fields(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_narrative_response(self._full_args())
        clarifier = ProfileClarifier(client=client)
        p = clarifier.clarify_narrative("recit long L2 droit vers dev/data")
        assert p.a_eviter == ["commercial", "vente"]
        assert p.spans["a_eviter"].startswith("je ne veux surtout pas")
        assert p.age_group == "etudiant_l1_l3"

    def test_uses_small_model_and_temperature_zero(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_narrative_response(self._full_args())
        clarifier = ProfileClarifier(client=client)
        clarifier.clarify_narrative("recit")
        kwargs = client.chat.complete.call_args.kwargs
        assert kwargs["model"] == "mistral-small-latest"
        assert kwargs["temperature"] == 0.0

    def test_silent_fallback_on_no_tool_call(self):
        client = MagicMock()
        msg = MagicMock()
        msg.tool_calls = None
        msg.content = "blabla pas de tool"
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response
        clarifier = ProfileClarifier(client=client)
        p = clarifier.clarify_narrative("recit")  # ne doit PAS raise
        assert isinstance(p, Profile)
        assert p.confidence == 0.0
        assert p.notes and p.notes.startswith("narrative_fallback")

    def test_silent_fallback_on_exception(self):
        client = MagicMock()
        client.chat.complete.side_effect = RuntimeError("mistral down")
        clarifier = ProfileClarifier(client=client)
        p = clarifier.clarify_narrative("recit")  # ne doit PAS raise
        assert isinstance(p, Profile)
        assert p.confidence == 0.0
        assert p.a_eviter == []

    def test_silent_fallback_on_bad_json(self):
        client = MagicMock()
        tool_call = MagicMock()
        tool_call.function.name = "extract_narrative_profile"
        tool_call.function.arguments = "{not valid json"
        msg = MagicMock()
        msg.tool_calls = [tool_call]
        msg.content = ""
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response
        clarifier = ProfileClarifier(client=client)
        p = clarifier.clarify_narrative("recit")
        assert isinstance(p, Profile)
        assert p.confidence == 0.0

    def test_spans_best_effort_absent(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_narrative_response(
            self._full_args(spans={})
        )
        clarifier = ProfileClarifier(client=client)
        p = clarifier.clarify_narrative("recit")
        assert p.spans == {}
