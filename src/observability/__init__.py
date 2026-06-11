"""Observability stack — Langfuse (tracing/prompts) + Ragas (RAG eval metrics).

Import this module BEFORE importing ragas anywhere in the codebase:

    import src.observability  # noqa: F401 — must come before ragas
    import ragas

Why: mistralai 2.3.2 ships as a PEP-420 namespace package with no top-level
re-export of the `Mistral` class. The `instructor` lib (transitive dep of ragas)
does `from mistralai import Mistral` at module load and crashes. This module
runs a one-line monkey-patch that mirrors `mistralai.client.Mistral` to the
top-level namespace, restoring v1.x-style imports without touching installed
package files.

It also exposes a light Langfuse instrumentation helper `obs_span()` that
returns a real span when `LANGFUSE_PUBLIC_KEY` is set, or a `nullcontext()`
otherwise. Pipeline code can use it unconditionally — production env without
Langfuse keys gets zero overhead.

Safe to import multiple times.
"""
from __future__ import annotations

import os
from contextlib import nullcontext
from typing import Any

import mistralai as _mistralai

# --- Step 1 : mistralai top-level shim (required for ragas/instructor) ---
if not hasattr(_mistralai, "Mistral"):
    from mistralai.client import Mistral as _Mistral

    _mistralai.Mistral = _Mistral  # type: ignore[attr-defined]


# --- Step 1b : langchain-mistralai usage-combine hardening (Ragas re-baseline) ---
# langchain_mistralai 1.1.4 `ChatMistralAI._combine_llm_outputs` does
# `overall_token_usage[k] += v` over Mistral's `token_usage` dict. Current Mistral
# usage payloads carry NESTED dicts (e.g. `completion_tokens_details`), so combining
# >=2 generations crashes with `TypeError: unsupported operand type(s) for +=:
# 'dict' and 'dict'`. This hits every Ragas metric that requests n>1 generations
# (answer_relevancy, strictness=3 -> n=3), silently NaN-ing those samples (~305/1158
# in the 2026-06-10 ragas_full run). We swap in a depth-aware merge that sums numeric
# leaves and recurses into nested dicts. `token_usage` is pure bookkeeping here
# (ragas_eval passes no token_usage_parser), so this NEVER affects metric scores -
# it only stops the crash. Idempotent; no-op if the lib is absent (prod venv).
def _merge_token_usage(acc: dict, new: Any) -> dict:
    for k, v in (new or {}).items():
        if isinstance(v, dict):
            base = acc.get(k) if isinstance(acc.get(k), dict) else {}
            acc[k] = _merge_token_usage(base, v)
        elif isinstance(v, (int, float)):
            prev = acc.get(k) if isinstance(acc.get(k), (int, float)) else 0
            acc[k] = prev + v
        else:
            acc[k] = v
    return acc


try:
    from langchain_mistralai.chat_models import ChatMistralAI as _ChatMistralAI

    def _safe_combine_llm_outputs(self: Any, llm_outputs: list) -> dict:
        overall: dict = {}
        for output in llm_outputs:
            if not output:  # None happens in streaming
                continue
            _merge_token_usage(overall, output.get("token_usage") or {})
        return {"token_usage": overall, "model_name": getattr(self, "model", None)}

    if getattr(_ChatMistralAI._combine_llm_outputs, "__name__", "") != "_safe_combine_llm_outputs":
        _ChatMistralAI._combine_llm_outputs = _safe_combine_llm_outputs  # type: ignore[assignment]
except Exception:  # pragma: no cover — lib absent in prod venv (deliberate, see CLAUDE.md)
    pass


# --- Step 2 : Langfuse client (lazy, opt-in via env) ---
_LANGFUSE_CLIENT: Any | None = None
_LANGFUSE_OBSERVE: Any | None = None


def _init_langfuse() -> None:
    """Initialise le client Langfuse une seule fois, si les clés sont set."""
    global _LANGFUSE_CLIENT, _LANGFUSE_OBSERVE

    if _LANGFUSE_CLIENT is not None or _LANGFUSE_OBSERVE is not None:
        return  # already initialized

    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        return  # no keys → leave both None, helpers will no-op

    try:
        from langfuse import Langfuse, observe  # type: ignore[import-not-found]
        _LANGFUSE_CLIENT = Langfuse()
        _LANGFUSE_OBSERVE = observe
    except Exception:  # pragma: no cover — SDK miss or runtime error
        _LANGFUSE_CLIENT = None
        _LANGFUSE_OBSERVE = None


def obs_span(name: str, as_type: str = "span", **kwargs: Any):
    """Context manager : observation Langfuse nommée si client up, sinon no-op.

    Langfuse v4 a renommé `start_as_current_span` → `start_as_current_observation`.
    Ce helper utilise la v4 API. as_type accepte 'span' (default), 'retriever',
    'generation', 'embedding', 'agent', 'tool', 'chain', 'evaluator', 'guardrail'.

    Usage :
        with obs_span("retrieval", as_type="retriever", input={"k": 30}):
            top = retriever.retrieve(...)
    """
    _init_langfuse()
    if _LANGFUSE_CLIENT is None:
        return nullcontext()
    try:
        return _LANGFUSE_CLIENT.start_as_current_observation(
            name=name, as_type=as_type, **kwargs
        )
    except Exception:
        return nullcontext()


def observe(*args: Any, **kwargs: Any):
    """Décorateur @observe Langfuse pass-through (no-op si client absent).

    Usage :
        @observe(name="orientia_answer")
        def answer(self, question): ...
    """
    _init_langfuse()
    if _LANGFUSE_OBSERVE is None:
        # No-op decorator factory
        def _noop_deco(func):
            return func

        if args and callable(args[0]) and not kwargs:
            # @observe sans parenthèses — args[0] est la fonction
            return args[0]
        return _noop_deco

    return _LANGFUSE_OBSERVE(*args, **kwargs)


def flush() -> None:
    """Force le flush Langfuse (utile en fin de script avant exit)."""
    if _LANGFUSE_CLIENT is not None:
        try:
            _LANGFUSE_CLIENT.flush()
        except Exception:
            pass
