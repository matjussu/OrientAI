"""Mesure déterministe avant/après — fix order 2026-06-11 (Fix 1 + Fix 2).

Preuve PAR-QUESTION, sans appel LLM/juge (déterministe sur sources figées) :
pour chaque cas étiqueté du tail (gel 497q), on compare ce que le JUGE voyait
AVANT (sources stockées dans le gel) à ce qu'il verra APRÈS (ré-extraction du
corpus corrigé + instrument run_battery._extract_fiche corrigé).

Cas couverts (ordre 2026-06-11) :
  - detresse-prec-007 : Fix 1 (debouches médical J11xx -> social K*)
  - reconv-001 / reconv-004-v1 / malform-004-v1 : Fix 2 (voies_acces brut "Par
    expérience" -> dispositifs_reconversion "VAE" visible du juge)

Usage: PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/measure_social_vae_before_after.py
"""
from __future__ import annotations

import json
from pathlib import Path

from run_battery import _extract_fiche  # noqa: E402  (même dossier)

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
FICHES = json.loads((REPO / "data/processed/formations.json").read_text())
GEL = json.loads((HERE / "results/gel_battery.json").read_text())

CASES = ["detresse-prec-007", "reconv-001", "reconv-004-v1", "malform-004-v1"]


def find_record(battery, case_id):
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") == case_id:
                found.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(battery)
    return found[0] if found else None


def fiche_by_nom(nom):
    for f in FICHES:
        if isinstance(f, dict) and f.get("nom") == nom:
            return f
    return None


def debouches_codes(src):
    return [d.get("code_rome") or d.get("code") for d in (src.get("debouches") or [])
            if isinstance(d, dict)]


def main():
    for case_id in CASES:
        rec = find_record(GEL, case_id)
        print("=" * 78)
        print(f"CAS : {case_id}")
        if not rec:
            print("  (introuvable dans le gel)")
            continue
        q = rec.get("question", "")
        print(f"  Q: {q[:90]}")
        old_sources = rec.get("sources") or []

        for src in old_sources:
            nom = src.get("nom") or "(sans nom)"
            sid = src.get("id")
            old_deb = debouches_codes(src)
            old_voies = src.get("voies_acces")
            has_social_signal = bool(old_voies) and any(
                "expérience" in str(v).lower() or "formation continue" in str(v).lower()
                for v in (old_voies or [])
            )
            # ne montrer que les sources concernées par un des 2 fixes
            is_medical = any(c and c.startswith("J") for c in old_deb)
            if not (is_medical or has_social_signal):
                continue

            cur = fiche_by_nom(nom)
            after = _extract_fiche({"fiche": cur}) if cur else {}
            new_deb = debouches_codes(after)
            new_disp = after.get("dispositifs_reconversion")

            print(f"\n  [{sid}] {nom[:66]}")
            if is_medical:
                print(f"    Fix1 debouches AVANT (juge): {old_deb}")
                print(f"    Fix1 debouches APRÈS (juge): {new_deb}  domaine={after.get('domaine')}")
                print(f"      -> claim 'débouchés social/éducation' : "
                      f"{'SUPPORTÉ' if any(str(c).startswith('K') for c in new_deb) else 'toujours non'}")
            if has_social_signal:
                print(f"    Fix2 voies_acces brut (juge AVANT): {old_voies}")
                print(f"    Fix2 dispositifs_reconversion (juge APRÈS): {new_disp}")
                print(f"      -> claim 'accessible en VAE' : "
                      f"{'SUPPORTÉ (VAE visible)' if new_disp and 'VAE' in new_disp else 'toujours non'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
