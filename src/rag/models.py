"""Versions de modèles PINNÉES (H1 lot 1.5, ordre 2026-07-16-0905).

Fin des alias ``-latest`` sur le chemin servi : un alias mobile change de
modèle sans signal (drift silencieux de comportement ET des embeddings).
Chaque constante ci-dessous est la version DATÉE que l'alias résolvait au
moment du pin (vérifié contre GET /v1/models le 2026-07-16, champ aliases).

- ``MISTRAL_MEDIUM`` : génération (contrat v4 strict + récit).
- ``MISTRAL_SMALL``  : scope classifier, router, layer3.
- ``MISTRAL_EMBED``  : embeddings requêtes ET corpus. LE PLUS SENSIBLE :
  l'index FAISS (52 040 × 1024) a été construit avec ``mistral-embed``,
  qui n'a jamais eu qu'une seule version datée (2312, créée 2023-12) —
  le pin est donc PAR CONSTRUCTION la version de l'index. Si Mistral
  publie un jour un nouvel embed, NE PAS bumper cette constante sans
  re-embed complet du corpus (~5-10 EUR) + gate golden retrieval.

Montée de version = décision EXPLICITE : nouvelle valeur ici, gate
avant/après sur golden (cf audit_empirique golden_ci), trace ADR.
"""
from __future__ import annotations

# mistral-medium-latest résolvait vers mistral-medium-2604 le 2026-07-16
MISTRAL_MEDIUM = "mistral-medium-2604"
# mistral-small-latest résolvait vers mistral-small-2603 le 2026-07-16
MISTRAL_SMALL = "mistral-small-2603"
# mistral-embed n'a qu'une version datée : 2312 (celle de l'index FAISS)
MISTRAL_EMBED = "mistral-embed-2312"
# mistral-large-latest résolvait vers mistral-large-2512 le 2026-07-16
# (utilisé par ProfileClarifier.clarify(), chemin agent ; le chemin récit
# servi utilise narrative_model = MISTRAL_SMALL)
MISTRAL_LARGE = "mistral-large-2512"
