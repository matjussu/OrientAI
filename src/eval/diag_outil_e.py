"""Diagnostic de l'appel d'outil de mistral-medium-2604 (ordre 2026-09-24-1020, phase 1).

Mesure du 23/09 (`results/donnee_etape_d/sonde_outil/RESUME.md`) : Medium n'appelle jamais `lire_fiche` au
format C, même avec tool_choice="any", mais l'appelle sur un prompt minimal. Ce script rejoue le PREMIER tour des
5 conversations de la sonde, prompt et cartes identiques à la grille D, en ne changeant qu'un réglage à la fois.

    python -m src.eval.diag_outil_e --modele mistral-medium-2604 --variantes defaut,effort_high --reps 1

Chaque appel est écrit dans results/banc_e/diag_outil/<modele>.jsonl (réglage, question, appels, fin, tokens,
caractères de raisonnement, modèle rendu, horodatage). Le contrôle négatif est une question sans besoin de fiche :
un modèle qui appelle l'outil dessus appelle par réflexe, pas par besoin.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from src.base_c.outils import Base
from src.eval.battery.config import SYSTEM_PROMPT_CTX
from src.eval.exposition_d import BANC
from src.eval.format_d import Formats
from src.eval.grille_d import BASE, CORPUS, EXPOSITION, OUTIL, PHRASE_OUTIL, SONDE, texte_reponse

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "results/banc_e/diag_outil"
SERVEUR = "https://api.eu.mistral.ai"
QUESTION_NEGATIVE = "Merci pour ton aide, c'est tout pour aujourd'hui. Bonne journée !"

# Un réglage = les arguments ajoutés à chat.complete, et le prompt système utilisé ("grille" ou "minimal").
VARIANTES = {
    "defaut": ({"tool_choice": "auto"}, "grille"),
    "effort_none": ({"tool_choice": "auto", "reasoning_effort": "none"}, "grille"),
    "effort_high": ({"tool_choice": "auto", "reasoning_effort": "high"}, "grille"),
    "any": ({"tool_choice": "any"}, "grille"),
    "any_effort_high": ({"tool_choice": "any", "reasoning_effort": "high"}, "grille"),
    "sans_parallele": ({"tool_choice": "auto", "parallel_tool_calls": False}, "grille"),
    "prompt_minimal": ({"tool_choice": "auto"}, "minimal"),
}


def systemes(ids_conv: list[str]) -> dict[str, tuple[str, str, list[str]]]:
    """Pour chaque conversation de la sonde : (prompt système grille, prompt minimal, identifiants exposés)."""
    exposition = json.loads(EXPOSITION.read_bytes())
    formats = Formats(Base.ouvrir(BASE), json.loads(CORPUS.read_bytes()))
    out = {}
    for c in ids_conv:
        ids = exposition["conversations"][c]["exposees"]
        corps = "\n\n---\n\n".join(formats.carte_c(i) for i in ids)
        bloc = PHRASE_OUTIL + f"\n\n<fiches>\n{corps}\n</fiches>"
        out[c] = (SYSTEM_PROMPT_CTX + bloc, bloc.strip(), ids)
    return out


def appel(client, modele: str, systeme: str, question: str, kw: dict) -> dict:
    t0 = time.time()
    r = client.chat.complete(model=modele, messages=[{"role": "system", "content": systeme},
                                                     {"role": "user", "content": question}],
                             temperature=0.3, tools=OUTIL, **kw)
    m = r.choices[0].message
    texte, pensee = texte_reponse(m)
    return {"appels": [tc.function.arguments if isinstance(tc.function.arguments, str)
                       else json.dumps(tc.function.arguments, ensure_ascii=False) for tc in (m.tool_calls or [])],
            "fin": r.choices[0].finish_reason, "tokens_in": r.usage.prompt_tokens,
            "tokens_out": r.usage.completion_tokens, "raisonnement_caracteres": pensee, "mots": len(texte.split()),
            "modele_rendu": r.model, "secondes": round(time.time() - t0, 2),
            "debut_texte": texte[:600], "fin_texte": texte[-300:]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modele", required=True)
    ap.add_argument("--variantes", default=",".join(VARIANTES))
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--negatif", action="store_true", help="joue aussi la question sans besoin de fiche")
    args = ap.parse_args(argv)
    from mistralai.client import Mistral
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"], server_url=SERVEUR, timeout_ms=int(os.environ.get("DIAG_TIMEOUT_MS", 180_000)))
    banc = {i["id"]: i for i in json.loads(BANC.read_bytes())["items"]}
    sys_ = systemes(list(SONDE))
    SORTIE.mkdir(parents=True, exist_ok=True)
    fichier = SORTIE / f"{args.modele}.jsonl"
    for v in args.variantes.split(","):
        kw, quel = VARIANTES[v]
        cas = [(c, banc[c]["turns"][0], "positif") for c in SONDE]
        if args.negatif:
            cas.append((SONDE[0], QUESTION_NEGATIVE, "negatif"))
        for rep in range(args.reps):
            for c, question, sens in cas:
                grille, minimal, _ = sys_[c]
                rec = {"variante": v, "reglages": kw, "prompt": quel, "conversation": c, "sens": sens, "rep": rep,
                       "modele": args.modele, "serveur": SERVEUR,
                       "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                try:
                    rec.update(appel(client, args.modele, grille if quel == "grille" else minimal, question, kw))
                except Exception as e:  # noqa: BLE001 - tracé tel quel
                    rec["erreur"] = f"{type(e).__name__}: {e}"[:400]
                if rec.get("modele_rendu") not in (None, args.modele):
                    raise SystemExit(f"modèle rendu {rec['modele_rendu']} différent de {args.modele} : arrêt")
                with open(fichier, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"{v:16} {c:9} {sens:7} appels={len(rec.get('appels', []))} fin={rec.get('fin')} "
                      f"out={rec.get('tokens_out')} pensee={rec.get('raisonnement_caracteres')} "
                      f"{rec.get('erreur', '')[:80]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
