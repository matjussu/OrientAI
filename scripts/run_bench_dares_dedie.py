"""Bench dédié DARES Métiers 2030 — A/B isolation phaseB vs phaseC_dares.

Conçu pour mesurer **équitablement** l'apport DARES en utilisant des
queries qui activent le domain hint `metier_prospective` (cf
`src/rag/intent.py:_PATTERNS_DOMAIN_METIER_PROSPECTIVE`).

## Pourquoi un bench dédié ?

Le bench nuit (`run_bench_personas_v5plusplusplus_dares.py`) utilisait les
18 queries personas v4 — formation-centric par design. 0/18 activaient
`metier_prospective` → le boost reranker ×1.5 jamais exercé. Verdict
triple-run IC95 ±7-8pp = équivalent v5++. Bench inadapté pour mesurer
DARES.

## Design A/B

10 queries prospectives explicit construites pour activer les patterns
regex (postes à pourvoir, métiers 2030, perspectives recrutement, FAP X,
déséquilibre potentiel, retraite massive, projection recrutement,
niveau de tension 2019, etc.).

Chaque query lancée sur **2 indexes distincts** :
- `formations_multi_corpus_phaseB.index` (sans DARES) — baseline
- `formations_multi_corpus_phaseC_dares.index` (avec DARES) — treatment

Le delta verified/halluc isole la contribution DARES sur queries adaptées.

## Usage

```bash
python scripts/run_bench_dares_dedie.py --variant phaseB
python scripts/run_bench_dares_dedie.py --variant phaseC_dares
```

Output : `results/bench_dares_dedie_2026-04-26_<variant>/`
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


# Queries dédiées DARES — chacune calibrée pour activer un pattern
# specific de _PATTERNS_DOMAIN_METIER_PROSPECTIVE. Les patterns ciblés
# sont annotés en commentaire pour traçabilité.
DARES_QUERIES = [
    {
        "id": "q01_postes_pourvoir_global",
        "pattern_target": "postes a pourvoir + metiers 2030",
        "text": "Quels métiers en 2030 vont recruter le plus de postes à pourvoir en France ?",
    },
    {
        "id": "q02_perspectives_bretagne",
        "pattern_target": "perspectives recrutement + region",
        "text": "Quelles sont les perspectives de recrutement en Bretagne d'ici 2030 ?",
    },
    {
        "id": "q03_postes_aides_soignants",
        "pattern_target": "postes a pourvoir + métier specific",
        "text": "Combien de postes à pourvoir sont attendus pour les aides-soignants d'ici 2030 ?",
    },
    {
        "id": "q04_retraite_massive",
        "pattern_target": "retraite massive",
        "text": "Quels métiers vont voir une retraite massive de leurs effectifs d'ici 2030 ?",
    },
    {
        "id": "q05_metiers_btp_recruter",
        "pattern_target": "quels métiers vont recruter + sector",
        "text": "Quels métiers du bâtiment vont recruter le plus en Île-de-France d'ici 2030 ?",
    },
    {
        "id": "q06_metiers_2030_aura",
        "pattern_target": "métiers 2030 + region",
        "text": "Métiers en 2030 : quels secteurs vont créer le plus d'emplois en Auvergne-Rhône-Alpes ?",
    },
    {
        "id": "q07_niveau_tension_enseignants",
        "pattern_target": "niveau de tension YYYY",
        "text": "Quel est le niveau de tension 2019 pour le métier d'enseignant ?",
    },
    {
        "id": "q08_desequilibre_conducteurs",
        "pattern_target": "déséquilibre potentiel",
        "text": "Y a-t-il un déséquilibre potentiel sur le marché des conducteurs de véhicules d'ici 2030 ?",
    },
    {
        "id": "q09_projection_numerique",
        "pattern_target": "projection recrutement + métiers 2030",
        "text": "Quelles sont les projections de recrutement pour les métiers du numérique d'ici 2030 ?",
    },
    {
        "id": "q10_fap_T4Z",
        "pattern_target": "FAP code explicit",
        "text": "FAP T4Z agents d'entretien : combien de postes à pourvoir d'ici 2030 et dans quelles régions ?",
    },
]


VARIANTS = {
    "phaseB": {
        "fiches": "data/processed/formations_multi_corpus_phaseB.json",
        "index": "data/embeddings/formations_multi_corpus_phaseB.index",
    },
    "phaseC_dares": {
        "fiches": "data/processed/formations_multi_corpus_phaseC_dares.json",
        "index": "data/embeddings/formations_multi_corpus_phaseC_dares.index",
    },
}


def _run_one_query(pipeline, checker, query, idx):
    t0 = time.time()
    try:
        answer, sources = pipeline.answer(query["text"])
        elapsed_gen = round(time.time() - t0, 2)
    except Exception as e:
        return {
            "idx_global": idx,
            "query_id": query["id"],
            "query_text": query["text"],
            "pattern_target": query["pattern_target"],
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
        "query_id": query["id"],
        "query_text": query["text"],
        "pattern_target": query["pattern_target"],
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
    parser.add_argument("--variant", choices=list(VARIANTS.keys()), required=True,
                        help="Index variant: phaseB (sans DARES) ou phaseC_dares (avec DARES)")
    parser.add_argument("--out-suffix", type=str, default="",
                        help="Suffix appendu à OUT_DIR (ex: '_boost_1_1' pour distinguer une re-run avec config reranker tunée).")
    args = parser.parse_args()

    variant = VARIANTS[args.variant]
    fiches_path = REPO_ROOT / variant["fiches"]
    index_path = REPO_ROOT / variant["index"]
    out_dir = REPO_ROOT / "results" / f"bench_dares_dedie_2026-04-26_{args.variant}{args.out_suffix}"

    if not fiches_path.exists() or not index_path.exists():
        print(f"❌ Variant {args.variant} files absents:")
        print(f"  fiches: {fiches_path}")
        print(f"  index : {index_path}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)  # ADR-047
    fiches = json.loads(fiches_path.read_text(encoding="utf-8"))
    print(f"Variant: {args.variant} — {len(fiches):,} fiches")

    pipeline = OrientIAPipeline(client, fiches)
    pipeline.load_index_from(str(index_path))
    checker = StatFactChecker(client)

    print(f"Bench dédié DARES : {len(DARES_QUERIES)} queries prospectives")
    print("=" * 60)

    all_results = []
    for idx, query in enumerate(DARES_QUERIES, 1):
        print(f"\n[{idx:2d}/{len(DARES_QUERIES)}] {query['id']} (target: {query['pattern_target']})")
        print(f"    \"{query['text']}\"")
        res = _run_one_query(pipeline, checker, query, idx)
        out_path = out_dir / f"query_{idx:02d}_{query['id']}.json"
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
    print(f"\n✅ Bench dédié DARES variant={args.variant} fini. Output → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
