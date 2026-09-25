"""Mesures déterministes du gate F (contrat du cerveau, section 9 ; CONTRAT-etape3, section 9). Zéro appel d'API.

    python -m src.eval.multiversion.gate_f --tag <tag>     # lit results/multiversion/<tag>/v2__gatef.jsonl

Critères (tous requis pour le gate de l'étape 3) :
1. fiches attendues rendues par les outils de la conversation >= 90 %, familles recherche, nom, multi-tour (fiches du
   tour 2, rendues au tour 2) et honnêteté ;
2. 0 formation citée hors des résultats d'outils : un établissement de la base C écrit dans la réponse alors
   qu'aucune formation rendue dans la conversation n'est de cet établissement. Contrôle positif joué à chaque
   mesure (une réponse à laquelle on ajoute un établissement non rendu doit être comptée) ;
3. clarification : orientation d'abord (au moins 150 caractères avant la première question) et au plus 2 questions,
   sur les 5 questions de la famille ;
4. chiffres affichés adossés : 100 %, recompté ici sur les valeurs que la trace garde de chaque appel d'outil (et les
   chiffres de l'élève), avec la même tolérance que `numbers.py`, sans passer par `src/v2/verificateur.py`.

Angles morts publiés : une formation citée par un sigle ou un surnom seul (« l'IUT », « Lyon 1 ») n'est pas vue par
le critère 2 ; un établissement dont le nom normalisé fait moins de 12 caractères n'est pas cherché (trop de
coïncidences).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from src.eval.battery.runner import read_jsonl
from src.eval.multiversion.lanceur import RESULTATS, charger_banc
from src.eval.multiversion.mesures import adosses_v2
from src.v2.outils import Outils, normaliser

RACINE = Path(__file__).resolve().parents[3]
GATE_F = RACINE / "docs/cerveau/gate_f/requetes_gate_f.json"
FAMILLES_FICHES = ("recherche", "nom", "multi-tour", "honnetete")
MIN_ETAB = 12
SEUIL_FICHES = 0.90


def _questions(reponse: str) -> list[tuple[int, str]]:
    """Questions posées à l'élève : chaque « ? » hors parenthèses clôt une question (une parenthèse qui commente la
    question, « (ça change tout : proche ou loin ?) », n'en fait pas une seconde). Rend (position du début de la
    phrase, phrase)."""
    sans_parentheses = re.sub(r"\([^()]*\)", lambda m: " " * len(m.group(0)), reponse)
    out, debut = [], 0
    for m in re.finditer(r"[.!?\n]", sans_parentheses):
        if m.group(0) == "?":
            phrase = reponse[debut:m.end()].strip()
            out.append((reponse.find(phrase, debut), phrase))
        debut = m.end()
    return out


class Detecteur:
    """Établissements de la base C écrits dans une réponse, contre ceux des formations rendues."""

    def __init__(self, outils: Outils):
        self.etab_de = {f["id"]: f["etab_norm"] for f in outils.index}
        self.etabs = sorted({e for e in self.etab_de.values() if len(e) >= MIN_ETAB}, key=len, reverse=True)

    def cites_hors(self, reponse: str, ids_rendus: list[str]) -> list[str]:
        texte = f" {normaliser(reponse)} "
        rendus = {self.etab_de.get(i) for i in ids_rendus}
        vus = []
        for e in self.etabs:
            if f" {e} " in texte and not any(e in x or x in e for x in vus):
                vus.append(e)
        return [e for e in vus if not any(e == r or (r and (e in r or r in e)) for r in rendus)]


def _adosses(tours: list[dict]) -> tuple[int, int, list[dict]]:
    """(chiffres, non adossés, détail) sur les réponses finales, recomptés depuis les valeurs tracées."""
    r = adosses_v2(tours)
    return r["chiffres_cites"], len(r["non_adosses"]), r["non_adosses"]


def mesurer(tag: str, fichier: str = "v2__gatef.jsonl") -> dict:
    items, sha = charger_banc("gatef")
    questions = {q["id"]: q for q in json.loads(GATE_F.read_text(encoding="utf-8"))["questions"]}
    recs = read_jsonl(RESULTATS / tag / fichier)
    par_q: dict[str, list[dict]] = {}
    for r in sorted(recs, key=lambda r: (r["id"], r["turn"])):
        par_q.setdefault(r["id"], []).append(r)
    det = Detecteur(Outils())
    lignes, attendues_tot, trouvees_tot = [], 0, 0
    hors_tot, n_chiffres, n_fautes, fautes = 0, 0, 0, []
    clarif = []
    for qid, q in questions.items():
        tours = par_q.get(qid, [])
        complete = len(tours) == len(q["tours"]) and not any(t.get("error") for t in tours)
        ligne = {"id": qid, "famille": q["famille"], "joue": complete}
        if not complete:
            lignes.append(ligne)
            continue
        ids_conv: list[str] = []
        for t in tours:
            for appel in (t.get("trace") or {}).get("outils", []):
                ids_conv += [i for i in appel.get("ids_rendus") or [] if i not in ids_conv]
        if q["famille"] in FAMILLES_FICHES:
            if "fiches_tour_2" in q["attendu"]:
                attendues = q["attendu"]["fiches_tour_2"]
                rendus = {i for a in (tours[1].get("trace") or {}).get("outils", []) for i in a.get("ids_rendus") or []}
            else:
                attendues, rendus = q["attendu"]["fiches"], set(ids_conv)
            trouvees = [i for i in attendues if i in rendus]
            attendues_tot += len(attendues)
            trouvees_tot += len(trouvees)
            ligne |= {"attendues": len(attendues), "trouvees": len(trouvees),
                      "manquantes": [i for i in attendues if i not in rendus]}
        hors = det.cites_hors(tours[-1]["answer"], ids_conv)
        hors_tot += len(hors)
        ligne["cites_hors_resultats"] = hors
        if q["famille"] == "clarification":
            rep = tours[0]["answer"]
            qs = _questions(rep)
            avant = qs[0][0] if qs else len(rep)
            ok = len(qs) <= 2 and avant >= 150
            clarif.append(ok)
            ligne |= {"questions_posees": len(qs), "caracteres_avant_premiere_question": avant, "clarification_ok": ok}
        c, f, detail = _adosses(tours)
        n_chiffres += c
        n_fautes += f
        fautes += detail
        ligne |= {"chiffres": c, "non_adosses": f, "appels_outils": sum(
            len((t.get("trace") or {}).get("outils", [])) for t in tours)}
        lignes.append(ligne)

    # Contrôle positif du détecteur : un établissement non rendu ajouté à une réponse doit être compté.
    temoin_q = next((l for l in lignes if l.get("joue")), None)
    temoin = None
    if temoin_q:
        tours = par_q[temoin_q["id"]]
        ids_conv = [i for t in tours for a in (t.get("trace") or {}).get("outils", []) for i in a.get("ids_rendus") or []]
        rendus = {det.etab_de.get(i) for i in ids_conv}
        etranger = next(e for e in det.etabs if e not in rendus and not any(e in r or r in e for r in rendus if r))
        sabotee = tours[-1]["answer"] + f"\n\nTu peux aussi regarder {etranger}."
        temoin = {"question": temoin_q["id"], "etablissement_ajoute": etranger,
                  "compte": len(det.cites_hors(sabotee, ids_conv)) - len(det.cites_hors(tours[-1]["answer"], ids_conv))}
    jouees = [l for l in lignes if l.get("joue")]
    part = trouvees_tot / attendues_tot if attendues_tot else None
    criteres = {
        "1_fiches_attendues": {"trouvees": trouvees_tot, "attendues": attendues_tot, "part": part,
                               "vert": part is not None and part >= SEUIL_FICHES},
        "2_cites_hors_resultats": {"nombre": hors_tot, "vert": hors_tot == 0 and bool(temoin and temoin["compte"] >= 1),
                                   "temoin_positif": temoin},
        "3_clarification": {"ok": sum(clarif), "questions": len(clarif), "vert": len(clarif) == 5 and all(clarif)},
        "4_adosses": {"chiffres": n_chiffres, "non_adosses": n_fautes, "vert": n_fautes == 0 and n_chiffres > 0,
                      "detail": fautes},
    }
    return {"tag": tag, "fichier": fichier, "gate_f_sha256": sha, "questions_jouees": len(jouees),
            "questions": len(questions), "criteres": criteres,
            "vert": len(jouees) == len(questions) and all(c["vert"] for c in criteres.values()), "lignes": lignes}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fichier", default="v2__gatef.jsonl")
    a = ap.parse_args(argv)
    r = mesurer(a.tag, a.fichier)
    (RESULTATS / a.tag / "gate_f.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "lignes"} | {"criteres": {
        k: {x: y for x, y in v.items() if x != "detail"} for k, v in r["criteres"].items()}},
        ensure_ascii=False, indent=1))
    return 0 if r["vert"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
