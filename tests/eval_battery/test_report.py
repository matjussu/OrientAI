"""Rapport (src/eval/battery/report.py) sur un passage minuscule ecrit a la main."""
import json

import pytest

from src.eval.battery.answers import answer_sha
from src.eval.battery.corpus import Corpus, CorpusVersionError
from src.eval.battery.report import build_report

FICHE = {"nom": "Licence - Informatique", "etablissement": "Universite Toulouse III", "ville": "Toulouse",
         "source": "parcoursup", "taux_acces_parcoursup_2025": 87.4}
SCORES = {"references": 4, "comprehension": 4, "expression": 4, "couverture": 4}


def write(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


@pytest.fixture
def corpus(tmp_path):
    path = tmp_path / "formations.json"
    path.write_text(json.dumps([FICHE]))
    return Corpus(path=path)


def turn(answer, positions, **extra):
    return {"id": "L01", "turn": 0, "persona": "lyceen", "tags": [], "question": "q", "history": [],
            "answer": answer, "sources": [], "source_positions": positions, "error": None, **extra}


def test_report_counts_adosse_numbers(tmp_path, corpus):
    run = tmp_path / "run"
    run.mkdir()
    write(run / "local.jsonl", [turn("Licence Info Toulouse : 87 % d'acces", [0])])
    write(run / "judge_opus_local.jsonl", [{"id": "L01", "turn": 0, **SCORES}])
    report = build_report(run, corpus, anchor=False)
    assert "| local | 1 | 0 | 4 |" in report
    assert "| 1 | 100 % (" in report


def test_report_refuses_positions_from_another_corpus(tmp_path, corpus):
    run = tmp_path / "run"
    run.mkdir()
    write(run / "local.jsonl", [turn("87 %", [0])])
    (run / "manifest.json").write_text(json.dumps({"corpus_sha256": "0" * 64, "battery_sha256": "x"}))
    with pytest.raises(CorpusVersionError):
        build_report(run, corpus, anchor=False)


def test_report_flags_claude_ctx_played_on_an_older_local(tmp_path, corpus):
    run = tmp_path / "run"
    run.mkdir()
    write(run / "local.jsonl", [turn("nouvelle reponse de local, 87 %", [0])])
    write(run / "claude_ctx.jsonl", [turn("reponse ctx", [0], local_answer_sha=answer_sha({"answer": "ancienne"}))])
    for s in ("local", "claude_ctx"):
        write(run / f"judge_opus_{s}.jsonl", [{"id": "L01", "turn": 0, **SCORES}])
    assert "1 tours de claude_ctx ont ete joues sur une version anterieure" in build_report(run, corpus, anchor=False)
