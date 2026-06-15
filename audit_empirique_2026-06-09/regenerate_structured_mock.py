"""Regenere le mock contrat front structured.json (ordre iter1 A1/A2).

Genere 1 exemple par format (recits representatifs) avec le code A1 (map sources
+ vraies URLs) et A2 (shortlist classee par critere annonce). Capture
pipe.last_narrative_structured (qui porte desormais `sources` + url resolues) et
ecrit gate_narrative_forme_structured.json = le contrat fige contre lequel le
sous-agent front build.

Usage : python audit_empirique_2026-06-09/regenerate_structured_mock.py
"""
from __future__ import annotations

import json
import time

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline

FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
SEED_PATH = "data/recits_seed.json"
OUT = "audit_empirique_2026-06-09/results/gate_narrative_forme_structured.json"

# 1 recit representatif par format (les T inline + R09 seed pour conseil).
T = {
    "T1": ("Je suis en terminale generale (spe maths et SES) a Toulouse, j'ai de bonnes notes "
           "mais honnetement je n'ai aucune idee de ce que je veux faire apres le bac. J'aime "
           "comprendre l'economie et la societe, je suis a l'aise a l'oral, mais je ne me vois pas "
           "faire 5 ans d'etudes tres theoriques. Je voudrais rester dans le Sud. Qu'est-ce qui pourrait me correspondre ?"),
    "T2": ("Je suis en terminale STMG a Lyon, admise sur Parcoursup a la fois en BUT GEA et en BTS "
           "Comptabilite-Gestion. Je n'arrive pas a choisir. Je veux travailler assez vite mais sans me "
           "fermer de portes si je veux continuer en ecole apres. Lequel est le mieux pour moi ?"),
    "T3": ("Je suis en L2 de droit a Lille mais je m'ennuie et les debouches me font peur. J'avais pris "
           "l'option NSI au lycee et le code m'avait beaucoup plu. J'aimerais basculer vers le developpement "
           "ou la data, mais j'ai peur d'avoir perdu deux annees pour rien et mes parents s'inquietent pour "
           "le salaire. Je suis bloque a Lille. Comment je peux faire la transition ?"),
    "T4": ("Je suis en terminale generale avec les spes maths et NSI, j'ai 15 de moyenne, et je pense "
           "candidater en MIAGE apres une licence d'informatique. J'aime les maths appliquees et l'idee de "
           "faire le pont entre l'informatique et la gestion d'entreprise, mais je n'aime pas du tout le "
           "developpement web pur toute la journee. Est-ce que MIAGE c'est un bon choix pour mon profil ?"),
    "T7": ("Je suis en terminale generale avec les spes maths et SVT a Bordeaux, 16 de moyenne, et je veux "
           "faire une ecole d'ingenieur post-bac plutot dans le biomedical ou les biotechnologies. J'ai deja "
           "pas mal reflechi, je connais mon projet. Donne-moi juste les meilleures ecoles d'inge post-bac en "
           "bio/sante que je devrais viser, pas besoin de tout m'expliquer."),
}
# format cible -> recit
TARGETS = [
    ("exploratoire", "T1", T["T1"]),
    ("comparaison", "T2", T["T2"]),
    ("trajectoire", "T3", T["T3"]),
    ("validation", "T4", T["T4"]),
    ("shortlist", "T7", T["T7"]),
    ("conseil", "R09", None),  # R09 depuis seed
]


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)
    fiches = json.load(open(FICHES_PATH, encoding="utf-8"))
    seed = {r["id"]: r["text"] for r in json.load(open(SEED_PATH, encoding="utf-8"))["recits"]}

    pipe = make_production_pipeline(
        client, fiches, enable_narrative_mode=True,
        enable_validator=False, enable_golden_qa=False, enable_post_process=False,
    )
    pipe.load_index_from(INDEX_PATH)
    try:
        pipe._build_double_subindices()
    except Exception:
        pass
    pipe.warmup_generation()

    out: dict[str, dict] = {}
    for fmt, rid, text in TARGETS:
        text = text or seed.get(rid, "")
        pipe.last_narrative_structured = None
        t0 = time.time()
        try:
            pipe.answer(text)
        except Exception as e:
            print(f"  {fmt}/{rid}: ERROR {type(e).__name__}: {e}")
            continue
        st = pipe.last_narrative_structured
        got_fmt = st.get("format") if st else "?"
        n_src = len(st.get("sources", [])) if st else 0
        n_url = sum(1 for s in (st.get("sources", []) if st else []) if s.get("url"))
        if st:
            st["_example_recit"] = rid
            out[got_fmt] = st  # cle = format reellement route
        print(f"  {fmt}/{rid} -> routed={got_fmt} sources={n_src} (url reelles={n_url}) "
              f"conf={st.get('parse_confidence') if st else None} ({time.time()-t0:.1f}s)")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(f"\nEcrit {OUT} : formats = {list(out.keys())}")


if __name__ == "__main__":
    main()
