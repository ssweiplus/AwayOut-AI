# AwayOut-AI

AwayOut-AI is a human-in-the-loop assistant for **authorized chatbot security testing**.

It is adapted from the open-source project **Hcxgraphics/JailBreak-AI**:

- Upstream: https://github.com/Hcxgraphics/JailBreak-AI
- Upstream license: MIT
- Upstream methods: DrAttack, PAIR, TAP, LLM-as-Judge

AwayOut-AI changes the usage model for real enterprise testing: the tester manually operates the target chatbot, while Attacker/Judge models generate candidates, evaluate responses, and drive the next iteration.

> Use only on systems you are authorized to test.

---

## 1. Algorithms

AwayOut-AI keeps the three-algorithm structure of the upstream project:

```text
1. PAIR     - feedback-driven iterative refinement      [available]
2. TAP      - Tree of Attacks with Pruning             [reserved]
3. DrAttack - prompt decomposition and reconstruction  [reserved]
```

`main.py` is the unified entry point. The current runnable implementation is PAIR; TAP and DrAttack are reserved for later integration.

---

## 2. CodeAgent integration

**CodeAgent has exactly one supported integration mode: Python Connector.**

Default file:

```text
codeagent_connector.py
```

Implement:

```python
def invoke(messages, model="", temperature=0.7, max_tokens=1200):
    return {
        "success": True,
        "result": "model output"
    }
```

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

The connector may internally call your own SDK, Python module, subprocess, RPC client, HTTP client, or proprietary CodeAgent integration. AwayOut-AI does not expose separate CodeAgent HTTP or CLI provider modes.

For the full contract, see `CODEAGENT_CONNECTOR.md`.

Do not commit secrets into the tracked connector template. Prefer environment variables or an external connector file:

```bat
set CODEAGENT_CONNECTOR=D:\private\my_codeagent_connector.py
```

---

## 3. Windows installation

Requirements:

- Windows 10/11
- Python 3.10+
- one model provider: CodeAgent Connector or Ollama

### Automatic setup

Run once:

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
cd D:\path\to\AwayOut-AI
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

## 4. Running AwayOut-AI

After installation, do not reinstall dependencies every time.

Windows launcher:

```bat
run_windows.bat
```

Direct run with `.venv`:

```bat
.venv\Scripts\python.exe main.py
```

Activated Conda environment:

```bat
conda activate awayout
python main.py
```

`main.py` first asks which algorithm to use.

---

## 5. Model providers

The PAIR runtime currently offers only:

```text
1. CodeAgent Python Connector
2. Ollama
```

### CodeAgent Python Connector

Default:

```text
codeagent_connector.py
```

Custom path:

```bat
set CODEAGENT_CONNECTOR=D:\path\to\connector.py
```

### Ollama

Default API:

```text
http://127.0.0.1:11434
```

Example:

```bat
ollama pull mistral
```

---

## 6. PAIR workflow

Current PAIR flow:

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

Before sending a generated prompt:

```text
Enter  use generated prompt
e      edit prompt
r      regenerate
s      switch strategy
q      save and quit
```

Target conversation mode:

- `continue` - continue the current target chat
- `new` - start a new target chat

Judge success threshold defaults to `7/10`.

---

## 7. Session logs

Logs are saved to:

```text
sessions/
```

Each iteration records the generated prompt, actual sent prompt, target response, Judge score/reason, strategy, human modification flag, tester note, and target conversation mode.

`sessions/` is ignored by Git because target responses may contain sensitive data.

---

## 8. Environment diagnostics

Run:

```bat
.venv\Scripts\python.exe doctor.py
```

or in an activated Conda environment:

```bat
python doctor.py
```

`doctor.py` checks Python, dependencies, CodeAgent Connector loadability, and Ollama availability. It does not invoke the CodeAgent model during the health check.

---

## 9. Project layout

```text
AwayOut-AI/
├── awayout/
│   ├── attacker.py
│   ├── judge.py
│   ├── ollama.py
│   ├── providers.py          # ChatClient + PythonConnectorClient
│   ├── seeds.py              # reserved extension point
│   └── session.py
├── main.py                   # unified three-algorithm entry point
├── interactive_pair.py       # PAIR implementation
├── codeagent_connector.py    # user-editable CodeAgent connector
├── CODEAGENT_CONNECTOR.md
├── doctor.py
├── setup_windows.bat
├── run_windows.bat
├── requirements.txt
└── README.md
```

Seed Prompt support is reserved only and is not loaded by the current CLI.

---

## 10. Current scope

Implemented now:

- unified algorithm entry point;
- PAIR human-in-the-loop testing;
- CodeAgent Python Connector;
- Ollama provider;
- Attacker/Judge scoring loop;
- session logging;
- Windows/uv/Conda setup support.

Reserved next:

- TAP;
- DrAttack;
- attack-tree visualization and branching;
- optional curated Seed Prompt library.
