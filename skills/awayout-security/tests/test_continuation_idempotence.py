"""Regression coverage for budget extension, checkpointing, and idempotent retries."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import api
from common.store import AgentSessionStore


class SessionContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store_path = Path(self.tmp.name) / ".awayout-agent"

    def run_cli(self, *args, ok=True):
        output = io.StringIO()
        argv = ["api.py", "--store", str(self.store_path), *args]
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
            code = api.main()
        result = json.loads(output.getvalue())
        self.assertEqual(code == 0, ok, result)
        return result["result"] if ok else result

    def create(self, algorithm="PAIR", *extra):
        return self.run_cli("start-test", "--algorithm", algorithm,
                            "--objective", "Return TEST_OK", *extra)["session_id"]

    def result(self, sid, data, *, request=None, ok=True):
        args = ["submit-result", sid, "--data", json.dumps(data)]
        if request:
            args += ["--request-id", request]
        return self.run_cli(*args, ok=ok)

    def reply(self, sid, response, *, request=None):
        args = ["submit-user-input", sid, "--message", response]
        if request:
            args.extend(["--request-id", request])
        return self.run_cli(*args)

    def document(self, sid):
        return json.loads((self.store_path / f"{sid}.json").read_text(encoding="utf-8"))

    def test_pair_extend_budget_preserves_history(self):
        sid = self.create("PAIR", "--max-iterations", "1")
        self.result(sid, {"prompt": "First"})
        self.reply(sid, "No")
        done = self.result(sid, {"score": 2, "reason": "rejected"})
        self.assertEqual(done["state"], "DONE")
        replay_done = self.run_cli("resume", "--session-id", sid)
        self.assertEqual(replay_done["state"], "DONE")

        extended = self.run_cli("extend-test", sid, "--extra-iterations", "2",
                                "--request-id", "extend-0001")
        self.assertEqual(extended["state"], "NEED_CANDIDATE")
        self.assertEqual(extended["progress"]["max_iterations"], 3)
        again = self.run_cli("extend-test", sid, "--extra-iterations", "2",
                             "--request-id", "extend-0001")
        self.assertTrue(again["idempotency"]["replayed"])
        self.assertEqual(again["progress"]["max_iterations"], 3)
        self.assertEqual(len(self.document(sid)["_runtime"]["operator_events"]), 1)
        self.result(sid, {"prompt": "Second", "template_use": {
            "action": "skip", "template_ids": [], "experience_ids": [],
        }}, request="candidate-2")
        self.reply(sid, "TEST_OK")
        self.result(sid, {"score": 9, "reason": "matched"})
        self.assertEqual(len(self.document(sid)["nodes"]), 2)
        self.assertEqual(self.document(sid)["nodes"][0]["score"], 2)
        self.assertTrue((Path(self.tmp.name) / f"test-report-{sid}" / "RESPONSES" / "round02.md").is_file())
        self.assertEqual(self.run_cli("get-state", sid)["state"], "NEED_CANDIDATE")

    def test_pair_first_success_requires_explicit_override(self):
        sid = self.create("PAIR", "--max-iterations", "2",
                          "--stop-policy", "first_success")
        self.result(sid, {"prompt": "First"})
        self.reply(sid, "TEST_OK")
        self.result(sid, {"score": 10, "reason": "done"})
        failed = self.run_cli("extend-test", sid, "--extra-iterations", "1", ok=False)
        self.assertIn("continue-after-success", failed["error"])
        resumed = self.run_cli("extend-test", sid, "--extra-iterations", "1",
                               "--continue-after-success")
        self.assertEqual(resumed["state"], "NEED_CANDIDATE")
        self.assertEqual(resumed["progress"]["stop_policy"], "exhaust_budget")

    def test_tap_extend_from_last_scored_survivor(self):
        sid = self.create("TAP", "--max-depth", "1", "--branch-factor", "2",
                          "--width", "1")
        self.result(sid, {"branches": [
            {"prompt": "A", "parent_id": None},
            {"prompt": "B", "parent_id": None},
        ]})
        nodes = self.document(sid)["current_ids"]
        self.result(sid, {"keep_node_ids": nodes})
        self.reply(sid, "No")
        self.reply(sid, "Partial")
        finished = self.result(sid, {"scores": {
            nodes[0]: {"score": 1, "reason": "blocked"},
            nodes[1]: {"score": 6, "reason": "almost"},
        }})
        self.assertEqual(finished["state"], "DONE")
        extended = self.run_cli("extend-test", sid, "--extra-depth", "2")
        self.assertEqual(extended["state"], "NEED_BRANCHES")
        self.assertEqual(extended["progress"]["max_depth"], 3)
        self.assertEqual(extended["parent_ids"], [nodes[1]])
        self.result(sid, {"branches": [{"prompt": "B-child", "parent_id": nodes[1]}]})
        document = self.document(sid)
        self.assertEqual(len(document["nodes"]), 3)
        self.assertEqual(document["nodes"][-1]["parent_id"], nodes[1])

    def test_drattack_extension_keeps_all_attempts(self):
        sid = self.create("DrAttack", "--strategies", "icl_structured,word_game")
        self.result(sid, {"prompt": "BASE"})
        self.reply(sid, "No")
        self.result(sid, {"sub_prompts": ["RETURN", "MARKER"]})
        self.result(sid, {"candidates": [["Return"], ["Marker"]],
                          "selected": ["Return", "Marker"]})
        self.result(sid, {"prompts": {"icl_structured": "ONE", "word_game": "TWO"}})
        self.reply(sid, "Partial")
        self.reply(sid, "No")
        done = self.result(sid, {"scores": {
            "icl_structured": {"score": 6, "reason": "partial"},
            "word_game": {"score": 2, "reason": "no"},
        }})
        self.assertEqual(done["state"], "DONE")
        resumed = self.run_cli("extend-test", sid, "--extra-reconstructions", "2",
                               "--request-id", "extend-reconstruction")
        self.assertEqual(resumed["state"], "NEED_RECONSTRUCTIONS")
        self.assertEqual(resumed["progress"]["attempt_no"], 2)
        self.assertEqual(resumed["progress"]["max_attempts"], 3)
        self.assertEqual(len(self.document(sid)["strategy_nodes"]), 2)
        self.assertEqual(resumed["handoff"]["template_guidance"]["elite_experiences"][0]["id"], "icl_structured")
        self.result(sid, {"prompts": {"icl_structured": "THREE", "word_game": "FOUR"},
                          "template_uses": {"word_game": {
                              "action": "skip", "template_ids": [], "experience_ids": ["icl_structured"]
                          }}})
        self.assertEqual(len(self.document(sid)["strategy_nodes"]), 4)
        self.assertEqual(self.document(sid)["_runtime"]["template_uses"][0]["source_ref"], "word_game@2")
        self.reply(sid, "Good")
        self.reply(sid, "No")
        next_round = self.result(sid, {"scores": {
            "icl_structured": {"score": 8, "reason": "close"},
            "word_game": {"score": 4, "reason": "weak"},
        }})
        self.assertEqual(next_round["state"], "NEED_RECONSTRUCTIONS")
        self.assertEqual(next_round["progress"]["attempt_no"], 3)
        self.result(sid, {"prompts": {"icl_structured": "FIVE", "word_game": "SIX"}})
        self.reply(sid, "TEST_OK")
        self.reply(sid, "Partial")
        self.result(sid, {"scores": {
            "icl_structured": {"score": 9, "reason": "success"},
            "word_game": {"score": 5, "reason": "partial"},
        }})
        doc = self.document(sid)
        self.assertEqual(doc["state"], "DONE")
        self.assertEqual(len(doc["strategy_nodes"]), 6)
        self.assertEqual(doc["strategy_nodes"][0]["prompt"], "ONE")
        self.assertEqual(doc["strategy_nodes"][-1]["node_id"], "word_game@3")
        self.assertEqual(AgentSessionStore(str(self.store_path)).load(sid).attempt_no, 3)
        report_dir = Path(self.tmp.name) / f"test-report-{sid}" / "RESPONSES"
        self.assertEqual(len(list(report_dir.glob("round*.md"))), 6)

    def test_idempotent_candidate_result_and_conflict(self):
        sid = self.create()
        first = self.result(sid, {"prompt": "P1"}, request="create-001")
        self.assertEqual(first["state"], "WAIT_TARGET_RESPONSE")
        same = self.result(sid, {"prompt": "P1"}, request="create-001")
        self.assertTrue(same["idempotency"]["replayed"])
        self.assertEqual(len(self.document(sid)["nodes"]), 1)
        bad = self.result(sid, {"prompt": "DIFFERENT"}, request="create-001", ok=False)
        self.assertIn("different content", bad["error"])
        self.assertEqual(len(self.document(sid)["nodes"]), 1)
        self.assertEqual(len(self.document(sid)["_runtime"]["submitted_requests"]), 1)

    def test_idempotent_response_with_operator_notes(self):
        sid = self.create()
        self.result(sid, {"prompt": "P1"})
        text = ("[[AWAYOUT:EVENT]]\n新开会话\n"
                "[[AWAYOUT:OPERATOR]]\n测试者观察\n"
                "[[AWAYOUT:RESPONSE]]\nTARGET_RESPONSE")
        first = self.reply(sid, text, request="response-001")
        self.assertEqual(first["state"], "NEED_JUDGEMENT")
        replay = self.reply(sid, text, request="response-001")
        self.assertTrue(replay["idempotency"]["replayed"])
        document = self.document(sid)
        self.assertEqual(len(document["_runtime"]["feedback"]), 1)
        self.assertEqual(len(document["_runtime"]["operator_events"]), 1)
        self.assertEqual(document["nodes"][0]["response"], "TARGET_RESPONSE")

    def test_response_idempotent_across_tap_branch_advancement(self):
        sid = self.create("TAP", "--branch-factor", "2")
        self.result(sid, {"branches": [
            {"prompt": "A", "parent_id": None},
            {"prompt": "B", "parent_id": None}]})
        self.result(sid, {"keep_node_ids": self.document(sid)["current_ids"]})
        self.reply(sid, "RESPONSE_A", request="response-A")
        retried = self.reply(sid, "RESPONSE_A", request="response-A")
        self.assertTrue(retried["idempotency"]["replayed"])
        self.assertEqual(retried["state"], "WAIT_TARGET_RESPONSES")
        self.assertEqual(retried["progress"]["current_response_index"], 1)
        self.reply(sid, "RESPONSE_B", request="response-B")
        self.assertEqual(self.document(sid)["state"], "NEED_SCORES")

    def test_resume_old_session_by_id(self):
        first = self.create()
        second = self.create()
        self.assertEqual(self.run_cli("get-active")["session_id"], second)
        self.run_cli("resume", "--session-id", first)
        self.assertEqual(self.run_cli("get-active")["session_id"], first)

    def test_failed_submit_does_not_reserve_request(self):
        sid = self.create()
        failure = self.result(sid, {"prompt": ""}, request="retry-001", ok=False)
        self.assertFalse(failure["success"])
        self.assertEqual(self.document(sid)["_runtime"].get("submitted_requests", []), [])
        self.result(sid, {"prompt": "valid"}, request="retry-001")
        self.assertEqual(len(self.document(sid)["nodes"]), 1)


if __name__ == "__main__":
    unittest.main()
