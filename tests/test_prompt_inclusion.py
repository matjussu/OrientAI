"""Gate CI d'inclusion de prompt (H1 lot 1, ordre 2026-07-16-0905).

Constat de l'audit 15/07 : « le chemin servi n'est pas le chemin certifié ».
Les règles R8 (alternative cadrée) et R9 (citation entrelacée) vivaient dans
system.py legacy NON servi ; le prompt servi (v4 strict + son dérivé récit)
ne les contenait pas.

Ce test verrouille l'inclusion des règles dans ce qui est RÉELLEMENT servi :
il passe par `_build_chat_kwargs` (l'assemblage des messages utilisé par
`generate()` ET `generate_stream()`), pas par les constantes de module.
Toute règle qui disparaît du prompt servi (refactor de découpage narratif,
split raté, suppression accidentelle) fait échouer la CI.
"""
from __future__ import annotations

import pytest

from src.rag.generator import _build_chat_kwargs

# Invariants par règle : (marqueur de titre, phrase pivot porteuse du sens).
# Si l'un des deux disparaît du prompt servi, le gate est rouge.
RULE_INVARIANTS = [
    ("### R1 — Chiffres", "UNIQUEMENT** citer les valeurs présentes dans le bloc `chiffres`"),
    ("### R2 — Identité des formations", "Je n'ai pas de formation pertinente dans mes sources"),
    ("### R3 — Citations sources", "[source SX]"),
    ("### R4 — Style", "ne reprends **JAMAIS** les chiffres ni les noms de formations cités dans cet exemple Golden"),
    ("### R5 — Posture", "Termine par une question ouverte"),
    ("### R7 — CONTRAINTES HARDLOCK", "Contrainte non satisfaisable"),
    # R8/R9 — portées du legacy vers le prompt servi (H1 lot 1.1)
    ("### R8 — ALTERNATIVE CADRÉE", "Je n'ai pas [cible précise] dans mes sources"),
    ("### R8 — ALTERNATIVE CADRÉE", "substitution déguisée"),
    ("### R9 — CITATION ENTRELACÉE", "nommée AVANT le chiffre"),
    ("### R9 — CITATION ENTRELACÉE", "Jamais de bloc « Sources : S1, S2… » en fin de réponse"),
]

# R6 (cap 250 mots) est VOLONTAIREMENT absent du mode récit (remplacé par la
# structure sectionnée) : inclus seulement dans les invariants v4 strict.
R6_INVARIANT = ("### R6 — LONGUEUR", "MAX 250 mots")


def _served_system_prompt(**overrides) -> str:
    """Prompt system tel qu'assemblé par le chemin de génération réel."""
    kwargs = dict(
        retrieved=[],
        question="Quelles études pour devenir infirmier ?",
        model="mistral-medium-latest",
        temperature=0.3,
        inject_user_level=False,
        system_prompt_override=None,
        golden_qa_prefix=None,
        history=None,
        hint_block="",
        use_strict_v4=True,
        hardlock_block="",
    )
    kwargs.update(overrides)
    chat_kwargs = _build_chat_kwargs(**kwargs)
    messages = chat_kwargs["messages"]
    assert messages[0]["role"] == "system"
    return messages[0]["content"]


@pytest.fixture(scope="module")
def prompt_v4() -> str:
    return _served_system_prompt()


@pytest.fixture(scope="module")
def prompt_narratif() -> str:
    return _served_system_prompt(narrative_mode=True)


@pytest.mark.parametrize("titre,pivot", RULE_INVARIANTS)
def test_regle_servie_v4_strict(prompt_v4, titre, pivot):
    assert titre in prompt_v4, f"titre absent du prompt servi v4 : {titre}"
    assert pivot in prompt_v4, f"phrase pivot absente du prompt servi v4 : {pivot}"


def test_r6_servie_v4_strict(prompt_v4):
    titre, pivot = R6_INVARIANT
    assert titre in prompt_v4
    assert pivot in prompt_v4


@pytest.mark.parametrize("titre,pivot", RULE_INVARIANTS)
def test_regle_servie_mode_recit(prompt_narratif, titre, pivot):
    """Le prompt récit est DÉRIVÉ de v4 strict par découpage (system_narrative).
    Ce test verrouille que le découpage n'ampute aucune règle du contrat
    (R6 excepté, remplacé sciemment par la structure sectionnée)."""
    assert titre in prompt_narratif, f"titre absent du prompt servi récit : {titre}"
    assert pivot in prompt_narratif, f"phrase pivot absente du prompt servi récit : {pivot}"


def test_r6_volontairement_absente_du_recit(prompt_narratif):
    """Si R6 réapparaît dans le récit, le découpage de system_narrative a
    changé de sémantique : à re-décider explicitement, pas silencieusement."""
    assert R6_INVARIANT[0] not in prompt_narratif


def test_hardlock_precede_les_regles(prompt_v4):
    """Le bloc hardlock R7 injecté en tête doit précéder le contrat."""
    prompt = _served_system_prompt(
        hardlock_block="## CONTRAINTES HARDLOCK (R7)\n- région : bretagne",
    )
    assert prompt.index("CONTRAINTES HARDLOCK") < prompt.index("### R1")
