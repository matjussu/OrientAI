"""Tests du module de métriques de pertinence (H1 lot 2.1)."""
from __future__ import annotations

import math

from src.eval.relevance_metrics import (
    QuestionLabels,
    evaluate,
    ndcg_at_k,
    recall_hit_at_k,
)


class TestRecall:
    def test_hit_quand_grade2_dans_topk(self):
        assert recall_hit_at_k(["a", "b", "c"], {"b": 2}, k=3) is True

    def test_miss_quand_grade2_hors_topk(self):
        assert recall_hit_at_k(["a", "b", "c", "d", "e", "target"], {"target": 2}, k=5) is False

    def test_grade1_ne_compte_pas_comme_hit(self):
        assert recall_hit_at_k(["a"], {"a": 1}, k=5) is False


class TestNdcg:
    def test_ordre_parfait_vaut_1(self):
        grades = {"a": 2, "b": 1}
        assert ndcg_at_k(["a", "b", "x"], grades, k=10) == 1.0

    def test_ordre_inverse_penalise(self):
        grades = {"a": 2, "b": 1}
        nd = ndcg_at_k(["b", "a"], grades, k=10)
        assert nd is not None and 0 < nd < 1.0

    def test_valeur_exacte_cas_simple(self):
        # retrieved [0, 2] avec ideal [2] : dcg = 2/log2(3), idcg = 2/log2(2)
        grades = {"t": 2}
        nd = ndcg_at_k(["x", "t"], grades, k=10)
        assert nd is not None
        assert abs(nd - (2 / math.log2(3)) / 2.0) < 1e-9

    def test_aucun_label_retourne_none_pas_zero(self):
        # Pas de vérité terrain -> pas de mesure (vide > faux)
        assert ndcg_at_k(["a", "b"], {}, k=10) is None


class TestEvaluate:
    def _labels(self):
        return [
            QuestionLabels("q1", {"f1": 2, "f2": 1}),
            QuestionLabels("q2", {"f9": 2}),
            QuestionLabels("q3", {}, none_relevant=True),
            QuestionLabels("q4", {"f5": 1}),  # que du grade 1 : hors denominateur recall
        ]

    def test_report_complet(self):
        runs = {
            "q1": ["f1", "x", "y"],          # hit
            "q2": ["a", "b", "c", "d", "e"],  # miss (f9 absent du top-5)
            "q4": ["f5"],
        }
        rep = evaluate(runs, self._labels(), k=5, ndcg_k=10)
        assert rep.n_questions == 4
        assert rep.n_scored == 2          # q1 et q2 seulement (grade 2 existant)
        assert rep.n_none_relevant == 1   # q3
        assert rep.recall_at_k == 0.5
        assert rep.misses == ["q2"]
        assert rep.ndcg_at_k is not None and 0 < rep.ndcg_at_k <= 1

    def test_question_sans_run_compte_comme_miss(self):
        rep = evaluate({}, [QuestionLabels("q1", {"f1": 2})], k=5)
        assert rep.recall_at_k == 0.0 and rep.misses == ["q1"]

    def test_aucune_question_scoree_recall_none(self):
        rep = evaluate({}, [QuestionLabels("q1", {}, none_relevant=True)], k=5)
        assert rep.recall_at_k is None and rep.n_none_relevant == 1


class TestLoadLabels:
    def test_chargement_format_flotte(self, tmp_path):
        import json

        from src.eval.relevance_metrics import load_labels

        f = tmp_path / "labels.json"
        f.write_text(json.dumps({"labels": [
            {"qid": "q1", "relevant": [{"fiche_id": "a", "grade": 2}], "none_relevant": False},
            {"qid": "q2", "relevant": [], "none_relevant": True},
        ]}))
        labels = load_labels(f)
        assert labels[0].grades == {"a": 2}
        assert labels[1].none_relevant is True
