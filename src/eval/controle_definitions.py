"""Contrôle des définitions de répartition (CONTRAT-etape4, section 7, choix D4 de Matteo, 10808). Déterministe.

Une famille de notions (même préfixe, ex. `part_acces_general`, `part_acces_techno`, `part_acces_pro`) dont les
valeurs d'une même fiche font 100 % à elles toutes est une RÉPARTITION : sa définition doit le dire (« parmi », « les
[...] font 100 % », « répartition »). Origine : la définition de « Accès des terminales » la lisait comme un taux par
série ; mesure du 26/09, les trois parts somment entre 97 et 103 sur 2 935 fiches Parcoursup sur 2 939.

Usage : `python -m src.eval.controle_definitions` (code de sortie 1 si une définition de répartition ne le dit pas).
Le paramètre `definitions` permet d'injecter d'autres textes (test de falsification, règle 9).
"""
from __future__ import annotations

import re
import sqlite3
import sys
from collections import defaultdict

from src.base_c import outils as bc

FAMILLES_MIN = 2          # au moins deux notions dans la famille
PART_FICHES = 0.95        # part des fiches complètes dont la somme tombe dans [97, 103]
DIT_REPARTITION = re.compile(r"\bparmi\b|font 100|répartition|repartition", re.IGNORECASE)


def familles(con: sqlite3.Connection) -> dict[str, list[str]]:
    """Notions en % regroupées par préfixe (tout sauf le dernier segment après « _ »)."""
    out: dict[str, list[str]] = defaultdict(list)
    for (champ,) in con.execute("SELECT champ FROM champ WHERE unite = '%' ORDER BY champ"):
        out[champ.rsplit("_", 1)[0]].append(champ)
    return {k: v for k, v in out.items() if len(v) >= FAMILLES_MIN}


def repartitions_mal_definies(con: sqlite3.Connection, definitions: dict[str, str] | None = None) -> list[dict]:
    defs = {r[0]: r[1] or "" for r in con.execute("SELECT champ, definition FROM champ")}
    defs.update(definitions or {})
    fautes = []
    for prefixe, champs in familles(con).items():
        sommes: dict[tuple[str, str], list[float]] = defaultdict(list)
        q = f"SELECT id, champ, session, valeur_num FROM valeur WHERE champ IN ({','.join('?' * len(champs))})"
        for id_, champ, session, valeur in con.execute(q, champs):
            if isinstance(valeur, (int, float)):
                sommes[(id_, session)].append(float(valeur))
        completes = [s for s in sommes.values() if len(s) == len(champs) and sum(s) > 0]
        if not completes:
            continue
        part = sum(97 <= sum(s) <= 103 for s in completes) / len(completes)
        if part >= PART_FICHES:
            for c in champs:
                if not DIT_REPARTITION.search(defs.get(c, "")):
                    fautes.append({"famille": prefixe, "champ": c, "part_fiches_a_100": round(part, 4),
                                   "fiches": len(completes), "definition": defs.get(c, "")})
    return fautes


def main() -> int:
    con = bc.Base.ouvrir().con
    fautes = repartitions_mal_definies(con)
    for f in fautes:
        print(f"{f['champ']} : répartition ({f['part_fiches_a_100']:.1%} de {f['fiches']} fiches à 100 %) mais la "
              f"définition ne le dit pas : {f['definition']!r}")
    print(f"{len(fautes)} définition(s) de répartition à corriger")
    return 1 if fautes else 0


if __name__ == "__main__":
    sys.exit(main())
