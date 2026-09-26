"""Étalonnage du détecteur d'absence (CONTRAT-etape4, section 6.2, choix D5), sur le banc lot 0 SEULEMENT.

Lit les brouillons et réponses du lot 0 de l'étape 3 (v2, et prod de la référence figée), sans appel d'API, et liste
chaque déclenchement de `src.v2.verificateur.absences`. Le verdict de chaque déclenchement (vraie absence de formation
ou non) est une lecture humaine, écrite dans VERDICTS ci-dessous avec sa raison ; la précision en découle. Le vertical
et le gate F ne sont jamais lus ici (règle de décision, section 11). Depuis la racine du dépôt :
    python3 docs/cerveau/etape4/mesures/etalonnage_absence.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RACINE))
from src.v2 import verificateur as vf  # noqa: E402

SOURCES = {"v2": RACINE / "results/multiversion/2026-09-25_v2/v2__lot0.jsonl",
           "prod": RACINE / "results/multiversion/2026-09-25_reference/prod__lot0.jsonl"}
# (version, id, tour) -> (vraie absence ?, raison). Lecture du 26/09, lexique final.
VERDICTS = {
    ("v2", "E07", 0): (True, "affirme qu'aucune formation ne correspond (recherche vide)"),
    ("v2", "E02", 0): (True, "affirme qu'aucun master IA n'existe près de Lyon"),
    ("prod", "L18", 0): (False, "« aucune mention de prépa obligatoire » : pas une absence de formation"),
    ("prod", "E15", 0): (True, "affirme qu'aucune licence pro n'apparaît"),
}


def main() -> dict:
    lignes = []
    for version, chemin in SOURCES.items():
        for l in open(chemin):
            r = json.loads(l)
            tr = r.get("trace") or {}
            for i, b in enumerate(tr.get("brouillons") or [r["answer"]]):
                for ph in vf.absences(b):
                    cle = (version, r["id"], r["turn"])
                    verdict = VERDICTS.get(cle)
                    lignes.append({"version": version, "id": r["id"], "tour": r["turn"], "brouillon": i, "phrase": ph,
                                   "condition": vf.motif_incomplet(tr.get("outils", [])) if tr else None,
                                   "vraie_absence": verdict[0] if verdict else None,
                                   "raison": verdict[1] if verdict else "NON LU"})
    lus = [x for x in lignes if x["vraie_absence"] is not None]
    out = {"banc": "lot0", "declenchements": len(lignes), "lus": len(lus),
           "vraies_absences": sum(x["vraie_absence"] for x in lus),
           "precision": round(sum(x["vraie_absence"] for x in lus) / len(lus), 3) if lus else None,
           "seuil_D5": 0.95, "lignes": lignes}
    Path(__file__).with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return out


if __name__ == "__main__":
    o = main()
    print({k: v for k, v in o.items() if k != "lignes"})
