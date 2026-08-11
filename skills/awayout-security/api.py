from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from algorithms.pair.controller import PairController
from common.store import AgentSessionStore


def emit(payload: dict, exit_code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


def fail(message: str, exit_code: int = 1) -> int:
    return emit({"success": False, "error": message}, exit_code)


def read_text(value: str | None, file_path: str | None, label: str) -> str:
    if value and file_path:
        raise ValueError(f"use either --{label} or --{label}-file, not both")
    if file_path:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"{label} file not found: {file_path}")
        return path.read_text(encoding="utf-8").strip()
    return (value or "").strip()


def cmd_start(args: argparse.Namespace, store: AgentSessionStore) -> int:
    algorithm = args.algorithm.upper()
    if algorithm != "PAIR":
        return fail(
            f"Algorithm {algorithm} is reserved but not implemented in Agent Mode yet. Available: PAIR"
        )
    controller = PairController(
        objective=args.objective,
        max_iterations=args.max_iterations,
        threshold=args.threshold,
        strategy=args.strategy,
    )
    store.save(controller)
    return emit({"success": True, "result": controller.next_action()})


def cmd_candidate(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    prompt = read_text(args.prompt, args.prompt_file, "prompt")
    result = controller.submit_candidate(prompt, args.strategy)
    store.save(controller)
    return emit({"success": True, "result": result})


def cmd_response(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    response = read_text(args.response, args.response_file, "response")
    result = controller.submit_response(response)
    store.save(controller)
    return emit({"success": True, "result": result})


def cmd_judgement(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    reason = read_text(args.reason, args.reason_file, "reason")
    result = controller.submit_judgement(args.score, reason)
    store.save(controller)
    return emit({"success": True, "result": result})


def cmd_state(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    return emit({"success": True, "result": controller.next_action()})


def cmd_tree(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    return emit({"success": True, "result": {"session_id": controller.session_id, "tree": controller.tree_text()}})


def cmd_summary(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    return emit({"success": True, "result": controller.summary()})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AwayOut-AI deterministic Agent API")
    parser.add_argument("--store", default=".awayout-agent", help="agent session directory")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start-test")
    start.add_argument("--algorithm", default="PAIR")
    start.add_argument("--objective", required=True)
    start.add_argument("--max-iterations", type=int, default=10)
    start.add_argument("--threshold", type=int, default=7)
    start.add_argument("--strategy", default="logical_appeal")

    candidate = sub.add_parser("submit-candidate")
    candidate.add_argument("session_id")
    candidate.add_argument("--prompt")
    candidate.add_argument("--prompt-file")
    candidate.add_argument("--strategy", default=None)

    response = sub.add_parser("submit-response")
    response.add_argument("session_id")
    response.add_argument("--response")
    response.add_argument("--response-file")

    judgement = sub.add_parser("submit-judgement")
    judgement.add_argument("session_id")
    judgement.add_argument("--score", type=int, required=True)
    judgement.add_argument("--reason")
    judgement.add_argument("--reason-file")

    for name in ("get-state", "get-tree", "get-summary"):
        item = sub.add_parser(name)
        item.add_argument("session_id")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    store = AgentSessionStore(args.store)
    handlers = {
        "start-test": cmd_start,
        "submit-candidate": cmd_candidate,
        "submit-response": cmd_response,
        "submit-judgement": cmd_judgement,
        "get-state": cmd_state,
        "get-tree": cmd_tree,
        "get-summary": cmd_summary,
    }
    try:
        return handlers[args.command](args, store)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
