"""Joue la batterie sur un systeme et ecrit `<run_dir>/<systeme>.jsonl`, un tour par ligne.

Reprise : les conversations deja completes dans le fichier sont sautees ; une conversation
interrompue est rejouee en entier (l'historique d'un tour depend des reponses precedentes).
Un tour en erreur est garde avec son erreur et la batterie continue : le rapport compte les
erreurs, il ne les masque pas.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.eval.battery.config import BATTERY_PATH, MODELS, REPO, price_usd


def load_battery(path: Path = BATTERY_PATH) -> list[dict]:
    return json.loads(Path(path).read_text())["items"]


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def by_turn(records: list[dict]) -> dict[tuple[str, int], dict]:
    return {(r["id"], r["turn"]): r for r in records}


def play_conversation(system, item: dict) -> list[dict]:
    history: list[dict] = []
    records = []
    for turn, question in enumerate(item["turns"]):
        t0 = time.time()
        try:
            result, error = system.ask(question, history, key=(item["id"], turn)), None
        except Exception as e:  # noqa: BLE001 - une panne d'API ne doit pas arreter la batterie
            result = {"answer": "", "sources": [], "source_positions": []}
            error = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}"
        records.append({
            "id": item["id"], "turn": turn, "persona": item["persona"],
            "domaine": item.get("domaine"), "tags": item["tags"], "question": question,
            "history": list(history), "latency_s": round(time.time() - t0, 2), "error": error,
            **result,
        })
        history = history + [{"role": "user", "content": question},
                             {"role": "assistant", "content": result["answer"] or "(erreur)"}]
    return records


def complete_conversations(records: list[dict], battery: list[dict]) -> set[str]:
    n_turns = {it["id"]: len(it["turns"]) for it in battery}
    seen: dict[str, set[int]] = {}
    for r in records:
        seen.setdefault(r["id"], set()).add(r["turn"])
    return {cid for cid, turns in seen.items() if len(turns) == n_turns.get(cid, -1)}


def play(system, battery: list[dict], out: Path, workers: int = 3, log=print) -> dict:
    """Joue les conversations manquantes, rend le cout du passage."""
    existing = read_jsonl(out)
    done = complete_conversations(existing, battery)
    if len(done) < len({r["id"] for r in existing}):
        # conversations interrompues : on les retire pour les rejouer d'un bloc
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in existing if r["id"] in done))
    todo = [it for it in battery if it["id"] not in done]
    log(f"[{system.name}] {len(todo)} conversations a jouer ({len(done)} deja faites)")

    tokens_in = tokens_out = errors = 0
    usage_reported = False
    t0 = time.time()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a") as fh, ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(play_conversation, system, it) for it in todo]
        for fut in as_completed(futures):
            for rec in fut.result():
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
                fh.flush()
                usage = rec.get("usage") or {}
                usage_reported |= bool(usage)
                tokens_in += usage.get("in", 0)
                tokens_out += usage.get("out", 0)
                errors += bool(rec["error"])
                log(f"  {'ERR' if rec['error'] else 'ok '} {rec['id']}.{rec['turn']} {rec['latency_s']}s "
                    f"{len(rec['answer'] or '')}c fiches={len(rec.get('source_positions') or [])}")
    # Un systeme qui ne remonte pas ses tokens (le pipeline local) a un cout NON MESURE, pas nul.
    cost = price_usd(getattr(system, "model", None), tokens_in, tokens_out) if usage_reported else None
    stats = {"system": system.name, "model": getattr(system, "model", None), "played": len(todo),
             "errors": errors, "tokens_in": tokens_in if usage_reported else None,
             "tokens_out": tokens_out if usage_reported else None,
             "cost_usd": None if cost is None else round(cost, 3), "seconds": round(time.time() - t0)}
    if hasattr(system, "fingerprint"):
        stats["fingerprint"] = system.fingerprint
    return stats


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def update_manifest(run_dir: Path, corpus_sha256: str | None, event: dict) -> dict:
    """Ecrit ce qui fixe le resultat d'un passage : code, batterie, corpus, modeles, couts."""
    path = run_dir / "manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else {
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--", "src")),
        "battery_sha256": hashlib.sha256(BATTERY_PATH.read_bytes()).hexdigest(),
        "corpus_sha256": corpus_sha256,
        "models": MODELS,
        "events": [],
    }
    if corpus_sha256 and not manifest.get("corpus_sha256"):
        manifest["corpus_sha256"] = corpus_sha256
    manifest["events"].append({"at": dt.datetime.now().isoformat(timespec="seconds"), **event})
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    return manifest
