"""Gate empirique 1c (mode récit) — retrieval + réponses brutes sur les 12 récits.

Critère de gate : pour R11, la fiche MIAGE Lille doit remonter dans le top.
Produit aussi les 12 réponses brutes (génération v4 actuelle ; le prompt
sectionné dédié arrive en 1d) pour le jugement humain en boucle de Jarvis.

Usage : python -m audit_empirique_2026-06-09.gate_narrative_1c
(ou via runpy ; nécessite l'index FAISS + Mistral key).
"""
from __future__ import annotations

import json
import time

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline
from src.rag.narrative_detect import narrative_signal
from src.rag.narrative_query import build_narrative_retrieval_query

FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
SEED_PATH = "data/recits_seed.json"
OUT_PATH = "audit_empirique_2026-06-09/results/gate_narrative_1c_retrieval.md"
TOP_SHOW = 8


import unicodedata


def unwrap(r: dict) -> dict:
    # retrieve/rerank renvoient {'fiche', 'score', 'base_score', 'embedding'} :
    # la vraie fiche est nichée sous 'fiche'. Robuste si déjà déballé.
    return r.get("fiche", r) if isinstance(r, dict) else r


def _norm(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c)
    ).lower()


def fiche_label(f: dict) -> str:
    f = unwrap(f)
    return str(
        f.get("nom")
        or f.get("libelle_humain")
        or f.get("libelle")
        or f.get("intitule")
        or (f.get("text", "")[:70])
    ).strip()


def fiche_domain(f: dict) -> str:
    f = unwrap(f)
    return str(f.get("domain") or f.get("source") or f.get("type_diplome") or "?")


def fiche_geo(f: dict) -> str:
    f = unwrap(f)
    return f"{f.get('etablissement','')} ({f.get('ville','')}/{f.get('region','')})".strip()


def _fiche_blob(f: dict) -> str:
    # MIAGE / Lille vivent dans nom + etablissement + ville + region, PAS dans text.
    f = unwrap(f)
    return _norm(
        " ".join(
            str(f.get(k, ""))
            for k in ("nom", "libelle_humain", "etablissement", "ville", "region", "domaine", "text")
        )
    )


def is_miage_lille(f: dict) -> bool:
    blob = _fiche_blob(f)
    # MIAGE = acronyme OU son expansion "methodes informatiques appliquees a la gestion".
    miage = "miage" in blob or "methodes informatiques appliquees a la gestion" in blob
    lille = "lille" in blob  # "Université de Lille" (campus Villeneuve d'Ascq)
    return miage and lille


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    print("Chargement corpus + index...")
    with open(FICHES_PATH, encoding="utf-8") as fh:
        fiches = json.load(fh)
    recits = json.load(open(SEED_PATH, encoding="utf-8"))["recits"]

    # Réponses BRUTES : validator / golden_qa / post_process OFF (on veut la
    # génération nue pour le jugement humain) ; scope ON (comportement
    # R06/R07/R08) ; narrative ON. Le prompt sectionné dédié arrive en 1d.
    pipe = make_production_pipeline(
        client,
        fiches,
        enable_narrative_mode=True,
        enable_validator=False,
        enable_golden_qa=False,
        enable_post_process=False,
    )
    pipe.load_index_from(INDEX_PATH)
    print(f"Pipeline prêt (narrative_mode={pipe.enable_narrative_mode}), {len(fiches)} fiches, {len(recits)} récits.")

    lines: list[str] = ["# Gate narratif 1c — retrieval + réponses brutes (12 récits)\n"]
    miage_rank = None

    for r in recits:
        rid, text = r["id"], r["text"]
        sig = narrative_signal(text)
        pipe.last_narrative_profile = None
        t0 = time.time()
        answer, top = pipe.answer(text)
        dt = time.time() - t0

        scope = pipe.last_scope_result.label if pipe.last_scope_result else "n/a"
        prof = pipe.last_narrative_profile
        rd = pipe.last_router_result

        lines.append(f"\n## {rid} ({r['type']}) — scope={scope} — {dt:.1f}s")
        lines.append(f"- narrative_detect: {sig.is_narrative} ({sig.reason})")
        lines.append(f"- expected_scope (seed): {r.get('expected_scope')}")

        if prof is not None:
            rq = build_narrative_retrieval_query(prof, text)
            lines.append(f"- profil: age={prof.age_group} edu={prof.education_level} intent={prof.intent_type} conf={prof.confidence}")
            lines.append(f"  sector={prof.sector_interest} region={prof.region} mobilite={prof.mobilite}")
            lines.append(f"  a_eviter={prof.a_eviter} contraintes={prof.contraintes}")
            lines.append(f"- requête forgée: `{rq}`")
            lines.append(f"- route sub_indexes: {rd.sub_indexes if rd else '?'} (criteria={rd.criteria if rd else '?'})")
            lines.append(f"- top {min(TOP_SHOW, len(top))}/{len(top)} fiches:")
            for i, f in enumerate(top[:TOP_SHOW]):
                mark = "  <== MIAGE LILLE" if is_miage_lille(f) else ""
                lines.append(f"    {i+1}. [{fiche_domain(f)}] {fiche_label(f)[:60]} | {fiche_geo(f)}{mark}")
            if rid == "R11":
                hit = next((i + 1 for i, f in enumerate(top) if is_miage_lille(f)), None)
                miage_rank = hit
                lines.append(f"- **R11 GATE: MIAGE Lille rang = {hit if hit else 'ABSENT'} (sur {len(top)})**")
        else:
            lines.append(f"- (branche narrative non prise — court-circuit scope={scope})")

        lines.append(f"\n### Réponse brute {rid}\n")
        lines.append(answer.strip())
        lines.append("\n---")
        print(f"  {rid}: scope={scope} top={len(top)} ({dt:.1f}s)")

    verdict = "PASS" if miage_rank else "FAIL"
    lines.insert(1, f"\n**GATE R11 (MIAGE Lille remonte) : {verdict}** (rang={miage_rank})\n")

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"\n=== GATE R11 : {verdict} (MIAGE Lille rang={miage_rank}) ===")
    print(f"Rapport: {OUT_PATH}")


if __name__ == "__main__":
    main()
