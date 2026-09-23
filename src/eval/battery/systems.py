"""Systemes joues par le banc. Chacun repond a `ask(question, history, key)` par un dict :

    answer            texte rendu a l'eleve
    sources           fiches exposees (titre, etablissement, ville, source), pour le juge
    source_positions  positions corpus de ces fiches (cle stable, cf corpus.py), pour le controle
                      des chiffres ; None pour une fiche que le pipeline a copiee (compte au rapport)
    usage, model      tokens et modele, pour le suivi de cout

Ajouter un systeme = une classe + une entree dans SYSTEMS.
"""
from __future__ import annotations

import json
import os

from src.eval.battery.answers import answer_sha
from src.eval.battery.config import (
    CORPUS_PATH,
    HISTORY_WINDOW,
    INDEX_PATH,
    MODELS,
    SYSTEM_PROMPT_BASELINE,
    SYSTEM_PROMPT_CTX,
)


def check_complete(stop_reason: str | None, model: str) -> None:
    """Refuse une reponse coupee par le plafond de tokens (Anthropic `max_tokens`, OpenAI et
    Mistral `length`) : jugee telle quelle, elle compterait comme une mauvaise reponse."""
    if stop_reason in ("max_tokens", "length"):
        from src.eval.battery.runner import IncompleteAnswer
        raise IncompleteAnswer(f"{model} : reponse coupee ({stop_reason})")


def _source_view(fiche: dict) -> dict:
    return {"titre": fiche.get("nom"), "etablissement": fiche.get("etablissement"),
            "ville": fiche.get("ville"), "source": fiche.get("source")}


# Delai des appels directs a Mistral (hors pipeline, qui garde son client de prod). Le defaut du
# SDK a coupe 2 tours de mistral-large-2512 sur 67 le 23/09 (ReadTimeout, reponses de ~20 s).
MISTRAL_TIMEOUT_MS = 120_000


def _mistral_client(timeout_ms: int | None = None):
    from mistralai.client import Mistral
    return Mistral(api_key=os.environ["MISTRAL_API_KEY"], timeout_ms=timeout_ms)


class LocalSystem:
    """Le pipeline OrientIA en conditions de serving (mode recit, historique borne)."""

    name = "local"

    def __init__(self, corpus):
        os.environ.setdefault("ORIENTIA_NARRATIVE_MODE", "1")
        from src.api.provenance import build_fingerprint
        from src.rag.embeddings import fiche_to_text
        from src.rag.factory import make_production_pipeline

        self.corpus = corpus
        self.pipeline = make_production_pipeline(_mistral_client(), corpus.fiches)
        self.pipeline.load_index_from(str(INDEX_PATH))
        self.fiche_to_text = fiche_to_text
        self.model = MODELS["mistral_medium"]
        # Meme empreinte que /health en prod (prompt, corpus, index, modeles) : prouve que le banc
        # a joue le code servi, ou dit en quoi il differe.
        self.fingerprint = build_fingerprint(CORPUS_PATH, INDEX_PATH)

    def _position(self, fiche: dict) -> int | None:
        try:
            return self.corpus.position_of(fiche)
        except KeyError:
            return None

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        text, top, trace = self.pipeline.answer(
            question, history=history[-HISTORY_WINDOW:] or None, return_trace=True)
        fiches = [t.get("fiche", t) for t in top]
        return {
            "answer": text,
            "sources": [_source_view(f) | {"score": t.get("score"), "text": self.fiche_to_text(f)}
                        for t, f in zip(top, fiches)],
            "source_positions": [self._position(f) for f in fiches],
            "trace": {
                "router": _jsonable(trace.router_result),
                "select_fallthrough": trace.select_fallthrough,
                "geo_refusal": trace.geo_refusal,
                "validation": _jsonable(trace.validation),
                "policy": _jsonable(trace.policy_result),
                "format_decision": _jsonable(trace.narrative_format_decision),
                "retry": trace.retry_metadata,
            },
            "model": self.model,
        }


def _jsonable(obj):
    if obj is None:
        return None
    try:
        return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))
    except (TypeError, ValueError):
        return str(obj)


class ClaudeSystem:
    """Sonnet seul (plafond culture generale) ou avec les memes fiches que `local` a servies."""

    def __init__(self, name: str, local_run: dict | None = None):
        import anthropic
        self.name = name
        self.local_run = local_run
        self.client = anthropic.Anthropic()
        self.model = MODELS["claude_sonnet"]

    def _system_prompt(self, key) -> tuple[str, list[dict], list]:
        if self.local_run is None:
            return SYSTEM_PROMPT_BASELINE, [], []
        served = self.local_run.get(key, {})
        sources, positions = served.get("sources", []), served.get("source_positions", [])
        if not sources:
            return SYSTEM_PROMPT_CTX + "\n\n<fiches>(aucune fiche servie sur ce tour)</fiches>", [], []
        fiches = "\n\n---\n\n".join(
            f"[fiche {i + 1} | source={s['source']}]\n{s['text']}" for i, s in enumerate(sources))
        views = [{k: s.get(k) for k in ("titre", "etablissement", "ville", "source")} for s in sources]
        return SYSTEM_PROMPT_CTX + f"\n\n<fiches>\n{fiches}\n</fiches>", views, positions

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        system, sources, positions = self._system_prompt(key)
        # Le tour de `local` dont on a repris les fiches : si local est rejoue ensuite, le rapport
        # voit que ce tour de claude_ctx porte sur d'anciennes fiches.
        local_sha = answer_sha(self.local_run.get(key, {})) if self.local_run is not None else None
        r = self.client.messages.create(
            model=self.model, max_tokens=2000, system=system,
            messages=history + [{"role": "user", "content": question}],
            thinking={"type": "adaptive"}, output_config={"effort": "medium"},
        )
        check_complete(r.stop_reason, self.model)
        return {"answer": "".join(b.text for b in r.content if b.type == "text"),
                "sources": sources, "source_positions": positions, "local_answer_sha": local_sha,
                "usage": {"in": r.usage.input_tokens, "out": r.usage.output_tokens},
                "model": self.model}


class OpenAISystem:
    name = "gpt_norag"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = MODELS["gpt"]

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT_BASELINE}, *history,
                {"role": "user", "content": question}]
        r = self.client.chat.completions.create(model=self.model, messages=msgs)
        check_complete(r.choices[0].finish_reason, self.model)
        return {"answer": r.choices[0].message.content, "sources": [], "source_positions": [],
                "usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens},
                "model": self.model}


class MistralSystem:
    """Un modele Mistral seul, sans fiche : sa culture generale, meme prompt que les autres."""

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model
        self.client = _mistral_client(MISTRAL_TIMEOUT_MS)

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT_BASELINE}, *history,
                {"role": "user", "content": question}]
        r = self.client.chat.complete(model=self.model, messages=msgs, temperature=0.3)
        check_complete(r.choices[0].finish_reason, self.model)
        return {"answer": r.choices[0].message.content, "sources": [], "source_positions": [],
                "usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens},
                "model": self.model}


def build(name: str, corpus=None, local_run: dict | None = None):
    """Instancie un systeme. `corpus` pour ceux qui lisent les fiches, `local_run` pour claude_ctx."""
    from src.eval.battery import agent

    if name == "local":
        return LocalSystem(corpus)
    if name == "claude_norag":
        return ClaudeSystem(name)
    if name == "claude_ctx":
        if not local_run:
            raise ValueError("claude_ctx rejoue les fiches de `local` : jouer `local` d'abord dans ce run")
        return ClaudeSystem(name, local_run=local_run)
    if name == "gpt_norag":
        return OpenAISystem()
    if name == "mistral_large_norag":
        return MistralSystem(name, MODELS["mistral_large"])
    if name == "mistral_medium_norag":
        return MistralSystem(name, MODELS["mistral_medium"])
    if name == "agent_sonnet":
        return agent.SonnetAgent(corpus)
    if name == "agent_mistral":
        return agent.MistralAgent(corpus)
    raise ValueError(f"systeme inconnu : {name}")


SYSTEMS = ["local", "claude_norag", "claude_ctx", "gpt_norag", "mistral_large_norag",
           "mistral_medium_norag", "agent_sonnet", "agent_mistral"]
NEEDS_CORPUS = {"local", "agent_sonnet", "agent_mistral"}
