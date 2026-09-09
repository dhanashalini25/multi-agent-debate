"""Multi-Agent Debate - proposers argue, a critic scores, an aggregator decides.

Three genuinely different personas answer in parallel, a critic scores each on
stated dimensions, rounds stop early once the answers converge, and the final
result carries both a confidence and the strongest dissenting view.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field

from .llm import complete
from .logging_setup import log

MAX_ROUNDS = 3
AGREEMENT_THRESHOLD = 0.7
DIMENSIONS = ["correctness", "evidence", "risk_awareness"]
DEMO = "Should a three-person startup use Kubernetes for its first product?"

PERSONAS = {
    "pragmatist": "You favour the simplest thing that ships this quarter. Be concrete and brief.",
    "skeptic": "You hunt for failure modes, hidden costs and bad assumptions. Be adversarial.",
    "theorist": "You reason from first principles and prefer long-run correctness over speed.",
}

_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "it", "for", "with", "that"}


@dataclass
class Proposal:
    author: str
    answer: str
    scores: dict[str, float] = field(default_factory=dict)

    @property
    def score(self) -> float:
        return sum(self.scores.values()) / len(self.scores) if self.scores else 0.0


@dataclass
class Debate:
    question: str
    rounds: list[list[Proposal]] = field(default_factory=list)
    final: str | None = None
    confidence: float = 0.0
    dissent: str | None = None
    stopped_because: str = "max_rounds"


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 2}


def agreement(proposals: list[Proposal]) -> float:
    """Mean pairwise Jaccard overlap of the answers - 1.0 means identical."""
    if len(proposals) < 2:
        return 1.0
    sets = [words(p.answer) for p in proposals]
    pairs = [
        len(a & b) / len(a | b) if (a | b) else 1.0
        for i, a in enumerate(sets)
        for b in sets[i + 1 :]
    ]
    return sum(pairs) / len(pairs)


async def _propose(persona: str, question: str, prior: str) -> Proposal:
    content = question if not prior else f"{question}\n\nOther agents argued:\n{prior}"
    text = await asyncio.to_thread(
        complete,
        [{"role": "system", "content": PERSONAS[persona]}, {"role": "user", "content": content}],
    )
    return Proposal(author=persona, answer=text.strip())


CRITIC = (
    "Score each proposal from 0 to 1 on " + ", ".join(DIMENSIONS) + ".\n"
    'Reply with ONE JSON object: {"<author>": {"correctness": 0.0, "evidence": 0.0, '
    '"risk_awareness": 0.0}}\n\nProposals:\n{body}'
)


def criticise(proposals: list[Proposal]) -> list[Proposal]:
    body = "\n\n".join(f"[{p.author}] {p.answer}" for p in proposals)
    raw = complete([{"role": "user", "content": CRITIC.replace("{body}", body)}])
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        scored = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        scored = {}

    for p in proposals:
        entry = scored.get(p.author, {})
        p.scores = {
            d: float(entry.get(d, 0.5)) for d in DIMENSIONS
        } if isinstance(entry, dict) else {d: 0.5 for d in DIMENSIONS}
    log.info("critic_scored", extra={a.author: round(a.score, 2) for a in proposals})
    return proposals


def aggregate(debate: Debate) -> Debate:
    last = debate.rounds[-1]
    ranked = sorted(last, key=lambda p: p.score, reverse=True)
    winner, loser = ranked[0], ranked[-1]

    debate.final = complete([{
        "role": "user",
        "content": (
            f"Question: {debate.question}\n\n"
            f"Leading answer ({winner.author}): {winner.answer}\n"
            f"Dissenting answer ({loser.author}): {loser.answer}\n\n"
            "Write the final answer in three sentences."
        ),
    }]).strip()

    debate.confidence = round(winner.score * agreement(last), 3)
    debate.dissent = f"[{loser.author}] {loser.answer}"
    return debate


async def debate_async(question: str, max_rounds: int = MAX_ROUNDS) -> Debate:
    d = Debate(question=question)
    prior = ""

    for r in range(max_rounds):
        proposals = criticise(list(await asyncio.gather(
            *(_propose(p, question, prior) for p in PERSONAS)
        )))
        d.rounds.append(proposals)

        if agreement(proposals) >= AGREEMENT_THRESHOLD:
            d.stopped_because = "consensus"
            log.info("early_consensus", extra={"round": r + 1})
            break
        prior = "\n".join(f"[{p.author}] {p.answer}" for p in proposals)

    return aggregate(d)


def debate(question: str, max_rounds: int = MAX_ROUNDS) -> Debate:
    return asyncio.run(debate_async(question, max_rounds))


def run(prompt: str) -> str:
    d = debate(prompt)
    return (
        f"{d.final}\n\n"
        f"confidence: {d.confidence}  |  rounds: {len(d.rounds)}  |  stopped: {d.stopped_because}\n"
        f"dissent: {d.dissent}"
    )
