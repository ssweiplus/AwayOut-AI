from __future__ import annotations

import os
import platform
import shutil
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

    provider_found = False

    connector_path = os.getenv("CODEAGENT_CONNECTOR", "codeagent_connector.py").strip()
    if connector_path:
        try:
            from awayout.providers import PythonConnectorClient

            connector = PythonConnectorClient(connector_path)
            if connector.is_running():
                provider_found = True
                try:
                    models = connector.list_models()
                except Exception as exc:
                    warn("CodeAgent Python Connector", f"loaded, but list_models() failed: {exc}")
                else:
                    ok(
                        "CodeAgent Python Connector",
                        f"{connector_path}; models: {', '.join(models) if models else '(manual model entry)'}",
                    )
            else:
                warn(
                    "CodeAgent Python Connector",
                    f"{connector_path} exists but cannot be loaded or does not define invoke()",
                )
        except Exception as exc:
            warn("CodeAgent Python Connector", str(exc))

    try:
        from awayout.ollama import OllamaClient

        ollama = OllamaClient()
        if ollama.is_running():
            provider_found = True
            try:
                models = ollama.list_models()
            except Exception as exc:
                warn("Ollama", f"API reachable but model listing failed: {exc}")
            else:
                ok("Ollama", f"API ready; models: {', '.join(models) if models else '(none installed)'}")
        elif shutil.which("ollama"):
            warn("Ollama", "CLI installed, API not currently running")
    except Exception as exc:
        warn("Ollama", str(exc))

    codeagent_base = os.getenv("CODEAGENT_BASE_URL", "").strip()
    if codeagent_base:
        try:
            from awayout.providers import OpenAICompatibleClient

            client = OpenAICompatibleClient(codeagent_base, os.getenv("CODEAGENT_API_KEY", ""))
            if client.is_running():
                provider_found = True
                try:
                    models = client.list_models()
                except Exception:
                    models = []
                ok("CodeAgent HTTP", f"{codeagent_base}; models: {', '.join(models) if models else '(not listed)'}")
            else:
                warn("CodeAgent HTTP", f"configured but not reachable: {codeagent_base}")
        except Exception as exc:
            warn("CodeAgent HTTP", str(exc))

    codeagent_command = os.getenv("CODEAGENT_COMMAND", "").strip()
    if codeagent_command:
        executable = codeagent_command.split()[0].strip('"')
        if shutil.which(executable) or os.path.exists(executable):
            provider_found = True
            ok("CodeAgent CLI", codeagent_command)
        else:
            warn("CodeAgent CLI", f"configured but executable not found: {executable}")

    if not provider_found:
        warn(
            "Model provider",
            "none detected automatically; configure codeagent_connector.py or choose another provider at startup",
        )

    print("\nBase environment is ready. Run interactive_pair.py or run_windows.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
