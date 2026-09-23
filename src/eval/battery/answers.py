"""Empreinte d'une reponse : relie un verdict ou un tour derive a la reponse exacte qu'il vise."""
from __future__ import annotations

import hashlib


def answer_sha(rec: dict) -> str:
    return hashlib.sha256((rec.get("answer") or "").encode()).hexdigest()[:12]
