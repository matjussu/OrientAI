"""Variante de `v2e4` avec `reasoning_effort="none"` (choix D3 de Matteo, 10808 ; CONTRAT-etape4, sections 8 et 11).
Retenue seulement si l'API l'accepte pour zai-glm-5-3 et si le gate F ne recule pas (règle de la section 11)."""
from __future__ import annotations

from src.eval.multiversion.versions.v2 import V2


class V2E4R(V2):
    nom = "v2e4r"
    PROMPT = "v1"
    RAISONNEMENT = "none"


VERSION = V2E4R
