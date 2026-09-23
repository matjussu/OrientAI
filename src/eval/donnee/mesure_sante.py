"""Remplissage du champ `sante` (étape B-2) par domaine de la démo, avant / après.

Les domaines sont ceux de l'explorateur de Jarvis (`_orientai-ref/verticale-2026-09/explorateur/
export_data.py`, `DOM`, `EXCLU`, `domaines`, lus le 23/09/2026), recopiés ici : le script de
l'explorateur s'exécute à l'import et ne peut pas être importé. Une fiche peut compter dans
plusieurs domaines (une LAS à majeure informatique est en santé et en informatique).

Usage :
    python -m src.eval.donnee.mesure_sante <corpus_b1.json> <corpus_b2.json>
"""
import collections as C
import json
import re
import sys

DOM = {
    "informatique": (r"(?i:informatiq|cyber|science des données|\bdata\b|réseaux et télécom|MIASHS|intelligence artificielle|développeur|MP2I|MPII)", ()),
    "sante": (r"\bPASS\b|(?i:accès santé|infirmi|kiné|masso|orthophon|ergothér|psychomot|manipulateur|pédicur|orthopt|audioprothé|sage-femme|maïeut)", ("PASS", "Licence_Las", "IFSI")),
    "maths": (r"(?i:math|MPSI|MP2I|MPII|MIASHS)", ()),
}
EXCLU = {"informatique": r"information[- ]communication|information et communication|génie électrique et informatique industrielle",
         "maths": r"avec (la|2) spécialit|\bECG\b"}


def txt(f):
    return " ".join(str(f.get(k) or "") for k in ("nom", "detail", "fili_code"))


def domaines(f):
    out = []
    for name, (pat, filis) in DOM.items():
        champ = f.get("nom") or "" if name == "maths" else txt(f)
        if (re.search(pat, champ) or f.get("fili_code") in filis) and not (name in EXCLU and re.search(EXCLU[name], txt(f), re.I)):
            out.append(name)
    return out


def main(chemins: list[str]) -> None:
    for chemin in chemins:
        d = json.loads(open(chemin, encoding="utf-8").read())
        R = C.defaultdict(C.Counter)
        for f in d:
            if f.get("source") != "parcoursup" or f.get("fili_code") not in ("PASS", "Licence_Las"):
                continue
            s = f.get("sante") or {}
            for dom in domaines(f):
                R[dom]["fiches_pass_las"] += 1
                for k, lib in (("passage_national", "avec_passage_national"), ("passage_universite", "avec_chiffre_universite"),
                               ("capacites_universite", "avec_capacites")):
                    if (s.get(k) or {}).get("statut") == "disponible":
                        R[dom][lib] += 1
        print(chemin.split('/')[-1], json.dumps({k: dict(v) for k, v in sorted(R.items())}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
