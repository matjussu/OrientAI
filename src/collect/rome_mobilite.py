"""ROME 4.0 (data.gouv ZIP) -> passerelles + RIASEC + flags transition, par code ROME.

Ordre 2026-06-14-1402. Données publiques Licence Ouverte (`data/raw/rome_4_0.zip`),
zéro auth. Enrichit la fact_card des fiches métier (`rome_api_v4`) avec le contenu
NOUVEAU de ROME 4.0 :
- passerelles (mobilités professionnelles) : trajectoires d'évolution/reconversion.
- RIASEC : profil d'intérêt du métier (Réaliste/Investigateur/Artistique/Social/
  Entreprenant/Conventionnel).
- flags transition : écologique (Vert/Brun/stratégique), numérique, démographique,
  métier réglementé, emploi cadre.

SKIP compétences/savoirs : déjà dans rome_api_v4 (competences_par_enjeu /
savoirs_par_categorie), redondant.

CONTRAINTE DURE : ces champs vont en fact_card UNIQUEMENT, JAMAIS dans
`fiche_to_text` (régression prouvée Run 5, ADR-033 ROME masking).
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Any

_MOBILITE = "unix_rubrique_mobilite_v460_utf8.csv"
_RIASEC = "unix_referentiel_code_rome_riasec_v460_utf8.csv"
_CODES = "unix_referentiel_code_rome_v460_utf8.csv"

_RIASEC_LABELS = {
    "R": "Réaliste", "I": "Investigateur", "A": "Artistique",
    "S": "Social", "E": "Entreprenant", "C": "Conventionnel",
}
_MAX_PASSERELLES = 8  # médiane 10/métier ; on cap pour ne pas alourdir la fact_card


def _read_csv(z: zipfile.ZipFile, name: str) -> list[dict]:
    data = z.read(name).decode("utf-8", errors="replace")
    first = data.splitlines()[0] if data else ""
    delim = ";" if first.count(";") >= first.count(",") else ","
    return list(csv.DictReader(io.StringIO(data), delimiter=delim))


def _transitions(row: dict) -> list[str]:
    """Labels transition non-neutres d'une ligne code_rome (skip 'Emploi Blanc'/N/vide)."""
    out: list[str] = []
    eco = (row.get("transition_eco") or "").strip()
    if eco and eco != "Emploi Blanc":
        out.append(eco)  # Emploi Vert / Emploi Brun / Emploi stratégique...
    if (row.get("transition_num") or "").strip() == "O":
        out.append("concerné par la transition numérique")
    if (row.get("transition_demo") or "").strip() == "O":
        out.append("concerné par la transition démographique")
    if (row.get("emploi_reglemente") or "").strip() == "O":
        out.append("métier réglementé")
    if (row.get("emploi_cadre") or "").strip() == "O":
        out.append("emploi cadre")
    return out


def _riasec_label(majeur: str, mineur: str) -> str | None:
    parts = []
    if majeur in _RIASEC_LABELS:
        parts.append(_RIASEC_LABELS[majeur])
    if mineur in _RIASEC_LABELS and mineur != majeur:
        parts.append(_RIASEC_LABELS[mineur])
    return " / ".join(parts) or None


def parse_rome_enrichment(zip_path: str | Path) -> dict[str, dict[str, Any]]:
    """{code_rome: {passerelles: [libellés], riasec: str|None, transitions: [str]}}.

    Déterministe : passerelles triées par numero_ordre, libellés humains (pas de codes).
    """
    z = zipfile.ZipFile(zip_path)
    codes = _read_csv(z, _CODES)
    lib = {r["code_rome"]: (r.get("libelle_rome") or "").strip()
           for r in codes if r.get("code_rome")}
    flags = {r["code_rome"]: _transitions(r) for r in codes if r.get("code_rome")}

    riasec: dict[str, str | None] = {}
    for r in _read_csv(z, _RIASEC):
        c = r.get("code_rome")
        if c:
            riasec[c] = _riasec_label((r.get("riasec_majeur") or "").strip(),
                                      (r.get("riasec_mineur") or "").strip())

    mob: dict[str, list[tuple[int, str]]] = {}
    for r in _read_csv(z, _MOBILITE):
        c, cible = r.get("code_rome"), r.get("code_rome_cible")
        if not c or not cible or cible == c:
            continue
        try:
            ordre = int(r.get("numero_ordre") or 999)
        except (ValueError, TypeError):
            ordre = 999
        mob.setdefault(c, []).append((ordre, cible))

    out: dict[str, dict[str, Any]] = {}
    for c in set(lib) | set(riasec) | set(mob):
        rec: dict[str, Any] = {}
        passerelles = [lib.get(t, t) for _, t in sorted(mob.get(c, []))[:_MAX_PASSERELLES]]
        passerelles = [p for p in passerelles if p]
        if passerelles:
            rec["passerelles"] = passerelles
        if riasec.get(c):
            rec["riasec"] = riasec[c]
        if flags.get(c):
            rec["transitions"] = flags[c]
        if rec:
            out[c] = rec
    return out


def attach_rome_enrichment(fiches: list[dict], enrichment: dict[str, dict]) -> int:
    """Pose rome_passerelles / rome_riasec / rome_transitions sur les fiches métier ROME.

    UNIQUEMENT source=rome_api_v4 (les fiches métier). Ne touche aucune autre source.
    Retourne le nombre de fiches enrichies. Idempotent.
    """
    n = 0
    for f in fiches:
        if not isinstance(f, dict) or f.get("source") != "rome_api_v4":
            continue
        rec = enrichment.get(f.get("code_rome"))
        if not rec:
            continue
        if rec.get("passerelles"):
            f["rome_passerelles"] = rec["passerelles"]
        if rec.get("riasec"):
            f["rome_riasec"] = rec["riasec"]
        if rec.get("transitions"):
            f["rome_transitions"] = rec["transitions"]
        n += 1
    return n
