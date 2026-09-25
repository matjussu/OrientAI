"""La prod telle que l'élève la voit : le chemin `/answer/stream` (appelé par la plateforme via `/api/ask/stream`).

Ce qui est reproduit du serveur (`src/api/server.py`) :
- chargement : `make_production_pipeline` + `load_index_from`, index de sous-corpus et BM25 chauffés, puis
  `warmup_generation`, comme dans `lifespan` ; drapeau ORIENTIA_NARRATIVE_MODE=1, seul drapeau posé sur Railway en
  plus des chemins (`railway variables`, lu le 25/09) ;
- question passée par `_sanitize_question`, puis `pipeline.answer_stream(question, history=...)` avec les arguments
  par défaut du serveur ;
- réponse = concaténation des événements `token`, ce que la plateforme accumule et affiche
  (`OrientAI_Platform/src/app/home-chat.tsx`, `case "token"`). Le chemin stream saute la policy et le post-traitement
  (`_validate_for_stream`) : on ne les rejoue pas.

Empreinte : `build_fingerprint`, la même que `/health` ; le lanceur refuse de jouer si elle diffère de la prod.
Un seul fil : la trace de la requête est lue sur `pipeline._last_trace`, posée par `answer_stream`.
"""
from __future__ import annotations

import asyncio
import os

from src.eval.battery.config import CORPUS_PATH, INDEX_PATH
from src.eval.battery.systems import _jsonable
from src.eval.multiversion.comptage import ClientCompte


class Prod:
    nom = "prod"
    fils = 1

    def __init__(self):
        os.environ["ORIENTIA_NARRATIVE_MODE"] = "1"
        from mistralai.client import Mistral

        from src.api.provenance import build_fingerprint
        from src.api.server import _MISTRAL_TIMEOUT_MS, _sanitize_question
        from src.eval.battery.corpus import Corpus
        from src.rag.embeddings import fiche_to_text
        from src.rag.factory import make_production_pipeline

        self.client = ClientCompte(Mistral(api_key=os.environ["MISTRAL_API_KEY"], timeout_ms=_MISTRAL_TIMEOUT_MS))
        self.corpus = Corpus()
        self.pipeline = make_production_pipeline(self.client, self.corpus.fiches)
        self.pipeline.load_index_from(str(INDEX_PATH))
        self._empreinte = build_fingerprint(CORPUS_PATH, INDEX_PATH)
        self.sanitize = _sanitize_question
        self.fiche_to_text = fiche_to_text
        self.modele = self._empreinte["model_gen"]
        self.modeles = [self._empreinte[k] for k in ("model_gen", "model_aux", "model_embed")]
        self.boucle = asyncio.new_event_loop()
        self.chauffe = None

    def empreinte(self) -> dict:
        return self._empreinte

    def chauffer(self) -> dict:
        """Comme `lifespan` : sous-index, BM25, pool Mistral et clarifieur récit. Coût relevé à part (hors tours)."""
        releve = self.client.nouveau_releve()
        self.pipeline._build_double_subindices()
        self.pipeline._retrieve_with_bm25("orientation", k=1)
        self.pipeline.warmup_generation()
        self.chauffe = releve.par_modele()
        return self.chauffe

    async def _jouer(self, question: str, history: list[dict] | None) -> dict:
        texte, top, evenements = [], [], {}
        async for ev in self.pipeline.answer_stream(question, history=history):
            t = ev.get("type")
            if t == "token":
                texte.append(ev.get("content") or "")
            elif t == "sources":
                top = ev.get("sources") or []
            elif t in ("structured", "faithfulness", "done", "error"):
                evenements[t] = ev
        return {"texte": "".join(texte), "top": top, "evenements": evenements}

    def _position(self, fiche: dict) -> int | None:
        try:
            return self.corpus.position_of(fiche)
        except KeyError:
            return None

    def ask(self, question: str, history: list[dict]) -> dict:
        if self.chauffe is None:
            self.chauffer()
        releve = self.client.nouveau_releve()
        question = self.sanitize(question)
        # Plateforme : les 6 derniers messages, absents au premier tour (home-chat.tsx, historyPayload.slice(-6)).
        out = self.boucle.run_until_complete(self._jouer(question, history[-6:] or None))
        if "error" in out["evenements"]:
            raise RuntimeError(f"evenement error du stream : {out['evenements']['error']}")
        trace = self.pipeline._last_trace
        fiches = [t.get("fiche", t) for t in out["top"]]
        routeur = _jsonable(getattr(trace, "router_result", None))
        return {
            "reponse": out["texte"],
            "sources": [{"titre": f.get("nom"), "etablissement": f.get("etablissement"), "ville": f.get("ville"),
                         "source": f.get("source"), "score": t.get("score"), "texte": self.fiche_to_text(f)}
                        for t, f in zip(out["top"], fiches)],
            "source_positions": [self._position(f) for f in fiches],
            "usage": releve.par_modele(),
            "appels": [vars(a) for a in releve.appels],
            "trace": {
                "router": routeur,
                "scope": _jsonable(getattr(trace, "scope_result", None)),
                "select_fallthrough": getattr(trace, "select_fallthrough", None),
                "geo_refusal": getattr(trace, "geo_refusal", None),
                "validation": _jsonable(getattr(trace, "validation", None)),
                "format_decision": _jsonable(getattr(trace, "narrative_format_decision", None)),
                "structured": _jsonable(out["evenements"].get("structured", {}).get("structured")),
                "faithfulness": out["evenements"].get("faithfulness"),
                "latence_pipeline_ms": (out["evenements"].get("done") or {}).get("latency_ms"),
            },
            "modele": self.modele,
        }


VERSION = Prod
