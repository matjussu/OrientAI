import json
from pathlib import Path  # noqa: F401  (still used elsewhere in tests)
from unittest.mock import MagicMock, patch  # noqa: F401
from src.eval.systems import OurRagSystem, MistralRawSystem


def test_mistral_raw_uses_neutral_prompt_not_optimized_system_prompt():
    """Phase E.1 — fair-baseline fix.

    Before E.1, MistralRawSystem shared the *optimized* SYSTEM_PROMPT
    with our_rag, which imposes anti-confession / Plan A/B/C /
    distinct-cities / fact-check rules. This crippled mistral_raw's
    free generation and structurally biased the comparison in our
    favor. For a legitimate baseline, mistral_raw must use a neutral
    prompt that describes the task but imposes no custom scoring
    rules.
    """
    from src.eval.systems import NEUTRAL_MISTRAL_PROMPT
    from src.prompt.system import SYSTEM_PROMPT

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="raw answer"))]
    mock_client.chat.complete.return_value = mock_response

    system = MistralRawSystem(mock_client)
    answer = system.answer("A1", "Quelles formations cyber ?")
    assert answer == "raw answer"
    messages = mock_client.chat.complete.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    # The baseline uses the neutral prompt, not the optimized v3.x prompt.
    assert messages[0]["content"] == NEUTRAL_MISTRAL_PROMPT
    assert messages[0]["content"] != SYSTEM_PROMPT
    # The user message carries the question and has no FICHE context
    # (the whole point of the ablation is to isolate the effect of RAG).
    assert "Quelles formations cyber" in messages[1]["content"]
    assert "FICHE" not in messages[1]["content"]


def test_neutral_mistral_prompt_is_minimal_and_free_of_custom_rules():
    """The neutral prompt describes the task but does NOT impose
    any of the v3.x optimizations (anti-confession, Plan A/B/C,
    distinct cities, fact-check, interdisciplinary). It should be
    what a generic orientation chatbot would ship with.
    """
    from src.eval.systems import NEUTRAL_MISTRAL_PROMPT
    # Must identify the assistant role
    assert "orientation" in NEUTRAL_MISTRAL_PROMPT.lower()
    # Must NOT carry any v3.x custom rules
    low = NEUTRAL_MISTRAL_PROMPT.lower()
    assert "plan a" not in low
    assert "anti-confession" not in low
    assert "connaissance générale" not in low  # v3.x-specific marker
    assert "villes distinctes" not in low
    assert "secnumedu" not in low  # label bias
    assert "interdisciplinaire" not in low


def test_our_rag_uses_pipeline():
    mock_pipeline = MagicMock()
    mock_pipeline.answer.return_value = ("our answer", [])

    system = OurRagSystem(mock_pipeline)
    assert system.answer("A1", "question") == "our answer"
    mock_pipeline.answer.assert_called_once_with("question")


def test_systems_have_name_attribute():
    """Each system exposes a `name` attribute used by the benchmark runner
    to build the label mapping in Task 4.2."""
    mock_client = MagicMock()
    mock_pipeline = MagicMock()

    assert OurRagSystem(mock_pipeline).name == "our_rag"
    assert MistralRawSystem(mock_client).name == "mistral_raw"


# --- Phase F.2 — 7-system baseline matrix ---


def test_mistral_with_custom_prompt_uses_supplied_prompt():
    """Phase F.2 — `mistral_v3_2_no_rag` baseline: same model as our_rag
    (mistral-medium-latest) but receives our optimized v3.2 prompt
    WITHOUT the RAG context. Isolates the contribution of retrieval
    on top of the prompt engineering."""
    from src.eval.systems import MistralWithCustomPromptSystem

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="ans"))]
    mock_client.chat.complete.return_value = mock_response

    custom_prompt = "Tu es un conseiller spécialisé. Plan A/B/C obligatoire."
    sys = MistralWithCustomPromptSystem(
        client=mock_client,
        system_prompt=custom_prompt,
        name="mistral_v3_2_no_rag",
    )
    assert sys.name == "mistral_v3_2_no_rag"
    assert sys.answer("Q1", "test ?") == "ans"
    msgs = mock_client.chat.complete.call_args.kwargs["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == custom_prompt
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "test ?"
    # No RAG context in the user message
    assert "FICHE" not in msgs[1]["content"]


def test_openai_baseline_uses_chat_completions():
    """OpenAI GPT-4o baseline. Wraps openai.OpenAI client."""
    from src.eval.systems import OpenAIBaseline

    mock_client = MagicMock()
    # OpenAI v1 SDK shape: client.chat.completions.create(...).choices[0].message.content
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="gpt answer"))]
    mock_client.chat.completions.create.return_value = mock_resp

    sys = OpenAIBaseline(
        client=mock_client,
        model="gpt-4o",
        system_prompt="generic prompt",
        name="gpt4o_neutral",
    )
    assert sys.name == "gpt4o_neutral"
    assert sys.answer("Q1", "Question test ?") == "gpt answer"

    call = mock_client.chat.completions.create.call_args
    assert call.kwargs.get("model") == "gpt-4o"
    msgs = call.kwargs["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "generic prompt"
    assert msgs[1]["role"] == "user"
    assert "Question test" in msgs[1]["content"]


def test_openai_baseline_default_temperature_matches_others():
    """All systems use temperature=0.3 for fair comparison (same as
    MistralRawSystem and OurRagSystem.generate)."""
    from src.eval.systems import OpenAIBaseline

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="x"))]
    mock_client.chat.completions.create.return_value = mock_resp

    OpenAIBaseline(
        client=mock_client, model="gpt-4o",
        system_prompt="p", name="gpt4o_neutral",
    ).answer("Q", "q")
    assert mock_client.chat.completions.create.call_args.kwargs["temperature"] == 0.3


def test_claude_baseline_uses_messages_create():
    """Claude Sonnet baseline. Wraps anthropic.Anthropic client.messages.create."""
    from src.eval.systems import ClaudeBaseline

    mock_client = MagicMock()
    # anthropic shape: client.messages.create(...).content[0].text
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="claude answer")]
    mock_client.messages.create.return_value = mock_resp

    sys = ClaudeBaseline(
        client=mock_client,
        model="claude-sonnet-4-5",
        system_prompt="generic prompt",
        name="claude_neutral",
    )
    assert sys.name == "claude_neutral"
    assert sys.answer("Q1", "Question test ?") == "claude answer"

    call = mock_client.messages.create.call_args
    assert call.kwargs.get("model") == "claude-sonnet-4-5"
    assert call.kwargs.get("system") == "generic prompt"
    msgs = call.kwargs["messages"]
    assert msgs[0]["role"] == "user"
    assert "Question test" in msgs[0]["content"]


def test_all_baselines_share_identical_answer_signature():
    """The benchmark runner calls system.answer(qid, text) generically.
    All 7 systems must accept this signature and return a string."""
    from src.eval.systems import (
        MistralWithCustomPromptSystem,
        OpenAIBaseline,
        ClaudeBaseline,
    )

    # Set up minimal mocks for all 3 new system classes
    mock_mistral = MagicMock()
    mock_mistral.chat.complete.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="m"))]
    )
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="o"))]
    )
    mock_claude = MagicMock()
    mock_claude.messages.create.return_value = MagicMock(
        content=[MagicMock(text="c")]
    )

    systems = [
        MistralWithCustomPromptSystem(mock_mistral, "p", "test_mistral"),
        OpenAIBaseline(mock_openai, "gpt-4o", "p", "test_openai"),
        ClaudeBaseline(mock_claude, "claude-sonnet-4-5", "p", "test_claude"),
    ]
    for s in systems:
        # Same signature: answer(qid, question) -> str
        result = s.answer("Q1", "anything ?")
        assert isinstance(result, str)
        assert result  # non-empty


# === Sprint 12 axe 2 — AgentPipelineSystem wrap test ===


def test_agent_pipeline_system_returns_answer_text():
    """AgentPipelineSystem wraps `pipeline.answer(query) → AgentAnswer`
    and returns only `answer_text` to bench runner."""
    from unittest.mock import MagicMock
    from src.eval.systems import AgentPipelineSystem
    from src.agent.pipeline_agent import AgentPipeline, AgentAnswer

    # Mock pipeline avec spec=AgentPipeline pour passer isinstance check
    mock_pipeline = MagicMock(spec=AgentPipeline)
    mock_answer = AgentAnswer(
        query="Quelles formations cyber ?",
        answer_text="3 pistes : EFREI, ENSIBS, ESIEE.",
        profile=None,
        plan=None,
        elapsed_total_s=42.0,
    )
    mock_pipeline.answer.return_value = mock_answer

    sys = AgentPipelineSystem(pipeline=mock_pipeline)
    assert sys.name == "agent_pipeline_v3_2"

    result = sys.answer("Q1", "Quelles formations cyber ?")
    assert result == "3 pistes : EFREI, ENSIBS, ESIEE."
    mock_pipeline.answer.assert_called_once_with("Quelles formations cyber ?")


def test_agent_pipeline_system_handles_pipeline_error():
    """En cas d'erreur AgentPipeline, retour string non-crash pour ne
    pas casser le runner bench (le judge verra réponse dégradée)."""
    from unittest.mock import MagicMock
    from src.eval.systems import AgentPipelineSystem
    from src.agent.pipeline_agent import AgentPipeline, AgentAnswer

    mock_pipeline = MagicMock(spec=AgentPipeline)
    mock_answer = AgentAnswer(
        query="Q",
        answer_text="",
        profile=None,
        plan=None,
        error="Mistral API timeout",
    )
    mock_pipeline.answer.return_value = mock_answer

    sys = AgentPipelineSystem(pipeline=mock_pipeline)
    result = sys.answer("Q1", "Q")
    assert isinstance(result, str)
    assert "pipeline_error" in result
    assert "Mistral API timeout" in result


def test_agent_pipeline_system_rejects_non_agent_pipeline_instance():
    """Type check : refuse les non-AgentPipeline instances pour éviter
    les surprises silencieuses au runner."""
    import pytest
    from src.eval.systems import AgentPipelineSystem

    with pytest.raises(TypeError) as exc:
        AgentPipelineSystem(pipeline="not_a_pipeline")
    assert "AgentPipeline" in str(exc.value)


def test_agent_pipeline_system_signature_matches_other_systems():
    """Signature `answer(qid, question) → str` cohérente avec les autres
    systems pour le runner bench."""
    from unittest.mock import MagicMock
    from src.eval.systems import AgentPipelineSystem
    from src.agent.pipeline_agent import AgentPipeline, AgentAnswer

    mock_pipeline = MagicMock(spec=AgentPipeline)
    mock_pipeline.answer.return_value = AgentAnswer(
        query="x", answer_text="ok", profile=None, plan=None,
    )

    sys = AgentPipelineSystem(pipeline=mock_pipeline)
    result = sys.answer("Q1", "anything ?")
    assert isinstance(result, str)
    assert result
