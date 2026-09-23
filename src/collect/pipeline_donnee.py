"""Une commande rejoue tout le pipeline de la donnée verticale (gate B du cahier des charges).

1. contrôle des empreintes des fichiers bruts contre le verrou (`src.collect.sources_officielles`) ;
2. étape A : `data/processed/formations.json` (référence prod, lu seulement) -> `formations_etape_a.json` ;
3. étape B-1 : `formations_etape_a.json` -> `formations_etape_b1.json`.

Chaque étape écrit son manifeste. Une empreinte divergente arrête tout avant la première écriture.

Usage :
    python -m src.collect.pipeline_donnee [--telecharger]
"""
from __future__ import annotations

import argparse
import sys

from src.collect import corpus_etape_a, corpus_etape_b, sources_officielles


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--telecharger", action="store_true", help="télécharge les bruts absents avant le contrôle")
    args = ap.parse_args(argv)

    controle = ["--telecharger"] if args.telecharger else []
    if sources_officielles.main(controle) != 0:
        print("Empreintes divergentes ou fichiers absents : pipeline arrêté avant toute écriture.", file=sys.stderr)
        return 1
    if corpus_etape_a.main([]) != 0:
        return 1
    return corpus_etape_b.main([])


if __name__ == "__main__":
    sys.exit(main())
