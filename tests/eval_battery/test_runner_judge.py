"""Runner (reprise, erreurs) et lecture des verdicts du juge."""
import json

from src.eval.battery.judge import build_prompt, load_verdicts, parse_verdict
from src.eval.battery.runner import complete_conversations, play, read_jsonl

BATTERY = [{"id": "L01", "persona": "lyceen", "domaine": "informatique", "tags": ["info"],
            "turns": ["q1"]},
           {"id": "L13", "persona": "lyceen", "domaine": "informatique", "tags": ["multi-tour"],
            "turns": ["q1", "q2"]}]


class EchoSystem:
    name = "echo"
    model = "inconnu"

    def __init__(self, fail_on=()):
        self.fail_on = fail_on
        self.calls = []

    def ask(self, question, history, key=None):
        self.calls.append((key, len(history)))
        if key in self.fail_on:
            raise RuntimeError("panne")
        return {"answer": f"reponse a {question}", "sources": [], "source_positions": []}


def test_history_is_replayed_and_errors_are_kept(tmp_path):
    out = tmp_path / "echo.jsonl"
    system = EchoSystem(fail_on={("L13", 0)})
    stats = play(system, BATTERY, out, workers=1, log=lambda *_: None)
    records = read_jsonl(out)
    assert stats["errors"] == 1 and len(records) == 3
    second = next(r for r in records if (r["id"], r["turn"]) == ("L13", 1))
    assert second["history"][1]["content"] == "(erreur)"
    assert second["domaine"] == "informatique"


def test_cost_is_not_measured_when_usage_is_absent(tmp_path):
    stats = play(EchoSystem(), BATTERY[:1], tmp_path / "e.jsonl", workers=1, log=lambda *_: None)
    assert stats["cost_usd"] is None and stats["tokens_in"] is None


def test_interrupted_conversation_is_replayed_whole(tmp_path):
    out = tmp_path / "echo.jsonl"
    out.write_text(json.dumps({"id": "L13", "turn": 0, "answer": "x"}) + "\n")
    assert complete_conversations(read_jsonl(out), BATTERY) == set()
    system = EchoSystem()
    play(system, BATTERY, out, workers=1, log=lambda *_: None)
    assert sorted((r["id"], r["turn"]) for r in read_jsonl(out)) == [("L01", 0), ("L13", 0), ("L13", 1)]


def test_parse_verdict_marks_unreadable_output():
    assert parse_verdict('```json\n{"references":4,"comprehension":4,"expression":5,"couverture":3}\n```')[
        "references"] == 4
    assert parse_verdict("je ne sais pas")["_parse_error"]
    assert parse_verdict('{"references":"bien"}')["_parse_error"]


def test_load_verdicts_keeps_last_valid_verdict(tmp_path):
    path = tmp_path / "judge_opus_local.jsonl"
    ok = {"id": "L01", "turn": 0, "references": 2, "comprehension": 2, "expression": 2, "couverture": 2}
    path.write_text("\n".join(json.dumps(v) for v in [{"id": "L01", "turn": 0, "_error": "429"}, ok]) + "\n")
    assert load_verdicts(tmp_path, "opus", "local")[("L01", 0)]["references"] == 2


def test_judge_prompt_lists_exposed_fiches():
    rec = {"persona": "lyceen", "tags": ["info"], "history": [], "question": "q", "answer": "a",
           "sources": [{"titre": "BUT Info", "etablissement": "IUT Lyon 1", "ville": "Lyon", "source": "parcoursup"}]}
    assert "BUT Info | IUT Lyon 1 | Lyon" in build_prompt(rec)


def test_conversation_with_an_error_is_replayed(tmp_path):
    out = tmp_path / "echo.jsonl"
    play(EchoSystem(fail_on={("L13", 0)}), BATTERY, out, workers=1, log=lambda *_: None)
    assert complete_conversations(read_jsonl(out), BATTERY) == {"L01"}
    play(EchoSystem(), BATTERY, out, workers=1, log=lambda *_: None)
    records = read_jsonl(out)
    assert len(records) == 3 and not any(r["error"] for r in records)


def test_verdict_of_a_replaced_answer_is_ignored(tmp_path):
    from src.eval.battery.judge import answer_sha
    rec = {"id": "L01", "turn": 0, "answer": "nouvelle reponse"}
    (tmp_path / "local.jsonl").write_text(json.dumps(rec) + "\n")
    scores = {"references": 1, "comprehension": 1, "expression": 1, "couverture": 1}
    stale = {"id": "L01", "turn": 0, "answer_sha": answer_sha({"answer": ""}), **scores}
    (tmp_path / "judge_opus_local.jsonl").write_text(json.dumps(stale) + "\n")
    assert load_verdicts(tmp_path, "opus", "local") == {}
