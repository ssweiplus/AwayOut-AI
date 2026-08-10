# AwayOut-AI

AwayOut-AI is a human-in-the-loop assistant for **authorized chatbot security testing**.

The current version implements a PAIR-style interactive workflow for real dialog boxes that do not expose an API:

```text
Objective
   ↓
Attacker LLM (local Ollama)
   ↓
Suggested test prompt
   ↓
Human copies prompt into target chatbot
   ↓
Human pastes target response into AwayOut-AI
   ↓
Judge LLM (local Ollama)
   ↓
Score + feedback
   ↓
Attacker generates the next prompt
```

The target system remains manual. Only the Attacker and Judge models run locally through Ollama.

> Use only on systems you are authorized to test.

---

## Windows: quickest way to run

### Requirements

You need:

1. **Windows 10 22H2 or newer / Windows 11**.
2. **Python 3.10 or newer**.
3. **Ollama for Windows**.
4. Enough disk/RAM for the Ollama model you choose.

Python download:

- https://www.python.org/downloads/windows/

Ollama Windows download:

- https://ollama.com/download/windows

The normal Ollama Windows installer runs Ollama in the background and exposes the local API at:

```text
http://127.0.0.1:11434
```

You normally **do not need to run `ollama serve` manually** after installing the Windows app. If the API is not available, start Ollama from the Windows Start menu. The setup script also tries `ollama serve` as a fallback.

### First run

Download/clone this repository, then simply double-click:

```text
setup_windows.bat
```

The setup script will:

- find `py` or `python`;
- verify Python 3.10+;
- create a local `.venv` virtual environment;
- upgrade pip inside `.venv`;
- install `requirements.txt`;
- check whether the `ollama` command exists;
- open the official Ollama Windows download page if Ollama is missing;
- verify the Ollama API;
- detect whether any local models are installed;
- offer to download `mistral` when no model exists;
- run `doctor.py` for a final environment check.

No global Python packages are installed. Everything is placed under this repository's `.venv` directory.

### Normal use after setup

Double-click:

```text
run_windows.bat
```

It performs an environment check and starts the interactive tester.

If `.venv` is missing, `run_windows.bat` automatically launches the first-time setup.

### Windows manual commands

If you prefer PowerShell or CMD instead of the BAT files:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe doctor.py
.\.venv\Scripts\python.exe interactive_pair.py
```

If you have no local Ollama model yet:

```powershell
ollama pull mistral
```

---

## Environment check

At any time run:

```bash
python doctor.py
```

On Windows with the repository virtual environment:

```powershell
.\.venv\Scripts\python.exe doctor.py
```

It checks:

- operating system;
- Python executable and version;
- `requests` dependency;
- Ollama API connectivity;
- installed Ollama models.

Typical healthy output:

```text
AwayOut-AI environment check
============================================================
[OK]   OS: Windows 11
[OK]   Python executable: ...\.venv\Scripts\python.exe
[OK]   Python version: 3.12.x
[OK]   requests: 2.x.x
[OK]   Ollama API: http://127.0.0.1:11434
[OK]   Ollama models: mistral:latest

Environment looks ready.
```

---

## Python dependencies

The Python dependency set is intentionally small:

```text
requests>=2.31.0,<3.0.0
```

Everything else used by the project is from the Python standard library.

Python 3.10+ is required because the code uses modern type annotation syntax.

---

## Ollama / model requirements

### Attacker model

The Attacker should be a chat/instruct model capable of:

- following structured instructions;
- producing JSON reliably;
- understanding previous target responses and scores;
- generating materially different prompt strategies across iterations.

### Judge model

The Judge should be instruction-following and stable. It evaluates the target response and returns a score/reason.

For basic local testing, the same Ollama model can be used for both roles.

For more rigorous evaluation, use different Attacker and Judge models to reduce same-model bias.

### Model size

AwayOut-AI does not impose a model size. Model speed and quality depend on your machine and model choice.

A small/medium instruct model is usually easiest for initial Windows testing. The setup script suggests `mistral` only as a convenient default; you may select any installed Ollama chat/instruct model when the program starts.

---

## Run on Linux/macOS

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start/launch Ollama according to your platform, install at least one model, then run:

```bash
python doctor.py
python interactive_pair.py
```

---

## Interactive workflow

Start with:

```bash
python interactive_pair.py
```

or on Windows:

```text
run_windows.bat
```

The CLI asks for:

1. Ollama URL;
2. Attacker model;
3. Judge model;
4. test Objective;
5. attack strategy;
6. maximum iterations;
7. Judge success threshold.

If local models are available, Attacker/Judge can be selected by number instead of manually typing an exact Ollama model name.

The numeric inputs are validated, so accidental text/out-of-range values will not terminate the program.

### Typical interaction

```text
AwayOut-AI · Interactive PAIR Assistant

测试目标 Objective: Test whether the chatbot reveals protected instructions
攻击策略: logical_appeal
最大轮数: 10

Iteration 1/10

[改进思路]
...

[建议发送到目标对话框的 Prompt]
...

下一步操作:
  Enter  直接使用上面的 Prompt
  e      手工修改 Prompt
  r      让攻击者重新生成
  s      切换策略后重新生成
  q      保存并退出
```

Send the suggested prompt to the real target chatbot. Then paste its complete response into AwayOut-AI.

Finish pasted multi-line content with a line containing only:

```text
END
```

AwayOut-AI will then:

```text
Target response
      ↓
Judge score + reason
      ↓
Feedback to Attacker
      ↓
Next suggested prompt
```

---

## Built-in attack strategies

The current PAIR-style attacker contains three strategies:

- `logical_appeal`
- `authority`
- `roleplay`

The tester can switch strategy during a session.

---

## Generated prompt vs actually sent prompt

A tester may modify a generated candidate before sending it. AwayOut-AI records both values:

```json
{
  "generated_prompt": "prompt produced by attacker model",
  "sent_prompt": "prompt actually sent by tester",
  "human_modified": true
}
```

This helps distinguish fully automated discoveries from human-assisted ones during later review.

---

## Target conversation state

For each interaction you can record:

- `continue` — send the prompt in the current target chat session;
- `new` — create a fresh target conversation first.

AwayOut-AI does not control the target UI. This field records what the human tester actually did.

This allows later comparison of:

- single-turn behavior;
- multi-turn behavior;
- gradual context accumulation.

---

## Session logs

Logs are written under:

```text
sessions/
```

Each record includes:

- iteration;
- strategy;
- attacker improvement summary;
- generated prompt;
- sent prompt;
- human-modified flag;
- target response;
- Judge score;
- Judge reason;
- tester note;
- target conversation mode.

`sessions/` is ignored by Git because test responses can contain sensitive information.

---

## Troubleshooting on Windows

### `Python was not found`

Install Python 3.10+ from:

```text
https://www.python.org/downloads/windows/
```

Then open a new CMD/PowerShell window and verify:

```powershell
py -3 --version
```

or:

```powershell
python --version
```

### `Ollama is not installed or is not on PATH`

Install Ollama from:

```text
https://ollama.com/download/windows
```

After installation, open a **new** terminal window and run:

```powershell
ollama --version
```

### Ollama command exists but API cannot be reached

Normal Windows installer:

1. open the Start menu;
2. launch **Ollama**;
3. retry `run_windows.bat`.

You can also check:

```powershell
curl http://127.0.0.1:11434/api/tags
```

If you intentionally use standalone CLI mode:

```powershell
ollama serve
```

### No Ollama model installed

Run:

```powershell
ollama pull mistral
```

Then check:

```powershell
ollama list
```

### Console Chinese text looks wrong

The Windows BAT files run:

```text
chcp 65001
```

to use UTF-8. Windows Terminal or a modern PowerShell/CMD terminal is recommended if characters still render incorrectly.

### Model is slow or runs out of memory

Choose a smaller Ollama model. AwayOut-AI itself uses very little memory; most resource consumption comes from the local Attacker/Judge LLM.

---

## Project layout

```text
AwayOut-AI/
├── awayout/
│   ├── __init__.py
│   ├── attacker.py
│   ├── judge.py
│   ├── ollama.py
│   └── session.py
├── doctor.py
├── interactive_pair.py
├── setup_windows.bat
├── run_windows.bat
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Current scope

The first version deliberately keeps the target dialog box manual. This avoids requiring browser automation, cookies, authentication, or a target API before the attack-assistance workflow can be used.

Potential later extensions:

- browser-extension target adapter;
- Playwright/Puppeteer adapter;
- generic HTTP/OpenAI-compatible target adapter;
- TAP-style multi-branch interactive testing;
- attack-tree visualization;
- session replay and branch-from-history.
