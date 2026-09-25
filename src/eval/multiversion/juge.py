"""Juge à l'aveugle d'un run multi-version (protocole section 5 et amendements).

    python -m src.eval.multiversion juger preparer --tag <tag>    # lots anonymisés + label_mapping.json
    python -m src.eval.multiversion juger collecter --tag <tag>   # verdicts -> judge/verdicts.jsonl

Même juge, même rubrique et même `build_prompt` que D et E ; la liste des titres « que l'assistant avait sous les
yeux » n'est pas passée (elle serait fausse pour une version qui n'a pas vu ces fiches). Fiches de référence :
- vertical : les 8 fiches de `results/banc_e/exposition.json` en carte B, identiques pour toutes les versions d'une
  conversation, précédées de la phrase du protocole v0.1 (« l'assistant ne les a pas forcément eues ») ;
- lot0 : aucune fiche ;
- gatef (étape 3) : les fiches attendues de la question (`attendu.fiches`, ou `fiches_tour_2`), en carte B de la base
  concordante, avec la même phrase ; aucune pour la famille clarification.
Aveugle : tous les runs du tag mélangés (graine dans seed.txt), identifiants opaques ; les marqueurs de provenance
des liens (`utm_source=chatgpt.com`) sont retirés de la copie lue par le juge, sinon ils nomment la version.
Un seul passage, sans rejugement (go de Matteo du 25/09).
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from src.eval import juge_d as jd
from src.eval.battery.judge import RUBRIC, build_prompt, parse_verdict, valid_scores
from src.eval.juge_e import texte_lot
from src.eval.multiversion.lanceur import BANCS, RESULTATS
from src.eval.multiversion.mesures import EXPOSITION

PHRASE_JUGE = ("Les fiches ci-dessous sont des données officielles de référence pour cette question ; l'assistant ne "
               "les a pas forcément eues. Un chiffre ou un fait qui les contredit est une erreur factuelle. Une "
               "information absente des fiches n'est pas une erreur en soi : juge-la sur tes connaissances.")
# Rejugement du 25/09 (contrat de concordance §8) : consigne ajoutée mot pour mot, fiches de la base concordante.
CONSIGNE_NOMMAGE = ("Un chiffre officiel correctement nommé n'est pas une erreur ; un chiffre d'un autre indicateur "
                    "présenté sous un nom qui ne lui correspond pas en est une.")
TAILLE_LOT = {"vertical": 6, "lot0": 12, "gatef": 6}
_PROVENANCE = re.compile(r"[?&]utm_source=[^)\s\]]+")


def neutraliser(texte: str) -> str:
    return _PROVENANCE.sub("", texte or "")


def prompt_juge(rec: dict, item: dict, cartes: list[str] | None, consigne: bool = False) -> str:
    p = build_prompt({"persona": item["persona"], "tags": item.get("tags", []), "question": rec["question"],
                      "history": [{**m, "content": neutraliser(m["content"])} for m in rec["history"]],
                      "answer": neutraliser(rec["answer"]), "sources": []})
    if cartes is None:
        return p
    phrase = PHRASE_JUGE + (f" {CONSIGNE_NOMMAGE}" if consigne else "")
    return p + f"\n\n{phrase}\n\nCONTENU DES FICHES :\n" + "\n\n".join(cartes)


def _cartes_vertical() -> dict[str, list[str]]:
    from src.base_c.outils import Base
    from src.eval.format_d import Formats
    from src.eval.grille_d import BASE, CORPUS
    expo = json.loads(EXPOSITION.read_text(encoding="utf-8"))["conversations"]
    f = Formats(Base.ouvrir(BASE), json.loads(CORPUS.read_bytes()))
    return {cid: [f.carte_b(i) for i in c["exposees"]] for cid, c in expo.items()}


def _cartes_gatef() -> dict[str, list[str]]:
    from src.base_c.outils import Base
    from src.eval.format_d import Formats
    from src.eval.grille_d import BASE
    f = Formats(Base.ouvrir(BASE), [])
    out = {}
    for q in json.loads(BANCS["gatef"].read_text(encoding="utf-8"))["questions"]:
        ids = q["attendu"].get("fiches") or q["attendu"].get("fiches_tour_2") or []
        out[q["id"]] = [f.carte_b(i) for i in ids]
    return out


def preparer(tag: str, graine: str, bancs: tuple[str, ...] = ("vertical",), dossier_juge: str = "judge",
             consigne: bool = False) -> dict:
    """`bancs` : bancs jugés (décision du 25/09 : vertical seulement ; lot0 plus tard, sur les réponses stockées)."""
    dossier = RESULTATS / tag
    juge = dossier / dossier_juge
    if (juge / "label_mapping.json").exists():
        raise SystemExit(f"{juge}/label_mapping.json existe déjà : un seul passage, pas de nouvelle préparation")
    from src.eval.multiversion.lanceur import charger_banc
    cartes = {"vertical": _cartes_vertical(), "gatef": _cartes_gatef() if "gatef" in bancs else {}}
    items = {b: {i["id"]: i for i in charger_banc(b)[0]} for b in BANCS}
    taches = {b: [] for b in BANCS}
    mapping, erreurs = {}, 0
    for f in sorted(dossier.glob("*__*.jsonl")):
        version, banc = f.stem.split("__")
        if banc not in bancs:
            continue
        for rec in (json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()):
            if rec.get("error"):
                erreurs += 1
                continue
            oid = jd.opaque(graine, f"{version}|{banc}", rec["id"], rec["turn"])
            mapping[oid] = {"version": version, "banc": banc, "id": rec["id"], "turn": rec["turn"]}
            item = items[banc][rec["id"]]
            fiches = cartes[banc].get(rec["id"]) if banc in cartes else None
            taches[banc].append({"oid": oid, "prompt": prompt_juge(rec, item, fiches or None, consigne)})
    (juge / "lots").mkdir(parents=True, exist_ok=True)
    n_lots = 0
    for banc, ts in taches.items():
        random.Random(f"{graine}|{banc}").shuffle(ts)
        for k in range(0, len(ts), TAILLE_LOT[banc]):
            lot = ts[k:k + TAILLE_LOT[banc]]
            base = juge / "lots" / f"{banc}_{k // TAILLE_LOT[banc] + 1:03d}"
            base.with_suffix(".json").write_text(json.dumps({"rubrique": RUBRIC, "taches": lot}, ensure_ascii=False,
                                                            indent=1) + "\n", encoding="utf-8")
            base.with_suffix(".txt").write_text(texte_lot(lot), encoding="utf-8")
            n_lots += 1
    (juge / "label_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                             encoding="utf-8")
    (juge / "seed.txt").write_text(graine + "\n", encoding="utf-8")
    return {"taches": len(mapping), "lots": n_lots, "tours_en_erreur_non_juges": erreurs,
            "par_banc": {b: len(t) for b, t in taches.items()}}


def collecter(tag: str, dossier_juge: str = "judge") -> dict:
    juge = RESULTATS / tag / dossier_juge
    mapping = json.loads((juge / "label_mapping.json").read_text(encoding="utf-8"))
    lignes, illisibles = [], []
    for p in sorted((juge / "verdicts").glob("*.json")) if (juge / "verdicts").exists() else []:
        v = parse_verdict(p.read_text(encoding="utf-8"))
        if p.stem not in mapping or not valid_scores(v):
            illisibles.append(p.name)
            continue
        lignes.append({**mapping[p.stem], "oid": p.stem, **v})
    (juge / "verdicts.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lignes),
                                        encoding="utf-8")
    return {"verdicts": len(lignes), "attendus": len(mapping), "manquants": len(mapping) - len(lignes),
            "illisibles": illisibles}


def lanceur_shell(tag: str, dossier_juge: str = "judge") -> Path:
    """Écrit le lanceur d'un lot (repris de results/banc_e/judge/traces_lanceur/juge_stdin_v2.sh, chemins du tag)."""
    juge = (RESULTATS / tag / dossier_juge).resolve()
    script = juge / "juge_stdin.sh"
    modele = Path(__file__).resolve().parents[3] / "results/banc_e/judge/traces_lanceur/juge_stdin_v2.sh"
    texte = modele.read_text(encoding="utf-8")
    texte = re.sub(r"^J=.*$", f"J={juge}", texte, flags=re.M)
    texte = re.sub(r"^S=.*$", f"S={juge}/sorties_juges", texte, flags=re.M)
    texte = texte.replace("(banc E, protocole v0.3.1", "(instrument multi-version, protocole v0.1")
    script.write_text(texte, encoding="utf-8")
    script.chmod(0o755)
    return script
