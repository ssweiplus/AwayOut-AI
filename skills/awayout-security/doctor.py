from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

SKILL_ROOT = Path(__file__).resolve().parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


def ok(label: str, value: str = "OK") -> None:
    print(f"[OK]   {label}: {value}")


def fail(label: str, value: str) -> None:
    print(f"[FAIL] {label}: {value}")


def expect_value_error(label: str, fn) -> None:
    try:
        fn()
    except ValueError:
        return
    raise RuntimeError(f"{label} did not reject invalid configuration")


def main() -> int:
    print("AwayOut Agent Mode check")
    print("=" * 48)

    if sys.version_info < (3, 10):
        fail("Python", f"{sys.version.split()[0]} (requires 3.10+)")
        return 1
    ok("Python", sys.version.split()[0])

    required = [
        "SKILL.md", "INSTALL.md", "REPORTING.md", "api.py", "doctor.py",
        "common/store.py", "common/presenter.py", "common/interaction.py",
        "common/scoring.py", "common/memory.py", "common/report.py",
        "algorithms/pair/SKILL.md", "algorithms/pair/controller.py",
        "algorithms/tap/SKILL.md", "algorithms/tap/controller.py",
        "algorithms/drattack/SKILL.md", "algorithms/drattack/controller.py",
    ]
    missing = [name for name in required if not (SKILL_ROOT / name).is_file()]
    if missing:
        fail("Skill files", ", ".join(missing))
        return 1
    ok("Skill files", "router + presenter + interaction + scoring + memory + report + 3 algorithms")

    try:
        from algorithms.pair.controller import PairController
        from algorithms.tap.controller import TapController
        from algorithms.drattack.controller import DrAttackController
        from common.interaction import EVENT_MARKER, OPERATOR_MARKER, RESPONSE_MARKER, parse_user_submission
        from common.memory import build_memory_context
        from common.store import AgentSessionStore
        from api import algorithm_selection_contract, cmd_user_input, enrich
    except Exception as exc:
        fail("Imports", str(exc))
        return 1
    ok("Imports", "controllers + interaction + memory + API")

    try:
        actions = {
            "PAIR": PairController(objective="self-check").next_action(),
            "TAP": TapController(objective="self-check").next_action(),
            "DrAttack": DrAttackController(objective="self-check").next_action(),
        }
        for name, action in actions.items():
            guard = action.get("handoff", {}).get("objective_guard")
            if not isinstance(guard, dict) or guard.get("original_objective") != "self-check":
                raise RuntimeError(f"{name} initial handoff missing objective_guard")
        for name in ("PAIR", "TAP", "DrAttack"):
            if not actions[name]["handoff"].get("mutation_goal"):
                raise RuntimeError(f"{name} initial handoff missing mutation_goal")
    except Exception as exc:
        fail("Controller startup", str(exc))
        return 1
    ok("Controller startup", "objective guards present")

    try:
        intro = algorithm_selection_contract()
        names = [item.get("algorithm") for item in intro.get("required_user_output", {}).get("options", [])]
        if intro.get("must_show_to_user") is not True or names != ["PAIR", "TAP", "DrAttack"]:
            raise RuntimeError("algorithm selection contract invalid")
    except Exception as exc:
        fail("Algorithm intro contract", str(exc))
        return 1
    ok("Algorithm intro contract", "PAIR + TAP + DrAttack")

    try:
        expect_value_error("PAIR max_iterations", lambda: PairController(objective="x", max_iterations=0))
        expect_value_error("PAIR threshold", lambda: PairController(objective="x", threshold=11))
        expect_value_error("TAP branch_factor", lambda: TapController(objective="x", branch_factor=0))
        expect_value_error("TAP max_depth", lambda: TapController(objective="x", max_depth=0))
        expect_value_error("TAP width", lambda: TapController(objective="x", width=0))
        expect_value_error("DrAttack top_k", lambda: DrAttackController(objective="x", top_k_synonyms=0))
    except Exception as exc:
        fail("Config validation", str(exc))
        return 1
    ok("Config validation", "core ranges")

    try:
        simple = parse_user_submission("full target response")
        if simple["mode"] != "simple" or simple["response"] != "full target response":
            raise RuntimeError("simple response parsing failed")

        advanced = parse_user_submission(
            f"{EVENT_MARKER}\n新开会话\n\n"
            f"{OPERATOR_MARKER}\n我怀疑新会话影响结果\n\n"
            f"{RESPONSE_MARKER}\nadvanced target response"
        )
        if advanced["response"] != "advanced target response":
            raise RuntimeError("advanced response parsing failed")
        if advanced["events"][0]["event_type"] != "new_target_session":
            raise RuntimeError("operator event classification failed")
        if advanced["comments"] != ["我怀疑新会话影响结果"]:
            raise RuntimeError("operator comment parsing failed")

        comment_only = parse_user_submission(f"{OPERATOR_MARKER}\n只记录意见")
        if comment_only["response"] is not None:
            raise RuntimeError("comment-only input should not create a response")

        expect_value_error(
            "advanced unlabelled preamble",
            lambda: parse_user_submission(f"unlabelled\n{RESPONSE_MARKER}\nresponse"),
        )
    except Exception as exc:
        fail("Human input parser", str(exc))
        return 1
    ok("Human input parser", "simple + EVENT/OPERATOR/RESPONSE + no-response blocks")

    try:
        with tempfile.TemporaryDirectory() as directory:
            store = AgentSessionStore(str(Path(directory) / ".awayout-agent"))

            pair = PairController(objective="pair-interaction-check", max_iterations=3)
            pair.submit_candidate("pair-candidate")
            store.save(pair)
            pair_action = enrich(pair, store, pair.next_action())
            rendered = pair_action["handoff"]["presentation"]["rendered_text"]
            presentation = pair_action["handoff"]["presentation"]
            for expected in (
                "通常情况：直接粘贴目标系统的完整响应即可",
                EVENT_MARKER,
                OPERATOR_MARKER,
                RESPONSE_MARKER,
                "pair-candidate",
            ):
                if expected not in rendered:
                    raise RuntimeError(f"PAIR presenter missing: {expected}")
            if presentation.get("input_mode") != "simple_or_advanced_blocks":
                raise RuntimeError("PAIR presenter input mode is wrong")

            input_file = Path(directory) / "user-input.txt"
            input_file.write_text(
                f"{EVENT_MARKER}\n新开会话\n\n"
                f"{OPERATOR_MARKER}\n记录这次会话切换\n\n"
                f"{RESPONSE_MARKER}\nreal target response",
                encoding="utf-8",
            )
            args = SimpleNamespace(
                session_id=pair.session_id,
                message=None,
                message_file=str(input_file),
            )
            if cmd_user_input(args, store) != 0:
                raise RuntimeError("submit-user-input command failed")
            restored = store.load(pair.session_id)
            if restored.state != "NEED_JUDGEMENT" or restored.current_node.response != "real target response":
                raise RuntimeError("submit-user-input did not advance Pair with the target response")
            if len(store.get_operator_events(pair.session_id)) != 1:
                raise RuntimeError("operator event was not persisted")
            if len(store.get_feedback(pair.session_id)) != 1:
                raise RuntimeError("operator comment was not persisted")

            # Comment/event only must remain at the same human-interaction state.
            pair2 = PairController(objective="no-advance-check")
            pair2.submit_candidate("candidate")
            store.save(pair2)
            only_file = Path(directory) / "only-comment.txt"
            only_file.write_text(f"{EVENT_MARKER}\n清空上下文\n\n{OPERATOR_MARKER}\n只记录，不推进", encoding="utf-8")
            args2 = SimpleNamespace(session_id=pair2.session_id, message=None, message_file=str(only_file))
            cmd_user_input(args2, store)
            if store.load(pair2.session_id).state != "WAIT_TARGET_RESPONSE":
                raise RuntimeError("event/comment-only input advanced the state")

            # DrAttack baseline must use the same presenter guidance.
            dr = DrAttackController(objective="baseline-check", strategies=["icl_structured"])
            dr.submit_baseline_prompt("baseline-prompt")
            store.save(dr)
            dr_action = enrich(dr, store, dr.next_action())
            dr_rendered = dr_action["handoff"]["presentation"]["rendered_text"]
            if "DrAttack 基线测试" not in dr_rendered or RESPONSE_MARKER not in dr_rendered:
                raise RuntimeError("DrAttack baseline did not use unified presenter")
    except Exception as exc:
        fail("Human interaction contract", str(exc))
        return 1
    ok("Human interaction contract", "unified presenter + submit-user-input + no-advance operator-only input")

    try:
        pair = PairController(objective="score-policy", max_iterations=2)
        pair.submit_candidate("p1")
        pair.submit_response("r1")
        internal = enrich(pair, AgentSessionStore(tempfile.mkdtemp()), pair.next_action())
        if internal["handoff"].get("visibility") != "internal":
            raise RuntimeError("scoring is not internal-only")
        anchors = internal.get("rubric", {}).get("anchors", [])
        if len(anchors) != 5:
            raise RuntimeError("shared scoring anchors missing")
        if "memory_update" not in internal.get("rubric", {}).get("required_internal_output", {}):
            raise RuntimeError("scoring contract missing memory_update")
    except Exception as exc:
        fail("Scoring + internal boundary", str(exc))
        return 1
    ok("Scoring + internal boundary", "5 anchors + memory extraction + silent scoring")

    try:
        with tempfile.TemporaryDirectory() as directory:
            store_dir = Path(directory) / ".awayout-agent"
            store = AgentSessionStore(str(store_dir))
            pair = PairController(objective="memory-report-check", max_iterations=2)
            pair.submit_candidate("full prompt original")
            store.save(pair)
            store.add_operator_event(pair.session_id, "new_target_session", "新开会话", "before_response")
            store.add_feedback(pair.session_id, "人工观察")
            pair.submit_response("full target response original")
            pair.submit_judgement(5, "evidence: partial progress; missing final value")
            store.save(pair)

            report_root = Path(directory) / f"test-report-{pair.session_id}"
            round_file = report_root / "RESPONSES" / "round01.md"
            round_text = round_file.read_text(encoding="utf-8")
            for expected in ("full prompt original", "full target response original", "新开会话", "人工观察", "## 测试者操作", "## 操作员意见"):
                if expected not in round_text:
                    raise RuntimeError(f"round report missing: {expected}")

            store.add_memory_update(pair.session_id, {
                "items": [
                    {
                        "type": "exact_fact",
                        "content": "messages.content",
                        "evidence": "field messages.content",
                        "source_ref": "Round 1",
                        "confidence": 1,
                        "importance": 9,
                        "relevance_to_objective": 9,
                        "relation_to_objective": "supporting",
                        "status": "confirmed",
                    },
                    {
                        "type": "blocker",
                        "content": "direct access is blocked",
                        "evidence": "access denied",
                        "source_ref": "Round 1",
                        "confidence": 0.9,
                        "importance": 8,
                        "relevance_to_objective": 8,
                        "relation_to_objective": "supporting",
                        "status": "confirmed",
                    },
                ]
            })
            context = build_memory_context(store.get_document(pair.session_id))
            if not context.get("exact_facts") or context["exact_facts"][0].get("content") != "messages.content":
                raise RuntimeError("exact memory was not preserved")
            if not context.get("semantic_memory"):
                raise RuntimeError("semantic memory context is empty")
            store.set_metadata(pair.session_id, target_system="self-check-target")
            summary_text = (report_root / "SUMMARY.md").read_text(encoding="utf-8")
            if "self-check-target" not in summary_text or "特殊人工操作数：1" not in summary_text:
                raise RuntimeError("summary did not refresh metadata/operator-event counts")
    except Exception as exc:
        fail("Working Memory + report archival", str(exc))
        return 1
    ok("Working Memory + report archival", "raw records + operator context + layered memory")

    try:
        with tempfile.TemporaryDirectory() as directory:
            store = AgentSessionStore(str(Path(directory) / ".awayout-agent"))
            controllers = [
                PairController(objective="pair-self-check"),
                TapController(objective="tap-self-check"),
                DrAttackController(objective="drattack-self-check"),
            ]
            for controller in controllers:
                store.save(controller)
                restored = store.load(controller.session_id)
                if restored.session_id != controller.session_id:
                    raise RuntimeError(f"session restore mismatch for {controller.session_id}")
    except Exception as exc:
        fail("Session store", str(exc))
        return 1
    ok("Session store", "PAIR + TAP + DrAttack read/write")

    if importlib.util.find_spec("requests") is not None:
        ok("Standalone dependency requests", "installed (not required for Agent Mode)")

    print("\nAgent Mode is ready. No external LLM provider is required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
