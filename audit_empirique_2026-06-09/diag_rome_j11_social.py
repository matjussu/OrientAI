"""Diagnostic ciblé — périmètre exact du bug mapping ROME J11 (ordre 2026-06-11-1840).

Mesure sur data/processed/formations.json (corpus servi en prod) :
- distribution `domaine`
- fiches portant des débouchés ROME médicaux J11xx (le "1733 fiches" du brief)
- sous-ensemble réellement TRAVAIL SOCIAL mal-classé (CESF, assistant social,
  éducateur, intervention sociale...) qui hérite à tort de débouchés médicaux
- inspection de la/les fiche(s) CESF (source S3 de detresse-prec-007)

Usage: PYTHONPATH=. .venv/bin/python audit_empirique_2026-06-09/diag_rome_j11_social.py
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"

# Les 10 codes ROME médicaux J11xx/J1xxx injectés par get_debouches_for_domain("sante")
MEDICAL_J_CODES = {
    "J1102", "J1103", "J1104", "J1201", "J1304",
    "J1401", "J1501", "J1502", "J1505", "J1506",
}

# Heuristique "travail social" sur le nom de la fiche (NSF 332).
SOCIAL_NAME_PAT = re.compile(
    r"\b("
    r"conseiller.{0,4}en.{0,4}[ée]conomie\s+sociale|cesf|"
    r"[ée]conomie\s+sociale\s+et\s+familiale|"
    r"assistant.{0,4}(de\s+)?service\s+social|service\s+social|"
    r"[ée]ducateur\s+(sp[ée]cialis[ée]|de\s+jeunes\s+enfants|technique)|"
    r"travail\s+social|intervention\s+social|m[ée]diation\s+social|"
    r"accompagnant\s+[ée]ducatif|moniteur.{0,4}[ée]ducateur|"
    r"animation\s+social|d[ée]veloppement\s+social|aide\s+sociale|"
    r"\bdeass\b|\bdeES\b|\beje\b|\bdecesf\b"
    r")",
    re.IGNORECASE,
)


def debouches_codes(f) -> set[str]:
    out = set()
    for d in (f.get("debouches") or []):
        if isinstance(d, dict):
            c = d.get("code_rome") or d.get("code")
            if c:
                out.add(c)
    return out


def get_codes_nsf(f) -> list[str]:
    out = []
    for nsf in (f.get("codes_nsf") or []):
        c = nsf.get("code") if isinstance(nsf, dict) else str(nsf)
        if c:
            out.append(c)
    return out


def main():
    fiches = json.loads(FICHES.read_text())
    n = len(fiches)
    print(f"corpus: {n} fiches\n")

    # 1. domaine distribution
    dom = collections.Counter(
        (f.get("domaine") or "(none)") for f in fiches if isinstance(f, dict))
    print("=== domaine distribution ===")
    for d, c in dom.most_common():
        print(f"  {d:28s} {c}")

    # 2. fiches with medical J-codes in debouches
    medical = [f for f in fiches if isinstance(f, dict) and (debouches_codes(f) & MEDICAL_J_CODES)]
    print(f"\n=== fiches avec débouchés ROME médicaux J11xx : {len(medical)} ===")
    print("  par domaine:",
          dict(collections.Counter(f.get("domaine") or "(none)" for f in medical)))
    print("  par source:",
          dict(collections.Counter(f.get("source") or "(none)" for f in medical).most_common(12)))

    # 3. sous-ensemble TRAVAIL SOCIAL mal-classé (nom matche social MAIS débouchés médicaux)
    mis = [f for f in medical if SOCIAL_NAME_PAT.search((f.get("nom") or ""))]
    print(f"\n=== sous-ensemble travail social mal-mappé (nom social + débouchés médicaux) : {len(mis)} ===")
    print("  par source:",
          dict(collections.Counter(f.get("source") or "(none)" for f in mis).most_common(12)))
    nsf_dist = collections.Counter()
    for f in mis:
        for c in get_codes_nsf(f):
            nsf_dist[c] += 1
    print("  codes_nsf présents sur ce sous-ensemble (top):", dict(nsf_dist.most_common(10)) or "AUCUN codes_nsf retenu sur fiche finale")

    print("\n  échantillon (jusqu'à 20 noms mal-mappés):")
    for f in mis[:20]:
        print(f"    - [{f.get('source')}] {(f.get('nom') or '')[:80]}  domaine={f.get('domaine')}")

    # 4. CESF spécifiquement
    cesf = [f for f in fiches if isinstance(f, dict) and re.search(
        r"[ée]conomie\s+sociale\s+et\s+familiale|cesf", (f.get("nom") or ""), re.IGNORECASE)]
    print(f"\n=== fiches CESF (économie sociale et familiale) : {len(cesf)} ===")
    for f in cesf[:6]:
        print(f"  nom: {f.get('nom')}")
        print(f"    source={f.get('source')} domaine={f.get('domaine')} niveau={f.get('niveau')}")
        print(f"    codes_nsf={get_codes_nsf(f)}")
        print(f"    debouches={[d.get('code_rome') or d.get('code') for d in (f.get('debouches') or [])]}")

    # 5. combien de NSF 332 dans tout le corpus (si codes_nsf retenu)
    has_332 = [f for f in fiches if isinstance(f, dict) and "332" in get_codes_nsf(f)]
    print(f"\n=== fiches avec codes_nsf contenant 332 (travail social) : {len(has_332)} ===")
    if has_332:
        print("  domaine de ces fiches:",
              dict(collections.Counter(f.get("domaine") or "(none)" for f in has_332)))


if __name__ == "__main__":
    main()
