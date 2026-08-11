# AwayOut-AI

AwayOut-AI is an agent-friendly toolkit for **authorized chatbot security testing**.

It is adapted from the open-source project **Hcxgraphics/JailBreak-AI**:

- Upstream: https://github.com/Hcxgraphics/JailBreak-AI
- Upstream license: MIT
- Upstream methods: DrAttack, PAIR, TAP, LLM-as-Judge

> Use only on systems you are authorized to test.

---

## 1. Architecture

AwayOut-AI is now organized around the Agent Skill as the primary entry point:

```text
User
  ↓
OpenCode / Codex / other Host Agent CLI
  ↓
skills/awayout-security/SKILL.md
  ↓
algorithm controller
  ↓
state + action + handoff
  ↓
Host Agent performs the requested reasoning/user interaction
  ↓
result submitted back to AwayOut
```

The tester stays in the **same host Agent CLI** throughout Agent Mode.

The controller owns:

- algorithm state transitions;
- iteration limits;
- success thresholds;
- allowed next actions;
- persistence;
- tree/summary generation;
- stop conditions.

The Host Agent owns:

- candidate wording;
- semantic analysis;
- judgement reasoning;
- interaction with the tester;
- result presentation.

If the Agent calls a step out of order, AwayOut rejects it.

---

## 2. Skill structure

```text
skills/
└── awayout-security/
    ├── SKILL.md                 # complete Agent instructions
    ├── api.py                   # real Agent API implementation
    ├── common/
    │   └── store.py             # deterministic session persistence
    └── algorithms/
        ├── pair/
        │   ├── SKILL.md         # PAIR-specific instructions
        │   └── controller.py    # deterministic PAIR state machine
        ├── tap/
        │   └── SKILL.md         # reserved
        └── drattack/
            └── SKILL.md         # reserved
```

Root `agent_api.py` is only a compatibility wrapper for:

```text
skills/awayout-security/api.py
```

---

## 3. Algorithms

```text
PAIR      Agent Mode implemented
TAP       reserved
DrAttack  reserved
```

PAIR is fixed as:

```text
NEED_CANDIDATE
      ↓
WAIT_TARGET_RESPONSE
      ↓
NEED_JUDGEMENT
      ↓
DONE or NEED_CANDIDATE
```

TAP and DrAttack must not be emulated manually until their deterministic controllers are implemented.

---

## 4. Agent Mode

Use:

```text
skills/awayout-security/SKILL.md
```

as the full operational guide.

Do not start `main.py` or `interactive_pair.py` while using Agent Mode.

### Start

```bat
.venv\Scripts\python.exe agent_api.py start-test --algorithm PAIR --objective "<objective>"
```

The returned JSON includes:

```text
session_id
state
action
handoff
```

`handoff` explicitly returns control to the Host Agent.

### Attacker boundary

When AwayOut returns:

```text
state = NEED_CANDIDATE
action = generate_candidate
handoff.kind = generate_candidate
```

AwayOut **does not call an Attacker LLM**. The Host Agent generates the candidate itself and submits it:

```bat
.venv\Scripts\python.exe agent_api.py submit-candidate <session_id> --prompt "<candidate>" --strategy "logical_appeal"
```

For multiline text:

```bat
.venv\Scripts\python.exe agent_api.py submit-candidate <session_id> --prompt-file prompt.txt --strategy "logical_appeal"
```

### Target interaction boundary

When AwayOut returns `WAIT_TARGET_RESPONSE`, the Host Agent shows the candidate to the tester in the same Agent CLI. The tester sends it to the authorized target and pastes the real response back into the Host Agent.

Submit it:

```bat
.venv\Scripts\python.exe agent_api.py submit-response <session_id> --response-file response.txt
```

Short responses may use `--response` directly.

### Judge boundary

When AwayOut returns:

```text
state = NEED_JUDGEMENT
action = judge_response
handoff.kind = judge_response
```

AwayOut **does not call a Judge LLM**. The Host Agent applies the returned rubric itself and submits the score/reason:

```bat
.venv\Scripts\python.exe agent_api.py submit-judgement <session_id> --score 5 --reason "<reason>"
```

For multiline reasons:

```bat
.venv\Scripts\python.exe agent_api.py submit-judgement <session_id> --score 5 --reason-file reason.txt
```

The controller decides whether to continue or stop.

### Inspect state / tree / summary

```bat
.venv\Scripts\python.exe agent_api.py get-state <session_id>
.venv\Scripts\python.exe agent_api.py get-tree <session_id>
.venv\Scripts\python.exe agent_api.py get-summary <session_id>
```

Agent state is stored under `.awayout-agent/` and ignored by Git.

---

## 5. Agent Mode user experience

```text
User remains in OpenCode
        ↓
OpenCode calls AwayOut
        ↓
AwayOut returns handoff
        ↓
OpenCode performs the requested language step
        ↓
OpenCode calls AwayOut again
```

The user never needs to enter an AwayOut sub-console.

---

## 6. Standalone Mode

The old Python-driven runtime is retained only for compatibility:

```text
main.py
interactive_pair.py
awayout/attacker.py
awayout/judge.py
```

Standalone PAIR may directly call Attacker/Judge models and present its own CLI.

This path is separate from Agent Mode.

Run standalone only when explicitly desired:

```bat
.venv\Scripts\python.exe main.py
```

or:

```bat
run_windows.bat
```

---

## 7. CodeAgent integration for Standalone Mode

CodeAgent has one supported integration mode: **Python Connector**.

```python
def invoke(message: str, model="", temperature=0.7, max_tokens=1200):
    return {
        "success": True,
        "result": "model output"
    }
```

See `CODEAGENT_CONNECTOR.md`.

Agent Mode does not need this connector because the Host Agent itself performs candidate generation and judgement reasoning.

---

## 8. Installation

Requirements:

- Python 3.10+
- Host Agent capable of running shell commands

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

For complete installation, usage, recovery, and exception handling instructions, read:

```text
skills/awayout-security/SKILL.md
```

---

## 9. Error recovery

Common recovery rule:

```bat
.venv\Scripts\python.exe agent_api.py get-state <session_id>
```

The controller is authoritative. Do not reconstruct workflow state from chat history.

The Skill documents handling for:

- invalid transitions;
- missing sessions;
- reserved algorithms;
- invalid scores;
- empty prompt/response;
- missing temporary files;
- shell quoting issues;
- Host Agent context loss.

---

## 10. Full project layout

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
│   ├── attacker.py            # standalone only
│   ├── judge.py               # standalone only
│   ├── ollama.py
│   ├── providers.py
│   ├── seeds.py
│   └── session.py
├── agent_api.py               # compatibility wrapper
├── main.py                    # standalone
├── interactive_pair.py        # standalone
├── codeagent_connector.py     # standalone CodeAgent connector
├── CODEAGENT_CONNECTOR.md
├── doctor.py
├── setup_windows.bat
├── run_windows.bat
├── requirements.txt
└── README.md
```

---

## 11. Current scope

Implemented:

- skill-centric Agent architecture;
- deterministic PAIR controller;
- explicit Host Agent handoff protocol;
- Attacker/Judge model-call boundaries cut in Agent Mode;
- enforced state transitions;
- persistent sessions;
- deterministic tree/summary output;
- file-based input for long prompt/response/reason text;
- comprehensive Skill documentation;
- standalone compatibility retained.

Reserved:

- deterministic TAP controller;
- deterministic DrAttack controller;
- richer attack-tree visualization;
- optional MCP wrapper;
- optional curated Seed Prompt library.
