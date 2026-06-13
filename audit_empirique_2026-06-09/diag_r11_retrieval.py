"""Diag R11 : structure des fiches retournées + rang de MIAGE Lille.

Isole le retrieval de answer(). Répond à 2 questions :
1. quelle est la STRUCTURE d'une fiche retournée (pourquoi [?] dans le gate) ?
2. la fiche MIAGE Lille est-elle retrievable par la requête forgée, à quel rang ?
"""
from __future__ import annotations

import json
import unicodedata

from mistralai.client import Mistral

from src.config import load_config
from src.rag.retriever import retrieve_top_k
from src.rag.index import load_index


def unwrap(r):
    # retrieve_top_k retourne {'fiche', 'score', 'base_score', 'embedding'}.
    return r.get("fiche", r) if isinstance(r, dict) else r


def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c)).lower()


def blob(f):
    return _norm(" ".join(str(f.get(k, "")) for k in ("nom", "libelle_humain", "etablissement", "ville", "region", "domaine", "text", "id")))


def is_ml(f):
    b = blob(f)
    return ("miage" in b or "methodes informatiques appliquees a la gestion" in b) and "lille" in b


def lab(f):
    return str(f.get("nom") or f.get("libelle_humain") or f.get("id") or "?")[:55]


def main():
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    fiches = json.load(open("data/processed/formations.json", encoding="utf-8"))
    index = load_index("data/embeddings/formations.index")

    # combien de MIAGE Lille dans le corpus + leurs index
    ml_idx = [i for i, f in enumerate(fiches) if is_ml(f)]
    print(f"MIAGE Lille dans corpus : {len(ml_idx)} (positions {ml_idx})")
    for i in ml_idx:
        f = fiches[i]
        print(f"  - pos {i}: {lab(f)} | etab={f.get('etablissement')} | retrieval_eligible={f.get('retrieval_eligible')} | source={f.get('source')}")

    query = "informatique gestion management MIAGE Hauts-de-France"
    print(f"\nRequête forgée R11 : {query!r}")
    res = retrieve_top_k(client, index, fiches, query, k=120)
    print(f"retrieve_top_k k=120 -> {len(res)} résultats")
    print(f"\nStructure résultat[0] : keys = {list(res[0].keys())[:25]}  (fiche nested sous 'fiche')")

    # rang MIAGE Lille (UNWRAP)
    rank = next((i + 1 for i, r in enumerate(res) if is_ml(unwrap(r))), None)
    print(f"\n==> MIAGE Lille rang dans retrieve brut (k=120) = {rank}")
    print("\nTop 12 retrieve brut :")
    for i, r in enumerate(res[:12]):
        f = unwrap(r)
        print(f"  {i+1}. {lab(f)} | etab={str(f.get('etablissement',''))[:30]} | ville={f.get('ville','')} | {'<== ML' if is_ml(f) else ''}")

    # variante : requête avec Lille + insertion explicites
    q2 = "master MIAGE methodes informatiques gestion entreprises Universite de Lille insertion salaire emploi"
    res2 = retrieve_top_k(client, index, fiches, q2, k=120)
    rank2 = next((i + 1 for i, r in enumerate(res2) if is_ml(unwrap(r))), None)
    print(f"\nVariante requête (+Lille +insertion) : MIAGE Lille rang = {rank2}")
    print(f"  q2 = {q2!r}")
    print("  top 6 variante:")
    for i, r in enumerate(res2[:6]):
        f = unwrap(r)
        print(f"    {i+1}. {lab(f)} | {str(f.get('etablissement',''))[:30]} {'<== ML' if is_ml(f) else ''}")


if __name__ == "__main__":
    main()
