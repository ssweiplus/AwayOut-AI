"""Offline regression tests for PyRIT soft guidance and Elite Memory."""
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
from common.template_guidance import (
    elite_experiences, guidance, import_pyrit, load_templates,
    normalize_use, render_reference, select_references,
)
from algorithms.pair.controller import PairController


SAMPLE = [
    {"id": "pyrit:role", "name": "Role", "category": "persona_role",
     "classification_source": "suggested", "template": "As a role, {{ prompt }}"},
    {"id": "pyrit:logical", "name": "Logic", "category": "philosophical_decision",
     "classification_source": "suggested", "template": "Reason about {{ prompt }}"},
    {"id": "pyrit:context", "name": "Context", "category": "context_manipulation",
     "classification_source": "suggested", "template": "Context for {{ prompt }}"},
]


class TemplateUnitTests(unittest.TestCase):
    def test_safe_substitution(self):
        self.assertEqual(
            render_reference("{{ prompt }} / {{ unknown }} / {% unsafe %}", "TEST_OK"),
            "TEST_OK / {{ unknown }} / {% unsafe %}",
        )

    def test_soft_strategy_mapping_and_diversity(self):
        refs = select_references(SAMPLE, "roleplay", "test", 2)
        self.assertEqual(refs[0]["id"], "pyrit:role")
        self.assertEqual(len({r["category"] for r in refs}), 2)
        self.assertIn("test", refs[0]["reference_text"])
        novel = select_references(SAMPLE, "roleplay", "test", 1, {"pyrit:role"})
        self.assertNotEqual(novel[0]["id"], "pyrit:role")

    def test_checked_in_catalog_when_present(self):
        bundle = ROOT / "resources" / "pyrit"
        if not any(bundle.glob("core-*.json")):
            self.skipTest("bundle not built in this checkout")
        with tempfile.TemporaryDirectory() as tmp:
            data = load_templates(tmp)
            self.assertGreaterEqual(len(data), 100)
            self.assertTrue(all(item["source"] == "PyRIT" for item in data))

    def test_actual_action_validation(self):
        use = normalize_use({
            "action": "combine", "template_ids": ["pyrit:role", "pyrit:logical"],
            "experience_ids": ["N-001"],
        }, mode="auto", known_ids={"pyrit:role", "pyrit:logical"})
        self.assertEqual(use["action"], "combine")
        self.assertIsNone(normalize_use(None, mode="auto", known_ids=set()))
        for bad in (
            {"action": "auto", "template_ids": []},
            {"action": "skip", "template_ids": ["pyrit:role"]},
            {"action": "reference", "template_ids": ["pyrit:unknown"]},
        ):
            with self.assertRaises(ValueError):
                normalize_use(bad, mode="auto", known_ids={"pyrit:role"})
        with self.assertRaises(ValueError):
            normalize_use({"action": "reference", "template_ids": ["pyrit:role"]},
                          mode="rewrite", known_ids={"pyrit:role"})

    def test_elite_comes_only_from_scored_nodes(self):
        controller = PairController(objective="TEST_OK", max_iterations=3)
        controller.submit_candidate("first")
        one = controller.current_node_id
        controller.submit_response("no")
        controller.submit_judgement(2, "rejected")
        controller.submit_candidate("second")
        two = controller.current_node_id
        controller.submit_response("TEST_OK")
        controller.submit_judgement(9, "matched")
        elite = elite_experiences(controller, {two: {
            "action": "reference", "template_ids": ["pyrit:role"]
        }})
        self.assertEqual([x["id"] for x in elite], [two, one])
        self.assertEqual(elite[0]["template_action"], "reference")
        self.assertIn("TEST_OK", elite[0]["target_evidence_excerpt"])
        view = guidance(controller, {"template_config": {"mode": "skip"}}, SAMPLE)
        self.assertFalse(view["recommended_templates"])
        self.assertEqual(view["elite_experiences"][0]["score"], 9)

    def test_yaml_import_and_missing_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsInstance(load_templates(root), list)  # May include bundled defaults.
            try:
                import yaml  # noqa: F401
            except ImportError:
                self.skipTest("PyYAML optional dependency not installed")
            source = root / "yaml"
            source.mkdir()
            (source / "example.yaml").write_text(
                "name: Example\nparameters:\n  - prompt\nvalue: 'Ask {{ prompt }}'\n", encoding="utf-8")
            (source / "unsupported.yaml").write_text(
                "name: Other\nvalue: 'Use {{ custom_variable }}'\n", encoding="utf-8")
            destination = root / "templates" / "pyrit.json"
            result = import_pyrit(source, destination)
            self.assertEqual(result["imported"], 1)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(len(load_templates(root)), 1)


class AgentModeAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "state"
        cat = self.store / "templates" / "pyrit.json"
        cat.parent.mkdir(parents=True)
        cat.write_text(json.dumps(SAMPLE), encoding="utf-8")

    def call(self, *args, success=True):
        out = io.StringIO()
        with patch.object(sys, "argv", ["api.py", "--store", str(self.store), *args]), contextlib.redirect_stdout(out):
            code = api.main()
        data = json.loads(out.getvalue())
        self.assertEqual(code == 0, success, data)
        return data["result"] if success else data

    def start(self, algorithm, *options):
        return self.call("start-test", "--algorithm", algorithm, "--objective", "Output TEST_OK", *options)

    def submit(self, session, data, success=True):
        return self.call("submit-result", session, "--data", json.dumps(data), success=success)

    def test_pair_elite_metadata_and_resume(self):
        first = self.start("PAIR", "--max-iterations", "2")
        sid = first["session_id"]
        self.assertEqual(first["handoff"]["template_guidance"]["catalog_size"], 3)
        candidate = self.submit(sid, {
            "prompt": "FIRST", "template_use": {
                "action": "reference", "template_ids": ["pyrit:logical"],
                "experience_ids": [],
            },
        })
        self.assertEqual(candidate["state"], "WAIT_TARGET_RESPONSE")
        uses = json.loads((self.store / (sid + ".json")).read_text())["_runtime"]["template_uses"]
        self.assertEqual(uses[0]["action"], "reference")
        self.call("submit-user-input", sid, "--message", "Partial TEST_OK")
        second = self.submit(sid, {"score": 8, "reason": "partial match"})
        self.assertEqual(second["state"], "NEED_CANDIDATE")
        elite = second["handoff"]["template_guidance"]["elite_experiences"]
        self.assertEqual(elite[0]["score"], 8)
        self.assertEqual(elite[0]["template_ids"], ["pyrit:logical"])
        self.assertEqual(elite[0]["id"], uses[0]["source_ref"])
        resumed = self.call("resume")
        self.assertEqual(resumed["handoff"]["template_guidance"]["elite_experiences"][0]["score"], 8)
        self.submit(sid, {"prompt": "SECOND",
                          "template_use": {"action": "skip", "template_ids": [],
                                           "experience_ids": [elite[0]["id"]]}})
        self.call("submit-user-input", sid, "--message", "TEST_OK")
        self.submit(sid, {"score": 9, "reason": "exact"})
        uses = json.loads((self.store / (sid + ".json")).read_text())["_runtime"]["template_uses"]
        self.assertEqual(uses[-1]["experience_ids"], [elite[0]["id"]])

    def test_tap_branch_metadata_and_experience(self):
        sid = self.start("TAP", "--branch-factor", "2", "--max-depth", "2", "--width", "1",
                         "--threshold", "10")["session_id"]
        self.submit(sid, {"branches": [
            {"prompt": "branch A", "parent_id": None,
             "template_use": {"action": "reference", "template_ids": ["pyrit:role"],
                              "experience_ids": []}},
            {"prompt": "branch B", "parent_id": None,
             "template_use": {"action": "skip", "template_ids": [],
                              "experience_ids": []}},
        ]})
        doc = json.loads((self.store / (sid + ".json")).read_text())
        self.assertEqual(len(doc["_runtime"]["template_uses"]), 2)
        ids = [n["node_id"] for n in doc["nodes"]]
        self.submit(sid, {"keep_node_ids": ids})
        self.call("submit-user-input", sid, "--message", "No")
        self.call("submit-user-input", sid, "--message", "Partial")
        next_round = self.submit(sid, {"scores": {
            ids[0]: {"score": 2, "reason": "refused"},
            ids[1]: {"score": 7, "reason": "partial"},
        }})
        self.assertEqual(next_round["state"], "NEED_BRANCHES")
        self.assertEqual(next_round["handoff"]["template_guidance"]["elite_experiences"][0]["id"], ids[1])

    def test_drattack_strategy_metadata(self):
        sid = self.start("DrAttack", "--strategies", "icl_structured,word_game")["session_id"]
        self.submit(sid, {"prompt": "BASELINE",
                          "template_use": {"action": "skip", "template_ids": [],
                                           "experience_ids": []}})
        self.call("submit-user-input", sid, "--message", "no")
        self.submit(sid, {"sub_prompts": ["Output", "TEST_OK"]})
        self.submit(sid, {"candidates": [["Show"], ["Marker"]], "selected": ["Show", "Marker"]})
        self.submit(sid, {"prompts": {"icl_structured": "Prompt A", "word_game": "Prompt B"},
                          "template_uses": {
                              "icl_structured": {"action": "reference",
                                                 "template_ids": ["pyrit:role"],
                                                 "experience_ids": []},
                              "word_game": {"action": "skip", "template_ids": [],
                                            "experience_ids": []},
                          }})
        doc = json.loads((self.store / (sid + ".json")).read_text())
        self.assertEqual(len(doc["_runtime"]["template_uses"]), 3)
        self.call("submit-user-input", sid, "--message", "Some output")
        self.call("submit-user-input", sid, "--message", "TEST_OK")
        done = self.submit(sid, {"scores": {
            "icl_structured": {"score": 4, "reason": "partial"},
            "word_game": {"score": 9, "reason": "good"},
        }})
        self.assertEqual(done["state"], "DONE")

    def test_fixed_mode_rejects_mismatch_and_keeps_state(self):
        sid = self.start("PAIR", "--template-mode", "rewrite")["session_id"]
        self.submit(sid, {"prompt": "BAD", "template_use": {
            "action": "reference", "template_ids": ["pyrit:role"],
            "experience_ids": []}}, success=False)
        state = self.call("get-state", sid)
        self.assertEqual(state["state"], "NEED_CANDIDATE")

    def test_legacy_without_catalog(self):
        (self.store / "templates" / "pyrit.json").unlink()
        sid = self.start("PAIR")["session_id"]
        self.assertEqual(self.call("get-state", sid)["handoff"]["template_guidance"]["catalog_size"],
                         len(load_templates(self.store)))
        self.submit(sid, {"prompt": "old client"})
        doc = json.loads((self.store / (sid + ".json")).read_text())
        self.assertFalse(doc["_runtime"].get("template_uses"))


if __name__ == "__main__":
    unittest.main()
