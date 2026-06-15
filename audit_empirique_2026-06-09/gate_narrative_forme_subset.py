"""Re-gen SUBSET après fixes A+B+C (ordre 1926) — récits affectés uniquement.

- B (troncature) : trajectoire R01, T3 (démo), R03 -> doivent finir « Premier pas »
  sans coupe ; truncated=False.
- A (options comparaison) : R05, R12 (refus complets avant) -> table partielle ;
  T2, T6 (déjà OK) -> non-régression. Reporte les options extraites.
- C (warmup) : on warm AVANT la boucle -> latences représentatives (pas de cold-start).

Usage : python audit_empirique_2026-06-09/gate_narrative_forme_subset.py
"""
from __future__ import annotations

import json
import sys
import time
import unicodedata

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline

FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
SEED_PATH = "data/recits_seed.json"
OUT_MD = "audit_empirique_2026-06-09/results/gate_narrative_forme_subset.md"
TOP_SHOW = 6

# Récits T réinjectés (texte = source Jarvis).
T = {
    "T2": ("Je suis en terminale STMG à Lyon, admise sur Parcoursup à la fois en BUT GEA et en BTS "
           "Comptabilité-Gestion. Je n'arrive pas à choisir. Je veux travailler assez vite mais sans "
           "me fermer de portes si jamais je veux continuer en école après. Lequel est le mieux pour moi ?"),
    "T3": ("Je suis en L2 de droit à Lille mais je m'ennuie et les débouchés me font peur. J'avais pris "
           "l'option NSI au lycée et le code m'avait beaucoup plu. J'aimerais basculer vers le développement "
           "ou la data, mais j'ai peur d'avoir perdu deux années pour rien et mes parents s'inquiètent pour "
           "le salaire. Je suis bloqué à Lille. Comment je peux faire la transition ?"),
    "T6": ("Je suis en terminale générale spé maths et physique à Rennes, j'ai un bon dossier. Je suis admis "
           "à la fois en prépa MPSI et en BUT Informatique, et je n'arrive vraiment pas à trancher. La prépa "
           "me fait un peu peur niveau rythme mais ça ouvre les écoles d'ingé, le BUT a l'air plus concret et "
           "plus court. Lequel correspond le mieux à quelqu'un qui veut devenir ingénieur sans se cramer ?"),
}
SUBSET = ["R01", "R03", "T3", "R05", "R12", "T2", "T6"]  # B (trajectoire) + A (comparaison)


def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c)).lower()


def unwrap(r):
    return r.get("fiche", r) if isinstance(r, dict) else r


def flabel(f):
    f = unwrap(f)
    return str(f.get("nom") or f.get("libelle_humain") or f.get("text", "")[:55]).strip()


def fgeo(f):
    f = unwrap(f)
    return f"{f.get('etablissement','')} ({f.get('ville','')}/{f.get('region','')})"


def main():
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)
    fiches = json.load(open(FICHES_PATH, encoding="utf-8"))
    seed = {r["id"]: r["text"] for r in json.load(open(SEED_PATH, encoding="utf-8"))["recits"]}
    texts = {**seed, **T}
    ids = [a for a in sys.argv[1:] if a in texts] or SUBSET

    pipe = make_production_pipeline(
        client, fiches, enable_narrative_mode=True,
        enable_validator=False, enable_golden_qa=False, enable_post_process=False,
    )
    pipe.load_index_from(INDEX_PATH)
    print("Warmup (retrieval + génération)...")
    try:
        pipe._build_double_subindices()
    except Exception as e:
        print("  warmup retrieval skip:", e)
    pipe.warmup_generation()
    print("Warm. Génération du subset...")

    lines = ["# Re-gen SUBSET fixes A+B+C (ordre 1926)\n"]
    for rid in ids:
        text = texts[rid]
        t0 = time.time()
        try:
            answer, top = pipe.answer(text)
        except Exception as e:
            lines.append(f"\n## {rid} — ERROR {type(e).__name__}: {e}\n---")
            print(f"  {rid}: ERROR {e}")
            continue
        dt = time.time() - t0
        dec = pipe.last_narrative_format_decision
        struct = pipe.last_narrative_structured or {}
        opts = pipe.last_narrative_comparison_options
        fmt = dec.format if dec else "?"
        conf = struct.get("parse_confidence")
        trunc = struct.get("truncated")
        lines.append(f"\n## {rid} — format={fmt} — {dt:.1f}s")
        lines.append(f"- parse_confidence={conf} truncated={trunc}")
        if fmt == "comparaison":
            lines.append(f"- options extraites: {opts}")
            tbl = next((b.get("table") for b in struct.get("blocks", []) if b.get("table")), None)
            if tbl:
                lines.append(f"- comparison_table options={tbl['options']} critères={len(tbl['criteria'])}")
            else:
                lines.append("- comparison_table: ABSENT")
        lines.append(f"- top {min(TOP_SHOW,len(top))}/{len(top)}:")
        for i, f in enumerate(top[:TOP_SHOW]):
            lines.append(f"    {i+1}. {flabel(f)[:50]} | {fgeo(f)}")
        lines.append(f"\n### Réponse {rid}\n")
        lines.append((answer or "").strip())
        lines.append("\n---")
        with open(OUT_MD, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        print(f"  {rid}: fmt={fmt} conf={conf} trunc={trunc} opts={opts} ({dt:.1f}s)")

    print(f"\nRapport: {OUT_MD}")


if __name__ == "__main__":
    main()
