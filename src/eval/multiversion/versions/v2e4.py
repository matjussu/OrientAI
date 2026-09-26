"""Le cerveau v2 de l'étape 4 (`docs/cerveau/etape4/CONTRAT-etape4.md`) : prompt v1 validé par Matteo (10808),
vérificateur réglé (libellé, absence), correctifs d'outils et de boucle. Raisonnement de GLM laissé par défaut."""
from __future__ import annotations

from src.eval.multiversion.versions.v2 import V2


class V2E4(V2):
    nom = "v2e4"
    PROMPT = "v1"
    RAISONNEMENT = None


VERSION = V2E4
