"""User-editable CodeAgent connector for AwayOut-AI.

AwayOut-AI passes one flattened string to this connector.
Implement `invoke(...)` and return exactly:

    {"success": True, "result": "model output"}

or on failure:

    {"success": False, "result": "error message"}
"""
from __future__ import annotations

from typing import Any


def invoke(
    message: str,
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    """Call your local CodeAgent with one string and return {'success': bool, 'result': str}."""

    # Replace this block with your own CodeAgent call.
    #
    # result = my_codeagent(
    #     message=message,
    #     model=model,
    # )
    # return {"success": True, "result": str(result)}

    return {
        "success": False,
        "result": (
            "codeagent_connector.py has not been configured yet. "
            "Edit invoke() and connect it to your local CodeAgent."
        ),
    }
