"""SPIKE (jetable) : conseiller a outils sur le corpus OrientIA, pour mesurer la voie "agent".

Le modele dispose de 2 outils sur data/processed/formations.json :
  search_formations(query, ville, region, source, type_formation, k)  -> BM25 lexical + filtres exacts
  get_fiche(idx)                                                    -> fiche complete (JSON epure)
Aucun embedding, aucun reranker : on mesure ce que donne un lookup structure honnete + un bon modele.

Systemes : agent_sonnet (claude-sonnet-5), agent_mistral (mistral-medium-2604, function calling).
Sortie : runs/{system}.jsonl au meme format que run_battery.py (jugeable par judge.py).
Usage : PYTHONPATH=. python spike_agent.py agent_sonnet [--only L03,L13] [--workers 3]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).parent
BATTERY = json.load(open(HERE / "battery.json"))["items"]

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


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", s)  # lyon1 -> lyon 1
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


DROP = {"provenance", "collected_at", "merge_confidence", "retrieval_eligible", "url_type", "match_method",
        "cross_refs", "id_mon_master", "cod_aff_form", "cod_uai", "phase", "labels", "trends"}


def clean(f: dict) -> dict:
    def rec(o):
        if isinstance(o, dict):
            return {k: rec(v) for k, v in o.items() if k not in DROP and v not in (None, "", [], {})}
        if isinstance(o, list):
            return [rec(x) for x in o[:12]]
        return o
    return rec(f)


class Corpus:
    def __init__(self):
        from rank_bm25 import BM25Okapi
        self.f = json.load(open("data/processed/formations.json"))
        docs = []
        for x in self.f:
            parts = [x.get("nom"), x.get("etablissement"), x.get("ville"), x.get("fili_code"), x.get("type_diplome"),
                     x.get("domaine"), x.get("mention"), x.get("parcours"), x.get("discipline"), x.get("detail"),
                     (x.get("text") or "")[:300]]
            docs.append(norm(" ".join(p for p in parts if isinstance(p, str))).split())
        self.bm25 = BM25Okapi(docs)
        self.nville = [norm(x.get("ville") or "") for x in self.f]
        self.nregion = [norm(x.get("region") or "") for x in self.f]

    def search(self, query, ville=None, region=None, source=None, type_formation=None, k=10):
        import numpy as np
        k = min(int(k or 10), 25)
        scores = self.bm25.get_scores(norm(query).split())
        nv, nr, nt = norm(ville or ""), norm(region or ""), norm(type_formation or "")
        mask = np.ones(len(self.f), dtype=bool)
        if nv:
            mask &= np.array([nv in v for v in self.nville])
        if nr:
            mask &= np.array([nr in r for r in self.nregion])
        if source:
            mask &= np.array([x.get("source") == source for x in self.f])
        if nt:
            mask &= np.array([nt in norm(x.get("fili_code") or "") or nt in norm(x.get("nom") or "") for x in self.f])
        scores = np.where(mask, scores, -1.0)
        order = np.argsort(-scores)[:k]
        out = []
        for i in order:
            if scores[i] <= 0:
                break
            x = self.f[i]
            out.append({"idx": int(i), "nom": x.get("nom"), "etablissement": x.get("etablissement"),
                        "ville": x.get("ville"), "source": x.get("source"),
                        "type": x.get("fili_code") or x.get("type_diplome"),
                        "taux_acces_2025": x.get("taux_acces_parcoursup_2025"), "places": x.get("nombre_places"),
                        "taux_admission_master": x.get("taux_admission")})
        return out if out else {"resultats": [], "conseil": "aucun resultat : elargis (retire un filtre, mots plus simples)"}

    def fiche(self, idx):
        try:
            return clean(self.f[int(idx)])
        except Exception:
            return {"erreur": "idx inconnu"}


CORPUS: Corpus | None = None


def run_tool(name, args):
    if name == "search_formations":
        return CORPUS.search(**{k: v for k, v in args.items() if k in
                                {"query", "ville", "region", "source", "type_formation", "k"}})
    if name == "get_fiche":
        return CORPUS.fiche(args.get("idx"))
    return {"erreur": "outil inconnu"}


def dumps(o):
    s = json.dumps(o, ensure_ascii=False)
    return s[:6000] + ("...(tronque)" if len(s) > 6000 else "")


# ---------------------------------------------------------------- agents

class SonnetAgent:
    name = "agent_sonnet"
    model = "claude-sonnet-5"

    def __init__(self):
        import anthropic
        self.c = anthropic.Anthropic()

    def ask(self, question, history):
        msgs = history + [{"role": "user", "content": question}]
        calls, tin, tout, seen = [], 0, 0, []
        for _ in range(8):
            r = self.c.messages.create(model=self.model, max_tokens=2500, system=SYSTEM, tools=TOOLS,
                                       messages=msgs, thinking={"type": "adaptive"},
                                       output_config={"effort": "medium"})
            tin += r.usage.input_tokens; tout += r.usage.output_tokens
            msgs = msgs + [{"role": "assistant", "content": r.content}]
            if r.stop_reason != "tool_use":
                break
            results = []
            for b in r.content:
                if b.type == "tool_use":
                    res = run_tool(b.name, b.input)
                    calls.append({"tool": b.name, "args": b.input, "n": len(res) if isinstance(res, list) else None})
                    if b.name == "get_fiche" and isinstance(res, dict) and "nom" in res:
                        seen.append({"id": res.get("url_canonical"), "titre": res.get("nom"),
                                     "etablissement": res.get("etablissement"), "ville": res.get("ville"),
                                     "source": res.get("source")})
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": dumps(res)})
            msgs = msgs + [{"role": "user", "content": results}]
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return {"answer": text, "sources": seen, "tool_calls": calls,
                "usage": {"in": tin, "out": tout}, "model": self.model}


class MistralAgent:
    name = "agent_mistral"
    model = "mistral-medium-2604"

    def __init__(self):
        from mistralai.client import Mistral
        from src.config import load_config
        self.c = Mistral(api_key=load_config().mistral_api_key)
        self.tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                         "parameters": t["input_schema"]}} for t in TOOLS]

    def ask(self, question, history):
        msgs = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": question}]
        calls, tin, tout, seen = [], 0, 0, []
        for _ in range(8):
            r = self.c.chat.complete(model=self.model, messages=msgs, tools=self.tools, temperature=0.3)
            tin += r.usage.prompt_tokens; tout += r.usage.completion_tokens
            m = r.choices[0].message
            msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": m.tool_calls})
            if not m.tool_calls:
                break
            for tc in m.tool_calls:
                args = tc.function.arguments
                args = json.loads(args) if isinstance(args, str) else args
                res = run_tool(tc.function.name, args)
                calls.append({"tool": tc.function.name, "args": args, "n": len(res) if isinstance(res, list) else None})
                if tc.function.name == "get_fiche" and isinstance(res, dict) and "nom" in res:
                    seen.append({"id": res.get("url_canonical"), "titre": res.get("nom"),
                                 "etablissement": res.get("etablissement"), "ville": res.get("ville"),
                                 "source": res.get("source")})
                msgs.append({"role": "tool", "name": tc.function.name, "content": dumps(res), "tool_call_id": tc.id})
        text = m.content if isinstance(m.content, str) else "".join(
            getattr(p, "text", "") for p in (m.content or []))
        return {"answer": text, "sources": seen, "tool_calls": calls,
                "usage": {"in": tin, "out": tout}, "model": self.model}


PRICES = {"claude-sonnet-5": (2.0, 10.0), "mistral-medium-2604": (0.4, 2.0)}  # USD/M, mistral suppose


def run_item(agent, item):
    history, recs = [], []
    for ti, q in enumerate(item["turns"]):
        t0 = time.time()
        try:
            res = agent.ask(q, history); err = None
        except Exception as e:
            res = {"answer": "", "sources": [], "tool_calls": []}
            err = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}"
        recs.append({"id": item["id"], "turn": ti, "persona": item["persona"], "tags": item["tags"],
                     "question": q, "history": list(history), "latency_s": round(time.time() - t0, 2),
                     "error": err, **res})
        history = history + [{"role": "user", "content": q},
                             {"role": "assistant", "content": res["answer"] or "(erreur)"}]
    return recs


def main():
    global CORPUS
    ap = argparse.ArgumentParser()
    ap.add_argument("system", choices=["agent_sonnet", "agent_mistral"])
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    CORPUS = Corpus()
    agent = SonnetAgent() if a.system == "agent_sonnet" else MistralAgent()
    items = BATTERY
    if a.only:
        keep = set(a.only.split(",")); items = [i for i in items if i["id"] in keep]
    out = HERE / f"runs/{a.system}.jsonl"
    done = set()
    if out.exists() and not a.only:
        done = {json.loads(l)["id"] for l in open(out)}
    todo = [i for i in items if i["id"] not in done]
    print(f"[{a.system}] {len(todo)} conversations a jouer ({len(done)} deja faites)", flush=True)
    tin = tout = 0
    t0 = time.time()
    with open(out, "a") as fh, ThreadPoolExecutor(max_workers=a.workers) as ex:
        for fut in as_completed({ex.submit(run_item, agent, it): it for it in todo}):
            for rec in fut.result():
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n"); fh.flush()
                u = rec.get("usage") or {}; tin += u.get("in", 0); tout += u.get("out", 0)
                print(f"  {'ERR' if rec['error'] else 'ok '} {rec['id']}.{rec['turn']} {rec['latency_s']}s "
                      f"{len(rec['answer'])}c calls={len(rec.get('tool_calls') or [])} fiches={len(rec['sources'])}",
                      flush=True)
    pi, po = PRICES[agent.model]
    print(f"cout estime {agent.model}: {(tin*pi+tout*po)/1e6:.3f} USD (in={tin} out={tout}) ; {time.time()-t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
