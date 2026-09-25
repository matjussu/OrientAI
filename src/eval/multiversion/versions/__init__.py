"""Versions branchables du pipeline. Une version = un module `versions/<nom>.py` qui expose `VERSION`, une classe
construite sans argument, avec :

    nom       str, identique au nom du module
    fils      nombre de conversations jouées en parallèle (1 si la version a un état partagé entre tours)
    modeles   modèles épinglés appelés (pour le manifeste)
    empreinte()                   dict ou None : ce qui prouve quel code a été joué (comparé au lancement)
    ask(question, history) -> dict
        reponse   texte lu par l'élève
        sources   fiches exposées [{titre, etablissement, ville, source, score, texte}], [] si aucune
        source_positions  positions corpus de ces fiches (cle de numbers.py), None par fiche introuvable
        usage     {modele: {"entree", "sortie", "non_mesures"}} : tokens réels remontés par l'API
        trace     dict libre (routeur, court-circuit, validation...) repris dans l'état des lieux
        modele    modèle de génération

Brancher une version (le v2 à l'étape 3) = ajouter un module ici ; le lanceur n'est pas modifié.
"""
from __future__ import annotations

import importlib
import pkgutil


def disponibles() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith("_"))


def charger(nom: str):
    if nom not in disponibles():
        raise SystemExit(f"version inconnue : {nom} (disponibles : {', '.join(disponibles())})")
    classe = importlib.import_module(f"{__name__}.{nom}").VERSION
    version = classe()
    if version.nom != nom:
        raise SystemExit(f"versions/{nom}.py expose une version nommée {version.nom!r}")
    return version
