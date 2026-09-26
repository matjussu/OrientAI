"""Le prompt de conseiller, lu tel quel dans `docs/cerveau/`.

- v0 : CONTRAT-etape3, section 7 (`docs/cerveau/etape3/prompt_conseiller_v0.txt`) ;
- v1 : CONTRAT-etape4, section 5 (`docs/cerveau/etape4/prompt_conseiller_v1.txt`), validé tel quel par Matteo le
  26/09 à 16h10 (Telegram 10808) : son sha256 est figé ici, et un fichier modifié refuse de se charger.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DOSSIER = Path(__file__).resolve().parents[2] / "docs/cerveau"
CHEMINS = {"v0": DOSSIER / "etape3/prompt_conseiller_v0.txt", "v1": DOSSIER / "etape4/prompt_conseiller_v1.txt"}
# sha256 du FICHIER validé (octets), celui que Jarvis a comparé à la pièce jointe reçue par Matteo (cmp identique).
VALIDES = {"v1": "145f0dd5a53c7b91b3393d0c111a795345125aba1a1641dc2559f14943e02352"}


class PromptModifie(RuntimeError):
    pass


def _lire(version: str) -> str:
    octets = CHEMINS[version].read_bytes()
    attendu = VALIDES.get(version)
    if attendu and hashlib.sha256(octets).hexdigest() != attendu:
        raise PromptModifie(f"prompt {version} modifié depuis sa validation (sha256 attendu {attendu[:12]})")
    return octets.decode("utf-8").strip()


TEXTES = {v: _lire(v) for v in CHEMINS}
SHAS = {v: hashlib.sha256(t.encode("utf-8")).hexdigest() for v, t in TEXTES.items()}
SHAS_FICHIER = {v: hashlib.sha256(c.read_bytes()).hexdigest() for v, c in CHEMINS.items()}
# Compatibilité avec l'étape 3 (empreinte de la version `v2` du lanceur).
TEXTE, SHA = TEXTES["v0"], SHAS["v0"]


def systeme(profil: dict, version: str = "v1") -> str:
    bloc = json.dumps(profil, ensure_ascii=False) if profil else "(vide : l'élève n'a encore rien dit de lui)"
    return f"{TEXTES[version]}\n\nProfil de l'élève, tel qu'enregistré dans cette conversation : {bloc}"
