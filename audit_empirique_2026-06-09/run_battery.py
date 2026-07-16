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
from src.rag.fact_card import _summarize_voies_acces

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
    # `insertion_pro` est gardé ENTIER (dict nested) : toute clé ajoutée dedans
    # côté collecte (salaire_median_embauche C2b, salaire_q1/salaire_q3 fourchette
    # order 0825) est AUTOMATIQUEMENT visible au juge — pas de re-sync par champ
    # nécessaire pour les ajouts sous insertion_pro. Vérifié order 0825 Phase 1.
    "insertion_pro", "profil_admis", "debouches", "salaire", "annee",
    "source", "url_canonical", "rncp",
    # Bloc A (2026-06-09) — champs exposés par fact_card mais qui manquaient au
    # contexte du juge : sans eux, un « taux d'admission 29,5 % » cité par le
    # générateur (et pourtant grounded dans la fiche) était faussement flaggé
    # comme hallucination. Validation de l'instrument avant de mesurer Bloc A.
    "taux_admission", "capacite", "n_candidats_pp", "n_acceptes_total",
    "rang_dernier_appele", "alternance", "trends",
    # C2a (2026-06-09) — voies_acces fonde la citation dispositifs_reconversion
    # (VAE/formation continue/alternance). Sans ce champ au contexte du juge, une
    # citation pourtant grounded serait faussement flaggée hallucination (même
    # piège d'instrument que taux_admission ci-dessus). Validation avant mesure.
    "voies_acces",
    # Instrument completion (2026-06-11) — 3e occurrence du pattern "juge
    # semi-aveugle". Le générateur LIT du contenu (salaire INSEE, descriptions
    # métier/RNCP) via FactCard.text_libre (`text`/`detail`) et le NOM de la
    # source via la name-cascade — tout cela était strippé côté juge. Résultat :
    # sur une question salaire, S2 (fiche INSEE) se sérialisait en "?" et le juge
    # ne pouvait ni vérifier le chiffre ni détecter le mismatch brut/net. On
    # ajoute exactement ce que le générateur voit. cf
    # [[feedback-validate-measurement-instrument]]. Inventaire complet :
    # docs (jalon 2 Jarvis). Fix DURABLE proposé séparément (juge = FactCard).
    "text", "detail",
    # name-cascade (fact_card._pick_formation_name) : sans ça le juge voit "?"
    # au lieu du vrai nom (ex « professions scientifiques PCS 34 »).
    "libelle_metier", "nom_metier", "libelle", "intitule",
    "libelle_diplome", "libelle_formation", "fap_libelle", "subject",
    "discipline", "grande_discipline",
    # salaire INSEE structuré (partition insee_salaire / salaan 2023) — net ET
    # brut explicitement étiquetés en SOURCE -> le juge peut vérifier le
    # qualificatif brut/net cité par le modèle (garde-fou salaire volet b).
    "salaire_net_median_annuel", "salaire_net_median_mensuel",
    "salaire_net_q1_mensuel", "salaire_net_q3_mensuel",
    "salaire_brut_median_annuel", "cs_libelle", "cs_code",
    "pcs_group_label", "effectif_total", "discipline_agregee",
    "taux_insertion", "part_cadre",
    # mineurs aussi exposés au générateur via FactCard.
    "domain", "url", "duree", "frais_annuels", "selectivite_code", "provenance",
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
    # tronquer text/detail (parité avec fact_card.text_libre, ~400-600 chars) —
    # capture la chaîne salaire INSEE complète sans gonfler le contexte juge.
    for tk in ("text", "detail"):
        if isinstance(out.get(tk), str) and len(out[tk]) > 600:
            out[tk] = out[tk][:600]
    out["_retrieval_score"] = s.get("score")
    out["_sub_index"] = s.get("_sub_index")
    # Fix order 2026-06-11 (Fix 2) — alignement instrument générateur/juge.
    # Le GÉNÉRATEUR voit la normalisation reconversion via
    # FactCard.dispositifs_reconversion (C2a) : "Par expérience" -> VAE,
    # "formation continue", alternance. Le JUGE ne voyait que le voies_acces
    # BRUT ("Par expérience"), d'où il flaguait à tort "accessible en VAE"
    # comme non-supporté (reconv-001/004-v1/malform-004-v1). On expose au juge
    # exactement la même chaîne canonique. cf [[feedback-validate-measurement-instrument]].
    dispositifs = _summarize_voies_acces(fiche.get("voies_acces"))
    if dispositifs:
        out["dispositifs_reconversion"] = dispositifs
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


def _answer_via_stream(pipeline, question: str, temperature: float):
    """Consomme answer_stream() comme le front (H1 lot 1.3, conditions de serving).

    Retourne (texte_complet, sources, meta) où meta capture ce que le bench
    sync ne voyait pas : verdict faithfulness émis DANS le stream (celui que
    l'utilisateur reçoit), latence au premier token, présence d'un event
    structured (mode récit), event error éventuel.

    Différences vs answer() qui justifient ce mode (audit 15/07 « le chemin
    servi n'est pas le chemin certifié ») :
      - pas de policy replacement ni post_process sur le texte streamé ;
      - le verdict vient de _validate_for_stream, pas du retry loop ;
      - pas de retry tour 2 du tout (stream uni-directionnel).
    """
    import asyncio

    async def _consume():
        tokens: list[str] = []
        sources: list = []
        meta: dict = {
            "mode": "stream",
            "stream_first_token_s": None,
            "stream_faithfulness": None,
            "stream_verdict": None,
            "stream_structured": False,
            "stream_error": None,
        }
        t0 = time.time()
        async for ev in pipeline.answer_stream(
            question, temperature=temperature, short_circuit_pace_s=0.0,
        ):
            etype = ev.get("type")
            if etype == "token":
                if meta["stream_first_token_s"] is None:
                    meta["stream_first_token_s"] = round(time.time() - t0, 2)
                tokens.append(ev.get("content") or "")
            elif etype == "sources":
                sources = ev.get("sources") or []
            elif etype == "faithfulness":
                meta["stream_faithfulness"] = ev.get("score")
                meta["stream_verdict"] = ev.get("verdict")
            elif etype == "structured":
                meta["stream_structured"] = ev.get("structured") is not None
            elif etype == "error":
                meta["stream_error"] = ev.get("error")
        return "".join(tokens), sources, meta

    return asyncio.run(_consume())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0, help="0 = toutes")
    ap.add_argument("--temperature", type=float, default=0.3,
                    help="0.0 = génération déterministe (A/B sans bruit de génération)")
    ap.add_argument("--serving", action="store_true",
                    help="conditions de serving RÉELLES (H1 lot 1.3) : passe par "
                         "answer_stream() — le chemin que le front consomme — au lieu "
                         "de answer(). Collecte tokens + events sources/faithfulness/"
                         "structured. À utiliser pour golden CI et batteries futures ; "
                         "le mode answer() reste pour comparabilité historique.")
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
            if args.serving:
                text, sources, stream_meta = _answer_via_stream(
                    pipeline, question, temperature=args.temperature,
                )
                rec.update(stream_meta)
            else:
                text, sources = pipeline.answer(question, temperature=args.temperature)
            rec["latency_s"] = round(time.time() - t0, 2)
            rec["answer"] = text
            rec["scope"] = _serialize_scope(pipeline.last_scope_result)
            rec["validation_selfreported"] = _serialize_validation(pipeline.last_validation)
            rec["sources"] = _serialize_sources(sources)
            rec["n_sources"] = len(sources or [])
            # Option B (J2 U1) — tag observabilité fall-through SELECT->RAG.
            rec["select_fallthrough"] = getattr(pipeline, "last_select_fallthrough", None)
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
