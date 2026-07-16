"""Agent loop with Mistral function-calling — orchestrateur central.

Pattern : `agent.run(question)` → boucle `chat.complete(tools=...)` →
dispatch tool calls retournés → réinjection résultats → composition
finale du LLM.

Cf ADR-051 et `experiments/poc_mistral_toolcall.py` pour le pattern
validé samedi 22/04.

Sprint 1 : Agent basique loop. Sprints 2-4 ajouteront des tools au
registry sans modif du loop principal.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from mistralai.client import Mistral

from src.agent.retry import call_with_retry
from src.agent.tool import ToolRegistry
from src.rag.models import MISTRAL_LARGE


DEFAULT_SYSTEM_PROMPT = (
    "Tu es OrientAI, un assistant d'orientation académique et "
    "professionnelle pour des étudiants français (Phase initiale, "
    "réorientation, master/insertion). Tu as accès à des outils que "
    "tu invoques quand pertinent. Réponds en français, concisément "
    "(150-300 mots), structurellement (TL;DR + plan d'action). Cite "
    "tes sources quand disponibles."
)


@dataclass
class AgentRunResult:
    """Résultat d'une invocation `agent.run(question)`."""

    answer: str | None
    tool_calls_made: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    latency_s: float = 0.0
    success: bool = True
    error: str | None = None


@dataclass
class Agent:
    """Agent loop orchestrateur Mistral tool-use."""

    client: Mistral
    registry: ToolRegistry
    model: str = MISTRAL_LARGE
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    max_iterations: int = 5
    timeout_ms: int = 180_000  # ADR-047
    max_retries_per_call: int = 3  # retry exponential backoff (cf retry.py)
    retry_initial_backoff: float = 2.0

    def run(self, question: str) -> AgentRunResult:
        """Boucle orchestration : question → final answer.

        Le LLM peut décider d'appeler 0, 1 ou plusieurs tools (ou en
        chaîne). Le loop sort dès que Mistral compose une réponse
        sans tool_calls (= réponse finale prête).
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question},
        ]
        tool_calls_made: list[dict[str, Any]] = []
        t0 = time.time()

        for iteration in range(self.max_iterations):
            try:
                response = call_with_retry(
                    lambda: self.client.chat.complete(
                        model=self.model,
                        messages=messages,
                        tools=self.registry.to_mistral_schemas() or None,
                        tool_choice="auto" if len(self.registry) else None,
                    ),
                    max_retries=self.max_retries_per_call,
                    initial_backoff=self.retry_initial_backoff,
                )
            except Exception as e:
                return AgentRunResult(
                    answer=None,
                    tool_calls_made=tool_calls_made,
                    iterations=iteration,
                    latency_s=round(time.time() - t0, 2),
                    success=False,
                    error=f"{type(e).__name__}: {e}",
                )
            msg = response.choices[0].message

            if msg.tool_calls:
                # Réinjecter le message assistant avec ses tool_calls
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
                # Dispatch chaque tool_call
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args: dict | None = None
                    try:
                        parsed = json.loads(tc.function.arguments)
                        args = parsed if isinstance(parsed, dict) else None
                    except json.JSONDecodeError as e:
                        result = {"error": "json_parse_failed",
                                  "message": str(e)}
                    else:
                        if args is None:
                            result = {"error": "args_not_object",
                                      "raw": tc.function.arguments[:200]}
                        else:
                            result = self.registry.dispatch(name, **args)
                    tool_calls_made.append({
                        "name": name,
                        "args": args,
                        "result": result,
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
            else:
                # Réponse finale composée par Mistral
                return AgentRunResult(
                    answer=msg.content,
                    tool_calls_made=tool_calls_made,
                    iterations=iteration + 1,
                    latency_s=round(time.time() - t0, 2),
                    success=True,
                )

        # Dépassement max_iterations
        return AgentRunResult(
            answer=None,
            tool_calls_made=tool_calls_made,
            iterations=self.max_iterations,
            latency_s=round(time.time() - t0, 2),
            success=False,
            error="max_iterations_reached",
        )
