from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Protocol

import requests


class ChatClient(Protocol):
    def is_running(self) -> bool: ...
    def list_models(self) -> list[str]: ...
    def chat(self, messages: list[dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1200) -> str: ...


class PythonConnectorClient:
    """Load a user-written Python connector exposing invoke(...) -> {success, result}."""

    def __init__(self, connector_path: str = "codeagent_connector.py"):
        self.connector_path = Path(connector_path).expanduser().resolve()
        self.module: Any | None = None

    def _load(self) -> Any:
        if self.module is not None:
            return self.module
        if not self.connector_path.is_file():
            raise RuntimeError(f"Connector file not found: {self.connector_path}")

        spec = importlib.util.spec_from_file_location("awayout_user_codeagent_connector", self.connector_path)
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

    def chat(self, messages: list[dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1200) -> str:
        module = self._load()
        response = module.invoke(
            messages=messages,
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


class OpenAICompatibleClient:
    """Client for CodeAgent or any OpenAI-compatible local model gateway."""

    def __init__(self, base_url: str, api_key: str = "", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def is_running(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/models", headers=self.headers, timeout=5)
            return response.status_code < 500
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        response = requests.get(f"{self.base_url}/models", headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", [])
        return [item.get("id", "") for item in data if item.get("id")]

    def chat(self, messages: list[dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1200) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class CommandClient:
    """Generic local CLI provider for CodeAgent-like tools."""

    def __init__(self, command_template: str, stdin_mode: str = "json", timeout: int = 120):
        if stdin_mode not in {"json", "prompt"}:
            raise ValueError("stdin_mode must be 'json' or 'prompt'")
        self.command_template = command_template
        self.stdin_mode = stdin_mode
        self.timeout = timeout

    def is_running(self) -> bool:
        try:
            command = self._build_command(model="")
            executable = command[0] if command else ""
            if not executable:
                return False
            from shutil import which
            return which(executable) is not None or os.path.exists(executable)
        except Exception:
            return False

    def list_models(self) -> list[str]:
        return []

    def _build_command(self, model: str) -> list[str]:
        rendered = self.command_template.replace("{model}", model)
        return shlex.split(rendered, posix=os.name != "nt")

    def _stdin_payload(self, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
        if self.stdin_mode == "prompt":
            blocks = []
            for message in messages:
                role = message.get("role", "user").upper()
                blocks.append(f"[{role}]\n{message.get('content', '')}")
            return "\n\n".join(blocks)
        return json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            ensure_ascii=False,
        )

    def chat(self, messages: list[dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1200) -> str:
        command = self._build_command(model)
        payload = self._stdin_payload(messages, model, temperature, max_tokens)
        result = subprocess.run(
            command,
            input=payload,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            raise RuntimeError(f"CodeAgent command failed ({result.returncode}): {result.stderr.strip()}")
        return result.stdout.strip()


def codeagent_http_from_env() -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        base_url=os.getenv("CODEAGENT_BASE_URL", "http://127.0.0.1:8000/v1"),
        api_key=os.getenv("CODEAGENT_API_KEY", ""),
    )
