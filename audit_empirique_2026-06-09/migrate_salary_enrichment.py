"""Migration C2b (order 2026-06-11) — enrichissement salaire du corpus servi.

Alimente `insertion_pro.salaire_median_embauche` (net, valeur SOURCE, zéro
agrégation) sur le corpus servi formations.json, SANS ré-embed (index FAISS figé
intact, contexte LLM lu live par fact_card). Deux apports :
  1. InserSup : join propre (MonMaster nom+discipline ; parcoursup UAI+type),
     salaire net médian CSV local.
  2. Doctorat : insertion_pro depuis les champs salaire top-level (ip_doc).

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/migrate_salary_enrichment.py          # dry-run + métriques
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/migrate_salary_enrichment.py --apply
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from src.collect.insersup_salary import build_salary_index, attach_insersup_salaries
from src.collect.ip_doc_doctorat import build_doctorat_insertion_pro

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"
CSV = REPO / "data/raw/insersup.csv"


def _enrich_doctorat(fiches: list[dict]) -> int:
    """Reconstruit insertion_pro pour les fiches doctorat. DÉTERMINISTE depuis les
    champs source top-level de la fiche elle-même (pas de jointure) -> rebuild
    inconditionnel sûr (idempotent : même salaire, cohorte corrigée annee_cohorte)."""
    n = 0
    for f in fiches:
        if not isinstance(f, dict) or f.get("source") != "ip_doc_doctorat":
            continue
        built = build_doctorat_insertion_pro(f)
        if built is not None:
            f["insertion_pro"] = built
            n += 1
    return n


def main(apply: bool) -> None:
    fiches = json.loads(FICHES.read_text())
    print(f"corpus: {len(fiches)} fiches")

    print("\n[1] Index salaire InserSup (CSV local)…")
    index = build_salary_index(CSV)
    print("  métriques index:", index["metrics"])

    print("\n[2] Attach InserSup salaires…")
    metrics = attach_insersup_salaries(fiches, index)
    print(f"  fiches enrichies InserSup: {metrics['n_enriched']}")
    print(f"  par méthode de jointure : {metrics['by_method']}  (exact-match normalisé, zéro fuzzy)")
    print(f"  par source fiche        : {metrics['by_source']}")
    print(f"  ambiguïtés résiduelles (même clé libellé + même promo, salaires divergents) : {index['metrics']['ambiguities_same_key_same_promo']}")
    print(f"  critère freshest-promo : on retient l'année de cohorte la plus récente par clé (tracée par fiche dans salaire_cohorte)")
    print("\n  EXEMPLES de paires jointes (vérifiables à la main) :")
    for ex in metrics["examples"]:
        print(f"    - [{ex['method']}] fiche '{ex['fiche_nom']}' ({ex['fiche_source']}, {ex['fiche_etab']}, {ex['fiche_discipline']})")
        print(f"        -> InserSup '{ex['insersup_etab']}' / {ex['insersup_type']} / {ex['insersup_discipline']} = {ex['salaire']}€ net {ex['horizon']} (promo {ex['cohorte']})")

    print("\n[3] Enrichissement doctorat (insertion_pro depuis salaire top-level)…")
    n_doc = _enrich_doctorat(fiches)
    print(f"  fiches doctorat enrichies: {n_doc}")

    total = metrics["n_enriched"] + n_doc
    n_salary_total = sum(
        1 for f in fiches if isinstance(f, dict)
        and isinstance(f.get("insertion_pro"), dict)
        and f["insertion_pro"].get("salaire_median_embauche") is not None
    )
    print(f"\n=== COUVERTURE SALAIRE après enrichissement ===")
    print(f"  nouvellement enrichies : {total} (InserSup {metrics['n_enriched']} + doctorat {n_doc})")
    print(f"  fiches avec salaire_median_embauche au total : {n_salary_total}")

    if not apply:
        print("\n--- DRY-RUN (aucune écriture). --apply pour migrer. ---")
        return

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = FICHES.with_suffix(f".json.bak-presalary-{ts}")
    shutil.copy2(FICHES, backup)
    FICHES.write_text(json.dumps(fiches, ensure_ascii=False, indent=2))
    print(f"\nbackup : {backup}")
    print(f"écrit  : {FICHES}")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
