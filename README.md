# AwayOut-AI

AwayOut-AI is an agent-friendly toolkit for **authorized chatbot security testing**.

It is adapted from the open-source project **Hcxgraphics/JailBreak-AI**:

- Upstream: https://github.com/Hcxgraphics/JailBreak-AI
- Upstream license: MIT
- Upstream methods: DrAttack, PAIR, TAP, LLM-as-Judge

> Use only on systems you are authorized to test.

---

## 1. Recommended architecture: Agent + deterministic AwayOut Engine

AwayOut-AI now separates language reasoning from workflow control:

```text
OpenCode / Codex / other Agent
          │
          │  AwayOut Skill
          ▼
      agent_api.py
          │
          ▼
 Deterministic Controller
          │
     ┌────┴────┐
     ▼         ▼
 Session      Tree
 State        Record
```

The **Agent does not choose the workflow order**. AwayOut code owns:

- algorithm state transitions;
- iteration limits;
- success thresholds;
- allowed next actions;
- session persistence;
- tree/summary generation.

The Agent only handles language-heavy steps such as candidate wording, semantic analysis, judgement reasoning, and presenting results to the user.

If the Agent calls a step out of order, AwayOut rejects it.

---

## 2. Algorithms

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

## 3. Agent Mode

The Agent-facing skill is:

```text
skills/awayout-security/SKILL.md
```

The high-level tool entry is:

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

## 4. Standalone Mode

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

## 5. CodeAgent integration for Standalone Mode

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

On failure:

```python
return {
    "success": False,
    "result": "error message"
}
```

Optional model discovery:

```python
def list_models():
    return ["model-a", "model-b"]
```

For the full contract, see `CODEAGENT_CONNECTOR.md`.

---

## 6. Windows installation

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

## 7. Standalone model providers

Standalone PAIR currently offers:

```text
1. CodeAgent Python Connector
2. Ollama
```

Agent Mode does not require AwayOut itself to call an Attacker/Judge model; the external Agent performs those language steps while the Controller enforces the workflow.

---

## 8. Project layout

```text
AwayOut-AI/
├── awayout/
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── pair.py            # deterministic PAIR state machine
│   ├── agent_store.py         # Agent Mode persistence
│   ├── attacker.py            # standalone engine
│   ├── judge.py               # standalone engine
│   ├── ollama.py
│   ├── providers.py
│   ├── seeds.py               # reserved extension point
│   └── session.py             # standalone session format
├── skills/
│   └── awayout-security/
│       └── SKILL.md           # Agent instructions
├── agent_api.py               # high-level Agent tool entry
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

## 9. Responsibility boundary

```text
Code / Controller
- what step happens next
- whether a transition is legal
- thresholds and limits
- persistence
- tree structure
- stop conditions

Agent / LLM
- candidate wording
- semantic interpretation
- judgement reasoning
- user interaction
- result presentation
```

The design goal is to keep non-deterministic language work in the Agent while preventing the Agent from freely changing the security-testing algorithm.

---

## 10. Current scope

Implemented now:

- Agent-friendly high-level API;
- deterministic PAIR controller;
- enforced state transitions;
- persistent Agent sessions;
- deterministic tree and summary output;
- Agent skill instructions;
- existing standalone PAIR retained;
- CodeAgent Python Connector retained for standalone mode;
- Windows / uv / Conda setup support.

Reserved next:

- deterministic TAP controller;
- deterministic DrAttack controller;
- richer branching/tree visualization;
- optional MCP wrapper around the stable `agent_api.py` operations;
- optional curated Seed Prompt library.
