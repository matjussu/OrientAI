"""python -m src.eval.multiversion run|juger|rapport ... (protocole results/multiversion/PROTOCOLE.md)."""
from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="joue une version sur un banc")
    r.add_argument("--version", required=True)
    r.add_argument("--banc", required=True, choices=["vertical", "lot0"])
    r.add_argument("--tag", required=True)
    r.add_argument("--limite", default="", help="ids de conversations séparés par des virgules (défaut : tout)")
    r.add_argument("--empreinte-prod", default="", help="URL /health : l'empreinte de la version doit y être égale")
    r.add_argument("--budget-tag", default="", help="registre de budget d'un autre tag (essai à blanc)")
    j = sub.add_parser("juger", help="prépare ou collecte le juge")
    j.add_argument("etape", choices=["preparer", "collecter", "lanceur"])
    j.add_argument("--tag", required=True)
    j.add_argument("--graine", default="multiversion-2026-09-25")
    j.add_argument("--bancs", default="vertical", help="bancs jugés, séparés par des virgules")
    j.add_argument("--dossier", default="judge", help="dossier du passage (judge_v2 pour un rejugement)")
    j.add_argument("--consigne-nommage", action="store_true", help="ajoute la consigne de nommage des chiffres (25/09)")
    p = sub.add_parser("rapport", help="critère 1, adossés, juge, coûts + export explorateur")
    p.add_argument("--tag", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "run":
        from src.eval.multiversion.lanceur import jouer
        from src.eval.multiversion.versions import charger
        attendue = None
        if a.empreinte_prod:
            import urllib.request
            attendue = json.load(urllib.request.urlopen(a.empreinte_prod, timeout=30))["provenance"]
        stats = jouer(charger(a.version), a.banc, a.tag, [x for x in a.limite.split(",") if x] or None,
                      empreinte_attendue=attendue, budget_tag=a.budget_tag or None)
        return 1 if stats["arret"] else 0
    if a.cmd == "juger":
        from src.eval.multiversion import juge
        r = {"preparer": lambda: juge.preparer(a.tag, a.graine, tuple(a.bancs.split(",")), a.dossier, a.consigne_nommage),
             "collecter": lambda: juge.collecter(a.tag, a.dossier),
             "lanceur": lambda: {"script": str(juge.lanceur_shell(a.tag, a.dossier))}}[a.etape]()
        print(json.dumps(r, ensure_ascii=False))
        return 0
    from src.eval.multiversion.export import exporter
    rapport = exporter(a.tag)
    print(json.dumps({k: {x: v[x] for x in ("n_tours", "erreurs_exec", "cout_usd", "latence_p90", "juge_moyenne_4",
                                              "critere1", "structured_part")}
                      for k, v in rapport["runs"].items()}, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
