"""Tests synthetiques de la rubrique juge (J3, etape 2) — valide answered_alternative_disclaimed
avant de figer la rubrique. Couvre les classes : honest_refusal, answered_grounded,
answered_alternative_disclaimed (relevant / weak-metrique / irrelevant-geo), metric_substitution
NON divulguee, et le garde-fou anti-gaming (chiffre fabrique -> answered_unsupported, JAMAIS
re-bucke en alternative).

Cout : ~7 appels Haiku temp=0 (centimes). Reproductible.

Usage : PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/test_rubric_synthetic.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_groundedness as jg  # noqa: E402
from anthropic import Anthropic  # noqa: E402


def src(**kw):
    return kw


CASES = [
    {
        "id": "syn-refusal",
        "question": "Quel est le taux d'acces du BTS MUC a Brest ?",
        "answer": "Je n'ai pas de formation pertinente dans mes sources pour cette question. "
                  "Je te suggere de verifier sur Parcoursup ou de prendre RDV au CIO le plus proche.",
        "sources": [],
        "expect_outcome": "honest_refusal",
        "expect_subst": False,
    },
    {
        "id": "syn-grounded",
        "question": "Quel est le taux d'acces du BTS SIO au Lycee La Martiniere a Lyon ?",
        "answer": "Le BTS SIO au Lycee La Martiniere a Lyon a un taux d'acces Parcoursup 2025 de 42 % [source S1].",
        "sources": [src(nom="BTS SIO", etablissement="Lycee La Martiniere", ville="Lyon",
                        taux_acces_parcoursup_2025=42.0)],
        "expect_outcome": "answered_grounded",
        "expect_subst": False,
    },
    {
        "id": "syn-alt-relevant",
        "question": "Quel est le taux d'acces sur Parcoursup pour licence MIASHS a Annecy ?",
        "answer": "Je n'ai pas de formation MIASHS a Annecy dans mes sources. Les licences MIASHS "
                  "disponibles en Auvergne-Rhone-Alpes sont a Grenoble (98 % [source S1]) et Lyon (78 % [source S2]). "
                  "Ces alternatives te conviennent-elles ?",
        "sources": [src(nom="Licence MIASHS", etablissement="Universite Grenoble Alpes", ville="Grenoble",
                        region="Auvergne-Rhone-Alpes", taux_acces_parcoursup_2025=98.0),
                    src(nom="Licence MIASHS", etablissement="Universite Lyon 2", ville="Lyon",
                        region="Auvergne-Rhone-Alpes", taux_acces_parcoursup_2025=78.0)],
        "expect_outcome": "answered_alternative_disclaimed",
        "expect_subst": False,
    },
    {
        "id": "syn-alt-weak-metric",  # cas-frontiere fact-013 : autre TYPE de metrique
        "question": "Quel est le salaire median a l'embauche pour licence STAPS a Lyon ?",
        "answer": "Le salaire median a l'embauche pour la licence STAPS n'est pas disponible dans mes sources. "
                  "En revanche, le taux d'emploi salarie a 6 mois est de 66 % et a 12 mois de 70 % [source S1].",
        "sources": [src(nom="Licence STAPS", ville="Lyon", taux_emploi_6mois=66.0, taux_emploi_12mois=70.0)],
        "expect_outcome": "answered_alternative_disclaimed",
        "expect_subst": False,
    },
    {
        "id": "syn-alt-irrelevant-geo",  # Papeete-pour-Nantes : fidele mais inutile
        "question": "Quel est le taux d'acces sur Parcoursup pour BTS Commerce international a Nantes ?",
        "answer": "Je n'ai pas de formation pertinente dans mes sources pour un BTS Commerce International a Nantes. "
                  "La seule fiche disponible concerne le BTS Services - Commerce International au Lycee La Mennais "
                  "a Papeete, avec un taux d'acces de 25 % [source S1].",
        "sources": [src(nom="BTS Services - Commerce International", etablissement="Lycee La Mennais",
                        ville="Papeete", departement="Polynesie francaise", taux_acces_parcoursup_2025=25.0)],
        "expect_outcome": "answered_alternative_disclaimed",
        "expect_subst": False,
    },
    {
        "id": "syn-substitution-undisclosed",  # donne une autre metrique SANS divulguer le manque
        "question": "Quel est le taux d'insertion professionnelle du BUT GEA a Tours ?",
        "answer": "Le BUT GEA a Tours a un taux d'acces Parcoursup de 35 % et propose 120 places [source S1].",
        "sources": [src(nom="BUT GEA", ville="Tours", taux_acces_parcoursup_2025=35.0, nombre_places=120)],
        "expect_outcome": "metric_substitution",
        "expect_subst": True,
    },
    {
        "id": "syn-fabricated-number",  # garde-fou anti-gaming : chiffre absent des sources
        "question": "Quel est le taux d'acces du BTS NDRC a Dijon ?",
        "answer": "Le BTS NDRC a Dijon a un taux d'acces Parcoursup 2025 de 58 % [source S1].",
        "sources": [src(nom="BTS NDRC", ville="Dijon", taux_acces_parcoursup_2025=41.0)],
        "expect_outcome": "answered_unsupported",
        "expect_subst": False,
    },
]


def main():
    jg._load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY manquant")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    n_pass = 0
    n_fail = 0
    for c in CASES:
        res = jg.judge_one(client, c)
        outcome = res.get("outcome")
        subst = bool(res.get("metric_substitution"))
        relevance = res.get("alternative_relevance")
        ok_outcome = outcome == c["expect_outcome"]
        ok_subst = subst == c["expect_subst"]
        # garde-fou : une alternative-disclaimed DOIT avoir une relevance non-nulle
        ok_rel = True
        if c["expect_outcome"] == "answered_alternative_disclaimed":
            ok_rel = relevance in ("relevant", "weak", "irrelevant")
        ok = ok_outcome and ok_subst and ok_rel
        n_pass += ok
        n_fail += not ok
        tag = "PASS" if ok else "FAIL"
        extra = f" relevance={relevance}" if outcome == "answered_alternative_disclaimed" else ""
        print(f"[{tag}] {c['id']:28s} outcome={outcome} (attendu {c['expect_outcome']}) "
              f"subst={subst}{extra}")
        if not ok:
            print(f"        notes: {res.get('notes','')[:160]}")

    print(f"\n{n_pass}/{len(CASES)} PASS, {n_fail} FAIL")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
