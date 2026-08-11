# CodeAgent Connector

AwayOut-AI can call a user-written Python connector instead of depending on a specific CodeAgent product/API.

Edit:

```text
codeagent_connector.py
```

or point AwayOut-AI to another connector file with:

```bat
set CODEAGENT_CONNECTOR=D:\path\to\my_connector.py
```

## Required function

The connector must define:

```python
def invoke(
    messages: list[dict[str, str]],
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 1200,
) -> dict:
    ...
```

`messages` follows the usual chat-message shape:

```python
[
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
]
```

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

`result` may also be a dict/list; AwayOut-AI serializes it to JSON text.

## Minimal example

```python
from typing import Any


def invoke(messages, model="", temperature=0.7, max_tokens=1200) -> dict[str, Any]:
    try:
        response = my_codeagent(messages=messages, model=model)
        return {"success": True, "result": response}
    except Exception as exc:
        return {"success": False, "result": str(exc)}
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

Prefer environment variables:

```python
import os

TOKEN = os.getenv("MY_CODEAGENT_TOKEN", "")
```

or keep your real connector outside the repository and use:

```bat
set CODEAGENT_CONNECTOR=D:\private\my_codeagent_connector.py
```

## Dependencies used by your connector

The base project installs only:

```text
requests>=2.31.0,<3.0.0
```

If your connector imports another SDK, install it into AwayOut-AI's local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install your-package
```

If every user of the repository needs that dependency, add it to `requirements.txt`.

## Runtime

Run:

```text
run_windows.bat
```

or:

```bash
python interactive_pair.py
```

Choose:

```text
1. CodeAgent Python Connector
```

The connector is used by both the Attacker and Judge roles. The target chatbot remains manual copy/paste.

## Diagnostics

Run:

```powershell
.\.venv\Scripts\python.exe doctor.py
```

`doctor.py` verifies that the connector can be loaded and that `invoke()` exists. It intentionally does not call `invoke()` because a health check should not trigger a real model request or consume tokens/resources.

Therefore, a connector can be reported as loadable while the actual CodeAgent call inside `invoke()` is still unconfigured. The first real Attacker/Judge call will surface the connector's failure message.

## Common errors

### `Connector file not found`

Check `CODEAGENT_CONNECTOR` or use the default `codeagent_connector.py` in the repository root.

### `Connector must define callable invoke(...)`

Make sure the file defines a top-level `invoke()` function with the required contract.

### `CodeAgent connector failed: ...`

This means your connector returned:

```python
{"success": False, "result": "..."}
```

The text in `result` is shown directly so you can debug the underlying CodeAgent call.

### Import error for your private SDK

Install that SDK into `.venv`, not necessarily into global Python.
