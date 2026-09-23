"""Identite stable d'une fiche (src/eval/battery/corpus.py)."""
import pytest

from src.eval.battery.corpus import Corpus, CorpusVersionError, fiche_key


def test_position_by_identity_even_without_id_field():
    fiches = [{"nom": "A"}, {"nom": "A"}, {"id": "metier:x", "nom": "B"}]
    corpus = Corpus(path="/dev/null", fiches=fiches)
    # deux fiches identiques en contenu gardent chacune leur position
    assert [corpus.position_of(f) for f in fiches] == [0, 1, 2]
    assert fiche_key(1) == "idx:1"


def test_falsification_copied_fiche_raises_instead_of_minus_one():
    fiches = [{"nom": "A"}]
    corpus = Corpus(path="/dev/null", fiches=fiches)
    with pytest.raises(KeyError):
        corpus.position_of(dict(fiches[0]))


def test_signature_lookup_reports_every_candidate():
    fiches = [{"nom": "BUT", "ville": "Lyon", "source": "parcoursup"}] * 2
    corpus = Corpus(path="/dev/null", fiches=fiches)
    assert corpus.positions_by_signature("BUT", None, "Lyon", "parcoursup") == [0, 1]


def test_version_mismatch_is_refused(tmp_path):
    path = tmp_path / "formations.json"
    path.write_text("[]")
    corpus = Corpus(path=path)
    corpus.assert_version(corpus.sha256, "labels")
    with pytest.raises(CorpusVersionError):
        corpus.assert_version("0" * 64, "labels")
