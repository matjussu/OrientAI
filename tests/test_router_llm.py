"""Tests unitaires RouterLLM.

Étapes 1+3 du plan. Sans appel LLM live (tout mocké) :
- RouteDecision construction, validation, post_init
- RouteDecision.from_tool_payload tolère les clés manquantes
- RouteDecision.hardlock_block_for_prompt formatte correctement
- ROUTE_DECISION_TOOL.to_mistral_schema() retourne le bon format
- _route_decision_tool_func normalise correctement
- ROUTER_SYSTEM_PROMPT contient les éléments critiques (sub_indexes nommés)
- RouterLLM.route() : succès canonique, history pris en compte,
  fallback gracieux sur exception / JSON invalide / tool_calls vide

Pour le test live (sans mock, sur 10 questions golden_60), voir
scripts/validate_router_llm_live.py (run manuel, hors pytest).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.rag.metadata_filter import FilterCriteria
from src.rag.router_llm import (
    REFUSAL_REASONS,
    REFUSAL_TEMPLATES,
    ROUTE_DECISION_TOOL,
    ROUTE_DECISION_TOOL_PARAMS,
    ROUTER_SYSTEM_PROMPT,
    RouteDecision,
    RouterLLM,
    SUB_INDEX_NAMES,
    _route_decision_tool_func,
)


# ────────────────────────── Constantes ──────────────────────────


def test_sub_index_names_are_four() -> None:
    """Les 4 sub-indexes attendus sont définis."""
    assert SUB_INDEX_NAMES == (
        "formations",
        "metiers",
        "statistiques",
        "aides_territoires",
    )


def test_refusal_reasons_match_schema() -> None:
    """Les 3 raisons de refus sont définies."""
    assert REFUSAL_REASONS == (
        "superlative_no_data",
        "cross_domain",
        "out_of_scope_specific",
    )


def test_refusal_templates_cover_all_reasons() -> None:
    """Chaque refusal_reason a un template pré-écrit non vide."""
    for reason in REFUSAL_REASONS:
        assert reason in REFUSAL_TEMPLATES
        assert len(REFUSAL_TEMPLATES[reason]) > 50


# ────────────────────────── RouteDecision construction ──────────────────────────


def test_route_decision_default_is_safe_fallback() -> None:
    """Default: tous sub_indexes (pas de routing), confidence=0, no refusal."""
    rd = RouteDecision()
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)
    assert rd.criteria is None
    assert rd.refusal_reason is None
    assert rd.pre_written_response is None
    assert rd.confidence == 0.0
    assert rd.is_fallback is False


def test_route_decision_dedupes_sub_indexes() -> None:
    """sub_indexes dupliqués sont déduplicés en préservant l'ordre."""
    rd = RouteDecision(sub_indexes=["formations", "metiers", "formations", "metiers"])
    assert rd.sub_indexes == ["formations", "metiers"]


def test_route_decision_invalid_sub_index_raises() -> None:
    """sub_indexes hors enum → ValueError."""
    with pytest.raises(ValueError, match="sub_indexes contient des valeurs invalides"):
        RouteDecision(sub_indexes=["formations", "wrong_name"])


def test_route_decision_empty_sub_indexes_falls_back_to_all() -> None:
    """sub_indexes=[] → toutes les routes (filet de sécurité)."""
    rd = RouteDecision(sub_indexes=[])
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)


def test_route_decision_invalid_refusal_reason_raises() -> None:
    """refusal_reason hors enum → ValueError."""
    with pytest.raises(ValueError, match="refusal_reason invalide"):
        RouteDecision(refusal_reason="hallucinated_reason")


def test_route_decision_refusal_auto_populates_pre_written() -> None:
    """Si refusal_reason set sans pre_written_response, le template s'applique."""
    rd = RouteDecision(refusal_reason="superlative_no_data")
    assert rd.pre_written_response is not None
    assert "classement" in rd.pre_written_response.lower()


def test_route_decision_refusal_explicit_response_preserved() -> None:
    """Si pre_written_response est explicitement fourni, il n'est pas écrasé."""
    rd = RouteDecision(
        refusal_reason="cross_domain",
        pre_written_response="Custom refusal text",
    )
    assert rd.pre_written_response == "Custom refusal text"


def test_route_decision_confidence_clamped_above() -> None:
    """confidence > 1.0 → 1.0."""
    rd = RouteDecision(confidence=1.5)
    assert rd.confidence == 1.0


def test_route_decision_confidence_clamped_below() -> None:
    """confidence < 0.0 → 0.0."""
    rd = RouteDecision(confidence=-0.3)
    assert rd.confidence == 0.0


# ────────────────────────── RouteDecision.from_tool_payload ──────────────────────────


def test_from_tool_payload_canonical() -> None:
    """Payload canonique LLM → RouteDecision attendu."""
    payload = {
        "sub_indexes": ["aides_territoires"],
        "region": "Bretagne",
        "niveau_min": None,
        "niveau_max": None,
        "secteur": ["informatique"],
        "domain_lock": ["crous"],
        "refusal_reason": None,
        "hardlock_region_strict": True,
        "hardlock_domain_strict": True,
        "top_k_override": 12,
        "confidence": 0.9,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.sub_indexes == ["aides_territoires"]
    assert rd.criteria is not None
    # lowercase + strip_accents (post-fix audit step 6)
    assert rd.criteria.region == "bretagne"
    assert rd.criteria.secteur == ["informatique"]
    assert rd.domain_lock == ["crous"]
    assert rd.hardlock_region_strict is True
    assert rd.hardlock_domain_strict is True
    assert rd.top_k_override == 12
    assert rd.confidence == 0.9


def test_from_tool_payload_normalizes_accents_in_region() -> None:
    """Audit fix step 6 : region avec accents → strip_accents + lowercase
    pour cohérence avec router_fallback (qui passe par _strip_accents)."""
    payload = {
        "sub_indexes": ["formations"],
        "region": "Provence-Alpes-Côte d'Azur",
        "confidence": 0.9,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.criteria is not None
    # Ni accents, ni majuscules — alignement strict avec _detect_region
    # du fallback (utilisé par apply_metadata_filter aval).
    assert rd.criteria.region == "provence-alpes-cote d'azur"


def test_from_tool_payload_minimal_missing_keys() -> None:
    """Payload minimal (LLM oublie des clés) → defaults safes."""
    payload = {"sub_indexes": ["formations"], "confidence": 0.5}
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.sub_indexes == ["formations"]
    assert rd.criteria is None
    assert rd.domain_lock is None
    assert rd.refusal_reason is None
    assert rd.top_k_override is None
    assert rd.confidence == 0.5


def test_from_tool_payload_no_criteria_when_all_null() -> None:
    """Si region/niveau/secteur tous null, pas de FilterCriteria construit."""
    payload = {
        "sub_indexes": ["formations"],
        "region": None,
        "niveau_min": None,
        "niveau_max": None,
        "secteur": None,
        "confidence": 0.7,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.criteria is None


def test_from_tool_payload_top_k_out_of_range_dropped() -> None:
    """top_k_override hors [5, 20] → None (défense vs LLM qui hallucine)."""
    payload = {"sub_indexes": ["formations"], "top_k_override": 100, "confidence": 0.8}
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.top_k_override is None

    payload2 = {"sub_indexes": ["formations"], "top_k_override": 2, "confidence": 0.8}
    rd2 = RouteDecision.from_tool_payload(payload2)
    assert rd2.top_k_override is None


def test_from_tool_payload_refusal_with_template() -> None:
    """Payload refusal_reason → pre_written_response auto-populé."""
    payload = {
        "sub_indexes": ["formations"],
        "refusal_reason": "superlative_no_data",
        "confidence": 0.95,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.refusal_reason == "superlative_no_data"
    assert rd.pre_written_response is not None
    assert "Onisep" in rd.pre_written_response


def test_from_tool_payload_domain_lock_normalized() -> None:
    """domain_lock listé → normalisé (lowercase, strip)."""
    payload = {
        "sub_indexes": ["aides_territoires"],
        "domain_lock": ["CROUS", "  financement_etudes  "],
        "confidence": 0.8,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.domain_lock == ["crous", "financement_etudes"]


def test_from_tool_payload_invalid_types_safe() -> None:
    """sub_indexes non-list, secteur non-list → fallback safes (pas de crash)."""
    payload = {
        "sub_indexes": "formations",  # string au lieu de list
        "secteur": "informatique",  # string au lieu de list
        "confidence": 0.5,
    }
    rd = RouteDecision.from_tool_payload(payload)
    # sub_indexes string → fallback all
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)
    # secteur string → ignoré (pas de criteria construit si tout None à part secteur invalide)
    assert rd.criteria is None or rd.criteria.secteur is None


# ────────────────────────── hardlock_block_for_prompt ──────────────────────────


def test_hardlock_block_empty_when_no_constraints() -> None:
    """Aucune contrainte hardlock → bloc vide."""
    rd = RouteDecision(sub_indexes=["formations"], confidence=0.8)
    assert rd.hardlock_block_for_prompt() == ""


def test_hardlock_block_region_only() -> None:
    """Hardlock région seule → bloc avec mention région imposée."""
    rd = RouteDecision(
        sub_indexes=["formations"],
        criteria=FilterCriteria(region="bretagne"),
        hardlock_region_strict=True,
        confidence=0.9,
    )
    block = rd.hardlock_block_for_prompt()
    assert "HARDLOCK" in block
    assert "bretagne" in block.lower()
    assert "alternative" in block.lower() or "hors-région" in block.lower()


def test_hardlock_block_domain_only() -> None:
    """Hardlock domaine seul → bloc avec mention domaine imposé."""
    rd = RouteDecision(
        sub_indexes=["aides_territoires"],
        domain_lock=["crous"],
        hardlock_domain_strict=True,
        confidence=0.9,
    )
    block = rd.hardlock_block_for_prompt()
    assert "HARDLOCK" in block
    assert "crous" in block.lower()


def test_hardlock_block_both_region_and_domain() -> None:
    """Hardlock région + domaine → bloc combiné."""
    rd = RouteDecision(
        sub_indexes=["aides_territoires"],
        criteria=FilterCriteria(region="bretagne"),
        domain_lock=["crous"],
        hardlock_region_strict=True,
        hardlock_domain_strict=True,
        confidence=0.95,
    )
    block = rd.hardlock_block_for_prompt()
    assert "bretagne" in block.lower()
    assert "crous" in block.lower()


def test_hardlock_block_empty_when_strict_flag_without_data() -> None:
    """Edge case (audit step 7 → 8) : hardlock_region_strict=True mais
    criteria.region absent → header sans bullet → on retourne "" plutôt
    qu'un anchor vide '## CONTRAINTES HARDLOCK (R7)\\n'."""
    rd = RouteDecision(
        sub_indexes=["formations"],
        hardlock_region_strict=True,
        criteria=None,  # ← incohérent avec le flag, mais le code doit résister
        confidence=0.7,
    )
    assert rd.hardlock_block_for_prompt() == ""

    # Inverse : domain_strict sans domain_lock
    rd2 = RouteDecision(
        sub_indexes=["aides_territoires"],
        hardlock_domain_strict=True,
        domain_lock=None,
        confidence=0.7,
    )
    assert rd2.hardlock_block_for_prompt() == ""


# ────────────────────────── ROUTE_DECISION_TOOL ──────────────────────────


def test_tool_to_mistral_schema_format() -> None:
    """ROUTE_DECISION_TOOL produit le format Mistral function-calling attendu."""
    schema = ROUTE_DECISION_TOOL.to_mistral_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "decide_route"
    assert "description" in schema["function"]
    assert "parameters" in schema["function"]


def test_tool_required_fields() -> None:
    """Le schema requiert sub_indexes et confidence."""
    assert "required" in ROUTE_DECISION_TOOL_PARAMS
    assert set(ROUTE_DECISION_TOOL_PARAMS["required"]) == {"sub_indexes", "confidence"}


def test_tool_sub_indexes_enum_matches_constant() -> None:
    """L'enum sub_indexes du schema matche SUB_INDEX_NAMES."""
    sub_indexes_schema = ROUTE_DECISION_TOOL_PARAMS["properties"]["sub_indexes"]
    assert sub_indexes_schema["items"]["enum"] == list(SUB_INDEX_NAMES)


def test_tool_func_passthrough_basic() -> None:
    """_route_decision_tool_func normalise les kwargs en dict cohérent."""
    result = _route_decision_tool_func(
        sub_indexes=["formations"],
        region="Bretagne",
        confidence=0.9,
    )
    assert result["sub_indexes"] == ["formations"]
    assert result["region"] == "Bretagne"
    assert result["confidence"] == 0.9
    assert result["hardlock_region_strict"] is False  # default
    assert result["domain_lock"] is None


def test_tool_func_missing_required_via_call() -> None:
    """Tool.call valide les required → erreur si manque."""
    result = ROUTE_DECISION_TOOL.call()  # ni sub_indexes ni confidence
    assert "error" in result
    assert "missing" in result["error"]


# ────────────────────────── ROUTER_SYSTEM_PROMPT sanity ──────────────────────────


def test_system_prompt_mentions_all_sub_indexes() -> None:
    """Le system prompt explique chaque sub-index pour guider le LLM."""
    for name in SUB_INDEX_NAMES:
        assert name in ROUTER_SYSTEM_PROMPT


def test_system_prompt_mentions_all_refusal_reasons() -> None:
    """Le system prompt explique chaque cas de refus."""
    for reason in REFUSAL_REASONS:
        assert reason in ROUTER_SYSTEM_PROMPT


def test_system_prompt_includes_examples() -> None:
    """Le system prompt contient des exemples concrets pour few-shot implicite."""
    assert "Exemples" in ROUTER_SYSTEM_PROMPT or "exemples" in ROUTER_SYSTEM_PROMPT
    # Au moins un cas typique cité
    assert "CROUS" in ROUTER_SYSTEM_PROMPT or "crous" in ROUTER_SYSTEM_PROMPT


# ────────────────────────── JSON Schema authoritative ──────────────────────────


def test_authoritative_schema_loadable() -> None:
    """Le JSON schema authoritative est lisible et bien formé."""
    schema_path = Path(__file__).resolve().parents[1] / "src" / "state" / "route_decision_schema.json"
    assert schema_path.exists(), f"Schema absent : {schema_path}"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["title"] == "RouteDecision"
    assert "sub_indexes" in schema["properties"]
    assert "confidence" in schema["properties"]


def test_authoritative_schema_sub_indexes_match() -> None:
    """L'enum sub_indexes du JSON schema matche SUB_INDEX_NAMES."""
    schema_path = Path(__file__).resolve().parents[1] / "src" / "state" / "route_decision_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    enum_values = schema["properties"]["sub_indexes"]["items"]["enum"]
    assert set(enum_values) == set(SUB_INDEX_NAMES)


# ────────────────────────── RouterLLM.route() avec mocks ──────────────────────────


def _mock_mistral_response(tool_payload: dict | None, tool_name: str = "decide_route") -> SimpleNamespace:
    """Construit un faux response Mistral avec tool_calls."""
    if tool_payload is None:
        # Pas de tool_calls
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=None))]
        )
    tc = SimpleNamespace(
        function=SimpleNamespace(name=tool_name, arguments=json.dumps(tool_payload))
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tc]))]
    )


def test_router_llm_route_canonical_crous() -> None:
    """Cas live #1 : 'logement CROUS Lyon' → aides_territoires + criteria + hardlock."""
    payload = {
        "sub_indexes": ["aides_territoires"],
        "region": "auvergne-rhône-alpes",
        "domain_lock": ["crous"],
        "hardlock_region_strict": True,
        "hardlock_domain_strict": True,
        "top_k_override": 10,
        "confidence": 0.9,
    }
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(payload)

    router = RouterLLM(client=client)
    rd = router.route("Combien coûte le logement CROUS à Lyon ?")

    assert rd.sub_indexes == ["aides_territoires"]
    assert rd.criteria is not None
    # Normalisation accents (post-fix audit step 6) — cohérent avec fallback
    assert rd.criteria.region == "auvergne-rhone-alpes"
    assert rd.domain_lock == ["crous"]
    assert rd.hardlock_region_strict is True
    assert rd.top_k_override == 10
    assert rd.confidence == 0.9
    assert rd.is_fallback is False  # LLM a réussi
    client.chat.complete.assert_called_once()


def test_router_llm_route_superlative_refusal() -> None:
    """LLM détecte superlatif → refusal_reason + pre_written_response auto."""
    payload = {
        "sub_indexes": ["formations"],
        "refusal_reason": "superlative_no_data",
        "confidence": 0.95,
    }
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(payload)

    router = RouterLLM(client=client)
    rd = router.route("Quelle est la meilleure école de commerce ?")

    assert rd.refusal_reason == "superlative_no_data"
    assert rd.pre_written_response is not None
    assert rd.is_fallback is False


def test_router_llm_route_passes_history() -> None:
    """history est inclus dans messages envoyés au LLM (cap à 12)."""
    payload = {"sub_indexes": ["formations"], "confidence": 0.7}
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(payload)

    router = RouterLLM(client=client)
    history = [
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Réponse 1"},
        {"role": "user", "content": "Question 2"},
        {"role": "assistant", "content": "Réponse 2"},
    ]
    router.route("Question actuelle", history=history)

    call_kwargs = client.chat.complete.call_args.kwargs
    messages = call_kwargs["messages"]
    # system + 4 history + 1 user = 6 messages
    assert len(messages) == 6
    assert messages[0]["role"] == "system"
    assert messages[-1]["content"] == "Question actuelle"


def test_router_llm_history_capped_at_12() -> None:
    """Si history > 12, seulement les 12 derniers sont passés."""
    payload = {"sub_indexes": ["formations"], "confidence": 0.7}
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(payload)

    router = RouterLLM(client=client)
    history = [{"role": "user", "content": f"q{i}"} for i in range(20)]
    router.route("now", history=history)

    messages = client.chat.complete.call_args.kwargs["messages"]
    # system + 12 history + 1 user = 14 messages
    assert len(messages) == 14


def test_router_llm_falls_back_on_no_tool_calls() -> None:
    """LLM répond sans tool_calls → fallback déterministe."""
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(None)

    router = RouterLLM(client=client)
    rd = router.route("Quelles formations en Bretagne ?")

    assert rd.is_fallback is True
    # Le fallback déterministe doit avoir attrapé Bretagne
    assert rd.criteria is not None
    assert rd.criteria.region == "bretagne"


def test_router_llm_falls_back_on_invalid_json() -> None:
    """LLM retourne JSON invalide → fallback déterministe."""
    tc = SimpleNamespace(
        function=SimpleNamespace(name="decide_route", arguments="{not valid json")
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tc]))]
    )
    client = MagicMock()
    client.chat.complete.return_value = response

    router = RouterLLM(client=client)
    rd = router.route("meilleure école commerce")

    assert rd.is_fallback is True
    # Fallback détecte le superlatif
    assert rd.refusal_reason == "superlative_no_data"


def test_router_llm_falls_back_on_wrong_tool_name() -> None:
    """LLM appelle un autre tool (hallucine) → fallback déterministe."""
    payload = {"foo": "bar"}
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(
        payload, tool_name="hallucinated_tool"
    )

    router = RouterLLM(client=client)
    rd = router.route("Que fait un actuaire ?")

    assert rd.is_fallback is True


def test_router_llm_falls_back_on_exception() -> None:
    """LLM lève une exception (timeout, 5xx) → fallback gracieux."""
    client = MagicMock()
    # Exception non-retryable propage immédiatement (TypeError n'est pas
    # dans RETRYABLE_INDICATORS de retry.py). On utilise un type d'erreur
    # qui ressemble à un fail réel.
    client.chat.complete.side_effect = RuntimeError("Generic LLM error")

    router = RouterLLM(client=client)
    rd = router.route("Que fait un actuaire ?")

    # Fallback gracieux
    assert rd.is_fallback is True
    # Domain hint matché par les patterns existants
    assert "metiers" in rd.sub_indexes


def test_router_llm_falls_back_on_invalid_sub_index() -> None:
    """LLM retourne un sub_index hors enum → fallback (validation post_init)."""
    payload = {
        "sub_indexes": ["formations", "hallucinated_index"],
        "confidence": 0.8,
    }
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(payload)

    router = RouterLLM(client=client)
    rd = router.route("Question test")

    # Tomber en fallback car RouteDecision __post_init__ raise ValueError
    assert rd.is_fallback is True


def test_router_llm_falls_back_on_empty_question() -> None:
    """Question vide → fallback direct sans appeler le LLM (économie)."""
    client = MagicMock()
    router = RouterLLM(client=client)
    rd = router.route("")

    assert rd.is_fallback is True
    # Pas d'appel LLM
    client.chat.complete.assert_not_called()


def test_router_llm_falls_back_on_tool_call_validation_error() -> None:
    """LLM retourne payload sans 'sub_indexes' (manque required) → fallback."""
    # Payload sans sub_indexes ni confidence (les 2 required)
    tc = SimpleNamespace(
        function=SimpleNamespace(name="decide_route", arguments="{}")
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tc]))]
    )
    client = MagicMock()
    client.chat.complete.return_value = response

    router = RouterLLM(client=client)
    rd = router.route("logement CROUS Lyon")

    # Tool.call retourne {"error": "missing_required"} → fallback
    assert rd.is_fallback is True
    # Le fallback rattrape via classify_domain_hint
    assert "aides_territoires" in rd.sub_indexes


def test_router_llm_uses_default_model_mistral_small() -> None:
    """Par défaut, RouterLLM utilise le pin MISTRAL_SMALL (souverain léger)."""
    router = RouterLLM(client=MagicMock())
    from src.rag.models import MISTRAL_SMALL
    assert router.model == MISTRAL_SMALL


def test_router_llm_passes_tool_choice_any() -> None:
    """Le call Mistral utilise tool_choice='any' (force tool call)."""
    payload = {"sub_indexes": ["formations"], "confidence": 0.8}
    client = MagicMock()
    client.chat.complete.return_value = _mock_mistral_response(payload)

    router = RouterLLM(client=client)
    router.route("Question test")

    kwargs = client.chat.complete.call_args.kwargs
    assert kwargs["tool_choice"] == "any"
    assert len(kwargs["tools"]) == 1
    assert kwargs["tools"][0]["function"]["name"] == "decide_route"
