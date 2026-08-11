# AwayOut-AI

AwayOut-AI is an agent-friendly toolkit for **authorized chatbot security testing**.

It is adapted from the open-source project **Hcxgraphics/JailBreak-AI**:

- Upstream: https://github.com/Hcxgraphics/JailBreak-AI
- Upstream license: MIT
- Upstream methods: DrAttack, PAIR, TAP, LLM-as-Judge

> Use only on systems you are authorized to test.

---

## 1. Recommended architecture: Skill outside, deterministic algorithms inside

AwayOut-AI is organized around the Agent Skill as the primary entry point:

```text
OpenCode / Codex / other Agent
          │
          ▼
skills/awayout-security/SKILL.md
          │
          ▼
   algorithms/<name>/
          │
          ▼
 deterministic controller
          │
     ┌────┴────┐
     ▼         ▼
   common     state/tree
```

The **Agent does not choose the workflow order**. The algorithm controller owns:

- algorithm state transitions;
- iteration limits;
- success thresholds;
- allowed next actions;
- session persistence;
- tree/summary generation.

The Agent only handles language-heavy steps such as candidate wording, semantic analysis, judgement reasoning, and presenting results to the user.

If the Agent calls a step out of order, AwayOut rejects it.

---

## 2. Skill structure

```text
skills/
└── awayout-security/
    ├── SKILL.md                 # top-level Agent instructions
    ├── api.py                   # real Agent API implementation
    ├── common/
    │   └── store.py             # deterministic session persistence
    └── algorithms/
        ├── pair/
        │   ├── SKILL.md         # PAIR-specific Agent instructions
        │   └── controller.py    # deterministic PAIR state machine
        ├── tap/
        │   └── SKILL.md         # reserved until controller is implemented
        └── drattack/
            └── SKILL.md         # reserved until controller is implemented
```

The root-level `agent_api.py` is only a compatibility wrapper that forwards execution to:

```text
skills/awayout-security/api.py
```

---

## 3. Algorithms

```text
1. PAIR     - feedback-driven iterative refinement      [Agent Mode available]
2. TAP      - Tree of Attacks with Pruning             [reserved]
3. DrAttack - prompt decomposition and reconstruction  [reserved]
```

PAIR Agent Mode is implemented as this fixed state machine:

```text
NEED_CANDIDATE
      ↓
WAIT_TARGET_RESPONSE
      ↓
NEED_JUDGEMENT
      ↓
DONE or NEED_CANDIDATE
```

TAP and DrAttack remain reserved until their deterministic controllers are implemented. The Agent must not emulate them by inventing its own workflow.

---

## 4. Agent Mode

The Agent-facing skill is:

```text
skills/awayout-security/SKILL.md
```

The high-level tool entry remains:

```text
agent_api.py
```

### Start a PAIR test

```bat
.venv\Scripts\python.exe agent_api.py start-test --algorithm PAIR --objective "<objective>"
```

The command returns JSON with:

```text
session_id
state
action
```

The Agent must obey the returned `state` and `action`.

### Submit a generated candidate

```bat
.venv\Scripts\python.exe agent_api.py submit-candidate <session_id> --prompt "<candidate>" --strategy "logical_appeal"
```

### Submit the real target response

```bat
.venv\Scripts\python.exe agent_api.py submit-response <session_id> --response "<target response>"
```

### Submit judgement

```bat
.venv\Scripts\python.exe agent_api.py submit-judgement <session_id> --score 5 --reason "<reason>"
```

The controller decides whether another iteration is allowed or the test is finished.

### Inspect state / tree / summary

```bat
.venv\Scripts\python.exe agent_api.py get-state <session_id>
.venv\Scripts\python.exe agent_api.py get-tree <session_id>
.venv\Scripts\python.exe agent_api.py get-summary <session_id>
```

Agent-mode state is stored under:

```text
.awayout-agent/
```

This directory is ignored by Git.

---

## 5. Standalone Mode

The existing Python-driven PAIR implementation is retained for compatibility.

Unified standalone entry:

```bat
.venv\Scripts\python.exe main.py
```

or:

```bat
run_windows.bat
```

`main.py` keeps the three-algorithm menu. PAIR is runnable; TAP and DrAttack are currently reserved.

Standalone PAIR still uses the existing `AttackerLLM` / `JudgeLLM` path. Agent Mode is the recommended direction when using OpenCode/Codex-style agents.

---

## 6. CodeAgent integration for Standalone Mode

CodeAgent has exactly one supported integration mode: **Python Connector**.

Default file:

```text
codeagent_connector.py
```

Connector input is a single string:

```python
def invoke(message: str, model="", temperature=0.7, max_tokens=1200):
    return {
        "success": True,
        "result": "model output"
    }
```

AwayOut internally owns multi-message chat history. `PythonConnectorClient` converts it to one string before calling your connector.

For the full contract, see `CODEAGENT_CONNECTOR.md`.

---

## 7. Windows installation

Requirements:

- Windows 10/11
- Python 3.10+

### Automatic setup

```bat
setup_windows.bat
```

Environment priority:

```text
1. active Conda environment
2. existing .venv
3. create .venv
```

If `uv` is available, setup uses `uv pip` and does not require pip inside a uv-created `.venv`.

### Manual installation with uv

```bat
cd D:\path\to\AwayOut-AI
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe doctor.py
```

If `.venv` already exists, skip `uv venv .venv`.

### Manual installation with standard Python

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe doctor.py
```

### Manual installation with Conda

```bat
conda create -n awayout python=3.11 -y
conda activate awayout
python -m pip install -r requirements.txt
python doctor.py
```

---

## 8. Responsibility boundary

```text
Skill
- tells the Agent how to use AwayOut
- tells the Agent which algorithm-specific instructions to follow
- tells the Agent to obey returned state/action

Algorithm Controller
- what step happens next
- whether a transition is legal
- thresholds and limits
- stop conditions

Common deterministic code
- persistence
- session loading/saving
- shared state utilities

Agent / LLM
- candidate wording
- semantic interpretation
- judgement reasoning
- user interaction
- result presentation
```

The design goal is to keep non-deterministic language work in the Agent while preventing the Agent from freely changing the security-testing algorithm.

---

## 9. Full project layout

```text
AwayOut-AI/
├── skills/
│   └── awayout-security/
│       ├── SKILL.md
│       ├── api.py
│       ├── common/
│       │   └── store.py
│       └── algorithms/
│           ├── pair/
│           │   ├── SKILL.md
│           │   └── controller.py
│           ├── tap/
│           │   └── SKILL.md
│           └── drattack/
│               └── SKILL.md
├── awayout/
│   ├── attacker.py            # standalone engine
│   ├── judge.py               # standalone engine
│   ├── ollama.py
│   ├── providers.py
│   ├── seeds.py               # reserved extension point
│   └── session.py             # standalone session format
├── agent_api.py               # compatibility wrapper -> skill api.py
├── main.py                    # standalone unified entry
├── interactive_pair.py        # standalone PAIR implementation
├── codeagent_connector.py
├── CODEAGENT_CONNECTOR.md
├── doctor.py
├── setup_windows.bat
├── run_windows.bat
├── requirements.txt
└── README.md
```

---

## 10. Current scope

Implemented now:

- skill-centric Agent architecture;
- Agent-friendly high-level API;
- deterministic PAIR controller inside the Skill package;
- enforced state transitions;
- persistent Agent sessions under Skill common code;
- deterministic tree and summary output;
- algorithm-specific Skill instructions;
- existing standalone PAIR retained;
- CodeAgent Python Connector retained for standalone mode;
- Windows / uv / Conda setup support.

Reserved next:

- deterministic TAP controller under `skills/awayout-security/algorithms/tap/`;
- deterministic DrAttack controller under `skills/awayout-security/algorithms/drattack/`;
- richer branching/tree visualization;
- optional MCP wrapper around the stable Agent API operations;
- optional curated Seed Prompt library.
