"""Constantes du banc : chemins, modeles epingles, prix, prompts.

Tout ce qui fixe le resultat d'un passage vit ici, pour que le manifeste d'un run
puisse le recopier tel quel (cf runner.update_manifest).
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent

BATTERY_PATH = PACKAGE / "battery.json"
CORPUS_PATH = REPO / "data/processed/formations.json"
INDEX_PATH = REPO / "data/embeddings/formations.index"
RESULTS_DIR = REPO / "results/battery"

# Identifiants epingles (jamais de -latest : un alias qui bouge rend deux passages incomparables).
MODELS = {
    "claude_sonnet": "claude-sonnet-5",
    "claude_opus": "claude-opus-5",
    "gpt": "gpt-5.5",
    "mistral_medium": "mistral-medium-2604",
    # Mistral Large le plus recent expose par l'API au 23/09/2026 (models.list, hors alias -latest).
    "mistral_large": "mistral-large-2512",
}

# USD par million de tokens (entree, sortie). Suivi budgetaire seulement, jamais une mesure :
# les prix marques "suppose" n'ont pas ete verifies sur une facture.
PRICES = {
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
    "gpt-5.5": (2.5, 15.0),            # suppose
    "mistral-medium-2604": (0.4, 2.0),  # suppose
    "mistral-large-2512": (0.5, 1.5),   # suppose
}

# Historique rejoue a chaque tour, en messages (le serving garde les 6 derniers).
HISTORY_WINDOW = 6

SYSTEM_PROMPT_BASELINE = (
    "Tu es un conseiller d'orientation expert du systeme educatif francais. Nous sommes en "
    "septembre 2026. Tu conseilles des lyceens (Parcoursup) et des etudiants du superieur "
    "(licence, master, prepa, BUT, BTS, reorientation). Reponds en francais, de facon concrete "
    "et personnalisee : nomme des formations et etablissements precis quand c'est pertinent, "
    "donne des chiffres (taux d'acces, insertion, cout) quand tu en es sur, et dis clairement "
    "quand tu n'es pas sur ou que l'information a pu changer. Pose au plus une question de "
    "clarification si le profil est trop vague. Reste concis (250 a 450 mots)."
)

SYSTEM_PROMPT_CTX = SYSTEM_PROMPT_BASELINE + (
    "\n\nTu disposes ci-dessous de FICHES issues d'une base de donnees officielle (Parcoursup, "
    "MonMaster, ONISEP, RNCP, InserJeunes...). Appuie-toi d'abord sur ces fiches pour les "
    "references et les chiffres, et signale explicitement ce qui vient de ta connaissance "
    "generale et non des fiches. Si les fiches ne repondent pas a la question, dis-le et "
    "reponds quand meme au mieux avec ta connaissance generale."
)


def price_usd(model: str | None, tokens_in: int, tokens_out: int) -> float | None:
    """Cout estime d'un passage, None si le modele n'a pas de prix connu."""
    if model not in PRICES:
        return None
    pin, pout = PRICES[model]
    return (tokens_in * pin + tokens_out * pout) / 1e6
