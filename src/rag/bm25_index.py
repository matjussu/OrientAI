"""BM25 lexical index — Phase C complement au retrieval dense FAISS.

Phase C ADR-058 (workaround Phase 3). BM25 (Best Matching 25) est un
algorithme de scoring lexical exact qui complémente le retrieval sémantique
dense (FAISS + Mistral embed). Pour les questions à **entités nommées**
(CROUS Lyon, RNCP 38450, PCS 37) ou **termes techniques exacts**
("L1 bac S mention bien", "doctorat chimie"), BM25 bat souvent dense.

## Cas d'usage spécifique au projet

Les corpora annexes (CROUS, INSEE, parcours_bacheliers, doctorat IP) ont
des `text` courts/stat dont l'embedding est mal aligné face aux questions
naturelles (cf finding investigation 2026-05-08). BM25 retrieve ces fiches
correctement via match lexical sur les entités exactes.

## Architecture

- Build : tokenize tous les `text` des fiches → BM25Okapi index
- Search : tokenize question → BM25 top-K avec scores
- Fusion via RRF (Reciprocal Rank Fusion) avec retrieval dense FAISS

## Dépendance

`rank_bm25` (pure Python, pas de C, MIT license). Léger et stable.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from rank_bm25 import BM25Okapi

from src.rag.sigle_expand import sigle_injection_text


# Stopwords FR minimaux — évite que "le", "la", "des" pollue le scoring
# tout en gardant les mots-outils signifiants ("après", "avec", "comment").
_FR_STOPWORDS = frozenset({
    "le", "la", "les", "un", "une", "des", "du", "de", "d",
    "et", "ou", "à", "a", "au", "aux", "en", "dans", "sur", "par",
    "ce", "cet", "cette", "ces", "se", "s", "sa", "son", "ses", "leur", "leurs",
    "qui", "que", "qu", "quoi", "dont", "où",
    "est", "sont", "être", "avoir", "fait", "faire",
    "il", "elle", "on", "nous", "vous", "ils", "elles", "je", "j", "tu", "me", "te",
    "pas", "ne", "n", "y",
})


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def _tokenize(text: str) -> list[str]:
    """Tokenization simple : lowercase, strip accents, split alphanumérique,
    filter stopwords. Pas de stemming (overkill pour BM25 + simple)."""
    if not text:
        return []
    norm = _strip_accents(str(text)).lower()
    # Garde les mots alphanumériques (incluant chiffres pour entités type "PCS 37")
    tokens = re.findall(r"[a-z0-9]+", norm)
    return [t for t in tokens if len(t) > 1 and t not in _FR_STOPWORDS]


def _fiche_to_search_text(fiche: dict[str, Any]) -> str:
    """Concatène les champs textuels signifiants d'une fiche pour indexation BM25.

    Stratégie : champs prioritaires (nom/libelle/text) en premier, puis
    enrichissement (etablissement, ville, region, codes_rome, debouches).
    Le BM25Okapi pondère naturellement les termes rares — pas besoin de
    boost manuel par champ.
    """
    parts: list[str] = []
    # Nom/libelle (cascade similar à fact_card._pick_formation_name)
    for key in ("nom", "libelle_metier", "nom_metier", "libelle",
                "intitule", "libelle_diplome", "libelle_formation",
                "fap_libelle", "subject"):
        v = fiche.get(key)
        if v:
            parts.append(str(v))
    # Texte retrievable
    for key in ("text", "detail"):
        v = fiche.get(key)
        if v:
            parts.append(str(v))
    # Identification
    for key in ("etablissement", "ville", "region", "departement",
                "type_diplome", "niveau", "discipline", "domaine"):
        v = fiche.get(key)
        if v:
            parts.append(str(v))
    # ID stable (utile pour les questions à code RNCP/MET/etc.)
    if fiche.get("id"):
        parts.append(str(fiche["id"]))
    # Codes ROME (identifiants exacts)
    codes = fiche.get("codes_rome") or []
    if isinstance(codes, list):
        for c in codes:
            if isinstance(c, dict):
                code = c.get("code")
                if code:
                    parts.append(str(code))
            elif isinstance(c, str):
                parts.append(c)
    # Debouches (libellés métiers)
    deb = fiche.get("debouches") or []
    if isinstance(deb, list):
        for d in deb:
            if isinstance(d, dict):
                lib = d.get("libelle")
                if lib:
                    parts.append(str(lib))
            elif isinstance(d, str):
                parts.append(d)
    # J2 enrichissement — injection sigle (additif) : symétrique à fiche_to_text
    # (dense) pour que BM25 matche l'acronyme nu des fiches forme-longue.
    inj = sigle_injection_text(fiche)
    if inj:
        parts.append(inj)
    return " ".join(parts)


class BM25Index:
    """BM25 lexical index sur le corpus de fiches.

    Build O(N) au démarrage, search O(N) par query (rapide même sur 47k
    fiches : ~50ms typique).

    Usage :
        bm25 = BM25Index(fiches)
        top = bm25.search("CROUS Lyon logement", k=30)
        # → [{"fiche": ..., "score_bm25": 12.4, "rank_bm25": 1}, ...]
    """

    def __init__(self, fiches: list[dict[str, Any]]):
        self._fiches = fiches
        self._tokenized_corpus: list[list[str]] = []
        # Tokenize chaque fiche, garantir au moins 1 token (placeholder
        # pour les fiches vides — évite ZeroDivisionError dans BM25Okapi).
        # Vague 1.C — fiches retrieval_eligible=false reçoivent un token
        # placeholder unique (`__retrieval_excluded__`) jamais utilisé en
        # query → score BM25 toujours ~0 → jamais dans top-K. Préserve
        # l'invariant `len(_fiches) == len(_tokenized_corpus)` aligné avec
        # l'index FAISS unifié.
        for f in fiches:
            if isinstance(f, dict) and f.get("retrieval_eligible") is False:
                self._tokenized_corpus.append(["__retrieval_excluded__"])
                continue
            tokens = _tokenize(_fiche_to_search_text(f))
            if not tokens:
                tokens = ["__empty__"]
            self._tokenized_corpus.append(tokens)
        # Build BM25Okapi — skip si corpus complètement vide
        if not self._tokenized_corpus:
            self._bm25 = None
        else:
            try:
                self._bm25 = BM25Okapi(self._tokenized_corpus)
            except ZeroDivisionError:
                # Corpus avec uniquement des placeholders — pas de signal BM25 réel
                self._bm25 = None

    def search(self, question: str, k: int = 30) -> list[dict[str, Any]]:
        """Top-K fiches par score BM25.

        Returns liste de {"fiche": dict, "score_bm25": float, "rank_bm25": int (1-based)}.
        Trié par score décroissant.
        """
        if self._bm25 is None:
            return []
        query_tokens = _tokenize(question)
        if not query_tokens:
            return []
        scores = self._bm25.get_scores(query_tokens)
        # Top-K via argpartition pour rapidité O(N + k log k)
        if k >= len(scores):
            top_indices = scores.argsort()[::-1]
        else:
            # numpy argpartition pour top-K
            import numpy as np
            top_unsorted = np.argpartition(scores, -k)[-k:]
            top_indices = top_unsorted[np.argsort(scores[top_unsorted])[::-1]]
        results = []
        for rank, idx in enumerate(top_indices[:k]):
            score = float(scores[int(idx)])
            if score <= 0.0:
                continue  # Pas de match BM25
            results.append({
                "fiche": self._fiches[int(idx)],
                "score_bm25": score,
                "rank_bm25": rank + 1,
                "_orig_index": int(idx),
            })
        return results

    @property
    def n_fiches(self) -> int:
        return len(self._fiches)


def reciprocal_rank_fusion(
    rankings: list[list[dict[str, Any]]],
    k_rrf: int = 60,
    id_key: str = "_orig_index",
) -> list[dict[str, Any]]:
    """Fusion de plusieurs rankings via Reciprocal Rank Fusion (RRF).

    RRF est la méthode de fusion standard en RAG hybride 2024+ — robuste,
    sans calibration de hyperparamètres entre les scores des différents
    retrievers (dense FAISS vs BM25 ont des échelles très différentes).

    Formule : pour chaque document d présent dans au moins un ranking :
        rrf_score(d) = sum over each ranking r: 1 / (k_rrf + rank_in_r(d))

    Args:
        rankings: liste de listes de results. Chaque result doit avoir
            un identifiant stable accessible via `id_key` (par défaut
            `_orig_index` qui est l'idx du fiche dans le corpus original).
        k_rrf: paramètre standard RRF (60 par défaut, valeur recommandée
            par les papers Cormack et al. 2009).
        id_key: clé d'identifiant dans les results.

    Returns:
        Liste fusionnée et triée par RRF score décroissant. Chaque item :
        - "fiche": dict (de la 1re occurrence)
        - "score_rrf": float
        - "score_dense": float (de FAISS, si présent)
        - "score_bm25": float (de BM25, si présent)
        - "ranks": dict {ranker_index: rank}
    """
    # Map id → entry (premier vu)
    fused: dict[Any, dict[str, Any]] = {}
    for ranker_idx, ranking in enumerate(rankings):
        for rank, result in enumerate(ranking):
            doc_id = result.get(id_key)
            if doc_id is None:
                # Fallback : utiliser id du fiche
                fiche = result.get("fiche") or {}
                doc_id = fiche.get("id") or id(fiche)
            entry = fused.setdefault(doc_id, {
                "fiche": result.get("fiche"),
                "score_rrf": 0.0,
                "score_dense": None,
                "score_bm25": None,
                "ranks": {},
            })
            # RRF score contribution
            entry["score_rrf"] += 1.0 / (k_rrf + rank + 1)  # rank 0-based → +1
            entry["ranks"][ranker_idx] = rank + 1
            # Préserver les scores spécifiques par ranker
            if "score" in result and entry["score_dense"] is None:
                entry["score_dense"] = result["score"]
            if "score_bm25" in result and entry["score_bm25"] is None:
                entry["score_bm25"] = result["score_bm25"]

    # Tri par RRF décroissant
    sorted_results = sorted(fused.values(), key=lambda x: -x["score_rrf"])
    return sorted_results
