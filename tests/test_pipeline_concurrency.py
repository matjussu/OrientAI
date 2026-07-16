"""Tests de concurrence RequestTrace (H1 lot 1.6, ordre 0905).

L'ancien design (attributs mutables pipeline.last_*) mélangeait l'état de
requêtes concurrentes : une requête A lente pouvait lire la validation de la
requête B rapide arrivée entre-temps (verdict INFIDELE attribué à la mauvaise
réponse). Ces tests prouvent que les traces RETOURNÉES ne se croisent plus,
sur les deux chemins (answer sync sous threads, answer_stream sous asyncio).

Scénario adversarial : la requête PROPRE est lente, la requête FLAGGÉE est
rapide et se termine PENDANT que la propre est en vol. Avec l'état partagé,
la propre récupérait le flag de l'autre.
"""
from __future__ import annotations

import asyncio
import threading
import time
from unittest.mock import MagicMock


import src.rag.pipeline as pipeline_mod
from src.rag.pipeline import OrientIAPipeline, RequestTrace
from src.validator.validator import Validator

# Question -> (délai de génération, réponse). La réponse "propre" cite un
# chiffre présent dans sa fiche ; la "flaggée" cite un chiffre fabriqué.
SCENARIO = {
    "question propre lente": (0.30, "Il offre 60 places [source S1]."),
    "question flaggee rapide": (0.05, "Le taux d'accès est de 99 % [source S1]."),
}

FICHE = {"nom": "BUT Info", "etablissement": "IUT Lyon 1", "nombre_places": 60}


def _pipeline() -> OrientIAPipeline:
    p = OrientIAPipeline(
        client=MagicMock(),
        fiches=[],
        validator=Validator(fiches=[]),
        use_strict_v4=True,
        enable_post_process=False,
        enable_geo_coherence=False,
    )
    p.index = MagicMock()  # bypass le check "Pipeline not built"

    def _stub_retrieve(**kw):
        return [{"score": 1.0, "fiche": dict(FICHE)}]

    p._retrieve_and_filter = _stub_retrieve  # type: ignore[assignment]
    return p


def _fake_generate(client, retrieved, question, **kwargs):
    delay, answer = SCENARIO[question]
    time.sleep(delay)
    return answer


async def _fake_generate_stream(client, retrieved, question, **kwargs):
    delay, answer = SCENARIO[question]
    for tok in answer.split(" "):
        await asyncio.sleep(delay / 5)
        yield tok + " "


class TestAnswerSyncConcurrent:
    def test_traces_ne_se_croisent_pas_sous_threads(self, monkeypatch):
        monkeypatch.setattr(pipeline_mod, "generate", _fake_generate)
        p = _pipeline()

        results: dict[str, RequestTrace] = {}
        barrier = threading.Barrier(2)

        def run(question: str):
            barrier.wait()
            _text, _sources, trace = p.answer(question, return_trace=True)
            results[question] = trace

        threads = [threading.Thread(target=run, args=(q,)) for q in SCENARIO]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        propre = results["question propre lente"]
        flaggee = results["question flaggee rapide"]
        # La flaggée est bien flaggée (99 % absent de la fiche)
        assert flaggee.validation is not None and flaggee.validation.flagged is True
        # La propre, terminée APRÈS la flaggée, ne récupère PAS son flag
        assert propre.validation is not None and propre.validation.flagged is False
        assert propre.validation is not flaggee.validation

    def test_answer_sans_return_trace_signature_inchangee(self, monkeypatch):
        monkeypatch.setattr(pipeline_mod, "generate", _fake_generate)
        p = _pipeline()
        out = p.answer("question flaggee rapide")
        assert isinstance(out, tuple) and len(out) == 2

    def test_proprietes_last_refletent_la_derniere_terminee(self, monkeypatch):
        """Contrat DEBUG des propriétés last_* : single-thread, elles gardent
        exactement l'ancien comportement (lecture post-appel)."""
        monkeypatch.setattr(pipeline_mod, "generate", _fake_generate)
        p = _pipeline()
        p.answer("question flaggee rapide")
        assert p.last_validation is not None and p.last_validation.flagged is True
        p.answer("question propre lente")
        assert p.last_validation.flagged is False


class TestAnswerStreamConcurrent:
    def test_verdicts_stream_ne_se_croisent_pas(self, monkeypatch):
        monkeypatch.setattr(pipeline_mod, "generate_stream", _fake_generate_stream)
        p = _pipeline()

        async def consume(question: str) -> dict:
            events = {}
            async for ev in p.answer_stream(question, short_circuit_pace_s=0.0):
                if ev["type"] == "faithfulness":
                    events["verdict"] = ev.get("verdict")
                if ev["type"] == "error":
                    raise AssertionError(f"stream error: {ev}")
            return events

        async def main():
            return await asyncio.gather(
                consume("question propre lente"),
                consume("question flaggee rapide"),
            )

        propre, flaggee = asyncio.run(main())
        assert flaggee["verdict"] == "INFIDELE"
        assert propre["verdict"] == "FIDELE"
