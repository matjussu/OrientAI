"""Juge LLM en aveugle sur les 4 criteres Matteo (ordre = priorite) :
1 references  : les formations/etablissements/dispositifs cites sont-ils les BONS pour ce profil ?
2 comprehension : la reponse a-t-elle compris la question ET le profil (niveau, lieu, contrainte) ?
3 expression  : francais naturel, clair, adapte a un jeune, pas de jargon ni de contradiction
4 couverture  : la reponse repond-elle (vs refus, esquive, renvoi vers "contacte le CIO")

Chaque critere 1-5. Plus : refus (bool), erreur_factuelle (bool + detail), cause_echec pour les
notes < 3 : data_absente | retrieval | generation | format | aucune.

Usage : PYTHONPATH=. python judge.py --judge opus|gpt [--systems local,claude_norag,...] [--sample N]
"""
from __future__ import annotations

import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).parent
RUNS = HERE / "runs"

RUBRIC = """Tu es un conseiller d'orientation senior du systeme francais (Parcoursup, MonMaster, universites,
IUT, BTS, CPGE, ecoles, RNCP, insertion). Nous sommes en septembre 2026. Tu evalues en aveugle la
reponse d'un assistant a un jeune (lyceen ou etudiant). Tu ne sais pas quel systeme l'a produite.

Note chaque critere de 1 (mauvais) a 5 (excellent) :
- references : les formations, etablissements, dispositifs, chiffres cites sont-ils pertinents et
  corrects POUR CE PROFIL ? 1 = references absentes ou hors sujet ou fausses ; 3 = correctes mais
  generiques ou incompletes (il manque l'evidence : ex. pas de Licence Informatique pour un lyceen
  qui la demande dans une ville qui en a une) ; 5 = les bonnes references, precises, avec chiffres utiles.
  Une reponse qui ne cite aucune reference concrete ne peut pas depasser 2.
- comprehension : la reponse tient-elle compte du niveau, du lieu, des contraintes, de l'implicite ?
  Si le profil est trop vague, poser UNE bonne question de clarification vaut 4-5.
- expression : francais naturel, tutoiement coherent, structure lisible, pas de contradiction
  interne, pas de jargon technique ("source S3", JSON, balises). Longueur adaptee.
- couverture : 5 = repond pleinement ; 3 = repond partiellement puis renvoie ailleurs ;
  1 = refuse ou dit "je n'ai pas cette information" alors que la question est standard.

Puis :
- refus : true si la reponse esquive l'essentiel de la question.
- erreur_factuelle : true si tu es SUR qu'un fait cite est faux (formation inexistante, chiffre
  invraisemblable, procedure fausse). Donne le detail. Dans le doute, false.
- cause_echec : si references < 3 ou couverture < 3, ta meilleure hypothese :
  "data_absente" (l'info ne semble pas exister dans une base de fiches), "retrieval" (l'info existe
  surement dans une base Parcoursup/MonMaster mais n'a pas ete trouvee), "generation" (l'info etait
  la ou est de culture generale, mais la redaction l'a mal exploitee), "format" (probleme de forme
  seulement). Sinon "aucune".
- commentaire : 1-2 phrases, la chose la plus importante a corriger.

Reponds UNIQUEMENT en JSON : {"references":n,"comprehension":n,"expression":n,"couverture":n,
"refus":bool,"erreur_factuelle":bool,"erreur_detail":"...","cause_echec":"...","commentaire":"..."}"""


def build_prompt(rec: dict) -> str:
    hist = ""
    if rec["history"]:
        hist = "\n\nHISTORIQUE DE LA CONVERSATION (tours precedents) :\n" + "\n".join(
            f"[{m['role']}] {m['content'][:1200]}" for m in rec["history"])
    ctx = ""
    srcs = rec.get("sources") or []
    if srcs and isinstance(srcs[0], dict):
        ctx = "\n\nFICHES QUE L'ASSISTANT AVAIT SOUS LES YEUX (titres) :\n" + "\n".join(
            f"- {s.get('titre')} | {s.get('etablissement')} | {s.get('ville')} | {s.get('source')}"
            for s in srcs[:12])
    return (f"PROFIL : {rec['persona']} ; tags : {', '.join(rec['tags'])}{hist}\n\n"
            f"QUESTION DU JEUNE :\n{rec['question']}\n\nREPONSE DE L'ASSISTANT :\n{rec['answer'] or '(vide / erreur)'}"
            f"{ctx}")


class OpusJudge:
    name = "opus"

    def __init__(self):
        import anthropic
        self.c = anthropic.Anthropic()

    def __call__(self, prompt: str) -> dict:
        r = self.c.messages.create(
            model="claude-opus-5", max_tokens=1200, system=RUBRIC,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "adaptive"}, output_config={"effort": "medium"},
        )
        txt = "".join(b.text for b in r.content if b.type == "text")
        return _parse(txt) | {"_usage": {"in": r.usage.input_tokens, "out": r.usage.output_tokens}}


class GPTJudge:
    name = "gpt"

    def __init__(self):
        from openai import OpenAI
        self.c = OpenAI()

    def __call__(self, prompt: str) -> dict:
        r = self.c.chat.completions.create(
            model="gpt-5.5", messages=[{"role": "system", "content": RUBRIC},
                                       {"role": "user", "content": prompt}],
            response_format={"type": "json_object"})
        return _parse(r.choices[0].message.content) | {
            "_usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}}


def _parse(txt: str) -> dict:
    txt = txt.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.startswith("json"):
            txt = txt[4:]
    s, e = txt.find("{"), txt.rfind("}")
    try:
        return json.loads(txt[s:e + 1])
    except Exception:
        return {"_raw": txt, "_parse_error": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", choices=["opus", "gpt"], default="opus")
    ap.add_argument("--systems", default="local,claude_norag,gpt_norag,claude_ctx")
    ap.add_argument("--sample", type=int, default=0, help="N tours tires au sort (seed 7) par systeme")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    judge = OpusJudge() if a.judge == "opus" else GPTJudge()

    jobs = []
    for sysname in a.systems.split(","):
        p = RUNS / f"{sysname}.jsonl"
        if not p.exists():
            print("absent :", p); continue
        recs = [json.loads(l) for l in open(p)]
        if a.sample:
            random.Random(7).shuffle(recs); recs = recs[: a.sample]
        out = RUNS / f"judge_{a.judge}_{sysname}.jsonl"
        done = set()
        if out.exists():
            done = {(json.loads(l)["id"], json.loads(l)["turn"]) for l in open(out)}
        for r in recs:
            if (r["id"], r["turn"]) not in done:
                jobs.append((sysname, out, r))
    print(f"[judge {a.judge}] {len(jobs)} evaluations", flush=True)

    tin = tout = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(judge, build_prompt(r)): (s, o, r) for s, o, r in jobs}
        for f in as_completed(futs):
            s, o, r = futs[f]
            try:
                res = f.result()
            except Exception as e:
                res = {"_error": f"{type(e).__name__}: {e}"}
            u = res.pop("_usage", {}); tin += u.get("in", 0); tout += u.get("out", 0)
            with open(o, "a") as fh:
                fh.write(json.dumps({"id": r["id"], "turn": r["turn"], "system": s, **res},
                                    ensure_ascii=False) + "\n")
            print(f"  {s} {r['id']}.{r['turn']} -> {res.get('references')}/{res.get('comprehension')}/"
                  f"{res.get('expression')}/{res.get('couverture')} {res.get('cause_echec','')}", flush=True)
    price = (5, 25) if a.judge == "opus" else (2.5, 15)
    print(f"cout juge ~{(tin*price[0]+tout*price[1])/1e6:.2f} USD, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
