from __future__ import annotations

import json
import os
import shlex
import subprocess
from typing import Protocol

import requests


class ChatClient(Protocol):
    def is_running(self) -> bool: ...
    def list_models(self) -> list[str]: ...
    def chat(self, messages: list[dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1200) -> str: ...


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
    """Generic local CLI model provider. The full conversation is passed on stdin as JSON."""

    def __init__(self, command_template: str, timeout: int = 120):
        self.command_template = command_template
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

    def chat(self, messages: list[dict[str, str]], model: str, temperature: float = 0.7, max_tokens: int = 1200) -> str:
        command = self._build_command(model)
        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            ensure_ascii=False,
        )
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
