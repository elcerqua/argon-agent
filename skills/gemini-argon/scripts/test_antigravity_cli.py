# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Cerqua (elcerqua)
"""Offline Antigravity transport tests; fake process only."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import antigravity_cli as agy
SPEC = importlib.util.spec_from_file_location("argon", Path(__file__).with_name("Gemini_Argon.py"))
argon = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(argon)


class AgyTests(unittest.TestCase):
    def setUp(self):
        parent = Path.cwd().resolve() / ".tmp"
        parent.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="argon-agy-tests-", dir=parent)
        self.root = Path(self.tmp.name)
        self.assertTrue(self.root.is_relative_to(parent))
        self.addCleanup(self.tmp.cleanup)
        for target, value in [("command", ["agy.exe"]), ("oauth_settings", {"api_fallback": False})]:
            mock = patch.object(agy, target, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch.object(argon, "key_info", return_value=("", None))
        mock.start()
        self.addCleanup(mock.stop)

    def prepare(self, name="run", *extra):
        argon.prepare(argon.parser().parse_args(["prepare", "--root", str(self.root), "--prompt", "Assess these claims.",
                                               "--out", str(self.root / name), *extra]))
        return self.root / name

    def send(self, run):
        return argon.send(argon.parser().parse_args(["send", "--run", str(run)]))

    def events(self, model="gemini-4-argon-high", status="SUCCESS", **more):
        result = {"conversation_id": "conversation-test", "status": status, "response": "Independent response", **more}
        return [{"event": "init", "init": {"model": model, "tools": []}}, {"event": "result", "result": result}]

    def process(self, factory, events):
        obj = factory.return_value
        obj.pid = 999
        obj.returncode = 0
        obj.communicate.return_value = (b"\n".join(json.dumps(e).encode() for e in events), b"")
        return obj

    def test_default_is_antigravity_oauth_no_rest(self):
        run = self.prepare()
        with patch.object(agy.subprocess, "Popen") as proc, patch.object(argon, "api_call", side_effect=AssertionError("payg")):
            fake = self.process(proc, self.events())
            result = self.send(run)
        self.assertEqual(result["backend"], "antigravity-cli")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["model"], "gemini-4-argon-high")
        command = proc.call_args.args[0]
        self.assertEqual(command[command.index("--mode") + 1], "plan")
        self.assertNotIn("--dangerously-skip-permissions", command)
        self.assertNotIn("-p", command)  # Stream stdin mode must not be mixed with -p.
        self.assertEqual(json.loads(fake.communicate.call_args.args[0])["event"], "user")
        self.assertNotIn("Assess these claims", " ".join(command))

    def test_all_three_effort_levels_pin_the_slug(self):
        for level in ("low", "medium", "high"):
            run = self.prepare(level, "--thinking", level)
            with patch.object(agy.subprocess, "Popen") as proc:
                self.process(proc, self.events(model=f"gemini-4-argon-{level}"))
                self.assertEqual(self.send(run)["status"], "completed")
                args = proc.call_args.args[0]
                self.assertEqual(args[args.index("--effort") + 1], level)
                self.assertEqual(args[args.index("--model") + 1], f"gemini-4-argon-{level}")

    def test_missing_auth_is_reported_without_payg_fallback(self):
        run = self.prepare()
        with patch.object(agy.subprocess, "Popen") as proc, patch.object(argon, "api_call", side_effect=AssertionError("payg")):
            self.process(proc, self.events(status="ERROR", error="Authentication required. Please sign in."))
            self.assertEqual(self.send(run)["status"], "login_required")
            self.assertEqual(proc.call_count, 1)

    def test_model_metadata_required(self):
        for name, events in [("missing", self.events()[1:]), ("different", self.events(model="gemini-3.8-flash-high"))]:
            run = self.prepare(name)
            with patch.object(agy.subprocess, "Popen") as proc:
                self.process(proc, events)
                self.assertEqual(self.send(run)["status"], "model_unverified")

    def test_tools_invalidate_consultation(self):
        run = self.prepare()
        events = self.events()
        events.insert(1, {"event": "step_update", "step_update": {"step_type": "tool", "tool_name": "run_command"}})
        with patch.object(agy.subprocess, "Popen") as proc:
            self.process(proc, events)
            self.assertEqual(self.send(run)["status"], "unexpected_tool_use")

    def test_errors_not_promoted(self):
        status, _ = agy.classify(self.events(status="ERROR", error="invalid model selection"), 1, "gemini-4-argon-high")
        self.assertEqual(status, "model_unavailable")
        status, _ = agy.classify(self.events(response=""), 0, "gemini-4-argon-high")
        self.assertEqual(status, "empty_response")

    def test_api_and_adc_environment_removed_only_for_child(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-secret", "AGY_ADC_AUTH": "true"}):
            env = agy.environment()
            self.assertNotIn("GEMINI_API_KEY", env)
            self.assertNotIn("AGY_ADC_AUTH", env)
            self.assertEqual(os.environ["GEMINI_API_KEY"], "fake-secret")

    def test_mixed_explicit_slug_and_effort_rejected(self):
        with self.assertRaises(RuntimeError):
            agy.slug("gemini-4-argon-low", "high")

    def test_other_model_slugs_are_pinned_without_rewriting(self):
        for model in ("gemini-3.8-flash-high", "gemini-3.1-pro-medium", "gemini-future-model"):
            run = self.prepare(model, "--model", model)
            level = "medium" if model.endswith("-medium") else "high"
            with patch.object(agy.subprocess, "Popen") as proc, patch.object(argon, "api_call", side_effect=AssertionError("payg")):
                self.process(proc, self.events(model=model))
                result = self.send(run)
            self.assertEqual(result["model"], model)
            self.assertTrue(result["model_verified"])
            command = proc.call_args.args[0]
            self.assertEqual(command[command.index("--model") + 1], model)
            self.assertEqual(command[command.index("--effort") + 1], level)
            self.assertEqual(argon.read_json(run / "request.json")["model"], model)

    def test_effort_is_inferred_from_explicit_slug(self):
        for level in ("low", "medium", "high"):
            model = f"gemini-example-{level}"
            run = self.prepare(level, "--model", model)
            self.assertEqual(argon.read_json(run / "state.json")["thinking"], level)
            self.assertEqual(argon.read_json(run / "request.json")["generation_config"]["thinking_level"], level)

    def test_conflicting_or_empty_model_fails_before_creating_run(self):
        for name, model in (("conflict", "gemini-3.8-flash-medium"), ("empty", "")):
            with patch.object(agy.subprocess, "Popen", side_effect=AssertionError("network")):
                with self.assertRaises(RuntimeError):
                    self.prepare(name, "--model", model, "--thinking", "high")
            self.assertFalse((self.root / name).exists())

    def test_other_model_unavailable_never_falls_back(self):
        model = "gemini-3.1-pro-medium"
        run = self.prepare("unavailable", "--model", model)
        with patch.object(agy.subprocess, "Popen") as proc, patch.object(argon, "api_call", side_effect=AssertionError("payg")):
            self.process(proc, self.events(model=model, status="ERROR", error="Model unavailable"))
            self.assertEqual(self.send(run)["status"], "model_unavailable")
            self.assertEqual(proc.call_count, 1)

    def test_other_model_followup_preserves_transcript_and_rejects_model_change(self):
        model = "gemini-3.8-flash-medium"
        run = self.prepare("first", "--model", model)
        with patch.object(agy.subprocess, "Popen") as proc:
            self.process(proc, self.events(model=model))
            self.send(run)
        followup = self.prepare("next", "--model", model, "--previous-run", str(run))
        self.assertIn("Independent response", argon.read_json(followup / "request.json")["input"])
        with self.assertRaises(argon.WrapperError):
            self.prepare("different", "--previous-run", str(run))

    def test_probe_uses_selected_model_without_attaching_files(self):
        model = "gemini-3.8-flash-medium"
        run = self.root / "probe"
        with patch.object(agy, "WORKSPACE", self.root), patch.object(agy.subprocess, "Popen") as proc, contextlib.redirect_stdout(io.StringIO()):
            self.process(proc, self.events(model=model, response=argon.PROBE_REPLY))
            code = argon.main(["probe", "--model", model, "--out", str(run)])
        self.assertEqual(code, 0)
        self.assertEqual(argon.read_json(run / "manifest.json")["files"], [])
        state = argon.read_json(run / "state.json")
        self.assertEqual(state["requested_model"], model)
        self.assertEqual(state["thinking"], "medium")
        self.assertTrue(state["probe_response_verified"])

    def test_probe_with_wrong_reply_is_not_success(self):
        run = self.root / "bad-probe"
        with patch.object(agy, "WORKSPACE", self.root), patch.object(agy.subprocess, "Popen") as proc, contextlib.redirect_stdout(io.StringIO()):
            self.process(proc, self.events(response="unrelated response"))
            code = argon.main(["probe", "--out", str(run)])
        self.assertEqual(code, 4)
        self.assertEqual(argon.read_json(run / "state.json")["status"], "probe_failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
