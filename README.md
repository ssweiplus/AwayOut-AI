# AwayOut-AI

AwayOut-AI is an agent-friendly toolkit for **authorized chatbot security testing**.

It is adapted from the open-source project **Hcxgraphics/JailBreak-AI**:

- Upstream: https://github.com/Hcxgraphics/JailBreak-AI
- Upstream license: MIT
- Upstream methods: DrAttack, PAIR, TAP, LLM-as-Judge

> Use only on systems you are authorized to test.

## Architecture

```text
User
  ↓
OpenCode / Codex / other Host Agent CLI
  ↓
skills/awayout-security/SKILL.md
  ↓
deterministic algorithm controller
  ↓
state + action + progress.can_stop + handoff
  ↓
Host Agent performs the requested reasoning/user interaction
  ↓
result submitted back to AwayOut
```

The tester stays in the same Host Agent CLI. Agent Mode does not call a second Attacker/Judge LLM.

The controller owns workflow order, limits, thresholds, pruning/ranking, persistence, tree state and stop conditions. The Host Agent owns language reasoning and user interaction.

## Agent Mode algorithms

```text
PAIR      implemented
TAP       implemented
DrAttack  implemented
```

### PAIR

```text
NEED_CANDIDATE
  -> WAIT_TARGET_RESPONSE
  -> NEED_JUDGEMENT
  -> NEED_CANDIDATE or DONE
```

Defaults: `max_iterations=10`, `threshold=7`, `strategy=logical_appeal`.

### TAP

```text
NEED_BRANCHES
  -> NEED_OFFTOPIC_REVIEW
  -> WAIT_TARGET_RESPONSES
  -> NEED_SCORES
  -> NEED_BRANCHES or DONE
```

Defaults: `branch_factor=2`, `max_depth=5`, `width=2`, `threshold=7`.

AwayOut applies off-topic pruning, score ranking and top-W pruning in code and records an actual attack tree.

### DrAttack

```text
NEED_BASELINE_PROMPT
  -> WAIT_BASELINE_RESPONSE
  -> NEED_DECOMPOSITION
  -> NEED_SYNONYMS
  -> NEED_RECONSTRUCTIONS
  -> WAIT_STRATEGY_RESPONSES
  -> NEED_STRATEGY_SCORES
  -> DONE
```

Defaults: `top_k_synonyms=3`, `threshold=7`, reconstruction strategies `icl_structured, icl_unstructured, word_game, icl_demo1, icl_demo2`.

## Critical stop rule

The Host Agent must never decide by itself that a test is finished.

Only announce completion when AwayOut returns all of:

```text
state = DONE
action = stop
progress.can_stop = true
```

Otherwise call/obey the returned handoff even after repeated failures. `stop_reason` explains why the deterministic controller stopped.

## Preflight

Before creating a session, the Skill must:

1. obtain the explicit test objective;
2. show the selected algorithm and effective parameters;
3. let the user modify them;
4. call `start-test` only after confirmation.

## Start examples

PAIR:

```bash
python agent_api.py start-test --algorithm PAIR --objective "..." --strategy logical_appeal --max-iterations 10 --threshold 7
```

TAP:

```bash
python agent_api.py start-test --algorithm TAP --objective "..." --branch-factor 2 --max-depth 5 --width 2 --threshold 7
```

DrAttack:

```bash
python agent_api.py start-test --algorithm DrAttack --objective "..." --top-k-synonyms 3 --threshold 7
```

## Agent API

PAIR keeps convenience commands:

```text
submit-candidate
submit-response
submit-judgement
```

All algorithms support:

```bash
python agent_api.py submit-result <session_id> --data '<json object>'
python agent_api.py submit-result <session_id> --data-file result.json
python agent_api.py get-state <session_id>
python agent_api.py get-tree <session_id>
python agent_api.py get-summary <session_id>
```

Prefer `--data-file` for multiline or structured TAP/DrAttack handoffs.

## Skill structure

```text
skills/
└── awayout-security/
    ├── SKILL.md
    ├── api.py
    ├── common/
    │   └── store.py
    └── algorithms/
        ├── pair/
        │   ├── SKILL.md
        │   └── controller.py
        ├── tap/
        │   ├── SKILL.md
        │   └── controller.py
        └── drattack/
            ├── SKILL.md
            └── controller.py
```

Root `agent_api.py` remains a compatibility wrapper for the Skill API.

## Installation

Python 3.10+ is required.

### uv on Windows

```bat
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe agent_api.py --help
```

### uv on Linux/macOS

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python agent_api.py --help
```

### Existing Python

```bash
python -m pip install -r requirements.txt
python agent_api.py --help
```

For the complete operational guide, preflight rules, handoff payloads and exception recovery, read:

```text
skills/awayout-security/SKILL.md
```

## Standalone compatibility

The old Python-driven runtime remains separate:

```text
main.py
interactive_pair.py
awayout/attacker.py
awayout/judge.py
codeagent_connector.py
```

Standalone mode may call its own Attacker/Judge models. Agent Mode does not.

## Current scope

Implemented:

- PAIR deterministic controller;
- TAP deterministic branching/pruning controller;
- DrAttack deterministic decomposition/reconstruction controller;
- single Host Agent handoff model;
- authoritative `can_stop` / `stop_reason` protocol;
- persistent sessions and deterministic tree/summary output;
- generic `submit-result` for structured handoffs;
- preflight objective/configuration confirmation;
- standalone compatibility.

Reserved next:

- richer visual attack-tree rendering;
- optional MCP wrapper over the stable Agent API;
- optional curated Seed Prompt library.
