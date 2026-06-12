"""Diff de ciblage re-gel (3b-bis étape 2, ordre 0825).

Décide, par question des 497q, si on peut PORTER la réponse+jugement du gel ou
s'il faut RÉGÉNÉRER, sous le critère rigoureux de Jarvis :

  portable (c) = set de sources servies IDENTIQUE au gel
                 ET zéro fiche du set parmi les fiches MODIFIÉES depuis le gel.
  régénérer   = (a) set changé  OU  (b) set identique mais >=1 fiche modifiée
                (le fact_card lit le corpus LIVE : une fiche dont le salaire/
                 quartile/social a été posé APRÈS la génération du gel sert un
                 contexte différent même à retrieval identique).

Fiches modifiées = positions dont le vecteur a changé entre l'index gel backupé
et le nouvel index (embed Mistral déterministe -> vecteur changé <=> fiche_to_text
changé ; salaire+quartiles+social sont dans fiche_to_text ET fact_card).

Gratuit hors embed des 497 requêtes (~centimes). N'écrit aucun fichier de gel.

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/regel_targeting_diff.py
"""
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

import src.observability  # noqa: F401
from mistralai.client import Mistral
from src.config import load_config
from src.rag.factory import make_production_pipeline
from src.eval.golden_ci import _retrieve_only

REPO = Path(__file__).resolve().parent.parent
GEL_INDEX = REPO / "data/embeddings/formations.index.gel-bak-pre-reembed-20260612"
NEW_INDEX = REPO / "data/embeddings/formations.index"
FICHES = REPO / "data/processed/formations.json"
GEL_BATTERY = REPO / "audit_empirique_2026-06-09/results/gel_battery.json"
OUT = REPO / "audit_empirique_2026-06-09/results/regel_targeting.json"


def _key(f: dict) -> tuple:
    """Identité stable d'une fiche (servie ou corpus)."""
    return (
        (f.get("nom") or "").strip().lower(),
        (f.get("etablissement") or "").strip().lower(),
        (f.get("ville") or "").strip().lower(),
    )


def main() -> None:
    # 1. Ensemble des fiches MODIFIÉES = positions à vecteur changé.
    gel = faiss.read_index(str(GEL_INDEX))
    new = faiss.read_index(str(NEW_INDEX))
    n = min(gel.ntotal, new.ntotal)
    d = np.linalg.norm(gel.reconstruct_n(0, n) - new.reconstruct_n(0, n), axis=1)
    modified_pos = set(int(i) for i in np.where(d >= 1e-6)[0])
    fiches = json.loads(FICHES.read_text())
    modified_ids = {_key(fiches[i]) for i in modified_pos}
    print(f"[modif] {len(modified_pos)} fiches modifiées (vecteur changé) -> "
          f"{len(modified_ids)} identités distinctes")

    # 2. Sources servies au gel, par question.
    battery = json.loads(GEL_BATTERY.read_text())
    gel_sources = {}
    for r in battery:
        srcs = r.get("sources") or []
        keys = []
        for s in srcs:
            f = s.get("fiche") if isinstance(s, dict) and "fiche" in s else s
            if isinstance(f, dict):
                keys.append(_key(f))
        gel_sources[r["id"]] = keys

    # 3. Retrieval-only sur le NOUVEL index, par question (eval = les 497 du gel).
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(NEW_INDEX))

    cat_a = cat_b = cat_c = 0          # set changé / set= mais modif / portable
    no_retrieval = 0                   # scope shortcut (pas de sources) -> portable
    detail = []
    for r in battery:
        qid = r["id"]
        gkeys = gel_sources.get(qid, [])
        if not gkeys:
            # court-circuit (urgent/oos/greeting) : contexte déterministe sans retrieval
            no_retrieval += 1
            cat_c += 1
            detail.append({"id": qid, "cat": "c", "reason": "no_retrieval_shortcut"})
            continue
        new_srcs = _retrieve_only(pipeline, r["question"])
        nkeys = [_key(s["fiche"]) for s in new_srcs if isinstance(s.get("fiche"), dict)]
        set_changed = set(gkeys) != set(nkeys)
        if set_changed:
            cat_a += 1
            detail.append({"id": qid, "cat": "a", "reason": "set_changed"})
        else:
            touched = [k for k in nkeys if k in modified_ids]
            if touched:
                cat_b += 1
                detail.append({"id": qid, "cat": "b", "reason": f"{len(touched)}_modif_in_set"})
            else:
                cat_c += 1
                detail.append({"id": qid, "cat": "c", "reason": "identical_unmodified"})

    total = len(battery)
    portables = cat_c
    regen = cat_a + cat_b
    OUT.write_text(json.dumps({
        "n_total": total,
        "n_modified_fiches": len(modified_pos),
        "a_set_changed": cat_a,
        "b_set_same_but_modified": cat_b,
        "c_portable": cat_c,
        "c_dont_no_retrieval_shortcut": no_retrieval,
        "n_portables": portables,
        "n_regen": regen,
        "pct_regen": round(100 * regen / total, 1),
        "detail": detail,
    }, ensure_ascii=False, indent=2))

    print(f"\n=== CIBLAGE RE-GEL (sur {total}q) ===")
    print(f"  (a) set changé              : {cat_a}")
    print(f"  (b) set= mais >=1 modifiée  : {cat_b}")
    print(f"  (c) PORTABLE (set= + 0 mod) : {cat_c}  (dont {no_retrieval} court-circuits sans retrieval)")
    print(f"  -> PORTABLES : {portables} | À RÉGÉNÉRER : {regen} ({100*regen/total:.1f}%)")
    print(f"  détail -> {OUT}")


if __name__ == "__main__":
    main()
