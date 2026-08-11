from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Protocol


class ChatClient(Protocol):
    def is_running(self) -> bool: ...
    def list_models(self) -> list[str]: ...
    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> str: ...


class PythonConnectorClient:
    """Load a user-written CodeAgent connector exposing invoke(message, ...) -> {success, result}."""

    def __init__(self, connector_path: str = "codeagent_connector.py"):
        self.connector_path = Path(connector_path).expanduser().resolve()
        self.module: Any | None = None

    def _load(self) -> Any:
        if self.module is not None:
            return self.module
        if not self.connector_path.is_file():
            raise RuntimeError(f"Connector file not found: {self.connector_path}")

        spec = importlib.util.spec_from_file_location(
            "awayout_user_codeagent_connector",
            self.connector_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load connector: {self.connector_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not callable(getattr(module, "invoke", None)):
            raise RuntimeError("Connector must define callable invoke(...)")

        self.module = module
        return module

    def is_running(self) -> bool:
        try:
            self._load()
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        module = self._load()
        func = getattr(module, "list_models", None)
        if not callable(func):
            return []

        value = func()
        if not isinstance(value, list):
            raise RuntimeError("Optional list_models() must return list[str]")
        return [str(item) for item in value]

    @staticmethod
    def _flatten_messages(messages: list[dict[str, str]]) -> str:
        blocks: list[str] = []
        for item in messages:
            role = str(item.get("role", "user")).upper()
            content = str(item.get("content", "")).strip()
            if content:
                blocks.append(f"[{role}]\n{content}")
        return "\n\n".join(blocks)

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> str:
        module = self._load()
        message = self._flatten_messages(messages)
        response = module.invoke(
            message=message,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not isinstance(response, dict):
            raise RuntimeError("Connector invoke() must return dict: {'success': bool, 'result': ...}")
        if "success" not in response or "result" not in response:
            raise RuntimeError("Connector result must contain both 'success' and 'result'")
        if response.get("success") is not True:
            raise RuntimeError(f"CodeAgent connector failed: {response.get('result', '')}")

        result = response.get("result")
        if result is None:
            return ""
        if isinstance(result, str):
            return result.strip()
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)
        return str(result).strip()
