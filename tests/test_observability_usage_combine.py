"""Regression: langchain-mistralai usage-combine must tolerate nested usage dicts.

Mistral `token_usage` payloads carry nested dicts (e.g. `completion_tokens_details`).
langchain_mistralai 1.1.4's stock `ChatMistralAI._combine_llm_outputs` does
`overall[k] += v` and crashes with `TypeError: unsupported operand type(s) for +=:
'dict' and 'dict'` when combining >=2 generations (the answer_relevancy strictness=3
path), silently NaN-ing those Ragas samples. `src.observability` patches it on import
(Step 1b). These tests pin the patched behaviour.

Pure dict manipulation: `_combine_llm_outputs` only reads `self.model`, never calls
the API, so this test costs nothing.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import src.observability  # noqa: F401 — installs the Step 1b patch on import

mistral_chat = pytest.importorskip("langchain_mistralai.chat_models")
ChatMistralAI = mistral_chat.ChatMistralAI


def _usage() -> dict:
    """One generation's llm_output, Mistral-shaped, with a nested usage sub-dict."""
    return {
        "token_usage": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "completion_tokens_details": {
                "reasoning_tokens": 1,
                "accepted_prediction_tokens": 2,
            },
        },
        "model_name": "mistral-small-latest",
    }


def test_combine_single_generation_preserves_nested_usage():
    """n=1 path (faithfulness, context_precision): passthrough, nested dict intact."""
    self_ = SimpleNamespace(model="mistral-small-latest")
    out = ChatMistralAI._combine_llm_outputs(self_, [_usage()])
    tu = out["token_usage"]
    assert tu["total_tokens"] == 120
    assert tu["completion_tokens_details"]["reasoning_tokens"] == 1
    assert out["model_name"] == "mistral-small-latest"


def test_combine_three_generations_no_typeerror_and_sums():
    """answer_relevancy strictness=3 -> n=3: must not raise, numeric leaves summed."""
    self_ = SimpleNamespace(model="mistral-small-latest")
    out = ChatMistralAI._combine_llm_outputs(self_, [_usage(), _usage(), _usage()])
    tu = out["token_usage"]
    assert tu["total_tokens"] == 360  # 120 * 3
    assert tu["prompt_tokens"] == 300
    # nested leaves summed recursively, not crashed on
    assert tu["completion_tokens_details"]["reasoning_tokens"] == 3
    assert tu["completion_tokens_details"]["accepted_prediction_tokens"] == 6


def test_combine_skips_none_outputs():
    """Streaming yields None outputs; combiner must skip them."""
    self_ = SimpleNamespace(model="mistral-small-latest")
    out = ChatMistralAI._combine_llm_outputs(self_, [None, _usage(), None])
    assert out["token_usage"]["total_tokens"] == 120


def test_patch_is_installed():
    """Guard: src.observability must have replaced the stock combiner."""
    assert ChatMistralAI._combine_llm_outputs.__name__ == "_safe_combine_llm_outputs"
