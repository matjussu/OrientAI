"""Joue la batterie sur un systeme et ecrit `<run_dir>/<systeme>.jsonl`, un tour par ligne.

Reprise : les conversations deja completes dans le fichier sont sautees ; une conversation
interrompue ou dont un tour est en erreur est rejouee en entier (l'historique d'un tour depend
des reponses precedentes, et une panne de transport n'est pas une reponse du systeme).
Pendant un passage, un tour en erreur est garde avec son erreur et la batterie continue ; le
nombre d'erreurs est ecrit dans le manifeste, et le rapport compte celles qui restent.
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


class IncompleteAnswer(RuntimeError):
    """Reponse coupee (plafond de tokens, boucle d'outils epuisee) ou vide : c'est une panne du
    passage, pas une reponse du systeme. Le tour part en erreur et sera rejoue."""


def play_conversation(system, item: dict) -> list[dict]:
    history: list[dict] = []
    records = []
    for turn, question in enumerate(item["turns"]):
        t0 = time.time()
        try:
            result, error = system.ask(question, history, key=(item["id"], turn)), None
            if not (result.get("answer") or "").strip():
                raise IncompleteAnswer("reponse vide")
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
    """Conversations dont tous les tours sont presents et sans erreur."""
    n_turns = {it["id"]: len(it["turns"]) for it in battery}
    seen: dict[str, set[int]] = {}
    failed = {r["id"] for r in records if r.get("error")}
    for r in records:
        seen.setdefault(r["id"], set()).add(r["turn"])
    return {cid for cid, turns in seen.items()
            if len(turns) == n_turns.get(cid, -1) and cid not in failed}


def play(system, battery: list[dict], out: Path, workers: int = 3, log=print,
         selection: list[str] | None = None) -> dict:
    """Joue les conversations manquantes de `selection` (toute la batterie par defaut), rend le
    cout du passage. `battery` est toujours la batterie COMPLETE : les conversations hors
    selection gardent leurs tours tels quels."""
    existing = read_jsonl(out)
    done = complete_conversations(existing, battery)
    wanted = set(selection) if selection is not None else {it["id"] for it in battery}
    todo = [it for it in battery if it["id"] in wanted and it["id"] not in done]
    replayed = {it["id"] for it in todo}
    kept = [r for r in existing if r["id"] not in replayed]
    if len(kept) < len(existing):
        # conversations interrompues ou en erreur : retirees pour etre rejouees d'un bloc
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept))
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


def _relative(path: Path) -> str:
    path = Path(path).resolve()
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False).stdout.strip()


def battery_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_manifest(run_dir: Path) -> dict:
    path = Path(run_dir) / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def assert_same_battery(run_dir: Path, battery_path: Path) -> None:
    """Un dossier de passage = une batterie. A appeler AVANT de jouer."""
    manifest = read_manifest(run_dir)
    if manifest and manifest["battery_sha256"] != battery_sha256(battery_path):
        raise ValueError(f"{run_dir} a ete joue sur une autre batterie "
                         f"({manifest.get('battery_path', 'src/eval/battery/battery.json')}) : choisir un autre --tag")


def code_state() -> dict:
    """Commit du code charge. A lire AU LANCEMENT : un commit fait pendant un passage long ne
    change pas le code deja importe (23/09 : manifeste ecrit apres un commit intermediaire)."""
    return {"git_commit": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain", "--", "src"))}


def update_manifest(run_dir: Path, corpus_sha256: str | None, event: dict,
                    battery_path: Path = BATTERY_PATH, code: dict | None = None) -> dict:
    """Ecrit ce qui fixe le resultat d'un passage : code, batterie, corpus, modeles, couts.
    Chaque etape porte le commit du code qui l'a jouee."""
    code = code or code_state()
    path = run_dir / "manifest.json"
    assert_same_battery(run_dir, battery_path)
    sha = battery_sha256(battery_path)
    if path.exists():
        manifest = json.loads(path.read_text())
    else:
        manifest = {
            "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            **code,
            "battery_path": _relative(battery_path),
            "battery_sha256": sha,
            "corpus_sha256": corpus_sha256,
            "models": MODELS,
            "events": [],
        }
    if corpus_sha256 and not manifest.get("corpus_sha256"):
        manifest["corpus_sha256"] = corpus_sha256
    manifest["events"].append({"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                               **code, **event})
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    return manifest
