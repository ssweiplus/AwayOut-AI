from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path


def ok(label: str, value: str) -> None:
    print(f"[OK]   {label}: {value}")


def fail(label: str, value: str) -> None:
    print(f"[FAIL] {label}: {value}")


def warn(label: str, value: str) -> None:
    print(f"[WARN] {label}: {value}")


def _check_agent_mode(repo_root: Path) -> bool:
    print("\n[Agent Mode]")
    success = True

    agent_api = repo_root / "agent_api.py"
    if agent_api.is_file():
        ok("agent_api.py", str(agent_api))
    else:
        fail("agent_api.py", "missing")
        success = False

    skill_root = repo_root / "skills" / "awayout-security"
    skill_api = skill_root / "api.py"
    if skill_api.is_file():
        ok("Skill API", str(skill_api))
    else:
        fail("Skill API", "skills/awayout-security/api.py missing")
        success = False

    if skill_root.is_dir():
        sys.path.insert(0, str(skill_root))
        checks = [
            ("PAIR controller", "algorithms.pair.controller", "PairController"),
            ("TAP controller", "algorithms.tap.controller", "TapController"),
            ("DrAttack controller", "algorithms.drattack.controller", "DrAttackController"),
            ("Agent session store", "common.store", "AgentSessionStore"),
        ]
        for label, module_name, attr in checks:
            try:
                module = __import__(module_name, fromlist=[attr])
                getattr(module, attr)
            except Exception as exc:
                fail(label, str(exc))
                success = False
            else:
                ok(label, "importable")
    else:
        fail("Skill root", str(skill_root))
        success = False

    store_dir = repo_root / ".awayout-agent"
    try:
        store_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=store_dir, prefix="doctor-", suffix=".tmp", delete=False) as fp:
            temp_path = Path(fp.name)
        temp_path.unlink(missing_ok=True)
    except Exception as exc:
        fail("Agent session store", f"not writable: {exc}")
        success = False
    else:
        ok("Agent session store", f"writable: {store_dir}")

    return success


def _check_standalone_optional() -> None:
    print("\n[Standalone Mode - optional]")
    provider_found = False

    connector_path = os.getenv("CODEAGENT_CONNECTOR", "codeagent_connector.py").strip()
    if connector_path:
        try:
            from awayout.providers import PythonConnectorClient

            connector = PythonConnectorClient(connector_path)
            if connector.is_running():
                provider_found = True
                ok("CodeAgent Python Connector", f"{connector_path}; contract loadable")
            else:
                warn("CodeAgent Python Connector", f"{connector_path} cannot be loaded or does not define invoke()")
        except Exception as exc:
            warn("CodeAgent Python Connector", str(exc))

    try:
        from awayout.ollama import OllamaClient

        ollama = OllamaClient()
        if ollama.is_running():
            provider_found = True
            ok("Ollama", "API ready")
        elif shutil.which("ollama"):
            warn("Ollama", "CLI installed, API not currently running")
    except Exception as exc:
        warn("Ollama", str(exc))

    if not provider_found:
        warn("Standalone model provider", "none detected; this does NOT block Agent Mode")


def main() -> int:
    repo_root = Path(__file__).resolve().parent
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
        fail("requests", "not installed; install requirements.txt")
        return 1
    else:
        ok("requests", requests.__version__)

    agent_ready = _check_agent_mode(repo_root)
    _check_standalone_optional()

    if agent_ready:
        print("\nAgent Mode is ready. Use agent_api.py or the AwayOut Skill from your host Agent CLI.")
        return 0

    print("\nAgent Mode check failed. Fix the [FAIL] items above and run doctor.py again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
