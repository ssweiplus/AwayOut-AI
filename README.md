# AwayOut-AI

AwayOut-AI is a human-in-the-loop assistant for **authorized chatbot security testing**.

It generates a test prompt with an Attacker LLM, lets the tester send that prompt manually to a real dialog box, evaluates the pasted response with a Judge LLM, then uses the result to generate the next attempt.

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

## Model providers

Attacker and Judge are no longer tied to Ollama. At startup you can choose:

1. **Ollama**
2. **CodeAgent / OpenAI-compatible HTTP API**
3. **CodeAgent CLI command**

The real target chatbot is still operated manually and does not need an API.

---

## Windows: download and run

### Requirements

Required:

- Windows 10/11
- Python 3.10+
- network/local access to at least one supported model provider

Python dependency:

```text
requests>=2.31.0,<3.0.0
```

You do **not** need Ollama if you use CodeAgent.

### First run

Download or clone the repository and double-click:

```text
setup_windows.bat
```

It will:

- detect Python;
- require Python 3.10+;
- create `.venv` locally in the project;
- install Python dependencies;
- run `doctor.py`.

It does not install global Python packages and no longer forces Ollama installation.

### Normal run

Double-click:

```text
run_windows.bat
```

Then choose the model provider interactively.

---

# Using local CodeAgent

Because different products/tools use the name `codeagent`, AwayOut-AI supports two generic CodeAgent integration modes instead of hard-coding one vendor-specific interface.

## Mode A: CodeAgent exposes an OpenAI-compatible API

Choose:

```text
2. CodeAgent / OpenAI-compatible HTTP
```

AwayOut-AI expects these endpoints below the Base URL:

```text
GET  /models
POST /chat/completions
```

For example, if CodeAgent exposes:

```text
http://127.0.0.1:8000/v1/chat/completions
```

enter:

```text
http://127.0.0.1:8000/v1
```

You will then be asked for:

```text
CodeAgent API Base URL
API Key
Attacker model
Judge model
```

If `/models` returns model IDs, AwayOut-AI displays them as a selectable list. If model discovery is unavailable, enter the model name manually.

### Optional Windows environment variables

CMD:

```bat
set CODEAGENT_BASE_URL=http://127.0.0.1:8000/v1
set CODEAGENT_MODEL=your-model-name
set CODEAGENT_API_KEY=
run_windows.bat
```

PowerShell:

```powershell
$env:CODEAGENT_BASE_URL="http://127.0.0.1:8000/v1"
$env:CODEAGENT_MODEL="your-model-name"
$env:CODEAGENT_API_KEY=""
.\run_windows.bat
```

The API key is optional for local gateways that do not require authentication.

## Mode B: CodeAgent is a local CLI command

Choose:

```text
3. CodeAgent CLI command
```

Enter a command template such as:

```text
codeagent --model {model}
```

`{model}` is replaced with the selected Attacker/Judge model name.

AwayOut-AI invokes the command with `subprocess`, writes the conversation to stdin and reads the model response from stdout. The provider implementation supports two stdin representations internally:

- `json`: structured model/messages/options payload;
- `prompt`: flattened `[SYSTEM] / [USER] / [ASSISTANT]` text.

The default is `json`. If your local CodeAgent CLI expects a different contract, adjust the `CommandClient` configuration in `awayout/providers.py`; the Attacker/Judge logic does not need modification.

You can preset the command on Windows:

```bat
set CODEAGENT_COMMAND=codeagent --model {model}
```

If `codeagent.exe` is not on `PATH`, use the complete executable path.

---

## Ollama mode

Ollama remains supported for compatibility.

Choose:

```text
1. Ollama
```

Default API:

```text
http://127.0.0.1:11434
```

Example:

```powershell
ollama pull mistral
```

On the normal Windows Ollama installation, the local API usually runs in the background. If needed, launch Ollama from the Start menu or run `ollama serve` for a standalone CLI setup.

---

## Interactive workflow

Run:

```bash
python interactive_pair.py
```

or on Windows:

```text
run_windows.bat
```

The program asks for:

1. Model Provider
2. Provider endpoint/command if applicable
3. Attacker model
4. Judge model
5. Test Objective
6. Attack strategy
7. Maximum iterations
8. Judge threshold

Available attack strategies:

- `logical_appeal`
- `authority`
- `roleplay`

Typical loop:

```text
Iteration 1
  ↓
Attacker generates candidate
  ↓
Tester may accept/edit/regenerate/switch strategy
  ↓
Tester sends prompt to target UI
  ↓
Paste target response and finish with END
  ↓
Judge scores 1-10
  ↓
Feedback enters next Attacker iteration
```

Commands before sending a candidate:

```text
Enter  use generated prompt
e      edit prompt
r      regenerate
s      switch attack strategy
q      save and quit
```

---

## Session logs

Logs are stored in:

```text
sessions/
```

Each iteration records:

- strategy
- attacker improvement
- generated prompt
- actually sent prompt
- whether the tester modified it
- target response
- Judge score
- Judge reason
- tester note
- target conversation mode (`continue` / `new`)

Provider information is included in the Attacker/Judge model identifiers, for example:

```text
codeagent-http:model-name
codeagent-cli:model-name
ollama:mistral:latest
```

`sessions/` is ignored by Git because target responses may contain sensitive information.

---

## Environment diagnostics

Run:

```bash
python doctor.py
```

Windows project environment:

```powershell
.\.venv\Scripts\python.exe doctor.py
```

`doctor.py` checks the base Python environment and reports any providers it can detect. A missing Ollama installation is no longer treated as an error because CodeAgent may be used instead.

For automatic CodeAgent HTTP diagnosis, set:

```text
CODEAGENT_BASE_URL
```

For automatic CodeAgent CLI diagnosis, set:

```text
CODEAGENT_COMMAND
```

---

## Project layout

```text
AwayOut-AI/
├── awayout/
│   ├── __init__.py
│   ├── attacker.py
│   ├── judge.py
│   ├── ollama.py
│   ├── providers.py
│   └── session.py
├── doctor.py
├── interactive_pair.py
├── setup_windows.bat
├── run_windows.bat
├── requirements.txt
└── README.md
```

### Provider architecture

```text
AttackerLLM ─┐
             ├── ChatClient
JudgeLLM ────┘      │
                    ├── OllamaClient
                    ├── OpenAICompatibleClient  ← CodeAgent HTTP
                    └── CommandClient           ← CodeAgent CLI
```

This keeps PAIR logic independent from the local model runtime. Adding another model gateway later only requires another provider implementing `chat()` / model discovery behavior.
