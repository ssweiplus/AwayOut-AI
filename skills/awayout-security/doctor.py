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
        "api.py",
        "doctor.py",
        "common/store.py",
        "common/presenter.py",
        "common/scoring.py",
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
    ok("Skill files", "router + presenter + scoring + store + 3 algorithms")

    try:
        from algorithms.pair.controller import PairController
        from algorithms.tap.controller import TapController
        from algorithms.drattack.controller import DrAttackController
        from common.scoring import objective_scoring_rubric
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
            if not handoff.get("mutation_goal"):
                raise RuntimeError(f"{name} initial handoff missing mutation_goal")
    except Exception as exc:
        fail("Controller startup", str(exc))
        return 1
    ok("Controller startup", "objective guards + mutation goals")

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
        rubric = objective_scoring_rubric(7)
        anchors = rubric.get("anchors", [])
        if len(anchors) != 5:
            raise RuntimeError("shared scoring rubric must contain five anchor bands")
        if [item.get("range") for item in anchors] != ["1-2", "3-4", "5-6", "7-8", "9-10"]:
            raise RuntimeError("shared scoring anchor ranges are incorrect")
        if rubric.get("basis") != "original_objective_only":
            raise RuntimeError("scoring rubric is not tied to original objective")
        if len(rubric.get("required_reason_fields", [])) != 3:
            raise RuntimeError("scoring rubric reason evidence contract is incomplete")
    except Exception as exc:
        fail("Scoring contract", str(exc))
        return 1
    ok("Scoring contract", "5 anchored bands + evidence-based reason")

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
            store = AgentSessionStore(directory)
            fresh = [
                PairController(objective="pair-start"),
                TapController(objective="tap-start"),
                DrAttackController(objective="dr-start"),
            ]
            for controller in fresh:
                store.save(controller)
                action = enrich(controller, store, controller.next_action())
                handoff = action.get("handoff", {})
                policy = action.get("display_policy", {})
                if handoff.get("visibility") != "internal":
                    raise RuntimeError(f"{controller.__class__.__name__} startup handoff is not internal")
                if handoff.get("must_not_show_to_user") is not True:
                    raise RuntimeError(f"{controller.__class__.__name__} startup handoff may leak to user")
                if policy.get("user_facing_now") is not False or policy.get("continue_internal_until_boundary") is not True:
                    raise RuntimeError(f"{controller.__class__.__name__} startup display policy is incorrect")
    except Exception as exc:
        fail("Startup boundary", str(exc))
        return 1
    ok("Startup boundary", "first prompt generation is Agent-internal")

    try:
        with tempfile.TemporaryDirectory() as directory:
            store = AgentSessionStore(directory)

            pair = PairController(objective="pair-interaction-check", max_iterations=3)
            pair.submit_candidate("pair-candidate-1")
            store.save(pair)
            pair_action = enrich(pair, store, pair.next_action())
            pair_presentation = pair_action.get("handoff", {}).get("presentation", {})
            rendered = str(pair_presentation.get("rendered_text", ""))
            for expected in ("PAIR 第 1/3 轮", "pair-candidate-1", "人工意见（可选）", OPERATOR_MARKER):
                if expected not in rendered:
                    raise RuntimeError(f"PAIR presentation missing: {expected}")

            pair.submit_response("partial target response")
            store.save(pair)
            score_action = enrich(pair, store, pair.next_action())
            if score_action.get("handoff", {}).get("visibility") != "internal":
                raise RuntimeError("PAIR scoring is not internal-only")
            if len(score_action.get("rubric", {}).get("anchors", [])) != 5:
                raise RuntimeError("PAIR scoring did not receive shared rubric")
            pair.submit_judgement(5, "evidence: partial; satisfied: subset; missing: final requested result")
            pair.submit_candidate("pair-candidate-2", "continuation")
            store.save(pair)
            next_action = enrich(pair, store, pair.next_action())
            next_rendered = str(next_action.get("presentation", {}).get("rendered_text", ""))
            if "上一步结果" not in next_rendered or "5/10" not in next_rendered or "pair-candidate-2" not in next_rendered:
                raise RuntimeError("PAIR did not combine previous score and next prompt in one presentation")

            tap = TapController(objective="tap-interaction-check", branch_factor=2)
            tap.submit_branches([
                {"prompt": "tap-candidate-1", "improvement": "direction-1"},
                {"prompt": "tap-candidate-2", "improvement": "direction-2"},
            ])
            tap.submit_offtopic_review(list(tap.current_ids))
            store.save(tap)
            tap_action = enrich(tap, store, tap.next_action())
            tap_presentation = tap_action.get("presentation", {})
            tap_rendered = str(tap_presentation.get("rendered_text", ""))
            if tap_presentation.get("input_mode") != "single_plain_text_response":
                raise RuntimeError("TAP interaction is not single plain-text response mode")
            for expected in ("TAP 深度 1/5", "分支测试 1/2", "tap-candidate-1", "不需要填写 JSON", OPERATOR_MARKER):
                if expected not in tap_rendered:
                    raise RuntimeError(f"TAP presentation missing: {expected}")
            first_tap = tap.submit_response("tap-response-1")
            if first_tap["state"] != "WAIT_TARGET_RESPONSES":
                raise RuntimeError("TAP did not remain waiting after first response")
            store.save(tap)
            restored_tap = store.load(tap.session_id)
            if restored_tap.current_response_index != 1:
                raise RuntimeError("TAP response cursor was not persisted")
            second_tap = restored_tap.submit_response("tap-response-2")
            if second_tap["state"] != "NEED_SCORES":
                raise RuntimeError("TAP did not advance to scoring after all branch responses")
            store.save(restored_tap)
            tap_score = enrich(restored_tap, store, restored_tap.next_action())
            if tap_score.get("handoff", {}).get("visibility") != "internal":
                raise RuntimeError("TAP scoring is not internal-only")
            if len(tap_score.get("rubric", {}).get("anchors", [])) != 5:
                raise RuntimeError("TAP scoring did not receive shared rubric")

            drattack = DrAttackController(objective="drattack-interaction-check", strategies=["icl_structured", "word_game"])
            drattack.submit_baseline_prompt("drattack-baseline")
            drattack.submit_baseline_response("baseline-response")
            drattack.submit_decomposition(["part-a", "part-b"])
            drattack.submit_synonyms([["a1"], ["b1"]], ["a1", "b1"])
            drattack.submit_reconstructions({"icl_structured": "structured-prompt", "word_game": "word-game-prompt"})
            store.save(drattack)
            dr_action = enrich(drattack, store, drattack.next_action())
            dr_presentation = dr_action.get("presentation", {})
            dr_rendered = str(dr_presentation.get("rendered_text", ""))
            if dr_presentation.get("input_mode") != "single_plain_text_response":
                raise RuntimeError("DrAttack interaction is not single plain-text response mode")
            for expected in ("DrAttack 策略测试 1/2", "structured-prompt", "不需要填写 JSON", OPERATOR_MARKER):
                if expected not in dr_rendered:
                    raise RuntimeError(f"DrAttack presentation missing: {expected}")
            drattack.submit_strategy_response("structured-response")
            drattack.submit_strategy_response("word-game-response")
            store.save(drattack)
            dr_score = enrich(drattack, store, drattack.next_action())
            if dr_score.get("handoff", {}).get("visibility") != "internal":
                raise RuntimeError("DrAttack scoring is not internal-only")
            if len(dr_score.get("rubric", {}).get("anchors", [])) != 5:
                raise RuntimeError("DrAttack scoring did not receive shared rubric")
            drattack.submit_strategy_scores({
                "icl_structured": {"score": 4, "reason": "partial only"},
                "word_game": {"score": 7, "reason": "substantially satisfies objective"},
            })
            store.save(drattack)
            dr_final = enrich(drattack, store, drattack.next_action())
            final_handoff = dr_final.get("handoff", {})
            final_text = str(dr_final.get("presentation", {}).get("rendered_text", ""))
            if final_handoff.get("visibility") != "user" or final_handoff.get("must_show_to_user") is not True:
                raise RuntimeError("final result is not a user-facing presenter boundary")
            if "DrAttack 测试结果" not in final_text or "7/10" not in final_text:
                raise RuntimeError("final result presentation does not contain persisted score")
    except Exception as exc:
        fail("Presentation pipeline", str(exc))
        return 1
    ok("Presentation pipeline", "silent scoring + deterministic combined presentations")

    try:
        with tempfile.TemporaryDirectory() as directory:
            store = AgentSessionStore(directory)
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
