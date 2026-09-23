"""Migration unique (23/09/2026) des labels partiels vers la cle `idx:<position>`.

Les labels du 16/07 designaient une fiche de trois facons :
  - `idx:N`   fiches sans champ `id` trouvees par le mode lexical : N est deja la position ;
  - `<id>`    valeur du champ `id` (ex. `metier:...`) : convertie via l'index id -> position,
              refusee si l'id est absent ou partage par plusieurs fiches ;
  - `idx:-1`  bug du miner (dense et bm25) : le juge a vu le resume (nom, etablissement, ville,
              source) du candidat `idx:-1` de la question ; la fiche est retrouvee par cette
              signature, refusee si elle est ambigue ou introuvable.
Mesure du 23/09 sur les 135 questions : 1 172 references, toutes resolues (608 par id unique,
485 deja en position, 79 idx:-1 par signature unique), 0 refusee.

Limite qui reste : le pool juge le 16/07 avait perdu les candidats dense/bm25 confondus en
`idx:-1` (il n'en gardait qu'un par question). Une fiche pertinente de ce pool perdu n'a jamais
ete jugee : le recall mesure sur ces labels est une borne basse.

Usage : PYTHONPATH=. python scripts/relevance_set/migrate_labels_idx.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.eval.battery.corpus import Corpus, fiche_key

LABELS = REPO / "scripts/relevance_set/labels_partial.json"
# Le pool juge le 16/07 : celui du commit c7402d3, pas le candidates.json re-mine apres le fix.
POOL_COMMIT = "c7402d3"


def main() -> None:
    corpus = Corpus()
    raw = json.loads(LABELS.read_text())
    if raw.get("_meta", {}).get("corpus_sha256"):
        sys.exit("labels deja migres")
    pool = json.loads(subprocess.run(
        ["git", "show", f"{POOL_COMMIT}:scripts/relevance_set/candidates.json"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout)
    judged_pool = {q["qid"]: q["candidates"] for q in pool}

    by_id = defaultdict(list)
    for i, f in enumerate(corpus.fiches):
        if f.get("id"):
            by_id[f["id"]].append(i)

    counts: Counter = Counter()
    migrated = []
    for q in raw["labels"]:
        relevant = []
        for ref in q["relevant"]:
            fid = ref["fiche_id"]
            if fid == "idx:-1":
                seen = next(c for c in judged_pool[q["qid"]] if c["fiche_id"] == "idx:-1")
                found = corpus.positions_by_signature(seen["nom"], seen["etablissement"], seen["ville"],
                                                      seen["source"])
                kind = "idx-1_signature"
            elif fid.startswith("idx:"):
                found, kind = [int(fid[4:])], "idx"
            else:
                found, kind = by_id.get(fid, []), "id"
            if len(found) != 1:
                counts[f"{kind}_refuse"] += 1
                continue
            counts[kind] += 1
            relevant.append({"fiche_id": fiche_key(found[0]), "grade": ref["grade"]})
        migrated.append({**q, "relevant": relevant})

    raw["labels"] = migrated
    raw["_meta"] = {**raw.get("_meta", {}), "corpus_sha256": corpus.sha256,
                    "cle": "idx:<position dans formations.json>",
                    "migration_2026-09-23": dict(counts),
                    "bug_connu": "corrige le 23/09 (migrate_labels_idx.py) ; recall = borne basse, cf docstring"}
    LABELS.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n")
    print(dict(counts))


if __name__ == "__main__":
    main()
