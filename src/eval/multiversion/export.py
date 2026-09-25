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
    """Rang le plus proche : la plus petite valeur dont au moins 90 % des valeurs sont inférieures ou égales.
    L'état des lieux du 24/09 prenait xs[int(0.9 * (n - 1))], qui rend le minimum sur 2 valeurs (défaut relevé
    par Jarvis le 25/09 sur l'essai : p90 19,92 < médiane 27,19). Sur 67 valeurs, les deux diffèrent d'un rang."""
    import math
    xs = sorted(x for x in xs if x is not None)
    return xs[math.ceil(0.9 * len(xs)) - 1] if xs else None


def _tokens_lisibles(usage: dict) -> dict:
    """Les appels de recherche web sont comptés en « entree » pour le calcul du coût ; à l'export ils s'appellent
    « appels », pour ne pas être lus comme des tokens."""
    return {m: ({"appels": u.get("entree", 0)} if m == "openai-web-search" else u) for m, u in usage.items()}


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
        "tokens": _tokens_lisibles(x.get("usage") or {}), "cout_usd": x.get("cout_usd"),
        "juge": None if not juge else {k: juge.get(k) for k in (*CRITERES, "refus", "erreur_factuelle", "erreur_detail",
                                                                "cause_echec", "commentaire")},
        "chiffres": chiffres,
        # Cerveau v2 : les étages de la trace (CONTRAT-etape3 section 2), pour l'onglet de l'explorateur.
        "v2": None if x.get("version") != "v2" else {
            "filtre": tr.get("filtre"), "court_circuit": tr.get("court_circuit"), "etapes": tr.get("etapes"),
            "outils": [{k: a.get(k) for k in ("nom", "arguments", "execute", "ids_rendus", "erreur", "secondes")}
                       | {"nb_resultats": (a.get("meta") or {}).get("nb_resultats"),
                          "tronque": (a.get("meta") or {}).get("tronque"), "nb_valeurs": len(a.get("valeurs") or [])}
                       for a in tr.get("outils") or []],
            "profil_avant": tr.get("profil_avant"), "profil_apres": tr.get("profil_apres"),
            "brouillons": tr.get("brouillons"), "phrases_retirees": tr.get("phrases_retirees"),
            "verifications": [{k: len(v.get(k) or []) for k in ("adosses", "eleve", "non_adosses")}
                              | {"non_adosses_detail": v.get("non_adosses")} for v in tr.get("verifications") or []],
            "plafond_atteint": tr.get("plafond_atteint"), "garantie_adosses": tr.get("garantie_adosses"),
            "latence_s": tr.get("latence_s"), "appels_modele": len(tr.get("appels_modele") or [])},
    }


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    """IC95 de Wilson d'une proportion k/n (choisi plutôt que le bootstrap : fermé, déterministe, correct aux
    petits effectifs et près de 0 %)."""
    if n == 0:
        return None
    import math
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - demi), 4), round(min(1.0, centre + demi), 4)]


def _synthese(version: str, banc: str, recs: list[dict], verdicts: dict, detail_c1: dict | None) -> tuple[list, dict]:
    ok = [r for r in recs if not r.get("error")]
    ad = adosses(ok, version)
    par_tour = ad.pop("par_tour", {})
    c1 = None
    if banc == "vertical":
        b = lire_banc(BANCS[banc])
        rep = {(r["id"], r["turn"]): r["answer"] for r in ok}
        plein = critere1(b, rep)
        c1 = {k: v for k, v in plein.items() if k != "par_conversation"} | {
            "taux_sans_correction_tableaux": critere1(b, rep, tableaux=False)["taux"]}
    tours = []
    for r in recs:
        t = _tour(r, verdicts.get((version, banc, r["id"], r["turn"])),
                  [[c["value"], c["unit"], c["status"]] for c in par_tour.get((r["id"], r["turn"]), [])]
                  if par_tour else None)
        if detail_c1 is not None:
            t["critere1"] = detail_c1.get((r["id"], r["turn"]))
        tours.append(t)
    juges = [t["juge"] for t in tours if t["juge"]]
    n_fait = sum(1 for j in juges if j["erreur_factuelle"])
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
        "tokens": {m: {k: sum((t["tokens"].get(m) or {}).get(k, 0) for t in tours)
                       for k in (("appels",) if m == "openai-web-search" else ("entree", "sortie", "non_mesures"))}
                   for m in sorted({m for t in tours for m in t["tokens"]})},
        "juge_n": len(juges), "juge_moyennes": {c: _moy([j[c] for j in juges]) for c in CRITERES},
        "juge_moyenne_4": _moy([_moy([j[c] for c in CRITERES]) for j in juges]),
        "refus": sum(1 for j in juges if j["refus"]), "erreurs_fait": n_fait,
        "erreurs_fait_part": round(n_fait / len(juges), 4) if juges else None,
        "erreurs_fait_ic95_wilson": wilson(n_fait, len(juges)),
        "critere1": c1, "adosses": ad,
    }
    return tours, synth


def exporter(tag: str, dossier_juge: str = "judge") -> dict:
    """`dossier_juge` : passage du juge lu (judge, ou judge_v2 pour le rejugement du 25/09) ; les exports et le rapport
    d'un autre passage que le premier sont suffixés, pour ne rien écraser."""
    from src.eval.multiversion.mesures import detail_par_tour
    dossier = RESULTATS / tag
    (dossier / "export").mkdir(exist_ok=True)
    verdicts = {}
    vj = dossier / dossier_juge / "verdicts.jsonl"
    suffixe = "" if dossier_juge == "judge" else f"_{dossier_juge}"
    if vj.exists():
        for line in vj.read_text(encoding="utf-8").splitlines():
            if line.strip():
                v = json.loads(line)
                verdicts[(v["version"], v["banc"], v["id"], v["turn"])] = v
    budget = json.loads((dossier / "budget.json").read_text()) if (dossier / "budget.json").exists() else {}
    echantillon = RESULTATS / "echantillon_vertical_25.json"
    ids_ech = set(json.loads(echantillon.read_text())["ids"]) if echantillon.exists() else None
    rapport = {"tag": tag, "juge": dossier_juge, "budget": budget, "ic95": "Wilson (score), z = 1,96", "runs": {}}
    for f in sorted(dossier.glob("*__*.jsonl")):
        version, banc = f.stem.split("__")
        recs = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        detail = None
        if banc == "vertical":
            detail = detail_par_tour(lire_banc(BANCS[banc]),
                                     {(r["id"], r["turn"]): r["answer"] for r in recs if not r.get("error")})
        tours, synth = _synthese(version, banc, recs, verdicts, detail)
        meta = {"version": version, "banc": banc, "source": f"results/multiversion/{tag}/{f.name}",
                "empreinte_fichier": hashlib.sha256(f.read_bytes()).hexdigest()[:12],
                "runs": [r for r in budget.get("runs", []) if r.get("version") == version and r.get("banc") == banc]}
        out = dossier / f"export{suffixe}" / f"{version}__{banc}.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"meta": meta, "synthese": synth, "tours": tours}, ensure_ascii=False,
                                  separators=(",", ":"), default=str), encoding="utf-8")
        rapport["runs"][f"{version}__{banc}"] = synth
        if version == "prod" and banc == "vertical" and ids_ech:
            # Même base que chatgpt_web : les 25 conversations de l'échantillon figé (protocole v0.3).
            sous = [r for r in recs if r["id"] in ids_ech]
            _, synth_e = _synthese(version, banc, sous, verdicts, detail)
            rapport["runs"]["prod__vertical_echantillon25"] = synth_e
    (dossier / f"RAPPORT{suffixe}.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=str) + "\n",
                                          encoding="utf-8")
    return rapport
