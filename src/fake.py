"""Canned debate for MODEL=fake: distinct personas, a critic, then a synthesis."""
from __future__ import annotations


def respond(messages: list[dict]) -> str:
    system = messages[0]["content"] if messages[0]["role"] == "system" else ""
    last = messages[-1]["content"]

    if last.startswith("Score each proposal"):
        return (
            '{"pragmatist": {"correctness": 0.8, "evidence": 0.7, "risk_awareness": 0.6},'
            ' "skeptic": {"correctness": 0.7, "evidence": 0.8, "risk_awareness": 0.9},'
            ' "theorist": {"correctness": 0.6, "evidence": 0.6, "risk_awareness": 0.5}}'
        )
    if "Other agents argued" in last:
        # second round: the agents converge, so the debate stops early
        return (
            "A managed platform is the right call at three people; revisit Kubernetes "
            "when deploy complexity rather than traffic becomes the bottleneck."
        )
    if "Write the final answer" in last:
        return (
            "No - three people should not run Kubernetes for a first product. "
            "A managed platform costs less attention and buys the same reliability at this size. "
            "Revisit the decision when deploy complexity, not traffic, becomes the bottleneck."
        )
    if "simplest thing that ships" in system:
        return "Skip it. Use a managed platform and ship this quarter."
    if "failure modes" in system:
        return "Kubernetes adds an on-call burden three people cannot staff. The hidden cost is attention."
    return "Container orchestration is correct in principle but premature before scale demands it."
