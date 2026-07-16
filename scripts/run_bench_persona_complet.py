"""Bench persona complet — baseline pré-agentique INRIA (ordre 1210).

48 queries unified couvrant 4 sous-suites :
- 18 queries PERSONAS v4 (formation-centric, déjà bench v5++/v5+++)
- 10 queries DARES dédiées (calibrées prospective FAP/région/2030)
- 10 queries blocs RNCP dédiées (calibrées contenu pédagogique/blocs)
- 10 queries user-naturel multi-domain (sans trigger pattern, stress
  cohabitation L2 brute)

Index cible : `formations_multi_corpus_phaseD.index` (54 297 vecteurs =
phaseB 49 295 + DARES 111 + blocs 4 891) — état "main actuel" post
DARES + blocs + tune ×1.0.

Output : `results/bench_persona_complet_2026-04-26{out_suffix}/` avec
sous-dossier par query (ID inclus) pour traçabilité fine.

Usage :
```bash
python scripts/run_bench_persona_complet.py
python scripts/run_bench_persona_complet.py --out-suffix _run2
python scripts/run_bench_persona_complet.py --out-suffix _run3
```

Pour triple-run IC95 baseline pré-agentique.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mistralai.client import Mistral  # noqa: E402
from src.config import load_config  # noqa: E402
from src.experimental.fact_checker import StatFactChecker  # noqa: E402
from src.rag.pipeline import OrientIAPipeline  # noqa: E402
from scripts.run_bench_personas_v3 import PERSONAS  # noqa: E402
from scripts.run_bench_dares_dedie import DARES_QUERIES  # noqa: E402


FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseD.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseD.index"


# Queries blocs RNCP dédiées (10) — calibrées patterns competences_certif
BLOCS_QUERIES = [
    {"id": "q01_blocs_BTS_compta", "pattern_target": "bloc + competence",
     "text": "Quels blocs de compétences valide le BTS comptabilité ?"},
    {"id": "q02_blocs_BUT_info_apprendre", "pattern_target": "que vais-je apprendre",
     "text": "Que vais-je apprendre en BUT informatique ?"},
    {"id": "q03_blocs_master_cyber", "pattern_target": "competences certifiées",
     "text": "Quelles compétences certifiées par un master en cybersécurité ?"},
    {"id": "q04_blocs_BTS_electro_contenu", "pattern_target": "contenu BTS + objectifs pédagogiques",
     "text": "Contenu pédagogique du BTS électrotechnique : quels objectifs pédagogiques ?"},
    {"id": "q05_blocs_VAE_partielle", "pattern_target": "VAE par bloc + RNCP",
     "text": "Comment valider un titre RNCP par VAE par bloc ?"},
    {"id": "q06_blocs_savoir_faire_BTS_hotel", "pattern_target": "savoir-faire certifié",
     "text": "Quels savoir-faire certifiés à la sortie d'un BTS hôtellerie-restauration ?"},
    {"id": "q07_blocs_BUT_GEA", "pattern_target": "que permet de faire",
     "text": "Que permet de faire un BUT GEA dans la pratique ?"},
    {"id": "q08_blocs_RNCP35185", "pattern_target": "rncp\\d+",
     "text": "RNCP35185 : quels blocs de compétences couvre cette fiche ?"},
    {"id": "q09_blocs_master_marketing", "pattern_target": "programme pédagogique",
     "text": "Quel est le programme pédagogique du master Marketing Digital ?"},
    {"id": "q10_blocs_licence_pro_com", "pattern_target": "competences acquises",
     "text": "Quelles compétences acquises après une licence pro en communication ?"},
]


# Queries user-naturel multi-domain (10) — domain=None (pas de trigger
# pattern), stress cohabitation L2 brute + couvre GAPs DATA_INVENTORY
USER_NATUREL_QUERIES = [
    {"id": "q11_lycee_reunion_metropole", "gap_target": "DROM-COM",
     "text": "Je suis lycéen à La Réunion, j'aimerais étudier le numérique en métropole. Quelles options s'offrent à moi ?"},
    {"id": "q12_apprentissage_vs_bac_general", "gap_target": "Phase (a) apprentissage",
     "text": "Mon fils de 17 ans hésite entre l'apprentissage et le bac général. Comment l'aider à décider ?"},
    {"id": "q13_reconversion_grande_distrib", "gap_target": "Reconversion 25+",
     "text": "Je travaille dans la grande distribution depuis 8 ans, je veux changer complètement de secteur. Par où commencer ?"},
    {"id": "q14_passerelle_infirmier_RH", "gap_target": "Reconversion + passerelles",
     "text": "Une amie infirmière souhaite passer à un poste en ressources humaines. Quelles passerelles existent ?"},
    {"id": "q15_cout_ecole_commerce_5ans", "gap_target": "Financement",
     "text": "Combien faut-il prévoir financièrement pour 5 années d'études en école de commerce ?"},
    {"id": "q16_bacpro_BUT_taux", "gap_target": "Bac pro × BUT",
     "text": "Mon fils a un bac pro vente, peut-il intégrer un BUT et avec quelle chance de réussir ?"},
    {"id": "q17_decouverte_dehors_mains", "gap_target": "Découverte multi-domain",
     "text": "Quels secteurs d'avenir conviendraient à quelqu'un qui aime travailler dehors et avec ses mains ?"},
    {"id": "q18_seconde_orientation", "gap_target": "Conseil 2nde",
     "text": "Je suis en seconde, j'ai peur de ne pas savoir quoi faire après le bac. Comment commencer à réfléchir à mon orientation ?"},
    {"id": "q19_kine_debouches", "gap_target": "Métier × débouchés",
     "text": "Étudier la kinésithérapie aujourd'hui, est-ce que ça vaut le coup au regard des débouchés ?"},
    {"id": "q20_sante_rural", "gap_target": "Santé × géographique rural",
     "text": "Comment trouver un poste de soignant en zone rurale ? Quelles options de carrière ?"},
]


def _build_unified_queries():
    """Combine les 4 sous-suites en une seule liste tagged par sous-suite."""
    queries = []
    # Sous-suite 1 : 18 PERSONAS v4
    for persona in PERSONAS:
        for q in persona["queries"]:
            queries.append({
                "suite": "personas_v4",
                "persona_id": persona["id"],
                "id": f"{persona['id']}_{q['id']}",
                "text": q["text"],
                "query_type": q.get("type"),
                "scope": persona.get("scope"),
                "persona_description": persona.get("description"),
            })
    # Sous-suite 2 : 10 DARES dédiées
    for q in DARES_QUERIES:
        queries.append({
            "suite": "dares_dedie",
            "persona_id": None,
            "id": q["id"],
            "text": q["text"],
            "pattern_target": q["pattern_target"],
        })
    # Sous-suite 3 : 10 blocs RNCP dédiées
    for q in BLOCS_QUERIES:
        queries.append({
            "suite": "blocs_dedie",
            "persona_id": None,
            "id": q["id"],
            "text": q["text"],
            "pattern_target": q["pattern_target"],
        })
    # Sous-suite 4 : 10 user-naturel
    for q in USER_NATUREL_QUERIES:
        queries.append({
            "suite": "user_naturel",
            "persona_id": None,
            "id": q["id"],
            "text": q["text"],
            "gap_target": q["gap_target"],
        })
    return queries


def _run_one_query(pipeline, checker, query, idx):
    t0 = time.time()
    try:
        answer, sources = pipeline.answer(query["text"])
        elapsed_gen = round(time.time() - t0, 2)
    except Exception as e:
        return {
            "idx_global": idx,
            "suite": query["suite"],
            "query_id": query["id"],
            "query_text": query["text"],
            "error_pipeline": f"{type(e).__name__}: {e}",
        }

    t1 = time.time()
    try:
        report = checker.verify(answer, sources)
    except Exception as e:
        report = None
        fact_check_error = f"{type(e).__name__}: {e}"
    else:
        fact_check_error = None
    elapsed_fc = round(time.time() - t1, 2)

    if report and report.stats_hallucinated:
        answer_annotated = checker.annotate(answer, report)
    else:
        answer_annotated = answer

    return {
        "idx_global": idx,
        "suite": query["suite"],
        "persona_id": query.get("persona_id"),
        "query_id": query["id"],
        "query_text": query["text"],
        "query_type": query.get("query_type"),
        "scope": query.get("scope"),
        "pattern_target": query.get("pattern_target"),
        "gap_target": query.get("gap_target"),
        "elapsed_gen_s": elapsed_gen,
        "elapsed_fact_check_s": elapsed_fc,
        "answer_raw": answer,
        "answer_annotated": answer_annotated,
        "annotated_differs": answer != answer_annotated,
        "n_sources": len(sources),
        "fact_check_error": fact_check_error,
        "fact_check_summary": report.summary if report else None,
        "fact_check_stats": [
            {
                "stat_text": s.stat_text,
                "stat_value": s.stat_value,
                "stat_unit": s.stat_unit,
                "context_in_response": s.context_in_response,
                "verdict": s.verdict,
                "source_fiche_excerpt": s.source_fiche_excerpt,
            }
            for s in (report.stats_extracted if report else [])
        ],
        "sources_top10": [
            {
                "score": round(float(s.get("score", 0)), 4),
                "nom": s["fiche"].get("nom", "")[:100] or s["fiche"].get("text", "")[:100],
                "etablissement": s["fiche"].get("etablissement", ""),
                "niveau": s["fiche"].get("niveau"),
                "phase": s["fiche"].get("phase"),
                "source": s["fiche"].get("source"),
                "domaine": s["fiche"].get("domaine"),
                "domain": s["fiche"].get("domain", "formation"),
            }
            for s in sources[:10]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-suffix", type=str, default="",
                        help="Suffix appendu à OUT_DIR (ex: '_run2' pour triple-run).")
    parser.add_argument("--max", type=int, default=None,
                        help="Limite le nombre de queries (debug).")
    parser.add_argument("--suite", type=str, default=None,
                        help="Filtrer une sous-suite (personas_v4 / dares_dedie / blocs_dedie / user_naturel).")
    args = parser.parse_args()

    out_dir = REPO_ROOT / "results" / f"bench_persona_complet_2026-04-26{args.out_suffix}"

    if not FICHES_PATH.exists() or not INDEX_PATH.exists():
        print("❌ Phase D index/fiches absent.")
        print("   → Run d'abord : python scripts/build_index_phaseD.py")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))
    print(f"Phase D index : {len(fiches):,} fiches (phaseB + DARES + blocs combiné)")

    pipeline = OrientIAPipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))
    checker = StatFactChecker(client)

    queries = _build_unified_queries()
    if args.suite:
        queries = [q for q in queries if q["suite"] == args.suite]
    if args.max:
        queries = queries[:args.max]

    print(f"Bench persona complet : {len(queries)} queries (4 sous-suites)")
    print("=" * 70)

    all_results = []
    for idx, query in enumerate(queries, 1):
        suite_emoji = {"personas_v4": "👤", "dares_dedie": "📊",
                       "blocs_dedie": "🎓", "user_naturel": "🗣️"}.get(query["suite"], "?")
        print(f"\n[{idx:2d}/{len(queries)}] {suite_emoji} [{query['suite']:<14}] {query['id']}")
        print(f"    \"{query['text'][:80]}{'...' if len(query['text']) > 80 else ''}\"")
        res = _run_one_query(pipeline, checker, query, idx)
        out_path = out_dir / f"query_{idx:02d}_{query['suite']}_{query['id']}.json"
        out_path.write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        all_results.append(res)
        if "error_pipeline" in res:
            print(f"    ❌ pipeline error : {res['error_pipeline'][:80]}")
        else:
            fc = res.get("fact_check_summary") or {}
            domains_in_top = sorted({s["domain"] for s in res["sources_top10"]})
            print(
                f"    gen {res['elapsed_gen_s']}s + fc {res['elapsed_fact_check_s']}s"
                f" | stats {fc.get('n_stats_total',0)} → {fc.get('n_verified',0)}✅"
                f" / {fc.get('n_with_disclaimer',0)}🟡 / {fc.get('n_hallucinated',0)}🔴"
                f" | domains {domains_in_top}"
            )

    all_path = out_dir / "_ALL_QUERIES.json"
    all_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✅ Bench persona complet fini. Output → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
