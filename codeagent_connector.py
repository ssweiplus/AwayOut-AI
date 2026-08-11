"""User-editable CodeAgent connector for AwayOut-AI.

Implement `invoke(...)` and return exactly:

    {"success": True, "result": "model output"}

or on failure:

    {"success": False, "result": "error message"}

You can call any local SDK, Python module, executable, socket, HTTP service,
or proprietary CodeAgent integration inside this file.
"""
from __future__ import annotations

from typing import Any


def invoke(
    messages: list[dict[str, str]],
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    """Call your local CodeAgent and return {'success': bool, 'result': str}."""

    # Example shape only. Replace this block with your own CodeAgent call.
    #
    # result = my_codeagent.chat(
    #     messages=messages,
    #     model=model,
    #     temperature=temperature,
    #     max_tokens=max_tokens,
    # )
    # return {"success": True, "result": result}

    return {
        "success": False,
        "result": (
            "codeagent_connector.py has not been configured yet. "
            "Edit invoke() and connect it to your local CodeAgent."
        ),
    }
