# 09 - Multi-Agent Debate System

> Proposers argue, a critic scores, an aggregator decides.

**What it demonstrates:** Orchestrating several agents and resolving their disagreement

**Status:** working implementation with passing tests. Built as a learning project to understand the pattern, not as a production service.

---

## Run it right now

No API key needed - every project ships with `MODEL=fake`, a deterministic
offline responder, so you can see the whole flow work before spending anything.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
python -m src.main
pytest -q
```

To use a real model, edit `.env`:

```
MODEL=gpt-4o-mini            # + OPENAI_API_KEY
MODEL=claude-3-5-haiku-latest  # + ANTHROPIC_API_KEY
MODEL=ollama/llama3.1        # free, runs locally
```

## How it works

Three personas - pragmatist, skeptic, theorist - answer the same question concurrently with genuinely different system prompts. A critic then scores every proposal on stated dimensions and returns structured JSON, so ranking is a number rather than a vibe.

`agreement()` measures mean pairwise word overlap between the answers. Once it clears the threshold the debate stops early - there is no point paying for another round when everyone already agrees. Otherwise each round sees the others' arguments and responds.

The aggregator synthesises the highest-scoring answer into a final response, reports confidence as `winning score x agreement`, and always surfaces the strongest dissent - because a confident answer with a good objection attached is more useful than a confident answer alone.

## What "done" means here

- Personas have genuinely different system prompts, not one prompt repeated
- Proposals are generated concurrently
- The critic returns structured scores and survives unparseable output
- Rounds stop early once the answers converge
- Confidence combines the winner's score with how much the agents agreed
- The dissenting view is always reported alongside the final answer

Every one of those lines has a test behind it in `tests/` - `pytest -q` is the
proof, not the README.

## Layout

```
src/llm.py             provider-agnostic completion, plus offline fake mode
src/fake.py            the canned responses that make MODEL=fake work
src/logging_setup.py   structured JSON logging
src/agent.py           the pattern itself
src/main.py            CLI entrypoint
tests/                 10 tests, all passing
```

## Next steps

- Replace word-overlap agreement with embedding similarity
- Give each persona a different model, not just a different prompt
- Benchmark debate vs a single agent on a reasoning set - and report it honestly if debate loses

## Reference

https://github.com/composable-models/llm_multiagent_debate

---

Part of a 12-project agentic AI series - [github.com/dhanashalini25](https://github.com/dhanashalini25?tab=repositories)
