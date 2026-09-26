"""Variante de `v2e4` avec `reasoning_effort="low"` (choix D3 de Matteo : « none » le 26/09 à 16h10, Telegram 10808 ;
refusé par l'API, valeurs admises low, high, max ; « low » le 26/09 à 18h16, Telegram 10818). CONTRAT-etape4,
sections 8, 11 et 15.4. Retenue selon la règle de l'amendement v1.2 (section 15.4)."""
from __future__ import annotations

from src.eval.multiversion.versions.v2 import V2


class V2E4R(V2):
    nom = "v2e4r"
    PROMPT = "v1"
    RAISONNEMENT = "low"


VERSION = V2E4R
