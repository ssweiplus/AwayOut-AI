# AwayOut-AI

AwayOut-AI is a human-in-the-loop assistant for **authorized chatbot security testing**.

It uses an Attacker model to generate a test prompt, lets a tester send that prompt manually to a real target dialog box, evaluates the pasted target response with a Judge model, and then uses the response + score to generate the next attempt.

```text
Objective
   ↓
Seed Prompt(s) (optional)
   ↓
Attacker LLM
   ↓
Suggested test prompt
   ↓
Human sends prompt to target chatbot
   ↓
Human pastes target response back
   ↓
Judge LLM
   ↓
Score + feedback
   ↓
Next test prompt
```

> Use only on systems you are authorized to test.

---

## Origin and attribution

AwayOut-AI was adapted from the open-source project **Hcxgraphics/JailBreak-AI**:

- Upstream repository: https://github.com/Hcxgraphics/JailBreak-AI
- Upstream project license: MIT

The upstream project implements DrAttack, PAIR, TAP, LLM-as-Judge evaluation, Ollama-based model access, and experiment logging. AwayOut-AI currently focuses on the **PAIR-style generate → evaluate → refine loop**, but changes the usage model substantially for real enterprise testing:

- target chatbot is operated manually by the tester;
- Attacker/Judge model runtime is abstracted behind providers;
- a user-written CodeAgent Python Connector is the recommended model integration;
- Windows setup and diagnostics are provided;
- generated prompt and actually sent prompt are recorded separately;
- target conversation state (`continue` / `new`) is recorded;
- optional high-quality Seed Prompt libraries can be used as mutation starting points.

The PAIR-style attack concept used by the upstream project is based on **Prompt Automatic Iterative Refinement (PAIR)**: *Jailbreaking Black Box Large Language Models in Twenty Queries* (Chao et al.). The upstream project also references DrAttack and TAP research.

AwayOut-AI is not presented as the original implementation of those research methods. Please cite the upstream project and the underlying research when using the framework in reports or publications.

---

## 1. Recommended setup: local CodeAgent connector

The recommended model integration is a user-written Python connector.

AwayOut-AI only requires one contract:

```python
def invoke(messages, model="", temperature=0.7, max_tokens=1200):
    return {
        "success": True,
        "result": "model output"
    }
```

On failure:

```python
{
    "success": False,
    "result": "error message"
}
```

The default connector file is:

```text
codeagent_connector.py
```

Edit only that file to call your own local CodeAgent SDK, module, HTTP client, subprocess, RPC client, or other integration.

A minimal implementation looks like:

```python
def invoke(messages, model="", temperature=0.7, max_tokens=1200):
    try:
        result = my_codeagent(messages=messages, model=model)
        return {"success": True, "result": result}
    except Exception as exc:
        return {"success": False, "result": str(exc)}
```

Optional model discovery:

```python
def list_models():
    return ["model-a", "model-b"]
```

If `list_models()` is not implemented, AwayOut-AI simply asks you to type the Attacker/Judge model name.

For the complete connector contract, see `CODEAGENT_CONNECTOR.md`.

### Do not hard-code secrets

`codeagent_connector.py` is a tracked repository file. Do not commit API keys, tokens, passwords, or sensitive internal endpoints into it.

Prefer environment variables, or point AwayOut-AI to a connector outside the repository:

```bat
set CODEAGENT_CONNECTOR=D:\private\my_codeagent_connector.py
```

---

## 2. Windows: download and run

### Requirements

Required:

- Windows 10/11
- Python 3.10+
- access to at least one model provider

Python dependency:

```text
requests>=2.31.0,<3.0.0
```

Ollama is optional. You do not need Ollama when using your CodeAgent connector.

### First run

Download/clone the repository and double-click:

```text
setup_windows.bat
```

The script will:

- find `py` or `python`;
- verify Python 3.10+;
- create a project-local `.venv`;
- upgrade pip inside `.venv`;
- install `requirements.txt`;
- run `doctor.py`.

No global Python packages are installed.

### Normal run

Double-click:

```text
run_windows.bat
```

If `.venv` does not exist, it automatically launches the setup script first.

### Manual Windows commands

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe doctor.py
.\.venv\Scripts\python.exe interactive_pair.py
```

---

## 3. Model providers

At startup AwayOut-AI offers:

```text
1. CodeAgent Python Connector (recommended)
2. Ollama
3. CodeAgent / OpenAI-compatible HTTP
4. CodeAgent CLI command
```

The Attacker and Judge may use the same provider/model or different model names within the selected provider.

### Provider 1: CodeAgent Python Connector

Default:

```text
codeagent_connector.py
```

Custom path:

```bat
set CODEAGENT_CONNECTOR=D:\path\to\connector.py
```

The connector must define `invoke(...)` and return `success` + `result`.

### Provider 2: Ollama

Default API:

```text
http://127.0.0.1:11434
```

Example:

```powershell
ollama pull mistral
```

### Provider 3: OpenAI-compatible HTTP

Expected endpoints below the configured Base URL:

```text
GET  /models
POST /chat/completions
```

Example Base URL:

```text
http://127.0.0.1:8000/v1
```

Optional environment variables:

```bat
set CODEAGENT_BASE_URL=http://127.0.0.1:8000/v1
set CODEAGENT_MODEL=your-model
set CODEAGENT_API_KEY=
```

### Provider 4: CLI command

Example:

```text
codeagent --model {model}
```

Preset on Windows:

```bat
set CODEAGENT_COMMAND=codeagent --model {model}
```

AwayOut-AI writes the conversation to stdin and reads stdout as the model response.

---

## 4. Seed Prompt library: should you use one?

**Recommended, but optional.** AwayOut-AI can generate directly from the Objective with no seeds. However, for repeatable security testing, a small set of high-quality original templates usually gives the Attacker a stronger starting point and reduces wasted iterations.

Good seeds should capture reusable structure rather than one brittle payload. Useful qualities include:

- a framing or reasoning pattern that has worked reliably;
- clear alignment with a specific strategy such as `logical_appeal`, `authority`, or `roleplay`;
- a `{objective}` placeholder instead of hard-coding one target request;
- enough structure for the Attacker to mutate, but not so much text that every variant becomes near-identical;
- provenance and test notes maintained outside the runtime file when you build a mature corpus.

### Where to add seeds

Default seed file:

```text
seeds/seeds.json
```

Schema:

```json
[
  {
    "name": "research_evaluation",
    "strategy": "logical_appeal",
    "template": "... {objective} ..."
  }
]
```

`strategy` can be:

```text
logical_appeal
authority
roleplay
any
```

At startup, AwayOut-AI loads seeds matching the selected strategy, replaces `{objective}` with the current test Objective, and passes them to the Attacker as **reference starting points**. They are not sent directly to the target unless the Attacker independently produces the same text.

The Attacker is explicitly instructed to preserve useful structure while adapting, combining, or substantially mutating the seeds using the current Objective, previous target response, Judge score, and human notes.

Only the first several matching seeds are included in the Attacker context to avoid a very large seed library overwhelming the feedback signal.

### Custom seed file

Windows CMD:

```bat
set AWAYOUT_SEED_FILE=D:\security\my-seeds.json
run_windows.bat
```

PowerShell:

```powershell
$env:AWAYOUT_SEED_FILE="D:\security\my-seeds.json"
.\run_windows.bat
```

To run without seeds, point `AWAYOUT_SEED_FILE` to a nonexistent/empty library or remove/rename the default seed file. The Attacker will fall back to Objective-only generation.

### Recommended corpus layout for larger teams

For the first version, `seeds/seeds.json` is intentionally simple. As the corpus grows, a useful operational split is:

```text
seeds/
├── seeds.json                 # curated active seeds used by default
├── candidates/                # newly collected templates awaiting review
├── archived/                  # retired/low-quality seeds
└── notes/                     # provenance, target type, success rate, observations
```

Do not treat a large prompt dump as a high-quality seed library. Curate seeds based on reproducibility and test value.

---

## 5. Complete first-test walkthrough

Run:

```text
run_windows.bat
```

Then:

1. Choose `1. CodeAgent Python Connector`.
2. Accept `codeagent_connector.py`, or enter your custom connector path.
3. Choose/type the Attacker model.
4. Choose/type the Judge model.
5. Enter the test Objective.
6. Select an attack strategy.
7. AwayOut-AI loads matching seeds from `seeds/seeds.json` if available.
8. Set the maximum number of iterations.
9. Set the Judge success threshold (default `7`).

Each round works like this:

```text
Attacker generates candidate
        ↓
Tester accepts / edits / regenerates / changes strategy
        ↓
Tester manually sends prompt to target chatbot
        ↓
Tester pastes complete target response
        ↓
Type END on a new line
        ↓
Judge scores response 1-10
        ↓
Response + score feed the next Attacker iteration
```

Before sending a generated prompt:

```text
Enter  use generated prompt
e      edit prompt
r      regenerate
s      switch attack strategy
q      save and quit
```

When pasting a target response, terminate input with a line containing only:

```text
END
```

For target conversation state, choose:

- `continue` — keep using the same target chat session;
- `new` — start a fresh target conversation first.

---

## 6. Built-in attack strategies

Current PAIR-style strategies:

- `logical_appeal`
- `authority`
- `roleplay`

The tester may switch strategy during a session. When the strategy changes, AwayOut-AI reloads matching seeds for the new strategy.

---

## 7. Session logs and review

Logs are written to:

```text
sessions/
```

Each iteration records:

- iteration number;
- strategy;
- attacker improvement summary;
- generated prompt;
- actually sent prompt;
- whether the human modified it;
- target response;
- Judge score;
- Judge reason;
- tester note;
- target conversation mode.

Provider information is stored in model identifiers, for example:

```text
codeagent-connector:model-a
ollama:mistral:latest
codeagent-http:model-b
```

`sessions/` is ignored by Git because target responses may contain sensitive information.

---

## 8. Environment diagnostics

Run:

```bash
python doctor.py
```

Windows project environment:

```powershell
.\.venv\Scripts\python.exe doctor.py
```

`doctor.py` checks:

- operating system;
- Python version;
- `requests` dependency;
- the configured/default Python connector;
- Ollama if present;
- CodeAgent HTTP when `CODEAGENT_BASE_URL` is set;
- CodeAgent CLI when `CODEAGENT_COMMAND` is set.

The default `codeagent_connector.py` intentionally returns a configuration error until you implement `invoke()`. That is expected on a fresh clone.

---

## 9. Troubleshooting

### `Python was not found`

Install Python 3.10+ and open a new terminal. Verify:

```powershell
py -3 --version
```

### Connector cannot be loaded

Check that the file exists and contains:

```python
def invoke(...):
    ...
```

Default path:

```text
codeagent_connector.py
```

### Connector returns failure

AwayOut-AI displays the connector's `result` as the error message. Test the underlying CodeAgent call inside your connector first.

### Connector uses a private Python SDK

Install that SDK into the project's `.venv`, for example:

```powershell
.\.venv\Scripts\python.exe -m pip install your-package
```

If the dependency should be required for every user, add it to `requirements.txt`.

### Seed file fails to load

Validate that the file is UTF-8 JSON and its top level is a list. Every usable item should contain a non-empty `template` string. Invalid/missing seed files do not prevent Objective-only testing.

### Chinese text looks wrong in Windows console

The BAT scripts use UTF-8 (`chcp 65001`). Windows Terminal is recommended if rendering is still incorrect.

### Ollama is selected but unavailable

Start Ollama or choose the CodeAgent Python Connector instead.

---

## 10. Project layout

```text
AwayOut-AI/
├── awayout/
│   ├── __init__.py
│   ├── attacker.py
│   ├── judge.py
│   ├── ollama.py
│   ├── providers.py
│   ├── seeds.py
│   └── session.py
├── seeds/
│   └── seeds.json             # curated Seed Prompt library
├── codeagent_connector.py     # user-editable connector template
├── CODEAGENT_CONNECTOR.md     # connector contract
├── doctor.py                  # environment diagnostics
├── interactive_pair.py        # main CLI
├── setup_windows.bat          # first-time Windows setup
├── run_windows.bat            # normal Windows launcher
├── requirements.txt
├── .gitignore
└── README.md
```

Provider architecture:

```text
Seed Library ──────────────┐
                           ↓
                      AttackerLLM ─┐
                                   ├── ChatClient
                      JudgeLLM ────┘      │
                                          ├── PythonConnectorClient
                                          ├── OllamaClient
                                          ├── OpenAICompatibleClient
                                          └── CommandClient
```

The PAIR attack loop is independent from the model runtime. Adding a new runtime only requires another provider implementation or a different user connector.

---

## 11. Current scope

This version intentionally keeps the target chatbot manual. AwayOut-AI does not automate browser authentication, cookies, target APIs, or UI interaction.

Current focus:

- optional Seed Prompt initialization;
- iterative prompt generation;
- human-in-the-loop target interaction;
- Judge scoring;
- feedback-driven refinement;
- session logging and later review.

Natural future extensions include attack-tree visualization, session replay/branching, browser adapters, automated target connectors, and seed effectiveness statistics.
