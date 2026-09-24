"""Banc E, juge à l'aveugle qui voit les fiches (protocole results/banc_e/PROTOCOLE.md v0.3, section 5).

    python -m src.eval.juge_e preparer --generation 1     # lots anonymisés de 6 tâches + label_mapping.json
    python -m src.eval.juge_e collecter                    # verdicts -> judge/verdicts.jsonl

Même juge que D (agent juge-aveugle, claude -p, Opus 5.5 effort low, abonnement), même rubrique, même
`build_prompt`, même aveugle. Seul ajout : après le prompt de D, une phrase d'accompagnement et le contenu des
8 fiches exposées rendu en carte B complète, identique pour toutes les combinaisons d'une même conversation.
Lots de 6 tâches (les fiches font 55 k caractères par tâche en médiane).
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from src.eval import juge_d as jd
from src.eval.battery.judge import RUBRIC, parse_verdict, valid_scores

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "results/banc_e"
JUGE = SORTIE / "judge"
TAILLE_LOT = 6

PHRASE_JUGE = ("Les fiches ci-dessous sont les données officielles montrées à l'assistant. Un chiffre ou un fait "
               "qui les contredit est une erreur factuelle. Une information absente des fiches n'est pas une "
               "erreur en soi : juge-la sur tes connaissances.")


def prompt_juge(rec: dict, item: dict, formations: dict[str, dict], cartes: dict[str, str]) -> str:
    """Prompt de D inchangé, suivi de la phrase et du contenu des fiches exposées (même ordre que l'exposition)."""
    corps = "\n\n".join(cartes[i] for i in rec["exposees"])
    return (jd.prompt_juge(rec, item, formations)
            + f"\n\n{PHRASE_JUGE}\n\nCONTENU DES FICHES :\n{corps if corps else '(aucune fiche)'}")


def texte_lot(taches: list[dict]) -> str:
    """Le lot lu par le juge, en texte multiligne. Mesure du 24/09 (lots g1_lot_001 à 004) : en JSON, chaque prompt
    tient sur une seule ligne de 27 000 à 39 000 tokens, au-dessus des 25 000 que l'outil Read accepte par lecture ;
    les juges n'ont pu noter que 9 tâches sur 24. En texte, le juge lit par tranches de lignes. Contenu identique
    au JSON (rubrique et prompts mot pour mot)."""
    parties = [f"RUBRIQUE (consignes du juge, à appliquer telles quelles) :\n{RUBRIC}\n\n"
               f"TACHES : {len(taches)}, oid dans l'ordre : {', '.join(t['oid'] for t in taches)}\n"]
    for t in taches:
        parties.append(f"\n=== TACHE oid={t['oid']} ===\n{t['prompt']}\n=== FIN TACHE oid={t['oid']} ===\n")
    return "".join(parties)


def _cartes(ids: set[str]) -> dict[str, str]:
    from src.base_c.outils import Base
    from src.eval.format_d import Formats
    from src.eval.grille_d import BASE, CORPUS
    f = Formats(Base.ouvrir(BASE), json.loads(CORPUS.read_bytes()))
    return {i: f.carte_b(i) for i in sorted(ids)}


def preparer(generation: int, banc: dict, base_path: Path, graine: str, combinaisons: list[str] | None = None) -> dict:
    items = {i["id"]: i for i in banc["items"]}
    formations = jd._formations(base_path)
    recs = []
    for dossier in sorted((SORTIE / "runs").iterdir()):
        if combinaisons and dossier.name not in combinaisons:
            continue
        p = dossier / f"g{generation}.jsonl"
        recs += [(dossier.name, json.loads(x)) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    cartes = _cartes({i for _, r in recs for i in r["exposees"]})
    taches, mapping = [], {}
    for comb, rec in recs:
        if rec.get("erreur"):
            continue
        oid = jd.opaque(graine, f"{comb}|g{generation}", rec["id"], rec["turn"])
        mapping[oid] = {"combinaison": comb, "id": rec["id"], "turn": rec["turn"], "generation": generation}
        taches.append({"oid": oid, "prompt": prompt_juge(rec, items[rec["id"]], formations, cartes)})
    rng = random.Random(f"{graine}|g{generation}")
    rng.shuffle(taches)
    par_comb: dict[str, list[str]] = {}
    for t in taches:
        par_comb.setdefault(mapping[t["oid"]]["combinaison"], []).append(t["oid"])
    rejuges = set()
    for comb, oids in sorted(par_comb.items()):
        n = max(jd.MIN_REJUGE, round(jd.PART_REJUGEE * len(oids)))
        rejuges |= set(random.Random(f"{graine}|{comb}|g{generation}").sample(sorted(oids), min(n, len(oids))))
    lots = [taches[i:i + TAILLE_LOT] for i in range(0, len(taches), TAILLE_LOT)]
    relots = [t for t in taches if t["oid"] in rejuges]
    random.Random(f"{graine}|rejuge|g{generation}").shuffle(relots)
    relots = [relots[i:i + TAILLE_LOT] for i in range(0, len(relots), TAILLE_LOT)]
    (JUGE / "lots").mkdir(parents=True, exist_ok=True)
    for nom, groupe in (("lot", lots), ("rejuge", relots)):
        for k, lot in enumerate(groupe, 1):
            base = JUGE / "lots" / f"g{generation}_{nom}_{k:03d}"
            base.with_suffix(".json").write_text(json.dumps(
                {"rubrique": RUBRIC, "taches": lot}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            base.with_suffix(".txt").write_text(texte_lot(lot), encoding="utf-8")
    mp = JUGE / "label_mapping.json"
    ancien = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    mp.write_text(json.dumps({**ancien, **mapping}, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                  encoding="utf-8")
    (JUGE / f"rejuges_g{generation}.json").write_text(json.dumps(sorted(rejuges)) + "\n", encoding="utf-8")
    (JUGE / "seed.txt").write_text(graine + "\n", encoding="utf-8")
    return {"taches": len(taches), "lots": len(lots), "rejuges": len(rejuges), "lots_rejuge": len(relots)}


def collecter() -> dict:
    mapping = json.loads((JUGE / "label_mapping.json").read_text(encoding="utf-8"))
    out, illisibles = {}, []
    for passe in ("verdicts", "verdicts_rejuge"):
        for p in sorted((JUGE / passe).glob("*.json")) if (JUGE / passe).exists() else []:
            v = parse_verdict(p.read_text(encoding="utf-8"))
            if not valid_scores(v):
                illisibles.append(f"{passe}/{p.name}")
                continue
            out.setdefault(passe, []).append({**mapping[p.stem], "oid": p.stem, **v})
    for passe, lignes in out.items():
        (JUGE / f"{passe}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lignes),
                                             encoding="utf-8")
    return {"verdicts": len(out.get("verdicts", [])), "rejuges": len(out.get("verdicts_rejuge", [])),
            "illisibles": illisibles}


def main(argv: list[str] | None = None) -> int:
    from src.eval.exposition_d import BANC
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preparer")
    p.add_argument("--generation", type=int, default=1)
    p.add_argument("--graine", default="banc-e-2026-09-24")
    p.add_argument("--combinaisons", default="", help="liste séparée par des virgules (g2) ; vide = toutes")
    sub.add_parser("collecter")
    args = ap.parse_args(argv)
    if args.cmd == "preparer":
        r = preparer(args.generation, json.loads(BANC.read_bytes()), RACINE / "data/processed/base_etape_c.sqlite",
                     args.graine, [c for c in args.combinaisons.split(",") if c] or None)
    else:
        r = collecter()
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
