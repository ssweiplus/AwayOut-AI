from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from algorithms.drattack.controller import DrAttackController
from algorithms.pair.controller import PairController
from algorithms.tap.controller import TapController
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


def read_json(value: str | None, file_path: str | None) -> dict:
    raw = read_text(value, file_path, "data")
    if not raw:
        raise ValueError("data cannot be empty")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("data must be a JSON object")
    return obj


def cmd_start(args: argparse.Namespace, store: AgentSessionStore) -> int:
    algorithm = args.algorithm.upper().replace("_", "")
    if algorithm == "PAIR":
        controller = PairController(objective=args.objective, max_iterations=args.max_iterations, threshold=args.threshold, strategy=args.strategy)
    elif algorithm == "TAP":
        controller = TapController(objective=args.objective, branch_factor=args.branch_factor, max_depth=args.max_depth, width=args.width, threshold=args.threshold)
    elif algorithm == "DRATTACK":
        strategies = [x.strip() for x in args.strategies.split(",") if x.strip()]
        controller = DrAttackController(objective=args.objective, threshold=args.threshold, top_k_synonyms=args.top_k_synonyms, strategies=strategies, stop_on_success=args.stop_on_success)
    else:
        return fail(f"unsupported algorithm: {args.algorithm}. Available: PAIR, TAP, DrAttack")
    store.save(controller)
    return emit({"success": True, "result": controller.next_action()})


def cmd_candidate(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    if not isinstance(controller, PairController):
        raise ValueError("submit-candidate is PAIR-only; use submit-result for TAP/DrAttack")
    prompt = read_text(args.prompt, args.prompt_file, "prompt")
    result = controller.submit_candidate(prompt, args.strategy)
    store.save(controller)
    return emit({"success": True, "result": result})


def cmd_response(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    if not isinstance(controller, PairController):
        raise ValueError("submit-response is PAIR-only; use submit-result for TAP/DrAttack")
    response = read_text(args.response, args.response_file, "response")
    result = controller.submit_response(response)
    store.save(controller)
    return emit({"success": True, "result": result})


def cmd_judgement(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    if not isinstance(controller, PairController):
        raise ValueError("submit-judgement is PAIR-only; use submit-result for TAP/DrAttack")
    reason = read_text(args.reason, args.reason_file, "reason")
    result = controller.submit_judgement(args.score, reason)
    store.save(controller)
    return emit({"success": True, "result": result})


def cmd_result(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    data = read_json(args.data, args.data_file)
    state = controller.state

    if isinstance(controller, PairController):
        if state == "NEED_CANDIDATE":
            result = controller.submit_candidate(str(data.get("prompt", "")), data.get("strategy"))
        elif state == "WAIT_TARGET_RESPONSE":
            result = controller.submit_response(str(data.get("response", "")))
        elif state == "NEED_JUDGEMENT":
            result = controller.submit_judgement(int(data.get("score")), str(data.get("reason", "")))
        else:
            raise ValueError("session is DONE; no more results are accepted")

    elif isinstance(controller, TapController):
        if state == "NEED_BRANCHES":
            result = controller.submit_branches(list(data.get("branches", [])))
        elif state == "NEED_OFFTOPIC_REVIEW":
            result = controller.submit_offtopic_review(list(data.get("keep_node_ids", [])))
        elif state == "WAIT_TARGET_RESPONSES":
            result = controller.submit_responses(dict(data.get("responses", {})))
        elif state == "NEED_SCORES":
            result = controller.submit_scores(dict(data.get("scores", {})))
        else:
            raise ValueError("session is DONE; no more results are accepted")

    elif isinstance(controller, DrAttackController):
        if state == "NEED_BASELINE_PROMPT":
            result = controller.submit_baseline_prompt(str(data.get("prompt", "")))
        elif state == "WAIT_BASELINE_RESPONSE":
            result = controller.submit_baseline_response(str(data.get("response", "")))
        elif state == "NEED_DECOMPOSITION":
            result = controller.submit_decomposition(list(data.get("sub_prompts", [])))
        elif state == "NEED_SYNONYMS":
            result = controller.submit_synonyms(list(data.get("candidates", [])), list(data.get("selected", [])))
        elif state == "NEED_RECONSTRUCTIONS":
            result = controller.submit_reconstructions(dict(data.get("prompts", {})))
        elif state == "WAIT_STRATEGY_RESPONSES":
            result = controller.submit_strategy_responses(dict(data.get("responses", {})))
        elif state == "NEED_STRATEGY_SCORES":
            result = controller.submit_strategy_scores(dict(data.get("scores", {})))
        else:
            raise ValueError("session is DONE; no more results are accepted")
    else:
        raise ValueError("unknown controller type")

    store.save(controller)
    return emit({"success": True, "result": result})


def cmd_state(args: argparse.Namespace, store: AgentSessionStore) -> int:
    return emit({"success": True, "result": store.load(args.session_id).next_action()})


def cmd_tree(args: argparse.Namespace, store: AgentSessionStore) -> int:
    controller = store.load(args.session_id)
    return emit({"success": True, "result": {"session_id": controller.session_id, "tree": controller.tree_text()}})


def cmd_summary(args: argparse.Namespace, store: AgentSessionStore) -> int:
    return emit({"success": True, "result": store.load(args.session_id).summary()})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AwayOut-AI deterministic Agent API")
    parser.add_argument("--store", default=".awayout-agent", help="agent session directory")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start-test")
    start.add_argument("--algorithm", default="PAIR")
    start.add_argument("--objective", required=True)
    start.add_argument("--threshold", type=int, default=7)
    start.add_argument("--max-iterations", type=int, default=10)
    start.add_argument("--strategy", default="logical_appeal")
    start.add_argument("--branch-factor", type=int, default=2)
    start.add_argument("--max-depth", type=int, default=5)
    start.add_argument("--width", type=int, default=2)
    start.add_argument("--top-k-synonyms", type=int, default=3)
    start.add_argument("--strategies", default="icl_structured,icl_unstructured,word_game,icl_demo1,icl_demo2")
    start.add_argument("--stop-on-success", action="store_true")

    candidate = sub.add_parser("submit-candidate"); candidate.add_argument("session_id"); candidate.add_argument("--prompt"); candidate.add_argument("--prompt-file"); candidate.add_argument("--strategy", default=None)
    response = sub.add_parser("submit-response"); response.add_argument("session_id"); response.add_argument("--response"); response.add_argument("--response-file")
    judgement = sub.add_parser("submit-judgement"); judgement.add_argument("session_id"); judgement.add_argument("--score", type=int, required=True); judgement.add_argument("--reason"); judgement.add_argument("--reason-file")
    result = sub.add_parser("submit-result"); result.add_argument("session_id"); result.add_argument("--data"); result.add_argument("--data-file")

    for name in ("get-state", "get-tree", "get-summary"):
        item = sub.add_parser(name); item.add_argument("session_id")
    return parser


def main() -> int:
    parser = build_parser(); args = parser.parse_args(); store = AgentSessionStore(args.store)
    handlers = {"start-test": cmd_start, "submit-candidate": cmd_candidate, "submit-response": cmd_response, "submit-judgement": cmd_judgement, "submit-result": cmd_result, "get-state": cmd_state, "get-tree": cmd_tree, "get-summary": cmd_summary}
    try:
        return handlers[args.command](args, store)
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
