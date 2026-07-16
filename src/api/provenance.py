"""Fingerprint de provenance par réponse (H1 lot 1.5, ordre 2026-07-16-0905).

Constat de l'audit 15/07 : impossible de savoir a posteriori QUELLE version
de prompt / corpus / index a produit une réponse donnée (les artefacts
changent sans trace dans les logs). Ce module calcule UNE FOIS au boot un
fingerprint compact et stable :

- ``prompt``  : sha256 des deux prompts system servis (v4 strict assemblé +
  récit dérivé), 12 hex. Change si une règle bouge.
- ``corpus``  : sha256 du fichier formations.json servi, 12 hex.
- ``index``   : sha256 du fichier FAISS servi, 12 hex.
- ``models``  : versions PINNÉES (cf src/rag/models.py), déjà lisibles mais
  répétées ici pour que le fingerprint soit autoportant dans un log.

Coût : ~1.5 s de hashing au boot (110 MB + 213 MB), zéro coût par requête
(dict figé). Format compact voulu (12 hex par artefact) pour ne pas gonfler
les logs par réponse.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from src.rag.models import MISTRAL_EMBED, MISTRAL_MEDIUM, MISTRAL_SMALL

_SHORT = 12


def _sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:_SHORT]


def _prompt_hash() -> str:
    """Hash des prompts system SERVIS (assemblés par le vrai chemin)."""
    from src.prompt.system_narrative import build_narrative_system_prompt
    from src.prompt.system_v4_strict import build_system_prompt_v4_strict

    payload = build_system_prompt_v4_strict() + "\n---\n" + build_narrative_system_prompt()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:_SHORT]


def build_fingerprint(fiches_path: str | Path, index_path: str | Path) -> dict:
    """Fingerprint autoportant, calculé une fois au lifespan startup.

    Les erreurs de hashing fichier (artefact absent en test) donnent "absent"
    plutôt qu'un crash : le fingerprint est de l'observabilité, jamais un
    point de panne.
    """
    def _safe(path: str | Path) -> str:
        try:
            return _sha256_file(path)
        except OSError:
            return "absent"

    return {
        "prompt": _prompt_hash(),
        "corpus": _safe(fiches_path),
        "index": _safe(index_path),
        "model_gen": MISTRAL_MEDIUM,
        "model_aux": MISTRAL_SMALL,
        "model_embed": MISTRAL_EMBED,
    }
