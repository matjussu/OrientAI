"""Juge de groundedness (faithfulness) - Claude juge, Mistral genere.

Principe (L4 "construire une IA avec une IA") : un LLM d'une AUTRE famille que
le generateur (Claude Sonnet vs Mistral Medium) juge, phrase/claim par claim,
si chaque affirmation factuelle de la reponse est SUPPORTEE par les sources
reellement fournies au generateur. Evite l'auto-jugement (le honesty_score
interne du pipeline etait justement faussement confiant).

Classe aussi l'OUTCOME de chaque reponse pour distinguer :
- answered_grounded         : repond + tout sourcé
- answered_unsupported      : repond mais >=1 claim non supportée (hallucination)
- metric_substitution       : refuse/devie puis donne une metrique a cote (ex
                              insertion demandee -> taux Parcoursup d'autres)
- honest_refusal            : refuse proprement, rien d'invente
- off_topic                 : repond a cote sans le dire
- crisis_response / oos     : court-circuit detresse / hors-perimetre

Lit les sorties brutes (battery_run.json), n'appelle Claude que sur les
réponses in_scope (les court-circuits urgent/oos sont classés sans LLM).
Ecrit incrementalement (resume-safe).

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/judge_groundedness.py \
        --in  audit_empirique_2026-06-09/results/battery_run.json \
        --out audit_empirique_2026-06-09/results/groundedness.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from anthropic import Anthropic

REPO = Path(__file__).resolve().parent.parent
# Juge Haiku : reproductible + CI-able + ~1-2$ (vs Sonnet ~5-7$), cross-family
# preserve (Claude juge Mistral). Decision coût ordre J-7 (run complet).
JUDGE_MODEL = "claude-haiku-4-5-20251001"


def _load_env():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _context_from_sources(sources) -> str:
    """Les sources sont deja extraites (champs reels de la fiche : nom,
    taux_acces_parcoursup_2025, insertion_pro, etc.). On les passe en JSON
    integral au juge - tout chiffre cite par la reponse doit s'y trouver."""
    if not sources:
        return "(AUCUNE source fournie au generateur)"
    return "\n".join(
        json.dumps(s, ensure_ascii=False) if isinstance(s, dict) else str(s)
        for s in sources
    )


JUDGE_SYS = (
    "Tu es un auditeur rigoureux d'un assistant d'orientation francais. On te donne une QUESTION, "
    "la REPONSE de l'assistant, et les SOURCES exactes qui lui ont ete fournies. Ta tache : verifier, "
    "claim par claim, si chaque affirmation FACTUELLE de la reponse (surtout les chiffres : taux, "
    "salaires, places, dates) est SUPPORTEE par les sources fournies. Une affirmation non presente dans "
    "les sources est NON supportee, meme si elle est plausible ou vraie dans le monde reel. "
    "Reponds UNIQUEMENT en JSON valide, sans texte autour."
)

JUDGE_TMPL = """QUESTION :
{question}

REPONSE DE L'ASSISTANT :
{answer}

SOURCES FOURNIES AU GENERATEUR (chaque chiffre cite doit venir d'ici) :
{context}

Renvoie ce JSON exact :
{{
  "outcome": "answered_grounded | answered_unsupported | metric_substitution | honest_refusal | off_topic",
  "answers_the_question": true/false,
  "claims": [
    {{"claim": "affirmation factuelle extraite", "is_numeric": true/false, "supported_by_sources": true/false, "note": "court"}}
  ],
  "n_claims": 0,
  "n_supported": 0,
  "groundedness": 0.0,
  "hallucinated_numbers": true/false,
  "metric_substitution": true/false,
  "notes": "1-2 phrases : ce que fait la reponse, et son principal defaut s'il y en a un"
}}

Regles IMPORTANTES :
- Un "claim" = une affirmation sur le MONDE (une formation existe, un chiffre vaut X, un debouche est Y). Les meta-phrases du type "je n'ai pas cette information dans mes sources", "consulte l'ONISEP", "prends RDV au CIO" NE SONT PAS des claims a grounder : ignore-les.
- Si la reponse ne fait AUCUN claim sur le monde (refus pur), alors outcome=honest_refusal, n_claims=0, groundedness=null.
- groundedness = n_supported / n_claims sinon.
- metric_substitution = true si la reponse refuse/n'a pas la metrique demandee MAIS fournit une autre metrique (ex : on demande l'insertion, elle donne des taux d'acces Parcoursup d'autres formations) comme si pertinent.
- honest_refusal = refuse proprement, n'avance aucun chiffre non source.
- off_topic = repond a cote sans le signaler.
- IMPORTANT : un chiffre suivi de [source SX] DOIT correspondre a une valeur reellement presente dans la source SX fournie. Si la valeur figure bien dans les sources, le claim est supporte."""


def judge_one(client: Anthropic, rec: dict) -> dict:
    ctx = _context_from_sources(rec.get("sources"))
    msg = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1500,
        system=JUDGE_SYS,
        messages=[{"role": "user", "content": JUDGE_TMPL.format(
            question=rec["question"], answer=rec.get("answer", ""), context=ctx)}],
    )
    txt = msg.content[0].text.strip()
    if txt.startswith("```"):
        txt = txt.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(txt)
    except Exception as e:  # noqa: BLE001
        return {"outcome": "judge_parse_error", "error": str(e), "raw": txt[:1000]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY manquant")

    rows = json.loads(Path(args.inp).read_text())
    out_path = Path(args.out)
    done = {}
    if out_path.exists():
        try:
            done = {r["id"]: r for r in json.loads(out_path.read_text())}
        except Exception:
            done = {}

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    results = list(done.values())
    for r in rows:
        if r["id"] in done:
            continue
        scope = (r.get("scope") or {}).get("label")
        base = {"id": r["id"], "category": r.get("category"),
                "scope": scope, "scope_via": (r.get("scope") or {}).get("via"),
                "n_sources": r.get("n_sources", 0),
                "honesty_selfreported": (r.get("validation_selfreported") or {}).get("honesty_score")}
        # court-circuits non in_scope : classes sans LLM
        if scope == "urgent":
            base["judgment"] = {"outcome": "crisis_response", "groundedness": None}
        elif scope in ("out_of_scope", "greeting", "identity"):
            base["judgment"] = {"outcome": f"shortcircuit_{scope}", "groundedness": None}
        elif r.get("error"):
            base["judgment"] = {"outcome": "pipeline_error", "groundedness": None}
        else:
            print(f"[judge] {r['id']} ({r.get('category')})")
            base["judgment"] = judge_one(client, r)
        results.append(base)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"[done] {len(results)} -> {out_path}")


if __name__ == "__main__":
    main()
