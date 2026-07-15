"""Rebuild complet de l'index FAISS formations (C4, nuit 2026-06-10, Jarvis).

Full rebuild justifie (vs append ADR-048) : fiche_to_text a change depuis le
build du 10 mai (Chantier C+ 112078a exploite le champ `text` pour ~13k fiches
annexes), donc les 47220 vecteurs existants sont stales par rapport au code
courant. Le rebuild embarque les +4820 fiches C1 et realigne tout le corpus
sur le fiche_to_text actuel. Alignement positionnel vecteur[i] <-> fiche[i]
garanti par construction.

Resume-safe (ADR-015) : embeddings sauvegardes en checkpoints .npy par
tranches ; au redemarrage, reprend apres le dernier checkpoint complet.

Usage:
    cd ~/projets/OrientIA
    PYTHONPATH=. nohup .venv/bin/python scripts/rebuild_index_c4.py \
        > audit_empirique_2026-06-09/results/c4_reembed.log 2>&1 &
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from src.config import load_config
from src.rag.embeddings import fiche_to_text, embed_texts
from src.rag.index import build_index, save_index
from mistralai.client import Mistral

REPO = Path(__file__).resolve().parent.parent
FICHES = REPO / "data/processed/formations.json"
INDEX = REPO / "data/embeddings/formations.index"
CKPT_DIR = REPO / "data/embeddings/_c4_checkpoints"
BATCH = 64
CKPT_EVERY_BATCHES = 50  # 50 batches * 64 = 3200 textes par checkpoint
EXPECTED = 52040


def embed_with_retry(client: Mistral, batch: list[str], attempts: int = 6):
    delay = 2.0
    for i in range(attempts):
        try:
            return embed_texts(client, batch)
        except Exception as e:  # noqa: BLE001 - rate limit / 5xx / reseau
            if i == attempts - 1:
                raise
            print(
                f"[retry {i + 1}/{attempts}] {type(e).__name__}: {e} "
                f"- sleep {delay:.0f}s",
                flush=True,
            )
            time.sleep(delay)
            delay = min(delay * 2, 120.0)


def main() -> None:
    fiches = json.loads(FICHES.read_text())
    n = len(fiches)
    print(f"[load] {n} fiches depuis {FICHES}", flush=True)
    if n != EXPECTED:
        sys.exit(f"ABORT: attendu {EXPECTED} fiches, trouve {n}")

    texts = [fiche_to_text(f) for f in fiches]
    print(f"[texts] {len(texts)} textes prepares", flush=True)

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    done_parts = sorted(CKPT_DIR.glob("part_*.npy"))
    chunks: list[np.ndarray] = [np.load(p) for p in done_parts]
    n_done = sum(len(a) for a in chunks)
    print(
        f"[resume] {n_done} embeddings deja faits "
        f"({len(done_parts)} checkpoints)",
        flush=True,
    )

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    buf: list[list[float]] = []
    part_idx = len(done_parts)
    t0 = time.time()
    i = n_done
    while i < n:
        batch = texts[i:i + BATCH]
        buf.extend(embed_with_retry(client, batch))
        i += len(batch)
        if len(buf) >= CKPT_EVERY_BATCHES * BATCH or i >= n:
            arr = np.asarray(buf, dtype="float32")
            np.save(CKPT_DIR / f"part_{part_idx:04d}.npy", arr)
            chunks.append(arr)
            buf = []
            part_idx += 1
            rate = (i - n_done) / max(time.time() - t0, 1.0)
            eta_min = (n - i) / max(rate, 1.0) / 60.0
            print(
                f"[ckpt {part_idx:04d}] {i}/{n} ({100 * i / n:.1f}%) "
                f"- {rate:.0f} textes/s - ETA {eta_min:.0f} min",
                flush=True,
            )

    all_emb = np.vstack(chunks)
    print(f"[embed done] shape={all_emb.shape}", flush=True)
    if all_emb.shape[0] != n:
        sys.exit(f"ABORT: {all_emb.shape[0]} embeddings != {n} fiches")

    index = build_index(all_emb)
    if index.ntotal != n:
        sys.exit(f"ABORT: ntotal {index.ntotal} != {n}")
    tmp = INDEX.parent / (INDEX.name + ".tmp")
    save_index(index, tmp)
    os.replace(tmp, INDEX)
    print(f"[index] ecrit {INDEX} ntotal={index.ntotal}", flush=True)
    print("=== C4_REEMBED_DONE ===", flush=True)


if __name__ == "__main__":
    main()
