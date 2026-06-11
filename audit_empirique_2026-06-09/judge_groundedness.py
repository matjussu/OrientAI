"""Juge de groundedness (faithfulness) - Claude juge, Mistral genere.

Principe (L4 "construire une IA avec une IA") : un LLM d'une AUTRE famille que
le generateur (Claude Sonnet vs Mistral Medium) juge, phrase/claim par claim,
si chaque affirmation factuelle de la reponse est SUPPORTEE par les sources
reellement fournies au generateur. Evite l'auto-jugement (le honesty_score
interne du pipeline etait justement faussement confiant).

Classe aussi l'OUTCOME de chaque reponse pour distinguer :
- answered_grounded               : repond directement a la question + tout sourcé
- answered_alternative_disclaimed : signale EXPLICITEMENT que la cible demandee est absente des
                                    sources, PUIS propose une alternative clairement etiquetee dont
                                    chaque claim est sourcé, SANS pretendre qu'elle repond a la
                                    question d'origine. Comportement FIDELE (J3, 2026-06-11).
- answered_unsupported            : repond mais >=1 claim non supportée (hallucination)
- metric_substitution             : donne une metrique/formation a cote SANS divulguer que la cible
                                    demandee manque, comme si c'etait la reponse (insertion demandee
                                    -> taux Parcoursup d'autres, presente sans disclaimer)
- honest_refusal                  : refuse proprement, rien d'invente
- off_topic                       : repond a cote sans le dire
- crisis_response / oos           : court-circuit detresse / hors-perimetre

GARDE-FOU ANTI-GAMING (J3) : answered_alternative_disclaimed ne re-bucket QUE des reponses dont le
juge a lui-meme prouve groundedness=1.0 (chaque claim supporte). hallucinated_numbers et la
detection de claim non-supporte restent INTOUCHES : une alternative NON sourcee ou un chiffre
fabrique reste answered_unsupported. On corrige un label auto-contradictoire (unsupported alors que
tous les claims sont supportes), on ne deguise pas du mauvais en bon. alternative_relevance
(relevant/weak/irrelevant) est un axe HELPFULNESS orthogonal, hors du gate faithfulness.

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
  "outcome": "answered_grounded | answered_alternative_disclaimed | answered_unsupported | metric_substitution | honest_refusal | off_topic",
  "answers_the_question": true/false,
  "claims": [
    {{"claim": "affirmation factuelle extraite", "is_numeric": true/false, "supported_by_sources": true/false, "note": "court"}}
  ],
  "n_claims": 0,
  "n_supported": 0,
  "groundedness": 0.0,
  "hallucinated_numbers": true/false,
  "metric_substitution": true/false,
  "alternative_relevance": "relevant | weak | irrelevant | null",
  "notes": "1-2 phrases : ce que fait la reponse, et son principal defaut s'il y en a un"
}}

Regles IMPORTANTES :
- Un "claim" = une affirmation sur le MONDE (une formation existe, un chiffre vaut X, un debouche est Y). Les meta-phrases du type "je n'ai pas cette information dans mes sources", "consulte l'ONISEP", "prends RDV au CIO" NE SONT PAS des claims a grounder : ignore-les.
- groundedness = n_supported / n_claims (null si n_claims=0).
- Un chiffre suivi de [source SX] DOIT correspondre a une valeur reellement presente dans la source SX fournie. Si la valeur figure bien dans les sources, le claim est supporte.

PROCEDURE DE DECISION DE L'OUTCOME (applique-la DANS CET ORDRE, prends le PREMIER cas qui matche) :
  A. La reponse ne fait AUCUN claim sur le monde (refus pur, aucune formation/chiffre avance) -> honest_refusal, n_claims=0, groundedness=null.
  B. La reponse DIVULGUE EXPLICITEMENT que la cible demandee (formation / lieu / metrique precis) est ABSENTE des sources (formulations type "je n'ai pas X dans mes sources", "X n'est pas disponible", "aucune fiche pour X"), PUIS propose une alternative clairement etiquetee (autre lieu, autre formation proche, metrique liee) ET chaque claim factuel de l'alternative est supporte par les sources (n_supported == n_claims) -> answered_alternative_disclaimed. metric_substitution=false. C'est FIDELE : le disclaimer empeche toute pretention de pertinence directe.
  C. La reponse fournit une autre metrique/formation que celle demandee MAIS SANS divulguer explicitement que la cible manque (presente l'alternative comme si elle repondait) -> metric_substitution=true, outcome=metric_substitution.
  D. Il reste >=1 claim NON supporte par les sources -> answered_unsupported. (NE JAMAIS choisir answered_unsupported si n_supported == n_claims : par definition il faut au moins un claim non supporte.)
  E. La reponse repond directement a la question posee, tous claims supportes -> answered_grounded.
  F. La reponse parle d'autre chose sans le signaler -> off_topic.

- metric_substitution (le flag booleen) = true UNIQUEMENT au cas C (substitution NON divulguee). Au cas B (alternative divulguee+sourcee) il est false.
- alternative_relevance : a remplir UNIQUEMENT si outcome=answered_alternative_disclaimed, sinon null. C'est un jugement de UTILITE de l'alternative pour l'utilisateur (PAS de fidelite, n'affecte pas groundedness) :
    * "relevant"   = alternative plausiblement utile (meme metrique meme region, ou meme lieu formation proche).
    * "weak"       = liee mais d'utilite limitee (autre type de metrique ; proxy de categorie large ; region differente).
    * "irrelevant" = geographiquement/thematiquement lointaine (ex : une formation a Papeete proposee pour une demande a Nantes).
- honest_refusal = refuse proprement, n'avance aucun chiffre non source."""


def judge_one(client: Anthropic, rec: dict) -> dict:
    ctx = _context_from_sources(rec.get("sources"))
    msg = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=1500,
        temperature=0,  # reproductibilite : reduit le bruit run-to-run du juge
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
