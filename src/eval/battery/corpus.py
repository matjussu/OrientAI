"""Corpus de fiches et identite stable d'une fiche.

Probleme corrige (RAPPORT 05/09 l.107 et 112, set de pertinence du 16/07) : le code identifiait
une fiche par son champ `id`, absent sur 38 596 des 52 040 fiches (mesure 23/09 sur
formations.json : `id` present sur 13 444 fiches, `url_canonical` sur 42 426 mais seulement
37 297 valeurs distinctes). Aucun champ de la fiche n'est donc une cle. Le fallback du miner
rendait `idx:-1` pour toutes les fiches sans `id`, qui se confondaient en une seule.

Cle retenue : la POSITION de la fiche dans formations.json, `idx:<position>`, comme l'index FAISS
(ligne i de l'index = fiche i). Une position ne vaut que pour une version du corpus : l'empreinte
sha256 du fichier est donc recopiee dans tout artefact qui porte des positions, et `Corpus`
refuse un artefact dont l'empreinte differe.

La position d'une fiche rendue par le pipeline se retrouve par IDENTITE d'objet (le pipeline
renvoie les dicts de la liste chargee, sans copie), jamais par une recherche sur ses champs.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from functools import cached_property
from pathlib import Path

from src.eval.battery.config import CORPUS_PATH


def fiche_key(position: int) -> str:
    return f"idx:{position}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text: str | None) -> str:
    """Minuscules sans accents, chiffres decolles des lettres (lyon1 -> lyon 1)."""
    s = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


class CorpusVersionError(RuntimeError):
    """Un artefact porte des positions calculees sur une autre version du corpus."""


class Corpus:
    def __init__(self, path: Path = CORPUS_PATH, fiches: list[dict] | None = None):
        self.path = Path(path)
        self.fiches: list[dict] = fiches if fiches is not None else json.loads(self.path.read_text())
        self._position_by_identity = {id(f): i for i, f in enumerate(self.fiches)}

    def __len__(self) -> int:
        return len(self.fiches)

    @cached_property
    def sha256(self) -> str:
        return sha256_file(self.path)

    def assert_version(self, sha256: str | None, what: str) -> None:
        if sha256 != self.sha256:
            raise CorpusVersionError(
                f"{what} a ete calcule sur le corpus {sha256}, le corpus charge est {self.sha256} : "
                "les positions ne designent plus les memes fiches.")

    def position_of(self, fiche: dict) -> int:
        """Position d'une fiche rendue par le pipeline (identite d'objet)."""
        try:
            return self._position_by_identity[id(fiche)]
        except KeyError:
            raise KeyError(
                "fiche absente de ce corpus par identite : elle a ete copiee ou vient d'une autre "
                f"liste ({fiche.get('nom')!r})") from None

    @cached_property
    def _positions_by_signature(self) -> dict[tuple, list[int]]:
        out: dict[tuple, list[int]] = {}
        for i, f in enumerate(self.fiches):
            out.setdefault(self.signature(f), []).append(i)
        return out

    @staticmethod
    def signature(f: dict) -> tuple:
        return (f.get("nom"), f.get("etablissement"), f.get("ville"), f.get("source"))

    def positions_by_signature(self, nom, etablissement, ville, source) -> list[int]:
        """Rattrapage pour les runs anterieurs au 23/09 qui n'ont pas enregistre les positions.
        Peut rendre plusieurs positions (signature partagee) : l'appelant doit le compter."""
        return self._positions_by_signature.get((nom, etablissement, ville, source), [])

    @cached_property
    def bm25(self):
        from rank_bm25 import BM25Okapi
        docs = []
        for x in self.fiches:
            parts = [x.get("nom"), x.get("etablissement"), x.get("ville"), x.get("fili_code"),
                     x.get("type_diplome"), x.get("domaine"), x.get("mention"), x.get("parcours"),
                     x.get("discipline"), x.get("detail"), (x.get("text") or "")[:300]]
            docs.append(norm(" ".join(p for p in parts if isinstance(p, str))).split())
        return BM25Okapi(docs)

    def search(self, query: str, k: int = 10, mask=None) -> list[int]:
        """Positions des k meilleures fiches BM25 (score > 0), filtre optionnel."""
        import numpy as np
        scores = self.bm25.get_scores(norm(query).split())
        if mask is not None:
            scores = np.where(mask, scores, -1.0)
        return [int(i) for i in np.argsort(-scores)[:k] if scores[i] > 0]
