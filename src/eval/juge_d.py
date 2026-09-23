"""Étape D, juge à l'aveugle par sous-agents (protocole §8, v0.1).

    python -m src.eval.juge_d preparer --generation 1     # lots anonymisés + label_mapping.json
    python -m src.eval.juge_d collecter                    # verdicts -> judge/verdicts.jsonl, par combinaison

Aucun appel d'API : les verdicts sont écrits par des sous-agents Claude Code (abonnement), qui lisent
chaque lot et écrivent un fichier par tour dans `judge/verdicts/<id_opaque>.json`.

- Même rubrique que le lot 0 : `RUBRIC` de src/eval/battery/judge.py, mot pour mot, et le même
  `build_prompt`, lu par le même `parse_verdict` / `valid_scores`.
- Aveugle : les 9 x 79 réponses sont mélangées (graine dans seed.txt), chacune reçoit un identifiant
  opaque ; la correspondance vit dans label_mapping.json, jamais dans un lot.
- Contexte neutre : les fiches passées au juge sont les titres des 8 fiches exposées, identiques pour les
  9 combinaisons (test octet pour octet) ; les appels d'outil du format C ne sont pas montrés.
- Rejugement : 20 % des tours (au moins 15 par combinaison), tirés avec la même graine, dans des lots
  séparés, jugés par d'autres sous-agents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from src.eval.battery.judge import RUBRIC, build_prompt, parse_verdict, valid_scores

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "results/donnee_etape_d"
JUGE = SORTIE / "judge"
TAILLE_LOT = 25
PART_REJUGEE = 0.20
MIN_REJUGE = 15


def opaque(graine: str, combinaison: str, id_: str, tour: int) -> str:
    return hashlib.sha256(f"{graine}|{combinaison}|{id_}|{tour}".encode()).hexdigest()[:10]


def fiches_neutres(ids: list[str], formations: dict[str, dict]) -> list[dict]:
    """Même contexte pour les 9 combinaisons : titre, établissement, ville et source de chaque fiche exposée."""
    return [{"titre": formations[i]["intitule"], "etablissement": formations[i]["etablissement"],
             "ville": formations[i]["commune"], "source": formations[i]["espace"]} for i in ids]


def prompt_juge(rec: dict, item: dict, formations: dict[str, dict]) -> str:
    return build_prompt({"persona": item["persona"], "tags": item["tags"], "question": rec["question"],
                         "history": rec["history"], "answer": rec.get("answer") or "",
                         "sources": fiches_neutres(rec["exposees"], formations)})


def _formations(base_path: Path) -> dict[str, dict]:
    import sqlite3
    con = sqlite3.connect(f"file:{base_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out = {r["id"]: dict(r) for r in con.execute(
        "SELECT f.id, f.intitule, f.etablissement, f.espace, l.commune FROM formation f "
        "LEFT JOIN lieu l ON l.id = f.id AND l.rang = 1")}
    con.close()
    return out


def preparer(generation: int, banc: dict, base_path: Path, graine: str) -> dict:
    items = {i["id"]: i for i in banc["items"]}
    formations = _formations(base_path)
    taches, mapping = [], {}
    for dossier in sorted((SORTIE / "runs").iterdir()):
        comb = dossier.name
        for ligne in (dossier / f"g{generation}.jsonl").read_text(encoding="utf-8").splitlines():
            rec = json.loads(ligne)
            if rec.get("erreur"):
                continue
            oid = opaque(graine, comb, rec["id"], rec["turn"])
            mapping[oid] = {"combinaison": comb, "id": rec["id"], "turn": rec["turn"], "generation": generation}
            taches.append({"oid": oid, "prompt": prompt_juge(rec, items[rec["id"]], formations)})
    rng = random.Random(graine)
    rng.shuffle(taches)
    # Rejugement : 20 % par combinaison, au moins MIN_REJUGE, même graine.
    par_comb: dict[str, list[str]] = {}
    for t in taches:
        par_comb.setdefault(mapping[t["oid"]]["combinaison"], []).append(t["oid"])
    rejuges = set()
    for comb, oids in sorted(par_comb.items()):
        n = max(MIN_REJUGE, round(PART_REJUGEE * len(oids)))
        rejuges |= set(random.Random(f"{graine}|{comb}").sample(sorted(oids), min(n, len(oids))))
    lots = [taches[i:i + TAILLE_LOT] for i in range(0, len(taches), TAILLE_LOT)]
    relots = [t for t in taches if t["oid"] in rejuges]
    random.Random(f"{graine}|rejuge").shuffle(relots)
    relots = [relots[i:i + TAILLE_LOT] for i in range(0, len(relots), TAILLE_LOT)]
    (JUGE / "lots").mkdir(parents=True, exist_ok=True)
    for nom, groupe in (("lot", lots), ("rejuge", relots)):
        for k, lot in enumerate(groupe, 1):
            (JUGE / "lots" / f"{nom}_{k:02d}.json").write_text(json.dumps(
                {"rubrique": RUBRIC, "taches": lot}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (JUGE / "label_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                             encoding="utf-8")
    (JUGE / "rejuges.json").write_text(json.dumps(sorted(rejuges)) + "\n", encoding="utf-8")
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
            m = mapping[p.stem]
            out.setdefault(passe, []).append({**m, "oid": p.stem, **v})
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
    p.add_argument("--graine", default="etape-d-2026-09-23")
    sub.add_parser("collecter")
    args = ap.parse_args(argv)
    if args.cmd == "preparer":
        r = preparer(args.generation, json.loads(BANC.read_bytes()), RACINE / "data/processed/base_etape_c.sqlite",
                     args.graine)
    else:
        r = collecter()
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
