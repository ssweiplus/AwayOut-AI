# AwayOut-AI

AwayOut-AI is an agent-friendly toolkit for **authorized chatbot security testing**.

It is adapted from the open-source project **Hcxgraphics/JailBreak-AI**:

- Upstream: https://github.com/Hcxgraphics/JailBreak-AI
- Upstream license: MIT
- Upstream methods: DrAttack, PAIR, TAP, LLM-as-Judge

> Use only on systems you are authorized to test.

## Agent Mode

Agent Mode is self-contained under:

```text
skills/awayout-security/
```

You can copy that whole folder into a host Agent environment and use it independently. It requires only Python 3.10+; it does not require CodeAgent, Ollama, `requests`, root `requirements.txt`, `main.py`, or `awayout/*`.

```text
User
  ↓
OpenCode / Codex / other Host Agent CLI
  ↓
skills/awayout-security/SKILL.md
  ↓
deterministic controller
  ↓ state + action + progress.can_stop + handoff
Host Agent performs language reasoning/user interaction
  ↓
result submitted back to AwayOut
```

The Host Agent stays in one continuous context. AwayOut controls workflow order, limits, thresholds, pruning/ranking, persistence and stop conditions; the Host Agent provides language reasoning.

Implemented Agent Mode algorithms:

```text
PAIR      single-path iterative refinement
TAP       multi-path tree search with pruning
DrAttack  semantic decomposition and reconstruction
```

Before first use:

```bash
cd skills/awayout-security
python doctor.py
```

Then follow `SKILL.md`. It handles objective collection, algorithm explanation, parameter confirmation, execution rules and troubleshooting. Algorithm-specific state/handoff contracts live in each algorithm's own `SKILL.md`.

Critical stop rule:

```text
Only finish when:
state = DONE
action = stop
progress.can_stop = true
```

## Agent Mode structure

```text
skills/
└── awayout-security/
    ├── SKILL.md
    ├── api.py
    ├── doctor.py
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

## Standalone compatibility

The repository root still retains the older Python-driven runtime for compatibility:

```text
main.py
interactive_pair.py
awayout/
codeagent_connector.py
requirements.txt
agent_api.py
```

Standalone mode may call its own Attacker/Judge models and may use CodeAgent/Ollama. These files are not required by Agent Mode.

Root `agent_api.py` remains only as a compatibility wrapper to the Skill API.

## Current scope

Implemented:

- self-contained Agent Mode Skill package;
- PAIR, TAP and DrAttack deterministic controllers;
- single Host Agent handoff model;
- authoritative `can_stop` / `stop_reason` protocol;
- persistent sessions and deterministic tree/summary output;
- objective/algorithm/parameter preflight guidance;
- Agent Mode self-check and troubleshooting;
- standalone compatibility.

Reserved next:

- richer visual attack-tree rendering;
- optional MCP wrapper;
- optional curated Seed Prompt library.
