"""Migration corpus déterministe — fix mapping ROME J11 (ordre 2026-06-11-1840).

Corrige, DANS LE CORPUS SERVI `data/processed/formations.json`, les formations
TRAVAIL SOCIAL (CESF, AES, éducateurs spécialisés...) mal classées domaine=sante
qui héritaient des 10 débouchés ROME médicaux J11xx (cf detresse-prec-007) :

    domaine: "sante" -> "social"
    debouches: [10 ROME médicaux J11xx] -> [débouchés ROME K* travail social]

Périmètre = prédicat déterministe `is_social_work_formation` (src/collect/merge.py),
identique à celui de la passe pipeline `reclassify_social_health` -> code et data
restent cohérents. Idempotente, réversible (backup horodaté).

IMPORTANT — stratégie baseline-safe (ordre 2026-06-11) :
- `debouches` et `domaine` sont DANS le texte embeddé FAISS. On NE ré-embedde PAS
  (opération >5$, gatée Matteo) : l'index figé reste byte-identique -> retrieval du
  gel 497q intact. Le contexte LLM (lu live depuis ce JSON par fact_card) reflète
  immédiatement la correction. Validation complète (ré-embed + re-run) = post-merge gaté.

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/migrate_social_debouches.py            # dry-run (défaut)
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/migrate_social_debouches.py --apply    # écrit + backup
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from src.collect.merge import is_social_work_formation
from src.collect.rome import get_debouches_for_domain

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"

MEDICAL_J_CODES = {
    "J1102", "J1103", "J1104", "J1201", "J1304",
    "J1401", "J1501", "J1502", "J1505", "J1506",
}


def _debouches_codes(f) -> set[str]:
    out = set()
    for d in (f.get("debouches") or []):
        if isinstance(d, dict):
            c = d.get("code_rome") or d.get("code")
            if c:
                out.add(c)
    return out


def main(apply: bool) -> None:
    fiches = json.loads(FICHES.read_text())
    social_debouches = get_debouches_for_domain("social")

    targets = [
        f for f in fiches
        if isinstance(f, dict)
        and f.get("domaine") == "sante"
        and is_social_work_formation(f.get("nom"))
    ]
    # combien portaient effectivement des débouchés médicaux
    with_medical = [f for f in targets if _debouches_codes(f) & MEDICAL_J_CODES]

    print(f"corpus            : {len(fiches)} fiches")
    print(f"domaine=sante     : {sum(1 for f in fiches if isinstance(f, dict) and f.get('domaine') == 'sante')}")
    print(f"cibles (sante + travail social) : {len(targets)}")
    print(f"  dont portant débouchés médicaux J11xx : {len(with_medical)}")
    print(f"débouchés sociaux appliqués : {[d['code_rome'] for d in social_debouches]}")

    # Témoin : la fiche CESF S3 de detresse-prec-007 (avant)
    cesf = next((f for f in targets if "conomie sociale familiale" in (f.get("nom") or "").lower()), None)
    if cesf:
        print("\n[témoin CESF S3 detresse-007] AVANT :")
        print(f"  domaine={cesf.get('domaine')} debouches={[d.get('code_rome') for d in (cesf.get('debouches') or [])]}")

    if not apply:
        print("\n--- DRY-RUN (aucune écriture). Relancer avec --apply pour migrer. ---")
        return

    # Backup horodaté
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = FICHES.with_suffix(f".json.bak-presocial-{ts}")
    shutil.copy2(FICHES, backup)
    print(f"\nbackup : {backup}")

    for f in targets:
        f["domaine"] = "social"
        f["debouches"] = [dict(d) for d in social_debouches]

    FICHES.write_text(json.dumps(fiches, ensure_ascii=False, indent=2))
    print(f"écrit  : {FICHES} ({len(targets)} fiches migrées sante→social)")

    if cesf:
        print("\n[témoin CESF S3 detresse-007] APRÈS :")
        print(f"  domaine={cesf.get('domaine')} debouches={[d.get('code_rome') for d in (cesf.get('debouches') or [])]}")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
