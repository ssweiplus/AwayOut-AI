# CodeAgent Connector

AwayOut-AI can call a user-written Python connector instead of depending on a specific CodeAgent product/API.

Edit:

```text
codeagent_connector.py
```

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

`result` may also be a dict/list; AwayOut-AI will serialize it to JSON text.

## Minimal example

```python
from typing import Any


def invoke(messages, model="", temperature=0.7, max_tokens=1200) -> dict[str, Any]:
    try:
        # Replace this with your own local CodeAgent invocation.
        response = my_codeagent(messages)
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

If `list_models()` is absent, AwayOut-AI simply asks you to type the Attacker/Judge model name.

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

By default AwayOut-AI loads `codeagent_connector.py` from the repository root. You can point to another file with:

```bat
set CODEAGENT_CONNECTOR=D:\path\to\my_connector.py
```

The connector is used by both the Attacker and Judge model roles. The target chatbot remains manual copy/paste.
