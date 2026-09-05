"""Batterie Jarvis 2026-09-05 : joue battery.json sur un systeme et ecrit un JSONL.

Systemes :
  local       pipeline OrientIA en conditions de serving (mode recit, temp 0.3, history <= 6)
  claude_norag  claude-sonnet-5 sans contexte (plafond culture generale)
  gpt_norag     gpt-5.5 sans contexte
  claude_ctx    claude-sonnet-5 avec les MEMES fiches que `local` a servies (lit local.jsonl)

Usage : PYTHONPATH=. python results/jarvis_analyse_2026-09-05/run_battery.py <system> [--limit N] [--workers W]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).parent
BATTERY = json.load(open(HERE / "battery.json"))["items"]

SYSTEM_PROMPT_BASELINE = (
    "Tu es un conseiller d'orientation expert du systeme educatif francais. Nous sommes en "
    "septembre 2026. Tu conseilles des lyceens (Parcoursup) et des etudiants du superieur "
    "(licence, master, prepa, BUT, BTS, reorientation). Reponds en francais, de facon concrete "
    "et personnalisee : nomme des formations et etablissements precis quand c'est pertinent, "
    "donne des chiffres (taux d'acces, insertion, cout) quand tu en es sur, et dis clairement "
    "quand tu n'es pas sur ou que l'information a pu changer. Pose au plus une question de "
    "clarification si le profil est trop vague. Reste concis (250 a 450 mots)."
)

SYSTEM_PROMPT_CTX = SYSTEM_PROMPT_BASELINE + (
    "\n\nTu disposes ci-dessous de FICHES issues d'une base de donnees officielle (Parcoursup, "
    "MonMaster, ONISEP, RNCP, InserJeunes...). Appuie-toi d'abord sur ces fiches pour les "
    "references et les chiffres, et signale explicitement ce qui vient de ta connaissance "
    "generale et non des fiches. Si les fiches ne repondent pas a la question, dis-le et "
    "reponds quand meme au mieux avec ta connaissance generale."
)

PRICES = {  # USD par 1M tokens (in, out) - pour le suivi budget
    "claude-sonnet-5": (2.0, 10.0),
    "gpt-5.5": (2.5, 15.0),  # suppose, a verifier sur la facture
}


def out_path(system: str) -> Path:
    return HERE / f"runs/{system}.jsonl"


# ---------------------------------------------------------------- systemes

class LocalSystem:
    name = "local"

    def __init__(self):
        os.environ.setdefault("ORIENTIA_NARRATIVE_MODE", "1")
        from mistralai.client import Mistral
        from src.config import load_config
        from src.rag.factory import make_production_pipeline
        c = load_config()
        client = Mistral(api_key=c.mistral_api_key)
        fiches = json.load(open("data/processed/formations.json"))
        self.p = make_production_pipeline(client, fiches)
        self.p.load_index_from("data/embeddings/formations.index")
        from src.rag.embeddings import fiche_to_text
        self.fiche_to_text = fiche_to_text

    def ask(self, question: str, history: list[dict]) -> dict:
        text, top, trace = self.p.answer(question, history=history[-6:] or None, return_trace=True)
        # top = [{"fiche": {...}, "score": ...}, ...] (cf cards_from_top_sources, citation_check.py:195)
        fiches = [t.get("fiche", t) if isinstance(t, dict) else t for t in top]
        return {
            "answer": text,
            "sources": [
                {
                    "id": f.get("url_canonical") or f.get("uai"),
                    "titre": f.get("nom"),
                    "etablissement": f.get("etablissement"),
                    "ville": f.get("ville"),
                    "source": f.get("source"),
                    "score": (t.get("score") if isinstance(t, dict) else None),
                    "text": self.fiche_to_text(f),
                }
                for t, f in zip(top, fiches)
            ],
            "trace": {
                "scope": _s(trace.scope_result),
                "router": _s(trace.router_result),
                "select": _s(trace.select_result),
                "select_fallthrough": trace.select_fallthrough,
                "geo_refusal": trace.geo_refusal,
                "validation": _s(trace.validation),
                "policy": _s(trace.policy_result),
                "format_decision": _s(trace.narrative_format_decision),
                "retry": trace.retry_metadata,
                "filter_stats": trace.filter_stats,
            },
        }


def _s(obj):
    if obj is None:
        return None
    try:
        return json.loads(json.dumps(obj, default=lambda o: getattr(o, "__dict__", str(o))))
    except Exception:
        return str(obj)


class ClaudeSystem:
    def __init__(self, name: str, with_ctx: bool):
        import anthropic
        self.name = name
        self.with_ctx = with_ctx
        self.client = anthropic.Anthropic()
        self.model = "claude-sonnet-5"
        self.local = _load_local() if with_ctx else {}

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        system = SYSTEM_PROMPT_BASELINE
        ctx_ids = []
        if self.with_ctx:
            src = self.local.get(key, {}).get("sources", [])
            ctx_ids = [s["id"] for s in src]
            if src:
                system = SYSTEM_PROMPT_CTX + "\n\n<fiches>\n" + "\n\n---\n\n".join(
                    f"[fiche {i+1} | source={s['source']}]\n{s['text']}" for i, s in enumerate(src)
                ) + "\n</fiches>"
            else:
                system = SYSTEM_PROMPT_CTX + "\n\n<fiches>(aucune fiche servie sur ce tour)</fiches>"
        msgs = history + [{"role": "user", "content": question}]
        r = self.client.messages.create(
            model=self.model, max_tokens=2000, system=system, messages=msgs,
            thinking={"type": "adaptive"}, output_config={"effort": "medium"},
        )
        text = "".join(b.text for b in r.content if b.type == "text")
        u = r.usage
        return {"answer": text, "sources": ctx_ids,
                "usage": {"in": u.input_tokens, "out": u.output_tokens}, "model": self.model}


class GPTSystem:
    name = "gpt_norag"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = "gpt-5.5"

    def ask(self, question: str, history: list[dict], key=None) -> dict:
        msgs = [{"role": "system", "content": SYSTEM_PROMPT_BASELINE}] + history + [
            {"role": "user", "content": question}]
        r = self.client.chat.completions.create(model=self.model, messages=msgs)
        u = r.usage
        return {"answer": r.choices[0].message.content, "sources": [],
                "usage": {"in": u.prompt_tokens, "out": u.completion_tokens}, "model": self.model}


def _load_local() -> dict:
    d = {}
    for line in open(out_path("local")):
        rec = json.loads(line)
        d[(rec["id"], rec["turn"])] = rec
    return d


# ---------------------------------------------------------------- runner

def run_item(system, item: dict) -> list[dict]:
    history: list[dict] = []
    recs = []
    for ti, q in enumerate(item["turns"]):
        t0 = time.time()
        try:
            if isinstance(system, LocalSystem):
                res = system.ask(q, history)
            else:
                res = system.ask(q, history, key=(item["id"], ti))
            err = None
        except Exception as e:  # on garde la trace, on continue la batterie
            res = {"answer": "", "sources": []}
            err = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}"
        rec = {
            "id": item["id"], "turn": ti, "persona": item["persona"], "tags": item["tags"],
            "question": q, "history": list(history), "latency_s": round(time.time() - t0, 2),
            "error": err, **res,
        }
        recs.append(rec)
        history = history + [{"role": "user", "content": q},
                             {"role": "assistant", "content": res["answer"] or "(erreur)"}]
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("system", choices=["local", "claude_norag", "gpt_norag", "claude_ctx"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", default="", help="ids separes par des virgules")
    a = ap.parse_args()

    if a.system == "local":
        system = LocalSystem()
    elif a.system == "claude_norag":
        system = ClaudeSystem("claude_norag", with_ctx=False)
    elif a.system == "claude_ctx":
        system = ClaudeSystem("claude_ctx", with_ctx=True)
    else:
        system = GPTSystem()

    items = BATTERY
    if a.only:
        keep = set(a.only.split(","))
        items = [i for i in items if i["id"] in keep]
    if a.limit:
        items = items[: a.limit]

    out = out_path(a.system)
    out.parent.mkdir(exist_ok=True)
    done = set()
    if out.exists() and not a.only:
        for line in open(out):
            done.add(json.loads(line)["id"])
    todo = [i for i in items if i["id"] not in done]
    print(f"[{a.system}] {len(todo)} conversations a jouer ({len(done)} deja faites)", flush=True)

    t0 = time.time()
    tot_in = tot_out = 0
    with open(out, "a") as fh, ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_item, system, it): it for it in todo}
        for fut in as_completed(futs):
            for rec in fut.result():
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                u = rec.get("usage") or {}
                tot_in += u.get("in", 0); tot_out += u.get("out", 0)
                flag = "ERR" if rec["error"] else "ok "
                print(f"  {flag} {rec['id']}.{rec['turn']} {rec['latency_s']}s "
                      f"{len(rec['answer'])}c src={len(rec['sources'])}", flush=True)
    model = getattr(system, "model", None)
    if model in PRICES:
        pi, po = PRICES[model]
        print(f"cout estime {model}: {(tot_in*pi + tot_out*po)/1e6:.3f} USD "
              f"(in={tot_in} out={tot_out})")
    print(f"termine en {time.time()-t0:.0f}s -> {out}")


if __name__ == "__main__":
    sys.exit(main())
