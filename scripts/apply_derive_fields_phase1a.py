"""Applique le fill type_diplome + région au corpus existant (Phase 1a, order 1230).

One-shot : applique derive_type_diplome + geocode_region à data/processed/
formations.json EN PLACE (backup .bak-pre-derive-AAAAMMJJ d'abord), SANS ré-embed.
Le chemin reproductible est le câblage dans run_merge_v3 (Stage 5.95) ; ce script
sert à mettre à jour le corpus déjà généré sans relancer un merge complet, comme
le fix ROME J11.

Usage : PYTHONPATH=. .venv/bin/python scripts/apply_derive_fields_phase1a.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.collect.derive_fields import derive_type_diplome, geocode_region

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"
BACKUP = REPO / "data/processed/formations.json.bak-pre-derive-20260614"


def _nonempty(v) -> bool:
    return bool(v and str(v).strip())


def _coverage(fiches):
    n = len(fiches)
    ps = [f for f in fiches if f.get("source") == "parcoursup"]
    mm = [f for f in fiches if f.get("source") == "monmaster"]
    elig = [f for f in fiches if f.get("retrieval_eligible")]
    td = sum(1 for f in fiches if _nonempty(f.get("type_diplome")))
    td_ps = sum(1 for f in ps if _nonempty(f.get("type_diplome")))
    td_mm = sum(1 for f in mm if _nonempty(f.get("type_diplome")))
    rg = sum(1 for f in elig if _nonempty(f.get("region")))
    return {
        "type_diplome_global_pct_vide": round(100 * (n - td) / n, 1),
        "type_diplome_parcoursup_pct_vide": round(100 * (len(ps) - td_ps) / len(ps), 1),
        "type_diplome_monmaster_pct_vide": round(100 * (len(mm) - td_mm) / len(mm), 1),
        "region_eligible_pct_vide": round(100 * (len(elig) - rg) / len(elig), 1),
    }


def main():
    fiches = json.loads(FICHES.read_text())
    before = _coverage(fiches)

    if not BACKUP.exists():
        shutil.copy2(FICHES, BACKUP)
        print(f"[backup] {BACKUP.name}")
    else:
        print(f"[backup] déjà présent : {BACKUP.name}")

    fiches = derive_type_diplome(fiches)
    fiches = geocode_region(fiches)
    after = _coverage(fiches)

    FICHES.write_text(json.dumps(fiches, ensure_ascii=False))

    print("\n=== Couverture AVANT -> APRÈS (% vide) ===")
    for k in before:
        print(f"  {k:38s} {before[k]:6.1f}% -> {after[k]:6.1f}%")


if __name__ == "__main__":
    main()
