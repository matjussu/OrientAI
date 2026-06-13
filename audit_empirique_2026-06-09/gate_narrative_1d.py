"""Gate empirique 1d (mode récit) — retrieval + réponses SECTIONNÉES sur les 12 récits.

Identique au harnais 1c, mais la génération passe désormais par le prompt
SECTIONNÉ dédié (4 sections « rendu conseiller », max_tokens relevé, few-shot
récit) via la branche narrative_mode câblée en 1d. Produit le LOT brut des 12
réponses pour le jugement humain EN BLOC de Jarvis (pas de tuning per-case).

Critère de gate inchangé : pour R11, la fiche MIAGE Lille doit remonter dans le top.
Inclut le fix R02 (règle négation clarifier) : médecine doit sortir en a_eviter,
pas en secteur -> requête forgée sans médecine.

Usage : python audit_empirique_2026-06-09/gate_narrative_1d.py
(depuis la racine repo ; nécessite l'index FAISS + Mistral key).
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
OUT_PATH = "audit_empirique_2026-06-09/results/gate_narrative_1d_sectioned.md"
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
    # Timeout généreux : les générations sectionnées (max_tokens=1500) sont plus
    # longues que le contrat court v4 et peuvent dépasser le default httpx.
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)
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

    lines: list[str] = ["# Gate narratif 1d — retrieval + réponses SECTIONNÉES (12 récits)\n"]
    miage_rank = None
    miage_done = False
    errors: list[str] = []

    def _flush() -> None:
        # Écriture INCRÉMENTALE (ADR-015) : un timeout sur un récit ne doit pas
        # perdre tout le LOT. On réécrit le fichier après chaque récit.
        verdict = "PASS" if miage_rank else ("FAIL" if miage_done else "EN COURS")
        gate_line = f"\n**GATE R11 (MIAGE Lille remonte) : {verdict}** (rang={miage_rank})\n"
        out = [lines[0], gate_line] + lines[1:]
        with open(OUT_PATH, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))

    def _answer_with_retry(text: str, attempts: int = 3):
        # generate() appelle client.chat.complete sans retry : on encapsule ici
        # pour le harnais (timeouts Mistral transitoires sur gen longue).
        last_err = None
        for a in range(attempts):
            try:
                return pipe.answer(text), None
            except Exception as e:  # noqa: BLE001 — robustesse harnais : note + continue
                last_err = e
                print(f"    {type(e).__name__} (tentative {a + 1}/{attempts}), retry dans 4s...")
                time.sleep(4)
        return (None, []), last_err

    for r in recits:
        rid, text = r["id"], r["text"]
        sig = narrative_signal(text)
        pipe.last_narrative_profile = None
        t0 = time.time()
        (answer, top), err = _answer_with_retry(text)
        dt = time.time() - t0

        if err is not None:
            lines.append(f"\n## {rid} ({r['type']}) — ⚠️ GENERATION ERROR — {dt:.1f}s")
            lines.append(f"- échec après retries: {type(err).__name__}: {err}")
            lines.append("\n---")
            errors.append(rid)
            print(f"  {rid}: ERROR {type(err).__name__}")
            _flush()
            continue

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
                miage_done = True
                lines.append(f"- **R11 GATE: MIAGE Lille rang = {hit if hit else 'ABSENT'} (sur {len(top)})**")
        else:
            lines.append(f"- (branche narrative non prise — court-circuit scope={scope})")

        lines.append(f"\n### Réponse brute {rid}\n")
        lines.append(answer.strip())
        lines.append("\n---")
        print(f"  {rid}: scope={scope} top={len(top)} ({dt:.1f}s)")
        _flush()

    _flush()
    verdict = "PASS" if miage_rank else "FAIL"
    print(f"\n=== GATE R11 : {verdict} (MIAGE Lille rang={miage_rank}) ===")
    if errors:
        print(f"⚠️ Récits en erreur (à rejouer) : {', '.join(errors)}")
    print(f"Rapport: {OUT_PATH}")


if __name__ == "__main__":
    main()
