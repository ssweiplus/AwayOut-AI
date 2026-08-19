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
        "SKILL.md",
        "INSTALL.md",
        "REPORTING.md",
        "api.py",
        "doctor.py",
        "common/store.py",
        "common/presenter.py",
        "common/scoring.py",
        "common/memory.py",
        "common/report.py",
        "algorithms/pair/SKILL.md",
        "algorithms/pair/controller.py",
        "algorithms/tap/SKILL.md",
        "algorithms/tap/controller.py",
        "algorithms/drattack/SKILL.md",
        "algorithms/drattack/controller.py",
    ]
    missing = [name for name in required if not (SKILL_ROOT / name).is_file()]
    if missing:
        fail("Skill files", ", ".join(missing))
        return 1
    ok("Skill files", "router + presenter + scoring + memory + report + 3 algorithm skills")

    try:
        from algorithms.pair.controller import PairController
        from algorithms.tap.controller import TapController
        from algorithms.drattack.controller import DrAttackController
        from common.memory import build_memory_context
        from common.store import AgentSessionStore
        from api import OPERATOR_MARKER, algorithm_selection_contract, enrich
    except Exception as exc:
        fail("Imports", str(exc))
        return 1
    ok("Controllers", "PAIR, TAP, DrAttack")

    try:
        actions = {
            "PAIR": PairController(objective="self-check").next_action(),
            "TAP": TapController(objective="self-check").next_action(),
            "DrAttack": DrAttackController(objective="self-check").next_action(),
        }
        for name, action in actions.items():
            handoff = action.get("handoff", {})
            guard = handoff.get("objective_guard") if isinstance(handoff, dict) else None
            if not isinstance(guard, dict) or guard.get("original_objective") != "self-check":
                raise RuntimeError(f"{name} initial handoff missing objective_guard")
        if not actions["PAIR"]["handoff"].get("mutation_goal"):
            raise RuntimeError("PAIR initial handoff missing mutation_goal")
        if not actions["TAP"]["handoff"].get("mutation_goal"):
            raise RuntimeError("TAP initial handoff missing mutation_goal")
        if not actions["DrAttack"]["handoff"].get("mutation_goal"):
            raise RuntimeError("DrAttack initial handoff missing mutation_goal")
    except Exception as exc:
        fail("Controller startup", str(exc))
        return 1
    ok("Controller startup", "objective guards present on all algorithms")

    try:
        intro = algorithm_selection_contract()
        required_output = intro.get("required_user_output", {})
        options = required_output.get("options", [])
        names = [item.get("algorithm") for item in options if isinstance(item, dict)]
        if intro.get("must_show_to_user") is not True:
            raise RuntimeError("algorithm introduction is not marked mandatory")
        if names != ["PAIR", "TAP", "DrAttack"]:
            raise RuntimeError("algorithm introduction does not expose PAIR/TAP/DrAttack in order")
        if not required_output.get("selection_prompt"):
            raise RuntimeError("algorithm introduction missing selection prompt")
    except Exception as exc:
        fail("Algorithm intro contract", str(exc))
        return 1
    ok("Algorithm intro contract", "PAIR + TAP + DrAttack must be shown")

    try:
        expect_value_error("PAIR max_iterations", lambda: PairController(objective="self-check", max_iterations=0))
        expect_value_error("PAIR threshold", lambda: PairController(objective="self-check", threshold=11))
        expect_value_error("TAP branch_factor", lambda: TapController(objective="self-check", branch_factor=0))
        expect_value_error("TAP max_depth", lambda: TapController(objective="self-check", max_depth=0))
        expect_value_error("TAP width", lambda: TapController(objective="self-check", width=0))
        expect_value_error("TAP threshold", lambda: TapController(objective="self-check", threshold=11))
        expect_value_error("DrAttack top_k_synonyms", lambda: DrAttackController(objective="self-check", top_k_synonyms=0))
        expect_value_error("DrAttack threshold", lambda: DrAttackController(objective="self-check", threshold=11))
        expect_value_error("DrAttack strategies", lambda: DrAttackController(objective="self-check", strategies=[]))
    except Exception as exc:
        fail("Config validation", str(exc))
        return 1
    ok("Config validation", "PAIR + TAP + DrAttack")

    try:
        pair = PairController(objective="self-check", max_iterations=2, threshold=7)
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

        early = PairController(objective="self-check", max_iterations=2, threshold=7, stop_policy="first_success")
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
            store = AgentSessionStore(str(Path(directory) / ".awayout-agent"))

            pair = PairController(objective="pair-interaction-check", max_iterations=3)
            pair.submit_candidate("pair-candidate")
            store.save(pair)

            tap = TapController(objective="tap-interaction-check", branch_factor=2)
            tap.submit_branches([
                {"prompt": "tap-candidate-1", "improvement": "direction-1"},
                {"prompt": "tap-candidate-2", "improvement": "direction-2"},
            ])
            tap.submit_offtopic_review(list(tap.current_ids))
            store.save(tap)

            drattack = DrAttackController(objective="drattack-interaction-check", strategies=["icl_structured", "word_game"])
            drattack.submit_baseline_prompt("drattack-baseline")
            drattack.submit_baseline_response("baseline-response")
            drattack.submit_decomposition(["part-a", "part-b"])
            drattack.submit_synonyms([["a1"], ["b1"]], ["a1", "b1"])
            drattack.submit_reconstructions({"icl_structured": "structured-prompt", "word_game": "word-game-prompt"})
            store.save(drattack)

            pair_action = enrich(pair, store, pair.next_action())
            pair_handoff = pair_action.get("handoff", {})
            pair_presentation = pair_handoff.get("presentation", {}) if isinstance(pair_handoff, dict) else {}
            rendered = str(pair_presentation.get("rendered_text", ""))
            if pair_handoff.get("kind") != "human_target_interaction" or pair_handoff.get("must_show_to_user") is not True:
                raise RuntimeError("PAIR human interaction contract invalid")
            if pair_presentation.get("must_show_verbatim") is not True or pair_presentation.get("copy_target") != "prompt_block_only":
                raise RuntimeError("PAIR presentation contract invalid")
            for expected in ("PAIR 第 1/3 轮", "本轮策略", "pair-candidate", "人工意见（可选）", OPERATOR_MARKER):
                if expected not in rendered:
                    raise RuntimeError(f"PAIR presentation missing: {expected}")

            tap_action = enrich(tap, store, tap.next_action())
            tap_handoff = tap_action.get("handoff", {})
            tap_presentation = tap_handoff.get("presentation", {}) if isinstance(tap_handoff, dict) else {}
            tap_rendered = str(tap_presentation.get("rendered_text", ""))
            if tap_presentation.get("input_mode") != "single_plain_text_response":
                raise RuntimeError("TAP interaction is not single plain-text response mode")
            if tap_presentation.get("branch_index") != 1 or tap_presentation.get("branch_total") != 2:
                raise RuntimeError("TAP first branch progress is incorrect")
            for expected in ("TAP 深度 1/5", "分支测试 1/2", "tap-candidate-1", "不需要填写 JSON", OPERATOR_MARKER):
                if expected not in tap_rendered:
                    raise RuntimeError(f"TAP presentation missing: {expected}")
            first_tap = tap.submit_response("tap-response-1")
            if first_tap["state"] != "WAIT_TARGET_RESPONSES" or first_tap["current_branch"]["prompt"] != "tap-candidate-2":
                raise RuntimeError("TAP did not advance sequentially")
            store.save(tap)
            restored_tap = store.load(tap.session_id)
            if restored_tap.current_response_index != 1:
                raise RuntimeError("TAP response cursor was not persisted")
            if restored_tap.submit_response("tap-response-2")["state"] != "NEED_SCORES":
                raise RuntimeError("TAP did not advance to scoring")

            dr_action = enrich(drattack, store, drattack.next_action())
            dr_handoff = dr_action.get("handoff", {})
            dr_presentation = dr_handoff.get("presentation", {}) if isinstance(dr_handoff, dict) else {}
            dr_rendered = str(dr_presentation.get("rendered_text", ""))
            if dr_presentation.get("input_mode") != "single_plain_text_response":
                raise RuntimeError("DrAttack interaction is not single plain-text response mode")
            if dr_presentation.get("strategy_index") != 1 or dr_presentation.get("strategy_total") != 2:
                raise RuntimeError("DrAttack first strategy progress is incorrect")
            for expected in ("DrAttack 策略测试 1/2", "structured-prompt", "不需要填写 JSON", OPERATOR_MARKER):
                if expected not in dr_rendered:
                    raise RuntimeError(f"DrAttack presentation missing: {expected}")
            if drattack.submit_strategy_response("structured-response")["state"] != "WAIT_STRATEGY_RESPONSES":
                raise RuntimeError("DrAttack did not remain sequential")
            store.save(drattack)
            restored = store.load(drattack.session_id)
            if restored.current_strategy_index != 1:
                raise RuntimeError("DrAttack strategy index was not persisted")
            if restored.submit_strategy_response("word-game-response")["state"] != "NEED_STRATEGY_SCORES":
                raise RuntimeError("DrAttack did not advance to scoring")
    except Exception as exc:
        fail("Human interaction contract", str(exc))
        return 1
    ok("Human interaction contract", "PAIR formatted + TAP sequential + DrAttack sequential")

    try:
        with tempfile.TemporaryDirectory() as directory:
            store_dir = Path(directory) / ".awayout-agent"
            store = AgentSessionStore(str(store_dir))
            pair = PairController(objective="memory-report-check", max_iterations=2)
            pair.submit_candidate("full prompt original")
            pair.submit_response("full target response original")
            pair.submit_judgement(5, "evidence: partial progress; missing final value")
            store.save(pair)

            report_root = Path(directory) / f"test-report-{pair.session_id}"
            round_file = report_root / "RESPONSES" / "round01.md"
            if not round_file.is_file():
                raise RuntimeError("round report was not created")
            round_text = round_file.read_text(encoding="utf-8")
            if "full prompt original" not in round_text or "full target response original" not in round_text:
                raise RuntimeError("raw Prompt/Response were not preserved in report")
            for required_name in ("SUMMARY.md", "ATTACK_PATTERN.md", "TURNING_POINTS.md", "prompt-tree.md", "strategy-evolution.md"):
                if not (report_root / required_name).is_file():
                    raise RuntimeError(f"report missing {required_name}")

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
            document = store.get_document(pair.session_id)
            context = build_memory_context(document)
            exact = context.get("exact_facts", [])
            if not exact or exact[0].get("content") != "messages.content":
                raise RuntimeError("exact memory was not preserved")
            if not context.get("semantic_memory"):
                raise RuntimeError("semantic memory context is empty")
            store.set_metadata(pair.session_id, target_system="self-check-target")
            summary_text = (report_root / "SUMMARY.md").read_text(encoding="utf-8")
            if "self-check-target" not in summary_text:
                raise RuntimeError("target-system metadata did not refresh report")
    except Exception as exc:
        fail("Working Memory + report archival", str(exc))
        return 1
    ok("Working Memory + report archival", "raw records + layered memory + auto-refresh report")

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
            if store.load(controllers[0].session_id).stop_policy != "exhaust_budget":
                raise RuntimeError("session restore lost PAIR stop_policy")
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
