"""Agrege les jugements runs/judge_{judge}_{system}.jsonl.

Sorties : moyennes par systeme et critere, taux refus / erreur factuelle, distribution cause_echec,
scores par persona, delta par tour local vs claude_ctx (memes fiches -> isole la generation),
pires tours de local. Usage : python aggregate.py [--judge opus] [--md out.md]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
RUNS = HERE / "runs"
CRIT = ["references", "comprehension", "expression", "couverture"]
SYSTEMS = ["local", "claude_ctx", "claude_norag", "gpt_norag", "agent_sonnet", "agent_mistral"]


def load(judge: str, system: str) -> dict:
    p = RUNS / f"judge_{judge}_{system}.jsonl"
    if not p.exists():
        return {}
    d = {}
    for l in open(p):
        r = json.loads(l)
        if all(isinstance(r.get(c), (int, float)) for c in CRIT):
            d[(r["id"], r["turn"])] = r
    return d


def load_run(system: str) -> dict:
    p = RUNS / f"{system}.jsonl"
    return {(r["id"], r["turn"]): r for r in map(json.loads, open(p))} if p.exists() else {}


def mean(xs):
    return round(st.mean(xs), 2) if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="opus")
    ap.add_argument("--md", default="")
    a = ap.parse_args()

    J = {s: load(a.judge, s) for s in SYSTEMS}
    R = {s: load_run(s) for s in SYSTEMS}
    out = []
    P = out.append

    P(f"# Agregation juge {a.judge} (batterie Jarvis 2026-09-05)\n")
    P("## Moyennes par systeme (1-5)\n")
    P("| systeme | n | references | comprehension | expression | couverture | moy. 4 | refus | err. fact. |")
    P("|---|---|---|---|---|---|---|---|---|")
    for s in SYSTEMS:
        js = list(J[s].values())
        if not js:
            P(f"| {s} | 0 | | | | | | | |"); continue
        ms = [mean([j[c] for j in js]) for c in CRIT]
        tot = mean([st.mean([j[c] for c in CRIT]) for j in js])
        refus = sum(bool(j.get("refus")) for j in js)
        err = sum(bool(j.get("erreur_factuelle")) for j in js)
        P(f"| {s} | {len(js)} | {ms[0]} | {ms[1]} | {ms[2]} | {ms[3]} | {tot} | "
          f"{refus} ({100*refus/len(js):.0f} %) | {err} ({100*err/len(js):.0f} %) |")

    P("\n## Par persona\n")
    P("| systeme | persona | n | ref | compr | expr | couv |")
    P("|---|---|---|---|---|---|---|")
    for s in SYSTEMS:
        by = defaultdict(list)
        for (i, t), j in J[s].items():
            by[i[0]].append(j)
        for k, js in sorted(by.items()):
            name = {"L": "lyceen", "E": "etudiant"}.get(k, k)
            P(f"| {s} | {name} | {len(js)} | " + " | ".join(str(mean([j[c] for j in js])) for c in CRIT) + " |")

    P("\n## Distribution des notes 'references' (critere 1)\n")
    P("| systeme | 1 | 2 | 3 | 4 | 5 | part >= 4 |")
    P("|---|---|---|---|---|---|---|")
    for s in SYSTEMS:
        c = Counter(int(j["references"]) for j in J[s].values())
        n = sum(c.values()) or 1
        P(f"| {s} | " + " | ".join(str(c.get(k, 0)) for k in range(1, 6)) + f" | {100*(c[4]+c[5])/n:.0f} % |")

    P("\n## cause_echec (quand references < 3 ou couverture < 3)\n")
    for s in SYSTEMS:
        c = Counter(j.get("cause_echec", "?") for j in J[s].values()
                    if j["references"] < 3 or j["couverture"] < 3)
        P(f"- {s} : " + ", ".join(f"{k} {v}" for k, v in c.most_common()) + f" (total {sum(c.values())})")

    if J["local"] and J["claude_ctx"]:
        P("\n## local vs claude_ctx, memes fiches (isole retrieval vs generation)\n")
        keys = sorted(set(J["local"]) & set(J["claude_ctx"]))
        for c in CRIT:
            d = [J["claude_ctx"][k][c] - J["local"][k][c] for k in keys]
            better = sum(x > 0 for x in d); worse = sum(x < 0 for x in d)
            P(f"- {c} : delta moyen {mean(d):+} ; ctx meilleur sur {better}, pire sur {worse}, egal {len(d)-better-worse} (n={len(d)})")
        # tours ou local reste mauvais MEME avec claude_ctx -> fiches en cause (retrieval/data)
        bad_both = [k for k in keys if J["local"][k]["references"] <= 2 and J["claude_ctx"][k]["references"] <= 2]
        fixed = [k for k in keys if J["local"][k]["references"] <= 2 and J["claude_ctx"][k]["references"] >= 4]
        P(f"- references <= 2 chez local : {sum(J['local'][k]['references'] <= 2 for k in keys)} tours ; "
          f"dont toujours <= 2 avec Sonnet sur les memes fiches (=> fiches en cause) : {len(bad_both)} "
          f"{[f'{i}.{t}' for i, t in bad_both]} ; dont remontes a >= 4 (=> generation en cause) : {len(fixed)} "
          f"{[f'{i}.{t}' for i, t in fixed]}")
        zero = [k for k in keys if not R["local"].get(k, {}).get("sources")]
        P(f"- tours sans aucune fiche servie : {[f'{i}.{t}' for i, t in zero]}")
        P("\n### Notes 'references' sur les tours 'fiches en cause', tous systemes\n")
        P("| tour | " + " | ".join(SYSTEMS) + " |")
        P("|---|" + "---|" * len(SYSTEMS))
        for k in bad_both:
            P(f"| {k[0]}.{k[1]} | " + " | ".join(str(J[s].get(k, {}).get("references", "-")) for s in SYSTEMS) + " |")

    agents = [s for s in ("agent_sonnet", "agent_mistral") if R[s]]
    if agents:
        P("\n## Agents a outils : usage des outils\n")
        for s in agents:
            rs = list(R[s].values())
            calls = [len(r.get("tool_calls") or []) for r in rs]
            fiches = [len(r.get("sources") or []) for r in rs]
            P(f"- {s} : n={len(rs)}, appels/tour med {st.median(calls)} max {max(calls)}, "
              f"0 appel sur {sum(c == 0 for c in calls)} tours, fiches lues med {st.median(fiches)}, "
              f"latence med {st.median(r['latency_s'] for r in rs)} s, erreurs {sum(bool(r.get('error')) for r in rs)}")

    P("\n## Multi-tour (tour >= 1) vs premier tour\n")
    P("| systeme | tour 0 : ref / compr | tour >= 1 : ref / compr | n1 |")
    P("|---|---|---|---|")
    for s in SYSTEMS:
        t0 = [j for (i, t), j in J[s].items() if t == 0]
        t1 = [j for (i, t), j in J[s].items() if t >= 1]
        if t0 and t1:
            P(f"| {s} | {mean([j['references'] for j in t0])} / {mean([j['comprehension'] for j in t0])} | "
              f"{mean([j['references'] for j in t1])} / {mean([j['comprehension'] for j in t1])} | {len(t1)} |")

    P("\n## Pires tours de local (moyenne 4 criteres)\n")
    worst = sorted(J["local"].items(), key=lambda kv: st.mean([kv[1][c] for c in CRIT]))[:15]
    for (i, t), j in worst:
        q = R["local"].get((i, t), {}).get("question", "")[:90]
        P(f"- {i}.{t} {j['references']}/{j['comprehension']}/{j['expression']}/{j['couverture']} "
          f"[{j.get('cause_echec')}] {q!r} : {j.get('commentaire','')[:160]}")

    P("\n## Erreurs factuelles relevees (local)\n")
    for (i, t), j in sorted(J["local"].items()):
        if j.get("erreur_factuelle"):
            P(f"- {i}.{t} : {j.get('erreur_detail','')[:200]}")
    for s in ("claude_norag", "gpt_norag", "claude_ctx"):
        errs = [(k, j) for k, j in sorted(J[s].items()) if j.get("erreur_factuelle")]
        if errs:
            P(f"\n### Erreurs factuelles {s} ({len(errs)})\n")
            for (i, t), j in errs:
                P(f"- {i}.{t} : {j.get('erreur_detail','')[:200]}")

    txt = "\n".join(out)
    print(txt)
    if a.md:
        Path(a.md).write_text(txt + "\n")


if __name__ == "__main__":
    main()
