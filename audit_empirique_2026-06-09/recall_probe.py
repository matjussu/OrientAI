"""Sonde de recall retrieval (proxy) - le retrieval trouve-t-il la bonne fiche ?

Pour des questions ciblant une formation/etablissement NOMME, on regarde si la
cible apparait dans le top-k retrieval. Proxy de recall@k sans set de
pertinence labellise complet (chantier futur). On mesure le lexical BM25
(deterministe, sans API) - complementaire du dense. Si meme BM25 ne trouve pas
une cible canonique, le probleme est data/index, pas generation.

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/recall_probe.py
"""
from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path

import src.observability  # noqa: F401
from mistralai.client import Mistral
from src.rag.factory import make_production_pipeline

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "audit_empirique_2026-06-09/results/recall_probe.json"
K = 30

# (question, termes-cible attendus dans une fiche pertinente)
PROBES = [
    ("BUT Informatique IUT Lyon 1 Villeurbanne", ["informatique", "lyon"]),
    ("BUT Informatique IUT de Bourges", ["informatique", "bourges"]),
    ("licence de droit Universite Paris-Dauphine", ["droit", "dauphine"]),
    ("INSA Lyon cycle ingenieur", ["insa", "lyon"]),
    ("BTS SIO SLAM", ["sio", "slam"]),
    ("prepa MPSI lycee du Parc Lyon", ["mpsi", "parc"]),
    ("licence psychologie", ["psychologie"]),
    ("BUT Techniques de Commercialisation IUT Annecy", ["commercialisation", "annecy"]),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _load_env():
    if os.environ.get("MISTRAL_API_KEY"):
        return
    for line in (REPO / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main():
    _load_env()
    fiches = json.loads((REPO / "data/processed/formations.json").read_text())
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    pipe = make_production_pipeline(client, fiches)
    pipe.load_index_from(str(REPO / "data/embeddings/formations.index"))

    out = []
    for q, terms in PROBES:
        try:
            cands = pipe._retrieve_with_bm25(q, k=K)
        except Exception as e:  # noqa: BLE001
            out.append({"q": q, "error": str(e)})
            print(f"{q[:45]:<46} ERROR {e}")
            continue
        # cherche une fiche dont nom+etab+ville contient TOUS les termes-cible
        hit_rank = None
        for i, c in enumerate(cands):
            f = c.get("fiche") if isinstance(c.get("fiche"), dict) else c
            blob = norm(" ".join(str(f.get(k, "")) for k in ("nom", "etablissement", "ville", "region")))
            if all(norm(t) in blob for t in terms):
                hit_rank = i + 1
                break
        out.append({"q": q, "terms": terms, "k": K, "hit_rank": hit_rank,
                    "found": hit_rank is not None, "n_cands": len(cands)})
        print(f"{q[:45]:<46} found={hit_rank is not None}  rank={hit_rank}  (n={len(cands)})")
    found = sum(1 for r in out if r.get("found"))
    print(f"\nBM25 recall@{K} (proxy, cible nommee): {found}/{len(PROBES)}")
    OUT.write_text(json.dumps({"k": K, "recall_proxy": f"{found}/{len(PROBES)}", "probes": out},
                              ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
