# AwayOut-AI

AwayOut-AI is a human-in-the-loop assistant for **authorized chatbot security testing**.

It uses an Attacker model to generate a test prompt, lets a tester send that prompt manually to a real target dialog box, evaluates the pasted target response with a Judge model, and then uses the response + score to generate the next attempt.

```text
Objective
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
- target conversation state (`continue` / `new`) is recorded.

The PAIR-style concept used by the upstream project is based on **Prompt Automatic Iterative Refinement (PAIR)**: *Jailbreaking Black Box Large Language Models in Twenty Queries* (Chao et al.). The upstream project also references DrAttack and TAP research.

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

Optional model discovery:

```python
def list_models():
    return ["model-a", "model-b"]
```

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

### Python environment priority

The Windows BAT scripts use this priority:

```text
1. currently active Conda environment
2. existing project .venv
3. create a new project .venv
```

So Conda users can keep their existing workflow. If a Conda environment is active, AwayOut-AI uses that environment directly and installs project dependencies into it.

Example:

```bat
conda activate awayout
setup_windows.bat
run_windows.bat
```

The active Conda environment must use Python 3.10 or newer.

If you do **not** want AwayOut-AI dependencies installed into your current Conda environment, deactivate Conda first:

```bat
conda deactivate
setup_windows.bat
```

Then the setup script creates and uses the repository-local `.venv` instead.

### First run

Download/clone the repository and run:

```text
setup_windows.bat
```

It will:

- reuse the active Conda Python when `CONDA_PREFIX` is present and valid;
- otherwise reuse an existing `.venv`;
- otherwise find `py` / `python` and create `.venv`;
- verify Python 3.10+;
- install/update required Python packages in the selected environment;
- run `doctor.py`.

### Normal run

Run:

```text
run_windows.bat
```

If a Conda environment is currently active, it is preferred over `.venv`. Otherwise `.venv` is used when available.

If neither is available, `run_windows.bat` automatically calls `setup_windows.bat`.

### Manual Windows commands with `.venv`

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe doctor.py
.\.venv\Scripts\python.exe interactive_pair.py
```

### Manual Windows commands with Conda

```bat
conda create -n awayout python=3.11 -y
conda activate awayout
python -m pip install -r requirements.txt
python doctor.py
python interactive_pair.py
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

### Provider 4: CLI command

Example:

```text
codeagent --model {model}
```

AwayOut-AI writes the conversation to stdin and reads stdout as the model response.

---

## 4. Complete first-test walkthrough

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
7. Set the maximum number of iterations.
8. Set the Judge success threshold (default `7`).

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

For target conversation state, choose:

- `continue` — keep using the same target chat session;
- `new` — start a fresh target conversation first.

---

## 5. Built-in attack strategies

Current PAIR-style strategies:

- `logical_appeal`
- `authority`
- `roleplay`

The tester may switch strategy during a session.

---

## 6. Session logs and review

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

`sessions/` is ignored by Git because target responses may contain sensitive information.

---

## 7. Environment diagnostics

Run with the currently selected Python environment:

```bash
python doctor.py
```

For `.venv` on Windows:

```powershell
.\.venv\Scripts\python.exe doctor.py
```

`doctor.py` checks the base Python environment and available/configured providers.

---

## 8. Troubleshooting

### Conda is installed but BAT still uses `.venv`

The BAT scripts only prefer Conda when a Conda environment is **currently activated** and `%CONDA_PREFIX%\python.exe` exists.

Run:

```bat
conda activate your-env
run_windows.bat
```

### I activated the wrong Conda environment

The BAT scripts intentionally trust the currently active environment. Activate the desired one before running them:

```bat
conda activate awayout
run_windows.bat
```

### Connector uses a private Python SDK

Install that SDK into whichever environment the launcher is using.

For active Conda:

```bat
python -m pip install your-package
```

For `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install your-package
```

### Chinese text looks wrong in Windows console

The BAT scripts use UTF-8 (`chcp 65001`). Windows Terminal is recommended if rendering is still incorrect.

---

## 9. Project layout

```text
AwayOut-AI/
├── awayout/
│   ├── __init__.py
│   ├── attacker.py
│   ├── judge.py
│   ├── ollama.py
│   ├── providers.py
│   ├── seeds.py              # reserved extension point; not used by current CLI
│   └── session.py
├── codeagent_connector.py
├── CODEAGENT_CONNECTOR.md
├── doctor.py
├── interactive_pair.py
├── setup_windows.bat
├── run_windows.bat
├── requirements.txt
├── .gitignore
└── README.md
```

### Reserved Seed capability

Seed Prompt support is currently **reserved only**. The current CLI does not load a Seed library and users do not need to prepare any templates.

`awayout/seeds.py` and the Attacker-side extension point are retained so a curated Seed library can be added later without redesigning the core loop.

---

## 10. Current scope

This version intentionally keeps the target chatbot manual. AwayOut-AI does not automate browser authentication, cookies, target APIs, or UI interaction.

Current focus:

- iterative prompt generation;
- human-in-the-loop target interaction;
- Judge scoring;
- feedback-driven refinement;
- session logging and later review.

Natural future extensions include attack-tree visualization, session replay/branching, browser adapters, automated target connectors, and optionally a curated Seed Prompt library.
