"""Banc OrientAI en une commande.

    python -m src.eval.battery bench  --tag 2026-09-23_ref --systems local,mistral_large_norag
    python -m src.eval.battery run    --tag ... --systems local [--only L01,E02] [--limit 5]
    python -m src.eval.battery judge  --tag ... --systems local [--judge opus]
    python -m src.eval.battery report --tag ...   (ou --run-dir <dossier>, ex. les runs du 05/09)

`bench` = run + judge + report. Tout passage ecrit dans results/battery/<tag>/ : un JSONL par
systeme, les verdicts, le controle des chiffres, manifest.json et REPORT.md. Relancer la meme
commande reprend ou elle s'est arretee.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from src.eval.battery.config import BATTERY_PATH, REPO, RESULTS_DIR

# Cles requises par famille de modele. Verifiees AVANT le premier appel : sans elles chaque tour
# echoue en 0 s et le passage produit un JSONL d'erreurs (05/09 : 67 erreurs d'auth).
KEYS = {"mistral": "MISTRAL_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
SYSTEM_KEYS = {
    "local": ["mistral"], "mistral_large_norag": ["mistral"], "mistral_medium_norag": ["mistral"],
    "agent_mistral": ["mistral"], "claude_norag": ["anthropic"], "claude_ctx": ["anthropic"],
    "agent_sonnet": ["anthropic"], "gpt_norag": ["openai"],
}
JUDGE_KEYS = {"opus": ["anthropic"], "gpt": ["openai"]}


def load_env() -> None:
    """Charge le .env du depot sans ecraser l'environnement deja exporte."""
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env", override=False)


def require_keys(families: set[str]) -> None:
    missing = [KEYS[f] for f in sorted(families) if not os.environ.get(KEYS[f])]
    if missing:
        sys.exit(f"cles absentes : {', '.join(missing)} (ni dans l'environnement ni dans {REPO / '.env'})")


def run_dir_of(args) -> Path:
    if args.run_dir:
        return Path(args.run_dir)
    if not args.tag:
        sys.exit("--tag ou --run-dir requis")
    return RESULTS_DIR / args.tag


def battery_of(args, run_dir: Path) -> Path:
    """--battery explicite, sinon celle du manifeste du passage, sinon la batterie par defaut."""
    from src.eval.battery.runner import read_manifest

    if args.battery:
        return Path(args.battery)
    recorded = read_manifest(run_dir).get("battery_path")
    if recorded:
        return Path(recorded) if Path(recorded).is_absolute() else REPO / recorded
    return BATTERY_PATH


def cmd_run(args) -> None:
    from src.eval.battery import systems as registry
    from src.eval.battery.corpus import Corpus
    from src.eval.battery.runner import (
        assert_same_battery,
        by_turn,
        code_state,
        load_battery,
        play,
        read_jsonl,
        read_manifest,
        update_manifest,
    )

    code = code_state()
    names = args.systems.split(",")
    unknown = set(names) - set(registry.SYSTEMS)
    if unknown:
        sys.exit(f"systemes inconnus : {', '.join(sorted(unknown))} (connus : {', '.join(registry.SYSTEMS)})")
    require_keys({f for n in names for f in SYSTEM_KEYS[n]})
    run_dir = run_dir_of(args)
    battery_path = battery_of(args, run_dir)
    try:
        assert_same_battery(run_dir, battery_path)
    except ValueError as e:
        sys.exit(str(e))
    battery = load_battery(battery_path)
    selection = [it["id"] for it in battery]
    if args.only:
        keep = set(args.only.split(","))
        selection = [cid for cid in selection if cid in keep]
    if args.limit:
        selection = selection[: args.limit]

    corpus = Corpus() if set(names) & registry.NEEDS_CORPUS else None
    recorded = read_manifest(run_dir).get("corpus_sha256")
    if corpus and recorded and recorded != corpus.sha256:
        sys.exit(f"{run_dir} a ete joue sur le corpus {recorded[:12]}, le corpus actuel est "
                 f"{corpus.sha256[:12]} : choisir un autre --tag")
    for name in names:
        local_run = by_turn(read_jsonl(run_dir / "local.jsonl")) if name == "claude_ctx" else None
        system = registry.build(name, corpus=corpus, local_run=local_run)
        stats = play(system, battery, run_dir / f"{name}.jsonl", workers=args.workers, selection=selection)
        print(f"[{name}] {stats}")
        update_manifest(run_dir, corpus.sha256 if corpus else None, {"step": "run", **stats}, battery_path, code)


def cmd_judge(args) -> None:
    from src.eval.battery.judge import judge_run
    from src.eval.battery.runner import code_state, update_manifest

    code = code_state()
    require_keys(set(JUDGE_KEYS[args.judge]))
    run_dir = run_dir_of(args)
    stats = judge_run(run_dir, args.systems.split(","), args.judge, sample=args.sample, workers=args.workers)
    print(f"[juge] {stats}")
    if (run_dir / "manifest.json").exists():
        update_manifest(run_dir, None, {"step": "judge", **stats}, battery_of(args, run_dir), code)


def cmd_report(args) -> None:
    from src.eval.battery.corpus import Corpus
    from src.eval.battery.report import build_report

    run_dir = run_dir_of(args)
    print(build_report(run_dir, Corpus(), judge_name=args.judge, title=args.title,
                       anchor=not args.no_anchor, out_dir=args.out or None,
                       battery_path=battery_of(args, run_dir)))


def cmd_bench(args) -> None:
    cmd_run(args)
    cmd_judge(args)
    cmd_report(args)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m src.eval.battery", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", cmd_run), ("judge", cmd_judge), ("report", cmd_report), ("bench", cmd_bench)):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        p.add_argument("--tag", default="", help="nom du passage, dossier results/battery/<tag>")
        p.add_argument("--run-dir", default="", help="dossier de passage explicite (prime sur --tag)")
        p.add_argument("--judge", default="opus", choices=["opus", "gpt"])
        p.add_argument("--battery", default="", help="chemin d'une autre batterie (meme format)")
        if name != "report":
            p.add_argument("--systems", required=True, help="liste separee par des virgules")
            p.add_argument("--workers", type=int, default=3)
        if name in ("run", "bench"):
            p.add_argument("--only", default="", help="ids de conversation, separes par des virgules")
            p.add_argument("--limit", type=int, default=0)
        if name in ("judge", "bench"):
            p.add_argument("--sample", type=int, default=0, help="N tours tires au sort par systeme (seed 7)")
        if name in ("report", "bench"):
            p.add_argument("--title", default="")
            p.add_argument("--no-anchor", action="store_true", help="sans l'ancrage corpus BM25 (plus rapide)")
            p.add_argument("--out", default="", help="dossier du rapport (defaut : celui du passage)")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)  # progression lisible meme redirigee vers un fichier
    load_env()
    args.fn(args)


if __name__ == "__main__":
    main()
