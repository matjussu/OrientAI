"""Juge LLM en aveugle sur les 4 criteres de Matteo, par ordre de priorite :

1 references     les formations, etablissements, dispositifs cites sont-ils les BONS pour ce profil ?
2 comprehension  la reponse a-t-elle compris la question ET le profil (niveau, lieu, contrainte) ?
3 expression     francais naturel, clair, adapte a un jeune, sans jargon ni contradiction
4 couverture     la reponse repond-elle (vs refus, esquive, « contacte le CIO »)

Chaque critere de 1 a 5, plus `refus`, `erreur_factuelle` (+ detail) et `cause_echec`.
Le juge est un outil interne : Opus est autorise ici, la contrainte « pas de modele americain
proprietaire » porte sur le produit (ordre 2026-09-23-0817). Sortie :
`<run_dir>/judge_<juge>_<systeme>.jsonl`, reprise sur les tours deja juges. Chaque verdict porte
l'empreinte de la reponse jugee : un tour rejoue (apres une panne) est rejuge, et son ancien
verdict est ignore.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.eval.battery.config import MODELS, price_usd
from src.eval.battery.runner import read_jsonl

CRITERIA = ["references", "comprehension", "expression", "couverture"]

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


def answer_sha(rec: dict) -> str:
    return hashlib.sha256((rec.get("answer") or "").encode()).hexdigest()[:12]


def build_prompt(rec: dict) -> str:
    history = ""
    if rec["history"]:
        history = "\n\nHISTORIQUE DE LA CONVERSATION (tours precedents) :\n" + "\n".join(
            f"[{m['role']}] {m['content'][:1200]}" for m in rec["history"])
    context = ""
    sources = [s for s in rec.get("sources") or [] if isinstance(s, dict)]
    if sources:
        context = "\n\nFICHES QUE L'ASSISTANT AVAIT SOUS LES YEUX (titres) :\n" + "\n".join(
            f"- {s.get('titre')} | {s.get('etablissement')} | {s.get('ville')} | {s.get('source')}"
            for s in sources[:12])
    return (f"PROFIL : {rec['persona']} ; tags : {', '.join(rec['tags'])}{history}\n\n"
            f"QUESTION DU JEUNE :\n{rec['question']}\n\n"
            f"REPONSE DE L'ASSISTANT :\n{rec['answer'] or '(vide / erreur)'}{context}")


def parse_verdict(text: str) -> dict:
    """JSON du juge, tolerant aux blocs ```json. Un verdict illisible est marque, jamais invente."""
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    try:
        verdict = json.loads(text[start:end + 1])
    except ValueError:
        return {"_raw": text, "_parse_error": True}
    if not all(isinstance(verdict.get(c), (int, float)) for c in CRITERIA):
        return {**verdict, "_parse_error": True}
    return verdict


class OpusJudge:
    name = "opus"

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = MODELS["claude_opus"]

    def __call__(self, prompt: str) -> tuple[dict, dict]:
        r = self.client.messages.create(
            model=self.model, max_tokens=1200, system=RUBRIC,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "adaptive"}, output_config={"effort": "medium"},
        )
        text = "".join(b.text for b in r.content if b.type == "text")
        return parse_verdict(text), {"in": r.usage.input_tokens, "out": r.usage.output_tokens}


class GPTJudge:
    """Contre-juge. Credits OpenAI a zero au 23/09 : plomberie gardee, non bloquant."""

    name = "gpt"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI()
        self.model = MODELS["gpt"]

    def __call__(self, prompt: str) -> tuple[dict, dict]:
        r = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "system", "content": RUBRIC},
                                        {"role": "user", "content": prompt}],
            response_format={"type": "json_object"})
        return parse_verdict(r.choices[0].message.content), {
            "in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}


JUDGES = {"opus": OpusJudge, "gpt": GPTJudge}


def judge_run(run_dir: Path, systems: list[str], judge_name: str = "opus", sample: int = 0,
              workers: int = 4, log=print) -> dict:
    judge = JUDGES[judge_name]()
    jobs = []
    for system in systems:
        records = read_jsonl(run_dir / f"{system}.jsonl")
        if not records:
            log(f"  absent : {system}.jsonl")
            continue
        if sample:
            random.Random(7).shuffle(records)
            records = records[:sample]
        out = run_dir / f"judge_{judge_name}_{system}.jsonl"
        done = {(v["id"], v["turn"], v.get("answer_sha")) for v in read_jsonl(out)
                if not v.get("_parse_error") and not v.get("_error")}
        jobs += [(system, out, r) for r in records if not r.get("error")
                 and (r["id"], r["turn"], answer_sha(r)) not in done]
    skipped = sum(bool(r.get("error")) for s in systems for r in read_jsonl(run_dir / f"{s}.jsonl"))
    if skipped:
        log(f"  {skipped} tours en erreur non juges : rejouer le run d'abord")
    log(f"[juge {judge_name}] {len(jobs)} evaluations")

    tokens_in = tokens_out = failures = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(judge, build_prompt(r)): (s, o, r) for s, o, r in jobs}
        for fut in as_completed(futures):
            system, out, rec = futures[fut]
            try:
                verdict, usage = fut.result()
            except Exception as e:  # noqa: BLE001 - garde la trace, le tour sera rejuge au prochain passage
                verdict, usage = {"_error": f"{type(e).__name__}: {e}"}, {}
            tokens_in += usage.get("in", 0)
            tokens_out += usage.get("out", 0)
            failures += bool(verdict.get("_error") or verdict.get("_parse_error"))
            with open(out, "a") as fh:
                fh.write(json.dumps({"id": rec["id"], "turn": rec["turn"], "system": system,
                                     "answer_sha": answer_sha(rec), **verdict}, ensure_ascii=False) + "\n")
            log(f"  {system} {rec['id']}.{rec['turn']} -> "
                + "/".join(str(verdict.get(c)) for c in CRITERIA))
    cost = price_usd(judge.model, tokens_in, tokens_out)
    return {"judge": judge_name, "model": judge.model, "judged": len(jobs), "failures": failures,
            "tokens_in": tokens_in, "tokens_out": tokens_out,
            "cost_usd": None if cost is None else round(cost, 3), "seconds": round(time.time() - t0)}


def load_verdicts(run_dir: Path, judge_name: str, system: str) -> dict[tuple[str, int], dict]:
    """Verdicts valides de la reponse ACTUELLE de chaque tour. Les verdicts sans empreinte
    (runs du 05/09) sont acceptes tels quels : ces runs n'ont jamais ete rejoues."""
    current = {(r["id"], r["turn"]): answer_sha(r)
               for r in read_jsonl(Path(run_dir) / f"{system}.jsonl")}
    out = {}
    for v in read_jsonl(Path(run_dir) / f"judge_{judge_name}_{system}.jsonl"):
        if not all(isinstance(v.get(c), (int, float)) for c in CRITERIA):
            continue
        key = (v["id"], v["turn"])
        if "answer_sha" in v and v["answer_sha"] != current.get(key):
            continue
        out[key] = v
    return out
