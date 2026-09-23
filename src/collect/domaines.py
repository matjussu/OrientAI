"""Classement des formations Parcoursup par domaine, par une table de correspondance relisible.

La table `data/reference/domaines_parcoursup.csv` est la référence : une règle par ligne,
évaluées dans l'ordre, la première qui s'applique gagne. Chaque règle porte un identifiant,
qui est écrit dans la fiche (`domaine_regle`) : on peut toujours dire pourquoi une formation
est dans son domaine.

Une règle combine trois critères, `*` signifiant « indifférent » :
- `fili`     : filière très agrégée Parcoursup (BUT, BTS, PASS...), égalité exacte ;
- `filiere`  : filière de formation Parcoursup (`form_lib_voe_acc`), expression régulière ;
- `intitule` : intitulé de la formation (libellé Parcoursup, intitulé complet de la
               cartographie et détail `detail_forma`), expression régulière.
Les comparaisons ignorent la casse et les espaces doublés.

Une formation qu'aucune règle ne couvre garde le domaine qu'elle avait dans le corpus de
référence, ou celui de sa fiche sœur si elle est nouvelle (`domaine_regle = "anterieur"`) ;
une formation nouvelle sans sœur reçoit le classement historique par mots-clés
(`domaine_cascade`, `domaine_regle = "cascade"`). La table couvre
les trois domaines de la démo (informatique, santé, maths) ; le reste du classement n'a pas
été revu à l'étape A.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

TABLE = Path(__file__).resolve().parents[2] / "data/reference/domaines_parcoursup.csv"
REGLE_CASCADE = "cascade"
REGLE_ANTERIEURE = "anterieur"


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


@dataclass(frozen=True)
class Regle:
    regle: str
    fili: str
    filiere: re.Pattern | None
    intitule: re.Pattern | None
    domaine: str
    motif: str

    def s_applique(self, fili: str, filiere: str, intitule: str) -> bool:
        if self.fili != "*" and self.fili != fili:
            return False
        if self.filiere and not self.filiere.search(_norm(filiere)):
            return False
        return not (self.intitule and not self.intitule.search(_norm(intitule)))


def _motif(expr: str) -> re.Pattern | None:
    return None if expr.strip() == "*" else re.compile(expr.strip(), re.IGNORECASE)


def charger_table(chemin: Path = TABLE) -> list[Regle]:
    with chemin.open(encoding="utf-8") as fh:
        lignes = list(csv.DictReader(fh, delimiter=";"))
    regles = [
        Regle(
            regle=l["regle"].strip(), fili=l["fili"].strip(), filiere=_motif(l["filiere"]),
            intitule=_motif(l["intitule"]), domaine=l["domaine"].strip(), motif=l["motif"].strip(),
        )
        for l in lignes
    ]
    ids = [r.regle for r in regles]
    if len(ids) != len(set(ids)):
        raise ValueError(f"identifiants de règle en double dans {chemin.name}")
    return regles


def classer(regles: list[Regle], fili: str | None, filiere: str | None, intitule: str | None) -> tuple[str, str] | None:
    """(domaine, identifiant de règle) de la première règle qui s'applique, sinon None."""
    for r in regles:
        if r.s_applique(fili or "", filiere or "", intitule or ""):
            return r.domaine, r.regle
    return None
