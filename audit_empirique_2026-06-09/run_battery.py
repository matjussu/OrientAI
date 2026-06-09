"""Runner empirique OrientAI - observe le pipeline RÉEL (pas la doc).

Construit le pipeline via la factory canonique de production
(make_production_pipeline), EXACTEMENT comme le serveur FastAPI le fait
(src/api/server.py:137-138). Lance chaque question de l'eval set, capture la
sortie brute réelle + scope + validation self-reported + sources + latence,
écrit incrémentalement en JSON (resume-safe).

Usage:
    cd ~/projets/OrientIA && source .venv/bin/activate
    python audit_empirique_2026-06-09/run_battery.py \
        --eval-set audit_empirique_2026-06-09/eval_set.json \
        --out audit_empirique_2026-06-09/results/battery_run.json

Aucune dépendance Ragas ici (mesure de faithfulness séparée, cf
measure_faithfulness.py) : on capture d'abord les sorties brutes, on mesure
ensuite, pour ne pas mélanger observation et jugement.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

import src.observability  # noqa: F401 - shim mistralai avant tout import lourd
from mistralai.client import Mistral

from src.rag.factory import make_production_pipeline

REPO = Path(__file__).resolve().parent.parent
FICHES_PATH = Path(os.environ.get("ORIENTIA_FICHES_PATH", REPO / "data/processed/formations.json"))
INDEX_PATH = os.environ.get("ORIENTIA_INDEX_PATH", str(REPO / "data/embeddings/formations.index"))


def _load_env():
    """Charge MISTRAL_API_KEY depuis .env si pas déjà dans l'environnement."""
    if os.environ.get("MISTRAL_API_KEY"):
        return
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _serialize_scope(scope) -> dict | None:
    if scope is None:
        return None
    return {
        "label": getattr(scope, "label", None),
        "via": getattr(scope, "via", None),  # regex_urgent | llm | fallback_in_scope ...
        "reason": getattr(scope, "reason", None),
        "has_prewritten": bool(getattr(scope, "pre_written_response", None)),
    }


def _serialize_validation(val) -> dict | None:
    if val is None:
        return None
    return {
        "honesty_score": getattr(val, "honesty_score", None),
        "flagged": getattr(val, "flagged", None),
        "rule_violations": [str(v) for v in getattr(val, "rule_violations", []) or []][:20],
        "corpus_warnings": [str(v) for v in getattr(val, "corpus_warnings", []) or []][:20],
        "presence_warnings": [str(v) for v in getattr(val, "presence_warnings", []) or []][:20],
    }


_FICHE_KEEP = (
    "nom", "etablissement", "ville", "region", "departement", "niveau",
    "statut", "type_diplome", "domaine", "taux_acces_parcoursup_2025",
    "nombre_places", "propositions_totales", "pct_acceptes_debut_pp",
    "insertion_pro", "profil_admis", "debouches", "salaire", "annee",
    "source", "url_canonical", "rncp",
    # Bloc A (2026-06-09) — champs exposés par fact_card mais qui manquaient au
    # contexte du juge : sans eux, un « taux d'admission 29,5 % » cité par le
    # générateur (et pourtant grounded dans la fiche) était faussement flaggé
    # comme hallucination. Validation de l'instrument avant de mesurer Bloc A.
    "taux_admission", "capacite", "n_candidats_pp", "n_acceptes_total",
    "rang_dernier_appele", "alternance", "trends",
)


def _extract_fiche(s: dict) -> dict:
    """Les sources renvoyees par answer() sont des wrappers retrieval
    {_sub_index, base_score, embedding, fiche, score}. Le contenu reel est
    sous `fiche`. On extrait les champs utiles (chiffres compris) et on jette
    l'embedding (vecteur volumineux)."""
    fiche = s.get("fiche") if isinstance(s.get("fiche"), dict) else s
    out = {k: fiche.get(k) for k in _FICHE_KEEP if fiche.get(k) is not None}
    # tronquer debouches volumineux
    if isinstance(out.get("debouches"), list):
        out["debouches"] = out["debouches"][:8]
    out["_retrieval_score"] = s.get("score")
    out["_sub_index"] = s.get("_sub_index")
    return out


def _serialize_sources(sources) -> list[dict]:
    """Extrait le contenu reel de chaque source (sous `fiche`) pour audit +
    contexte du juge de groundedness. Sans cette extraction, le juge ne voit
    pas les chiffres et flague a tort des reponses pourtant sourcees."""
    out = []
    for i, s in enumerate(sources or []):
        if not isinstance(s, dict):
            out.append({"raw": str(s)[:500]})
            continue
        rec = _extract_fiche(s)
        rec["id"] = f"S{i+1}"
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0, help="0 = toutes")
    args = ap.parse_args()

    _load_env()
    if not os.environ.get("MISTRAL_API_KEY"):
        raise SystemExit("MISTRAL_API_KEY manquant (ni env ni .env)")

    raw = json.loads(Path(args.eval_set).read_text())
    # accepte une liste plate OU le format versionne {version, n, items:[...]}
    questions = raw["items"] if isinstance(raw, dict) and "items" in raw else raw
    if args.limit:
        questions = questions[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Resume : skip les ids déjà faits
    done = {}
    if out_path.exists():
        try:
            done = {r["id"]: r for r in json.loads(out_path.read_text())}
        except Exception:
            done = {}

    print(f"[boot] fiches={FICHES_PATH} index={INDEX_PATH}")
    fiches = json.loads(FICHES_PATH.read_text())
    print(f"[boot] {len(fiches)} fiches chargees")
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(INDEX_PATH)
    print("[boot] pipeline pret (index charge)")

    results = list(done.values())
    for i, q in enumerate(questions):
        qid = q["id"]
        if qid in done:
            print(f"[skip] {qid} deja fait")
            continue
        question = q["question"]
        print(f"[{i+1}/{len(questions)}] {qid} :: {question[:70]}")
        rec = {
            "id": qid,
            "category": q.get("category"),
            "expectation": q.get("expectation"),
            "question": question,
        }
        t0 = time.time()
        try:
            text, sources = pipeline.answer(question)
            rec["latency_s"] = round(time.time() - t0, 2)
            rec["answer"] = text
            rec["scope"] = _serialize_scope(pipeline.last_scope_result)
            rec["validation_selfreported"] = _serialize_validation(pipeline.last_validation)
            rec["sources"] = _serialize_sources(sources)
            rec["n_sources"] = len(sources or [])
            rec["error"] = None
        except Exception as e:  # noqa: BLE001 - on logge le raté, on continue
            rec["latency_s"] = round(time.time() - t0, 2)
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["traceback"] = traceback.format_exc()[-2000:]
            print(f"   ERREUR: {rec['error']}")
        results.append(rec)
        # write incremental (resume-safe)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    print(f"[done] {len(results)} resultats -> {out_path}")


if __name__ == "__main__":
    main()
