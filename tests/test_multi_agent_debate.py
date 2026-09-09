import pytest

from src import agent
from src.agent import (
    AGREEMENT_THRESHOLD, DIMENSIONS, PERSONAS, Debate, Proposal, aggregate, agreement,
    criticise, debate,
)


def test_personas_are_genuinely_distinct():
    assert len(set(PERSONAS.values())) == len(PERSONAS) >= 3


def test_agreement_identical_answers():
    ps = [Proposal("a", "use postgres for writes"), Proposal("b", "use postgres for writes")]
    assert agreement(ps) == 1.0


def test_agreement_opposite_answers():
    ps = [Proposal("a", "adopt kubernetes now"), Proposal("b", "avoid orchestration entirely")]
    assert agreement(ps) < 0.3


def test_proposal_score_is_mean():
    p = Proposal("a", "x", scores={"correctness": 1.0, "evidence": 0.0, "risk_awareness": 0.5})
    assert p.score == pytest.approx(0.5)


def test_criticise_parses_structured_scores(monkeypatch):
    monkeypatch.setattr(agent, "complete", lambda m, **k: (
        '{"a": {"correctness": 0.9, "evidence": 0.8, "risk_awareness": 0.7}}'
    ))
    scored = criticise([Proposal("a", "answer")])
    assert scored[0].scores["correctness"] == 0.9


def test_criticise_survives_garbage(monkeypatch):
    monkeypatch.setattr(agent, "complete", lambda m, **k: "no idea, sorry")
    scored = criticise([Proposal("a", "answer")])
    assert set(scored[0].scores) == set(DIMENSIONS)


def test_early_consensus_stops_after_one_round(monkeypatch):
    monkeypatch.setattr(agent, "complete", lambda m, **k: (
        '{"x": {}}' if m[-1]["content"].startswith("Score") else "everyone agrees exactly here"
    ))
    d = debate("q")
    assert d.stopped_because == "consensus" and len(d.rounds) == 1


def test_disagreement_runs_more_rounds(monkeypatch):
    n = {"i": 0}

    def vary(messages, **kwargs):
        content = messages[-1]["content"]
        if content.startswith("Score"):
            return '{"x": {}}'
        if "Write the final answer" in content:
            return "final"
        n["i"] += 1
        return " ".join(f"tok{n['i']}x{j}" for j in range(6))  # no shared vocabulary

    monkeypatch.setattr(agent, "complete", vary)
    d = debate("q", max_rounds=2)
    assert len(d.rounds) == 2 and d.stopped_because == "max_rounds"


def test_aggregate_reports_confidence_and_dissent(monkeypatch):
    monkeypatch.setattr(agent, "complete", lambda m, **k: "synthesised answer")
    d = Debate(question="q", rounds=[[
        Proposal("winner", "use postgres because writes dominate",
                 scores={k: 0.9 for k in DIMENSIONS}),
        Proposal("loser", "use cassandra because writes dominate",
                 scores={k: 0.2 for k in DIMENSIONS}),
    ]])
    out = aggregate(d)
    assert out.final == "synthesised answer"
    assert 0 < out.confidence <= 1
    assert "loser" in out.dissent


def test_threshold_is_sane():
    assert 0 < AGREEMENT_THRESHOLD <= 1
