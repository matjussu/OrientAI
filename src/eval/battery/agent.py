"""Conseiller a outils sur le corpus : un lookup structure honnete + un bon modele.

Issu du spike du 05/09 (results/jarvis_analyse_2026-09-05/spike_agent.py). Deux outils sur
formations.json, sans embedding ni reranker :
  search_formations(query, ville, region, source, type_formation, k)  BM25 + filtres exacts
  get_fiche(idx)                                                     fiche complete epuree
`idx` est la position corpus (cle stable, cf corpus.py). Les fiches listees par une recherche et
les fiches lues sont toutes deux exposees au modele : leurs positions sont enregistrees.
"""
from __future__ import annotations

import json

import numpy as np

from src.eval.battery.config import MODELS
from src.eval.battery.corpus import norm

MAX_STEPS = 8
TOOL_RESULT_CHARS = 6000

SYSTEM = """Tu es un conseiller d'orientation expert du systeme educatif francais. Nous sommes en septembre 2026.
Tu conseilles des lyceens (Parcoursup) et des etudiants du superieur. Tu tutoies. Francais naturel, concret, 250 a 450 mots.

Tu as acces a une base officielle (Parcoursup 2025 avec taux d'acces, places, profil des admis par type de bac ;
MonMaster ; ONISEP ; RNCP ; InserSup insertion et salaires ; ROME metiers) via deux outils.
REGLE : avant de citer une formation ou un chiffre precis, cherche-la avec search_formations (plusieurs
recherches si besoin : varie les mots, la ville, le type) puis lis la fiche avec get_fiche. Cite ensuite le nom
exact, l'etablissement, la ville et les chiffres utiles (taux d'acces, places, part de bacs techno/pro admis,
insertion). Si la base ne contient pas ce qu'il faut, dis-le en une phrase et reponds quand meme avec ta
connaissance generale, en la signalant comme telle. Ne refuse jamais une question standard d'orientation.
Tiens compte du profil (niveau, bac, ville, contraintes, ce que la personne veut EVITER) et de l'historique.
Si le profil est trop vague pour conseiller, pose UNE question de clarification precise, sinon reponds.
Pas d'emoji, pas de balise technique, pas de "[source S1]" ; les fiches s'appellent par leur nom."""

TOOLS = [
    {
        "name": "search_formations",
        "description": "Recherche lexicale dans la base de formations et metiers. Renvoie jusqu'a k resultats compacts "
                       "(idx, nom, etablissement, ville, source, type, taux d'acces, places). Filtres exacts optionnels. "
                       "Astuce : mots-cles simples (ex: 'licence informatique', 'BTS MCO', 'master data science'), "
                       "puis affiner par ville ou region.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "mots-cles (nom de formation, discipline, metier)"},
                "ville": {"type": "string", "description": "ville exacte (ex: Toulouse, Lyon, Bordeaux)"},
                "region": {"type": "string", "description": "region (ex: Occitanie, Bretagne, Ile-de-France)"},
                "source": {"type": "string", "description": "parcoursup | monmaster | onisep | rncp | insersup_mesr | rome_api_v4 | inserjeunes_lycee_pro | labonnealternance"},
                "type_formation": {"type": "string", "description": "pour Parcoursup : BTS | BUT | Licence | Licence_Las | PASS | CPGE | Ecole d'Ingenieur | Ecole de Commerce | IFSI | EFTS"},
                "k": {"type": "integer", "description": "nombre de resultats, defaut 10, max 25"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_fiche",
        "description": "Lit la fiche complete d'une formation (JSON epure) a partir de son idx renvoye par search_formations.",
        "input_schema": {"type": "object", "properties": {"idx": {"type": "integer"}}, "required": ["idx"]},
    },
]

# Champs techniques retires de la fiche montree au modele (bruit, pas d'information utile).
_DROPPED_FIELDS = {"provenance", "collected_at", "merge_confidence", "retrieval_eligible", "url_type",
                   "match_method", "cross_refs", "id_mon_master", "cod_aff_form", "cod_uai", "phase",
                   "labels", "trends"}


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if k not in _DROPPED_FIELDS and v not in (None, "", [], {})}
    if isinstance(o, list):
        return [_clean(x) for x in o[:12]]
    return o


def _truncate(o) -> str:
    s = json.dumps(o, ensure_ascii=False)
    return s[:TOOL_RESULT_CHARS] + ("...(tronque)" if len(s) > TOOL_RESULT_CHARS else "")


class CorpusTools:
    """Les deux outils, et la trace des positions exposees pendant un tour."""

    def __init__(self, corpus):
        self.corpus = corpus
        f = corpus.fiches
        self._ville = np.array([norm(x.get("ville")) for x in f])
        self._region = np.array([norm(x.get("region")) for x in f])
        self._source = np.array([x.get("source") or "" for x in f])
        self._type = np.array([norm(x.get("fili_code")) + " | " + norm(x.get("nom")) for x in f])

    def _mask(self, ville, region, source, type_formation):
        mask = np.ones(len(self.corpus), dtype=bool)
        for wanted, column in ((norm(ville), self._ville), (norm(region), self._region),
                               (norm(type_formation), self._type)):
            if wanted:
                mask &= np.char.find(column, wanted) >= 0
        if source:
            mask &= self._source == source
        return mask

    def search(self, query, ville=None, region=None, source=None, type_formation=None, k=10):
        k = min(int(k or 10), 25)
        positions = self.corpus.search(query, k=k, mask=self._mask(ville, region, source, type_formation))
        rows = []
        for i in positions:
            x = self.corpus.fiches[i]
            rows.append({"idx": i, "nom": x.get("nom"), "etablissement": x.get("etablissement"),
                         "ville": x.get("ville"), "source": x.get("source"),
                         "type": x.get("fili_code") or x.get("type_diplome"),
                         "taux_acces_2025": x.get("taux_acces_parcoursup_2025"),
                         "places": x.get("nombre_places"), "taux_admission_master": x.get("taux_admission")})
        if not rows:
            return {"resultats": [], "conseil": "aucun resultat : elargis (retire un filtre, mots plus simples)"}, []
        return rows, positions

    def fiche(self, idx):
        try:
            i = int(idx)
            if not 0 <= i < len(self.corpus):
                raise IndexError
        except (TypeError, ValueError, IndexError):
            return {"erreur": "idx inconnu"}, []
        return _clean(self.corpus.fiches[i]), [i]

    def run(self, name: str, args: dict):
        """Rend (resultat JSON pour le modele, positions exposees)."""
        if name == "search_formations":
            allowed = {"query", "ville", "region", "source", "type_formation", "k"}
            return self.search(**{k: v for k, v in args.items() if k in allowed})
        if name == "get_fiche":
            return self.fiche(args.get("idx"))
        return {"erreur": "outil inconnu"}, []


class _Turn:
    """Accumulateur d'un tour : appels d'outils, fiches lues, positions exposees, tokens."""

    def __init__(self, corpus):
        self.corpus = corpus
        self.calls: list[dict] = []
        self.read: list[dict] = []
        self.positions: list[int] = []
        self.tokens_in = self.tokens_out = 0

    def record(self, tools: CorpusTools, name: str, args: dict) -> str:
        result, positions = tools.run(name, args)
        self.calls.append({"tool": name, "args": args, "n": len(result) if isinstance(result, list) else None})
        self.positions += [p for p in positions if p not in self.positions]
        if name == "get_fiche" and positions:
            f = self.corpus.fiches[positions[0]]
            self.read.append({"titre": f.get("nom"), "etablissement": f.get("etablissement"),
                              "ville": f.get("ville"), "source": f.get("source")})
        return _truncate(result)

    def result(self, answer: str, model: str) -> dict:
        return {"answer": answer, "sources": self.read, "source_positions": self.positions,
                "tool_calls": self.calls, "usage": {"in": self.tokens_in, "out": self.tokens_out},
                "model": model}


class SonnetAgent:
    name = "agent_sonnet"

    def __init__(self, corpus):
        import anthropic
        self.client = anthropic.Anthropic()
        self.corpus = corpus
        self.tools = CorpusTools(corpus)
        self.model = MODELS["claude_sonnet"]

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        turn = _Turn(self.corpus)
        msgs = history + [{"role": "user", "content": question}]
        for _ in range(MAX_STEPS):
            r = self.client.messages.create(model=self.model, max_tokens=2500, system=SYSTEM, tools=TOOLS,
                                            messages=msgs, thinking={"type": "adaptive"},
                                            output_config={"effort": "medium"})
            turn.tokens_in += r.usage.input_tokens
            turn.tokens_out += r.usage.output_tokens
            msgs = msgs + [{"role": "assistant", "content": r.content}]
            if r.stop_reason != "tool_use":
                break
            msgs = msgs + [{"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b.id, "content": turn.record(self.tools, b.name, b.input)}
                for b in r.content if b.type == "tool_use"]}]
        return turn.result("".join(b.text for b in r.content if getattr(b, "type", "") == "text"), self.model)


class MistralAgent:
    name = "agent_mistral"

    def __init__(self, corpus, model: str | None = None):
        from src.eval.battery.systems import MISTRAL_TIMEOUT_MS, _mistral_client
        self.client = _mistral_client(MISTRAL_TIMEOUT_MS)
        self.corpus = corpus
        self.tools = CorpusTools(corpus)
        self.model = model or MODELS["mistral_medium"]
        self.tool_specs = [{"type": "function", "function": {
            "name": t["name"], "description": t["description"], "parameters": t["input_schema"]}} for t in TOOLS]

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        turn = _Turn(self.corpus)
        msgs = [{"role": "system", "content": SYSTEM}, *history, {"role": "user", "content": question}]
        for _ in range(MAX_STEPS):
            r = self.client.chat.complete(model=self.model, messages=msgs, tools=self.tool_specs, temperature=0.3)
            turn.tokens_in += r.usage.prompt_tokens
            turn.tokens_out += r.usage.completion_tokens
            m = r.choices[0].message
            msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": m.tool_calls})
            if not m.tool_calls:
                break
            for tc in m.tool_calls:
                args = tc.function.arguments
                args = json.loads(args) if isinstance(args, str) else args
                msgs.append({"role": "tool", "name": tc.function.name, "tool_call_id": tc.id,
                             "content": turn.record(self.tools, tc.function.name, args)})
        answer = m.content if isinstance(m.content, str) else "".join(
            getattr(p, "text", "") for p in (m.content or []))
        return turn.result(answer, self.model)
