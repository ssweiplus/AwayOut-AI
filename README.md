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

## 2. Windows installation

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

### Option A: automatic setup

Run once after downloading/cloning the repository:

```bat
setup_windows.bat
```

The script reuses a suitable environment when possible and installs project dependencies.

Environment priority:

```text
1. currently active Conda environment
2. existing project .venv
3. create a new project .venv
```

If `uv` is available, the setup script can use `uv pip` to install dependencies into `.venv` without requiring `pip` inside that environment.

### Option B: manual installation with uv (recommended for uv users)

Run these commands only for the first setup, or when recreating the environment:

```bat
cd D:\path\to\AwayOut-AI
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe doctor.py
```

If `.venv` already exists, skip:

```bat
uv venv .venv
```

You do **not** need to activate `.venv`; directly calling `.venv\Scripts\python.exe` is sufficient.

### Option C: manual installation with standard Python

```bat
cd D:\path\to\AwayOut-AI
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe doctor.py
```

### Option D: manual installation with Conda

```bat
conda create -n awayout python=3.11 -y
conda activate awayout
python -m pip install -r requirements.txt
python doctor.py
```

---

## 3. Running AwayOut-AI

After installation is complete, normal startup does **not** require reinstalling dependencies.

### Option A: Windows launcher

```bat
run_windows.bat
```

### Option B: run directly with `.venv`

```bat
.venv\Scripts\python.exe interactive_pair.py
```

### Option C: run in an activated Conda environment

```bat
conda activate awayout
python interactive_pair.py
```

For most uv users, the normal daily command is simply:

```bat
.venv\Scripts\python.exe interactive_pair.py
```

---

## 4. Model providers

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

## 5. Complete first-test walkthrough

Start AwayOut-AI:

```text
run_windows.bat
```

or:

```text
.venv\Scripts\python.exe interactive_pair.py
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

## 6. Built-in attack strategies

Current PAIR-style strategies:

- `logical_appeal`
- `authority`
- `roleplay`

The tester may switch strategy during a session.

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

`sessions/` is ignored by Git because target responses may contain sensitive information.

---

## 8. Environment diagnostics

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

## 9. Troubleshooting

### uv-created `.venv` has no pip

This can be normal. Use:

```bat
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

You do not need to install pip into the uv-created environment just to use AwayOut-AI.

### Conda is installed but BAT still uses `.venv`

The BAT scripts only prefer Conda when a Conda environment is currently activated and `%CONDA_PREFIX%\python.exe` exists.

```bat
conda activate your-env
run_windows.bat
```

### Connector uses a private Python SDK

Install that SDK into whichever environment the launcher is using.

With uv:

```bat
uv pip install --python .venv\Scripts\python.exe your-package
```

With active Conda:

```bat
python -m pip install your-package
```

### Chinese text looks wrong in Windows console

The BAT scripts use UTF-8 (`chcp 65001`). Windows Terminal is recommended if rendering is still incorrect.

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

## 11. Current scope

This version intentionally keeps the target chatbot manual. AwayOut-AI does not automate browser authentication, cookies, target APIs, or UI interaction.

Current focus:

- iterative prompt generation;
- human-in-the-loop target interaction;
- Judge scoring;
- feedback-driven refinement;
- session logging and later review.

Natural future extensions include attack-tree visualization, session replay/branching, browser adapters, automated target connectors, and optionally a curated Seed Prompt library.
