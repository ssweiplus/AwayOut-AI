from __future__ import annotations

import platform
import sys


def ok(label: str, value: str) -> None:
    print(f"[OK]   {label}: {value}")


def fail(label: str, value: str) -> None:
    print(f"[FAIL] {label}: {value}")


def warn(label: str, value: str) -> None:
    print(f"[WARN] {label}: {value}")


def main() -> int:
    print("AwayOut-AI environment check")
    print("=" * 60)

    ok("OS", f"{platform.system()} {platform.release()}")
    ok("Python executable", sys.executable)
    version = sys.version_info
    if version >= (3, 10):
        ok("Python version", platform.python_version())
    else:
        fail("Python version", f"{platform.python_version()} (requires 3.10+)")
        return 1

    try:
        import requests
    except ImportError:
        fail("requests", "not installed; run setup_windows.bat or pip install -r requirements.txt")
        return 1
    else:
        ok("requests", requests.__version__)

    from awayout.ollama import OllamaClient

    client = OllamaClient()
    if not client.is_running():
        fail("Ollama API", "cannot reach http://127.0.0.1:11434")
        print("       On Windows, start the Ollama app from the Start menu.")
        print("       If you use standalone Ollama, run: ollama serve")
        return 2

    ok("Ollama API", "http://127.0.0.1:11434")
    try:
        models = client.list_models()
    except Exception as exc:  # diagnostic command: surface the concrete error
        fail("Ollama models", str(exc))
        return 2

    if not models:
        warn("Ollama models", "none installed; run: ollama pull mistral")
        return 3

    ok("Ollama models", ", ".join(models))
    print("\nEnvironment looks ready. Run interactive_pair.py or run_windows.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
