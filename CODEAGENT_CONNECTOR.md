# CodeAgent Connector

AwayOut-AI uses a user-written Python connector instead of depending on a specific CodeAgent product/API.

Edit:

```text
codeagent_connector.py
```

or point AwayOut-AI to another connector file with:

```bat
set CODEAGENT_CONNECTOR=D:\path\to\my_connector.py
```

## Required function

The connector only needs to accept **one string message**:

```python
def invoke(
    message: str,
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 1200,
) -> dict:
    ...
```

AwayOut-AI internally maintains multi-turn chat history for Attacker/Judge. Before calling your connector, that history is flattened into one string, for example:

```text
[SYSTEM]
You are assisting an authorized AI security tester...

[USER]
Generate the first test prompt...

[ASSISTANT]
previous model output...
```

Your CodeAgent does not need to understand `list[dict]`, chat roles, or AwayOut-AI's internal history structure. It only receives the final `message: str`.

## Required return format

Success:

```python
{
    "success": True,
    "result": "model response text"
}
```

Failure:

```python
{
    "success": False,
    "result": "error message"
}
```

The normal and recommended `result` is a string.

## Minimal example

```python
from typing import Any


def invoke(message: str, model="", temperature=0.7, max_tokens=1200) -> dict[str, Any]:
    try:
        response = my_codeagent(message)
        return {"success": True, "result": str(response)}
    except Exception as exc:
        return {"success": False, "result": str(exc)}
```

If your local function itself already returns `success, result`, simply adapt it:

```python
def invoke(message: str, model="", temperature=0.7, max_tokens=1200):
    success, result = my_codeagent(message)
    return {"success": success, "result": result}
```

## Optional model discovery

If your CodeAgent can list models, you may additionally define:

```python
def list_models() -> list[str]:
    return ["model-a", "model-b"]
```

If `list_models()` is absent, AwayOut-AI asks you to type the Attacker/Judge model name.

## Secrets and internal endpoints

`codeagent_connector.py` is tracked by Git. Do not hard-code API keys, passwords, tokens, or sensitive internal endpoints into that file and commit them.

Prefer environment variables, or keep your real connector outside the repository and set `CODEAGENT_CONNECTOR` to its path.

## Dependencies

Install connector-specific dependencies into the same environment used to run AwayOut-AI.

For uv:

```bat
uv pip install --python .venv\Scripts\python.exe your-package
```

## Runtime

Run:

```text
run_windows.bat
```

or:

```bat
.venv\Scripts\python.exe main.py
```

Choose `CodeAgent Python Connector` as the model provider.

The connector is used by both Attacker and Judge. The target chatbot remains manual copy/paste.

## Diagnostics

Run:

```bat
.venv\Scripts\python.exe doctor.py
```

`doctor.py` verifies that the connector can be loaded and that `invoke()` exists. It intentionally does not perform a real model request.
