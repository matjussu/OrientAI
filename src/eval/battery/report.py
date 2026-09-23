"""Agrege un passage en un rapport Markdown : `<run_dir>/REPORT.md`.

Tableau de tete, par systeme : note du juge (moyenne des 4 criteres et detail), refus, erreurs
factuelles, et controle deterministe des chiffres (part adossee a une fiche exposee, a cote de
son temoin de hasard). Puis : par domaine, distribution du critere references, causes d'echec,
local contre claude_ctx (memes fiches), multi-tour, pires tours.

Fonctionne aussi sur les runs du 05/09, qui n'enregistraient ni domaine ni positions : le domaine
vient de battery.json, les positions sont retrouvees par signature (nom, etablissement, ville,
source) et les signatures ambigues ou introuvables sont comptees dans le rapport.
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter
from pathlib import Path

from src.eval.battery.judge import CRITERIA, load_verdicts
from src.eval.battery.numbers import NumberChecker, NumberSummary
from src.eval.battery.runner import by_turn, load_battery, read_jsonl
from src.eval.battery.systems import SYSTEMS


def _mean(xs) -> float | None:
    xs = list(xs)
    return round(st.mean(xs), 2) if xs else None


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.0f} %"


def _fmt(x) -> str:
    return "" if x is None else str(x)


def _overall(v: dict) -> float:
    return st.mean(v[c] for c in CRITERIA)


def exposed_positions(rec: dict, corpus) -> tuple[list[int], int, int]:
    """Positions des fiches exposees sur un tour, et nb de fiches ambigues / introuvables."""
    if "source_positions" in rec:
        positions = rec["source_positions"] or []
        return [p for p in positions if p is not None], 0, sum(p is None for p in positions)
    positions, ambiguous, missing = [], 0, 0
    for s in rec.get("sources") or []:
        if not isinstance(s, dict):
            continue
        found = corpus.positions_by_signature(s.get("titre"), s.get("etablissement"), s.get("ville"),
                                              s.get("source"))
        ambiguous += len(found) > 1
        missing += not found
        positions += found
    return positions, ambiguous, missing


def check_numbers(run_dir: Path, systems: list[str], corpus, out_dir: Path, anchor: bool = True) -> dict:
    """Controle des chiffres par systeme. Ecrit `<out_dir>/numbers_<systeme>.jsonl` (un tour par ligne)."""
    checker = NumberChecker(corpus)
    runs = {s: by_turn(read_jsonl(run_dir / f"{s}.jsonl")) for s in systems}
    out = {}
    for system, records in runs.items():
        if not records:
            continue
        exposed_by_turn = {}
        if system == "claude_ctx" and runs.get("local"):
            base = runs["local"]  # claude_ctx voit les fiches de local, les runs du 05/09 ne le notent pas
        else:
            base = records
        summary = NumberSummary()
        ambiguous = missing = 0
        lines = []
        for key, rec in sorted(records.items()):
            source = rec if "source_positions" in rec else base.get(key, rec)
            positions, amb, miss = exposed_positions(source, corpus)
            ambiguous += amb
            missing += miss
            exposed_by_turn[key] = positions
            checks = checker.check(rec.get("answer") or "", positions, anchor=anchor)
            summary.add(checks, exposed=bool(positions))
            lines.append(json.dumps({"id": key[0], "turn": key[1], "exposed": len(positions),
                                     "checks": checks}, ensure_ascii=False))
        (out_dir / f"numbers_{system}.jsonl").write_text("\n".join(lines) + "\n")
        keys = sorted(records)
        chance = checker.chance_rate([records[k].get("answer") or "" for k in keys],
                                     [exposed_by_turn[k] for k in keys])
        out[system] = {"summary": summary, "chance": chance, "ambiguous": ambiguous, "missing": missing}
    return out


def build_report(run_dir: Path, corpus, judge_name: str = "opus", title: str = "",
                 anchor: bool = True, out_dir: Path | None = None) -> str:
    """Ecrit REPORT.md et les numbers_*.jsonl dans `out_dir` (par defaut le dossier du passage,
    un autre dossier pour rapporter sur des runs historiques sans les toucher)."""
    run_dir = Path(run_dir)
    out_dir = Path(out_dir or run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    battery = {it["id"]: it for it in load_battery()}
    systems = [s for s in SYSTEMS if (run_dir / f"{s}.jsonl").exists()]
    runs = {s: by_turn(read_jsonl(run_dir / f"{s}.jsonl")) for s in systems}
    verdicts = {s: load_verdicts(run_dir, judge_name, s) for s in systems}
    numbers = check_numbers(run_dir, systems, corpus, out_dir, anchor=anchor)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    lines: list[str] = []
    w = lines.append
    w(f"# {title or 'Banc OrientAI'} : {run_dir.name}\n")
    if manifest:
        w(f"Commit `{manifest.get('git_commit', '?')[:10]}`"
          f"{' (arbre modifie)' if manifest.get('git_dirty') else ''}, batterie "
          f"`{manifest.get('battery_sha256', '?')[:12]}`, corpus `{str(manifest.get('corpus_sha256'))[:12]}`, "
          f"juge `{judge_name}`.\n")
    else:
        w(f"Pas de manifeste (run anterieur au banc versionne). Juge `{judge_name}`.\n")

    w("## Tableau de tete\n")
    w("Note du juge de 1 a 5. **Chiffres adosses** = part des chiffres cites (%, EUR, places) "
      "presents dans une fiche que le systeme a exposee sur ce tour ; entre parentheses, le temoin de "
      "hasard (memes reponses contre les fiches d'un autre tour). Un systeme sans fiche est a 0 par "
      "construction : ses chiffres ne peuvent pas etre montres.\n")
    w("| systeme | tours | erreurs | moy. 4 | references | comprehension | expression | couverture "
      "| refus | err. fact. | chiffres cites | adosses (hasard) | corpus seul | non retrouves |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for s in systems:
        recs, vs = runs[s], list(verdicts[s].values())
        errors = sum(bool(r.get("error")) for r in recs.values())
        n = numbers.get(s)
        summ = n["summary"] if n else NumberSummary()
        crit = [_mean(v[c] for v in vs) for c in CRITERIA]
        refus = sum(bool(v.get("refus")) for v in vs)
        fact = sum(bool(v.get("erreur_factuelle")) for v in vs)
        judged = f"{len(vs)}/{len(recs)}" if len(vs) != len(recs) else str(len(recs))
        w(f"| {s} | {judged} | {errors} | {_fmt(_mean(_overall(v) for v in vs))} | "
          + " | ".join(_fmt(c) for c in crit)
          + f" | {_pct(refus / len(vs) if vs else None)} | {_pct(fact / len(vs) if vs else None)} "
          f"| {summ.n_claims} | {_pct(summ.rate('adosse'))} ({_pct(n['chance'] if n else None)}) "
          f"| {_pct(summ.rate('corpus'))} | {_pct(summ.rate('non_retrouve'))} |")
    w("")
    notes = [f"{s} : {n['ambiguous']} fiches exposees a signature ambigue, {n['missing']} introuvables"
             for s, n in numbers.items() if n["ambiguous"] or n["missing"]]
    if notes:
        w("Positions des fiches exposees : " + " ; ".join(notes) + ". Une signature ambigue compte "
          "toutes ses fiches (leger biais favorable au taux adosse) ; une fiche introuvable n'en compte "
          "aucune.\n")
    w("**Corpus seul** : chiffre absent des fiches exposees mais present dans une des 5 fiches que la "
      "ligne designe (BM25). Indicatif : calibre le 23/09, cet ancrage ne retrouve que 37 a 60 % des "
      "chiffres adosses et coincide par hasard sur ~15 % des chiffres. **Non retrouve** ne veut pas "
      "dire faux.\n")

    w("## Par domaine (moyenne des 4 criteres, n tours juges)\n")
    domains = sorted({battery[i]["domaine"] for i in battery})
    judged_systems = [s for s in systems if verdicts[s]]
    w("| domaine | " + " | ".join(judged_systems) + " |")
    w("|---|" + "---|" * len(judged_systems))
    for d in domains:
        cells = []
        for s in judged_systems:
            vs = [v for (cid, _), v in verdicts[s].items() if battery[cid]["domaine"] == d]
            cells.append(f"{_mean(_overall(v) for v in vs)} ({len(vs)})" if vs else "")
        w(f"| {d} | " + " | ".join(cells) + " |")
    w("")
    w("Chiffres adosses par domaine :\n")
    w("| domaine | " + " | ".join(numbers) + " |")
    w("|---|" + "---|" * len(numbers))
    for d in domains:
        cells = []
        for s in numbers:
            per_turn = read_jsonl(out_dir / f"numbers_{s}.jsonl")
            checks = [c for t in per_turn if battery[t["id"]]["domaine"] == d for c in t["checks"]]
            ok = sum(c["status"] == "adosse" for c in checks)
            cells.append(f"{_pct(ok / len(checks))} ({len(checks)})" if checks else "")
        w(f"| {d} | " + " | ".join(cells) + " |")
    w("")

    w("## Distribution du critere references\n")
    w("| systeme | 1 | 2 | 3 | 4 | 5 | part >= 4 |")
    w("|---|---|---|---|---|---|---|")
    for s in judged_systems:
        c = Counter(int(v["references"]) for v in verdicts[s].values())
        total = sum(c.values())
        w(f"| {s} | " + " | ".join(str(c.get(k, 0)) for k in range(1, 6))
          + f" | {_pct((c[4] + c[5]) / total)} |")
    w("")

    w("## Causes d'echec (quand references < 3 ou couverture < 3)\n")
    for s in judged_systems:
        c = Counter(v.get("cause_echec", "?") for v in verdicts[s].values()
                    if v["references"] < 3 or v["couverture"] < 3)
        w(f"- {s} : " + (", ".join(f"{k} {n}" for k, n in c.most_common()) or "aucune")
          + f" (total {sum(c.values())})")
    w("")

    if verdicts.get("local") and verdicts.get("claude_ctx"):
        local, ctx = verdicts["local"], verdicts["claude_ctx"]
        keys = sorted(set(local) & set(ctx))
        w("## local contre claude_ctx, memes fiches (isole la generation)\n")
        for c in CRITERIA:
            d = [ctx[k][c] - local[k][c] for k in keys]
            w(f"- {c} : delta moyen {_mean(d):+} ; ctx meilleur sur {sum(x > 0 for x in d)}, "
              f"pire sur {sum(x < 0 for x in d)} (n={len(d)})")
        w("")

    w("## Multi-tour contre premier tour (references / comprehension)\n")
    w("| systeme | tour 0 | tours >= 1 | n tours >= 1 |")
    w("|---|---|---|---|")
    for s in judged_systems:
        t0 = [v for (_, t), v in verdicts[s].items() if t == 0]
        t1 = [v for (_, t), v in verdicts[s].items() if t >= 1]
        if t0 and t1:
            w(f"| {s} | {_mean(v['references'] for v in t0)} / {_mean(v['comprehension'] for v in t0)} "
              f"| {_mean(v['references'] for v in t1)} / {_mean(v['comprehension'] for v in t1)} | {len(t1)} |")
    w("")

    for s in ("local",):
        if verdicts.get(s):
            w(f"## Pires tours de {s}\n")
            worst = sorted(verdicts[s].items(), key=lambda kv: _overall(kv[1]))[:10]
            for (cid, t), v in worst:
                q = runs[s].get((cid, t), {}).get("question", "")[:90]
                w(f"- {cid}.{t} {'/'.join(str(v[c]) for c in CRITERIA)} [{v.get('cause_echec')}] "
                  f"{q!r} : {v.get('commentaire', '')[:160]}")
            w("")

    w("## Erreurs factuelles relevees par le juge\n")
    for s in judged_systems:
        errs = [(k, v) for k, v in sorted(verdicts[s].items()) if v.get("erreur_factuelle")]
        if errs:
            w(f"### {s} ({len(errs)})\n")
            for (cid, t), v in errs:
                w(f"- {cid}.{t} : {v.get('erreur_detail', '')[:200]}")
            w("")

    text = "\n".join(lines).rstrip() + "\n"
    (out_dir / "REPORT.md").write_text(text)
    return text

