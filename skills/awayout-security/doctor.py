from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


def ok(label: str, value: str = "OK") -> None:
    print(f"[OK]   {label}: {value}")


def fail(label: str, value: str) -> None:
    print(f"[FAIL] {label}: {value}")


def main() -> int:
    print("AwayOut Agent Mode check")
    print("=" * 48)

    if sys.version_info < (3, 10):
        fail("Python", f"{sys.version.split()[0]} (requires 3.10+)")
        return 1
    ok("Python", sys.version.split()[0])

    required = [
        "SKILL.md",
        "api.py",
        "common/store.py",
        "algorithms/pair/controller.py",
        "algorithms/tap/controller.py",
        "algorithms/drattack/controller.py",
    ]
    missing = [name for name in required if not (SKILL_ROOT / name).is_file()]
    if missing:
        fail("Skill files", ", ".join(missing))
        return 1
    ok("Skill files", "complete")

    try:
        from algorithms.pair.controller import PairController
        from algorithms.tap.controller import TapController
        from algorithms.drattack.controller import DrAttackController
        from common.store import AgentSessionStore
    except Exception as exc:
        fail("Imports", str(exc))
        return 1
    ok("Controllers", "PAIR, TAP, DrAttack")

    try:
        PairController(objective="self-check").next_action()
        TapController(objective="self-check").next_action()
        DrAttackController(objective="self-check").next_action()
    except Exception as exc:
        fail("Controller startup", str(exc))
        return 1
    ok("Controller startup")

    try:
        pair = PairController(
            objective="self-check",
            max_iterations=2,
            threshold=7,
        )
        if pair.stop_policy != "exhaust_budget":
            raise RuntimeError("PAIR default stop_policy is not exhaust_budget")
        pair.submit_candidate("candidate-1")
        pair.submit_response("response-1")
        first = pair.submit_judgement(8, "threshold reached")
        if first["state"] != "NEED_CANDIDATE":
            raise RuntimeError("PAIR exhaust_budget stopped after first success")
        pair.submit_candidate("candidate-2")
        pair.submit_response("response-2")
        final = pair.submit_judgement(9, "second success")
        if final["state"] != "DONE" or final.get("stop_reason") != "max_iterations_reached":
            raise RuntimeError("PAIR exhaust_budget did not stop at max_iterations")
        if final["summary"]["best_node"]["score"] != 9:
            raise RuntimeError("PAIR summary did not retain the best result")

        early = PairController(
            objective="self-check",
            max_iterations=2,
            threshold=7,
            stop_policy="first_success",
        )
        early.submit_candidate("candidate-1")
        early.submit_response("response-1")
        stopped = early.submit_judgement(7, "threshold reached")
        if stopped["state"] != "DONE" or stopped.get("stop_reason") != "success_threshold_reached":
            raise RuntimeError("PAIR first_success did not stop on threshold")
    except Exception as exc:
        fail("PAIR stop policy", str(exc))
        return 1
    ok("PAIR stop policy", "exhaust_budget + first_success")

    try:
        with tempfile.TemporaryDirectory() as directory:
            store = AgentSessionStore(directory)
            controller = PairController(objective="self-check")
            store.save(controller)
            restored = store.load(controller.session_id)
            if restored.session_id != controller.session_id:
                raise RuntimeError("session restore mismatch")
            if restored.stop_policy != "exhaust_budget":
                raise RuntimeError("session restore lost PAIR stop_policy")
    except Exception as exc:
        fail("Session store", str(exc))
        return 1
    ok("Session store", "read/write")

    if importlib.util.find_spec("requests") is not None:
        ok("Standalone dependency requests", "installed (not required for Agent Mode)")

    print("\nAgent Mode is ready. No external LLM provider is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
