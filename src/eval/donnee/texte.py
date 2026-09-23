"""Accès à `fiche_to_text` d'une révision git donnée, pour mesurer un avant / après.

`charger_fiche_to_text(None)` rend la version du code courant. `charger_fiche_to_text("origin/main")`
rend celle de main, chargée depuis `git show` dans un module isolé : la mesure « avant » se
rejoue sans checkout ni worktree.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
_FICHIERS_TEXTE = ("src/rag/embeddings.py", "src/rag/texte_parcoursup.py")


def charger_fiche_to_text(revision: str | None = None) -> Callable[[dict], str]:
    if revision is None:
        from src.rag.embeddings import fiche_to_text

        return fiche_to_text

    dossier = Path(tempfile.mkdtemp(prefix="fiche_to_text_"))
    for chemin in _FICHIERS_TEXTE:
        rep = subprocess.run(
            ["git", "-C", str(RACINE), "show", f"{revision}:{chemin}"],
            capture_output=True, text=True, check=False,
        )
        if rep.returncode == 0:
            (dossier / Path(chemin).name).write_text(rep.stdout, encoding="utf-8")
        elif chemin.endswith("embeddings.py"):
            raise RuntimeError(f"{chemin} introuvable à la révision {revision} : {rep.stderr.strip()}")

    # Le module `texte_parcoursup` de la révision (s'il existe) doit être celui qu'importe
    # son `embeddings.py`, pas celui du code courant ; l'état de sys.modules est restauré après.
    cle = "src.rag.texte_parcoursup"
    absent = object()
    precedent = sys.modules.get(cle, absent)
    try:
        if (dossier / "texte_parcoursup.py").exists():
            spec_tp = importlib.util.spec_from_file_location(cle, dossier / "texte_parcoursup.py")
            module_tp = importlib.util.module_from_spec(spec_tp)
            spec_tp.loader.exec_module(module_tp)
            sys.modules[cle] = module_tp
        spec = importlib.util.spec_from_file_location(f"_embeddings_{abs(hash(revision))}", dossier / "embeddings.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if precedent is absent:
            sys.modules.pop(cle, None)
        else:
            sys.modules[cle] = precedent
    return module.fiche_to_text
