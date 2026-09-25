"""Le prompt de conseiller v0 (CONTRAT-etape3, section 7), lu tel quel dans `docs/cerveau/etape3/`."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CHEMIN = Path(__file__).resolve().parents[2] / "docs/cerveau/etape3/prompt_conseiller_v0.txt"
TEXTE = CHEMIN.read_text(encoding="utf-8").strip()
SHA = hashlib.sha256(TEXTE.encode("utf-8")).hexdigest()


def systeme(profil: dict) -> str:
    bloc = json.dumps(profil, ensure_ascii=False) if profil else "(vide : l'élève n'a encore rien dit de lui)"
    return f"{TEXTE}\n\nProfil de l'élève, tel qu'enregistré dans cette conversation : {bloc}"
