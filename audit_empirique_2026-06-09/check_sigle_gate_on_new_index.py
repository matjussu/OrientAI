"""Check gate J2 sigle sur le NOUVEL index re-embeddé (ordre 0825, avant re-gel).

Question (Jarvis) : le re-embed active l'injection sigle (dense) parkée par
arbitrage zéro-régression. Les déplacements LAS Cergy / MIAGE Paris du gate J2
se REPRODUISENT-ils sur l'index actuel ? Les 6+ gains sigles tiennent-ils ?

Méthode : retrieval hybride PROD (_retrieve_and_filter, BM25 injection ON des deux
côtés = état du gel battery 11/06) sur index gel backupé (dense SANS sigle) vs
nouvel index (dense AVEC sigle + debouches #146 + salaire). On isole l'effet du
re-embed dense sur les cas du gate. Rang de la fiche cible dans le top-10.
Gratuit hors embed des requêtes (~centimes).

Usage:
    PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/check_sigle_gate_on_new_index.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import src.observability  # noqa: F401
from mistralai.client import Mistral
from src.rag.factory import make_production_pipeline
from src.rag.intent import classify_domain_hint

REPO = Path(__file__).resolve().parent.parent
GEL_INDEX = str(REPO / "data/embeddings/formations.index.gel-bak-pre-reembed-20260612")
NEW_INDEX = str(REPO / "data/embeddings/formations.index")
FICHES = REPO / "data/processed/formations.json"

SIG = [("GEA", "Aubière", "gestion des entreprises et des administrations"),
       ("GEII", "Montluçon", "génie électrique et informatique"),
       ("GMP", "Montluçon", "génie mécanique et productique"),
       ("MMI", "Vichy", "multimédia et de l'"),
       ("GACO", "Morlaix", "gestion administrative et commerciale"),
       ("GCGP", "Périgueux", "génie chimique génie des procédés"),
       ("HSE", "Vesoul", "hygiène sécurité environnement"),
       ("CJ", "SAINT MARTIN D'H", "carrières juridiques"),
       ("LAS", "Cergy", "licence accès santé"),
       ("MIAGE", "PARIS", "méthodes informatiques appliquées")]
CTRL = [("BTS info Lille", "taux d'accès BTS SIO à Lille",
         lambda f: "sio" in _low(f, 'nom') or ("bts" in _low(f, 'nom') and "informatiques" in _low(f, 'nom'))),
        ("Licence droit Lyon", "taux d'accès licence droit à Lyon",
         lambda f: "droit" in _low(f, 'nom') and "lyon" in _low(f, 'ville')),
        ("Master psycho Paris", "taux d'accès master psychologie à Paris",
         lambda f: "psycho" in _low(f, 'nom') and "paris" in _low(f, 'ville'))]


def _low(f, *ks):
    return " ".join(str(f.get(k) or "") for k in ks).lower()


def _rank(rr, pred, k=10):
    for i, r in enumerate(rr[:k]):
        if pred(r.get("fiche", {})):
            return i + 1
    return None


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
    fiches = json.loads(FICHES.read_text())
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    def hy_for(index_path):
        p = make_production_pipeline(client, fiches)
        p.load_index_from(index_path)
        return lambda q: p._retrieve_and_filter(
            question=q, k=30, domain_hint=classify_domain_hint(q), target=10, criteria=None)

    hy_gel = hy_for(GEL_INDEX)   # dense SANS sigle (état baseline figée)
    hy_new = hy_for(NEW_INDEX)   # dense AVEC sigle + tout l'accumulé

    print(f"{'cas':20s} {'GEL':6s} {'NEW':6s} verdict")
    gains = 0
    displacements = []
    for sig, ville, key in SIG:
        pred = lambda f, key=key, ville=ville: key in _low(f, "nom") and ville.lower() in _low(f, "ville")
        q = f"taux d'accès BUT {sig} à {ville}"
        rg, rn = _rank(hy_gel(q), pred), _rank(hy_new(q), pred)
        if rg == rn:
            v = "="
        elif rn and (not rg or rn < rg):
            v = "GAIN"
            gains += 1
        else:
            v = "REGRESSION/DÉPLACEMENT"
            displacements.append((sig, ville, rg, rn))
        print(f"{sig+' '+ville:20s} {str(rg):6s} {str(rn):6s} {v}")

    print("--- CONTRÔLE (sans sigle, doit être stable) ---")
    ctrl_reg = []
    for label, q, pred in CTRL:
        rg, rn = _rank(hy_gel(q), pred), _rank(hy_new(q), pred)
        v = "=" if rg == rn else ("GAIN" if (rn and (not rg or rn < rg)) else "REGRESSION")
        print(f"{label:20s} {str(rg):6s} {str(rn):6s} {v}")
        if v == "REGRESSION":
            ctrl_reg.append((label, rg, rn))

    print("\n=== SYNTHÈSE gate J2 sur nouvel index ===")
    print(f"  gains sigles (rang amélioré) : {gains}/10")
    las = next((d for d in displacements if d[0] == "LAS"), None)
    miage = next((d for d in displacements if d[0] == "MIAGE"), None)
    print(f"  LAS Cergy déplacé ?   {'OUI '+str(las[2])+'→'+str(las[3]) if las else 'NON (stable)'}")
    print(f"  MIAGE Paris déplacé ? {'OUI '+str(miage[2])+'→'+str(miage[3]) if miage else 'NON (stable)'}")
    print(f"  autres déplacements : {[d[0] for d in displacements if d[0] not in ('LAS','MIAGE')]}")
    print(f"  régressions contrôle : {'AUCUNE' if not ctrl_reg else ctrl_reg}")


if __name__ == "__main__":
    main()
