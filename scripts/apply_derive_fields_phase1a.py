"""Applique le fill type_diplome + région au corpus existant (Phase 1a, ordres 1230 + 1305).

One-shot : reconstruit data/processed/formations.json depuis le backup propre
(.bak-pre-derive-20260614), applique les passes derive_fields EN PLACE, SANS ré-embed.
Le chemin reproductible reste le câblage run_merge_v3 (Stage 5.95) ; ce script met à
jour le corpus déjà généré sans relancer un merge complet (comme le fix ROME J11).

Passes : derive_type_diplome (1230) + derive_rncp_professional_title (1305) + geocode_region.

Backfill : type_enregistrement (signal autoritaire rncp 1305) est ré-injecté sur les
fiches rncp depuis le raw rncp_certifications.json (join numero_fiche), car il était
droppé du corpus. Au prochain run_merge_v3, rncp_to_fiche le préserve nativement.

Usage : PYTHONPATH=. .venv/bin/python scripts/apply_derive_fields_phase1a.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.collect.derive_fields import (
    derive_lyceepro_insertion,
    derive_onisep_niveau,
    derive_rncp_professional_title,
    derive_type_diplome,
    geocode_region,
)

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"
BACKUP = REPO / "data/processed/formations.json.bak-pre-derive-20260614"
RAW_RNCP = REPO / "data/processed/rncp_certifications.json"


def _nonempty(v) -> bool:
    return bool(v and str(v).strip())


def _backfill_type_enregistrement(fiches):
    """Ré-injecte type_enregistrement sur les fiches rncp depuis le raw (join numero_fiche)."""
    raw = json.loads(RAW_RNCP.read_text())
    by_num = {str(r.get("numero_fiche") or "").strip(): r for r in raw
              if _nonempty(r.get("numero_fiche"))}
    n = 0
    for f in fiches:
        if f.get("source") == "rncp" and not _nonempty(f.get("type_enregistrement")):
            r = by_num.get(str(f.get("rncp") or "").strip())
            if r and _nonempty(r.get("type_enregistrement")):
                f["type_enregistrement"] = r["type_enregistrement"]
                n += 1
    return n


def _coverage(fiches):
    n = len(fiches)
    sub = lambda s: [f for f in fiches if f.get("source") == s]
    ps, mm, rncp = sub("parcoursup"), sub("monmaster"), sub("rncp")
    on, lp = sub("onisep"), sub("inserjeunes_lycee_pro")
    elig = [f for f in fiches if f.get("retrieval_eligible")]
    vide = lambda lst: round(100 * sum(1 for f in lst if not _nonempty(f.get("type_diplome"))) / max(1, len(lst)), 1)
    vide_k = lambda lst, k: round(100 * sum(1 for f in lst if not _nonempty(f.get(k))) / max(1, len(lst)), 1)
    return {
        "type_diplome_global_pct_vide": round(100 * sum(1 for f in fiches if not _nonempty(f.get("type_diplome"))) / n, 1),
        "type_diplome_parcoursup_pct_vide": vide(ps),
        "type_diplome_monmaster_pct_vide": vide(mm),
        "type_diplome_rncp_pct_vide": vide(rncp),
        "niveau_onisep_pct_vide": vide_k(on, "niveau"),
        "insertion_pro_lyceepro_pct_absent": round(100 * sum(1 for f in lp if not f.get("insertion_pro")) / max(1, len(lp)), 1),
        "region_eligible_pct_vide": round(100 * sum(1 for f in elig if not _nonempty(f.get("region"))) / max(1, len(elig)), 1),
    }


def main():
    if not BACKUP.exists():
        shutil.copy2(FICHES, BACKUP)
        print(f"[backup créé] {BACKUP.name}")
    # Reconstruit depuis le backup propre (idempotent, before/after net)
    fiches = json.loads(BACKUP.read_text())
    before = _coverage(fiches)

    n_bf = _backfill_type_enregistrement(fiches)
    print(f"[backfill] type_enregistrement ré-injecté sur {n_bf} fiches rncp")

    fiches = derive_type_diplome(fiches)
    fiches = derive_rncp_professional_title(fiches)
    fiches = derive_lyceepro_insertion(fiches)
    fiches = derive_onisep_niveau(fiches)
    fiches = geocode_region(fiches)
    after = _coverage(fiches)

    FICHES.write_text(json.dumps(fiches, ensure_ascii=False))

    print("\n=== Couverture AVANT -> APRÈS (% vide) ===")
    for k in before:
        print(f"  {k:38s} {before[k]:6.1f}% -> {after[k]:6.1f}%")


if __name__ == "__main__":
    main()
