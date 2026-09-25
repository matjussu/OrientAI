"""Export d'un run au format de l'onglet « État des lieux » de l'explorateur
(`_orientai-ref/verticale-2026-09/explorateur/build_etat_lieux.py` : clés meta / synthese / tours, mêmes champs par
tour), plus `version`, `banc`, `tokens`, `cout_usd`, les URL des sources web et le critère 1 par conversation.

    python -m src.eval.multiversion rapport --tag <tag>   -> <tag>/export/<version>__<banc>.json + <tag>/RAPPORT.json
"""
from __future__ import annotations

import collections
import hashlib
import json
import statistics

from src.eval.multiversion.lanceur import BANCS, RESULTATS
from src.eval.multiversion.mesures import adosses, critere1, lire_banc

CRITERES = ("references", "comprehension", "expression", "couverture")


def _moy(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def _p90(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[int(0.9 * (len(xs) - 1))] if xs else None


def _tour(x: dict, juge: dict | None, chiffres: list | None) -> dict:
    tr = x.get("trace") or {}
    r = tr.get("router")
    v = tr.get("validation") or {}
    ans = x.get("answer") or ""
    alertes = ("rule_violations", "corpus_warnings", "layer3_warnings", "presence_warnings", "citation_mismatches")
    return {
        "id": x["id"], "turn": x["turn"], "persona": x.get("persona"), "domaine": x.get("domaine"),
        "tags": x.get("tags") or [], "question": x["question"], "history": x.get("history") or [],
        "latence": x.get("latency_s"), "erreur_exec": x.get("error"), "modele": x.get("model"),
        "version": x.get("version"), "banc": x.get("banc"),
        "router": None if not r else {k: r.get(k) for k in ("sub_indexes", "criteria", "domain_lock", "refusal_reason",
                                                             "top_k_override", "confidence", "is_fallback",
                                                             "hardlock_region_strict", "hardlock_domain_strict")},
        # Même règle que l'état des lieux du 24/09, pour la prod seulement (les autres versions n'ont pas de routeur).
        "court_circuit": (None if x.get("version") != "prod" else
                          "securite" if not r else ("routeur" if r.get("refusal_reason") else None)),
        "sources": [{"rang": i + 1, "titre": s.get("titre"), "etab": s.get("etablissement"), "ville": s.get("ville"),
                     "source": s.get("source"), "score": s.get("score"), "texte": (s.get("texte") or "")[:1500],
                     **({"url": s["url"]} if s.get("url") else {})}
                    for i, s in enumerate(x.get("sources") or [])],
        "select_fallthrough": tr.get("select_fallthrough"), "geo_refusal": tr.get("geo_refusal"),
        "validation": None if not v else {
            "flagged": v.get("flagged"), "honesty": v.get("honesty_score"),
            "n_alertes": sum(len(v.get(k) or []) for k in alertes),
            "detail": {k: v.get(k) for k in alertes if v.get(k)}},
        # Le chemin stream saute la policy (_validate_for_stream) : absente par construction, pas « passthrough ».
        "policy": None,
        "structured": tr.get("structured") is not None if x.get("version") == "prod" else None,
        "faithfulness": tr.get("faithfulness"),
        "reponse": ans, "mots": len(ans.split()),
        "tokens": x.get("usage") or {}, "cout_usd": x.get("cout_usd"),
        "juge": None if not juge else {k: juge.get(k) for k in (*CRITERES, "refus", "erreur_factuelle", "erreur_detail",
                                                                "cause_echec", "commentaire")},
        "chiffres": chiffres,
    }


def exporter(tag: str) -> dict:
    dossier = RESULTATS / tag
    (dossier / "export").mkdir(exist_ok=True)
    verdicts = {}
    vj = dossier / "judge/verdicts.jsonl"
    if vj.exists():
        for line in vj.read_text(encoding="utf-8").splitlines():
            if line.strip():
                v = json.loads(line)
                verdicts[(v["version"], v["banc"], v["id"], v["turn"])] = v
    budget = json.loads((dossier / "budget.json").read_text()) if (dossier / "budget.json").exists() else {}
    rapport = {"tag": tag, "budget": budget, "runs": {}}
    for f in sorted(dossier.glob("*__*.jsonl")):
        version, banc = f.stem.split("__")
        recs = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        ok = [r for r in recs if not r.get("error")]
        ad = adosses(ok, version)
        par_tour = ad.pop("par_tour", {})
        c1 = None
        if banc == "vertical":
            b = lire_banc(BANCS[banc])
            rep = {(r["id"], r["turn"]): r["answer"] for r in ok}
            c1 = critere1(b, rep)
            c1_sans = critere1(b, rep, tableaux=False)
            c1 = {k: v for k, v in c1.items() if k != "par_conversation"} | {
                "taux_sans_correction_tableaux": c1_sans["taux"]}
        tours = [_tour(r, verdicts.get((version, banc, r["id"], r["turn"])),
                       [[c["value"], c["unit"], c["status"]] for c in par_tour.get((r["id"], r["turn"]), [])]
                       if par_tour else None) for r in recs]
        juges = [t["juge"] for t in tours if t["juge"]]
        synth = {
            "n_tours": len(tours), "n_conversations": len({t["id"] for t in tours}),
            "erreurs_exec": sum(1 for t in tours if t["erreur_exec"]),
            "court_circuits": collections.Counter(t["court_circuit"] for t in tours if t["court_circuit"]).most_common(),
            "sources_mediane": statistics.median(len(t["sources"]) for t in tours) if tours else None,
            "structured_part": (sum(1 for t in tours if t["structured"]) / len(tours)) if version == "prod" and tours else None,
            "latence_mediane": statistics.median([t["latence"] for t in tours]) if tours else None,
            "latence_p90": _p90([t["latence"] for t in tours]),
            "mots_mediane": statistics.median(t["mots"] for t in tours) if tours else None,
            "cout_usd": round(sum(t["cout_usd"] or 0 for t in tours), 4),
            "tokens": {m: {k: sum((t["tokens"].get(m) or {}).get(k, 0) for t in tours) for k in ("entree", "sortie", "non_mesures")}
                       for m in sorted({m for t in tours for m in t["tokens"]})},
            "juge_n": len(juges), "juge_moyennes": {c: _moy([j[c] for j in juges]) for c in CRITERES},
            "juge_moyenne_4": _moy([_moy([j[c] for c in CRITERES]) for j in juges]),
            "refus": sum(1 for j in juges if j["refus"]), "erreurs_fait": sum(1 for j in juges if j["erreur_factuelle"]),
            "critere1": c1, "adosses": ad,
        }
        meta = {"version": version, "banc": banc, "source": f"results/multiversion/{tag}/{f.name}",
                "empreinte_fichier": hashlib.sha256(f.read_bytes()).hexdigest()[:12],
                "runs": [r for r in budget.get("runs", []) if r.get("version") == version and r.get("banc") == banc]}
        out = dossier / "export" / f"{version}__{banc}.json"
        out.write_text(json.dumps({"meta": meta, "synthese": synth, "tours": tours}, ensure_ascii=False,
                                  separators=(",", ":"), default=str), encoding="utf-8")
        rapport["runs"][f"{version}__{banc}"] = synth
    (dossier / "RAPPORT.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=str) + "\n",
                                          encoding="utf-8")
    return rapport
