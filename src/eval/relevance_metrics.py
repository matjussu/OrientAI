"""Métriques de pertinence retrieval (H1 lot 2.1, ordre 2026-07-16-0905).

Calculées contre le set de pertinence labellisé par agents
(scripts/relevance_set/labels.json) :

- recall@k   : part des questions AYANT au moins une fiche grade 2 dont le
  top-k retrieval surface au moins une fiche grade 2. Les questions
  none_relevant (aucune fiche pertinente dans le corpus vu) sont EXCLUES du
  denominateur du recall (rien à retrouver) mais comptées séparément
  (elles fondent la mesure des refus légitimes).
- nDCG@k     : gain cumulé actualisé normalisé, gains = grade (0/1/2),
  actualisation log2 standard. Mesure la QUALITÉ D'ORDRE, pas juste la
  présence.

Déterministe, zéro LLM. Les seuils de gate vivent dans l'appelant
(scripts/relevance_set/eval_retrieval.py) — ce module ne fait que mesurer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class QuestionLabels:
    qid: str
    grades: dict[str, int]  # fiche_id -> 1|2
    none_relevant: bool = False


@dataclass
class RelevanceReport:
    n_questions: int
    n_scored: int              # questions avec >= 1 fiche grade 2 (denominateur recall)
    n_none_relevant: int       # questions sans aucune fiche pertinente (refus légitime)
    recall_at_k: float | None
    ndcg_at_k: float | None
    k: int
    misses: list[str] = field(default_factory=list)  # qids sans grade 2 dans le top-k

    def summary(self) -> str:
        r = "n/a" if self.recall_at_k is None else f"{self.recall_at_k:.3f}"
        n = "n/a" if self.ndcg_at_k is None else f"{self.ndcg_at_k:.3f}"
        return (
            f"recall@{self.k}={r} ({self.n_scored} questions scorees) | "
            f"nDCG@{self.k}={n} | none_relevant={self.n_none_relevant} | "
            f"misses={len(self.misses)}"
        )


def dcg(gains: list[int]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(retrieved_ids: list[str], grades: dict[str, int], k: int) -> float | None:
    """nDCG@k pour une question. None si aucune fiche labellisée (pas de
    vérité terrain -> pas de mesure, jamais un 0 fabriqué)."""
    if not grades:
        return None
    gains = [grades.get(fid, 0) for fid in retrieved_ids[:k]]
    ideal = sorted(grades.values(), reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0:
        return None
    return dcg(gains) / ideal_dcg


def recall_hit_at_k(retrieved_ids: list[str], grades: dict[str, int], k: int) -> bool:
    """Vrai si au moins une fiche grade 2 est dans le top-k."""
    targets = {fid for fid, g in grades.items() if g >= 2}
    return bool(targets & set(retrieved_ids[:k]))


def evaluate(
    runs: dict[str, list[str]],
    labels: list[QuestionLabels],
    k: int = 5,
    ndcg_k: int = 10,
) -> RelevanceReport:
    """Évalue un run de retrieval complet contre les labels.

    Args:
        runs: qid -> liste ORDONNÉE de fiche_id retrievés (au moins ndcg_k).
        labels: labels agents (grades + none_relevant).
        k: cutoff du recall (défaut 5, la fenêtre v4 servie au LLM).
        ndcg_k: cutoff du nDCG (défaut 10).
    """
    n_scored = 0
    hits = 0
    ndcgs: list[float] = []
    misses: list[str] = []
    n_none = 0

    for ql in labels:
        if ql.none_relevant or not ql.grades:
            n_none += 1
            continue
        retrieved = runs.get(ql.qid, [])
        nd = ndcg_at_k(retrieved, ql.grades, ndcg_k)
        if nd is not None:
            ndcgs.append(nd)
        if any(g >= 2 for g in ql.grades.values()):
            n_scored += 1
            if recall_hit_at_k(retrieved, ql.grades, k):
                hits += 1
            else:
                misses.append(ql.qid)

    return RelevanceReport(
        n_questions=len(labels),
        n_scored=n_scored,
        n_none_relevant=n_none,
        recall_at_k=(hits / n_scored) if n_scored else None,
        ndcg_at_k=(sum(ndcgs) / len(ndcgs)) if ndcgs else None,
        k=k,
        misses=misses,
    )


def load_labels(path) -> list[QuestionLabels]:
    """Charge labels.json (sortie de la flotte de juges, assemblée)."""
    import json
    from pathlib import Path

    raw = json.loads(Path(path).read_text())
    items = raw["labels"] if isinstance(raw, dict) else raw
    out = []
    for r in items:
        out.append(QuestionLabels(
            qid=r["qid"],
            grades={x["fiche_id"]: int(x["grade"]) for x in r.get("relevant", [])},
            none_relevant=bool(r.get("none_relevant")),
        ))
    return out
