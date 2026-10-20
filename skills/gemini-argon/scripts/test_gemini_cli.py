# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Cerqua (elcerqua)
"""Offline CLI transport tests: no login, credentials, network, or real model."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_cli as cli

SPEC = importlib.util.spec_from_file_location("argon", Path(__file__).with_name("Gemini_Argon.py"))
argon = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(argon)


class CliTests(unittest.TestCase):
    def setUp(self):
        parent = Path.cwd().resolve() / ".tmp"
        parent.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="argon-cli-tests-", dir=parent)
        self.root = Path(self.tmp.name)
        self.assertTrue(self.root.resolve().is_relative_to(parent))
        self.addCleanup(self.tmp.cleanup)
        for target, value in [("CLI_HOME", self.root / "home"), ("WORKSPACE", self.root / "workspace")]:
            mock = patch.object(cli, target, value)
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch.object(cli, "command", return_value=["node", "official-gemini.js"])
        mock.start()
        self.addCleanup(mock.stop)
        mock = patch.object(argon, "key_info", return_value=("", None))
        mock.start()
        self.addCleanup(mock.stop)
        cli.setup_home(argon.write_json)

    def prepare(self, name="run", *more):
        argon.prepare(argon.parser().parse_args(["prepare", "--backend", "gemini-cli", "--root", str(self.root),
                      "--out", str(self.root / name), "--prompt", "Review this claim.", *more]))
        return self.root / name

    def authorize(self):
        (cli.CLI_HOME / ".gemini" / "oauth_creds.json").write_text("{}", encoding="utf-8")

    def send(self, run):
        return argon.send(argon.parser().parse_args(["send", "--run", str(run)]))

    def response(self, model=argon.MODEL, **extra):
        return {"session_id": "test-session", "response": "Independent opinion", "stats": {
            "models": {model: {"api": {"totalRequests": 1}, "tokens": {"total": 10}}}}, **extra}

    def process(self, factory, result):
        obj = factory.return_value
        obj.pid = 12345
        obj.returncode = 0
        obj.communicate.return_value = (json.dumps(result).encode(), b"")
        return obj

    def test_default_is_oauth_and_no_api_request(self):
        run = self.prepare()
        self.assertEqual(argon.read_json(run / "state.json")["backend"], "gemini-cli")
        with patch.object(argon, "api_call", side_effect=AssertionError("billable API")), patch.object(cli.subprocess, "Popen") as proc:
            result = self.send(run)
            self.assertEqual(result["status"], "login_required")
            proc.assert_not_called()

    def test_cli_success_passes_dossier_by_stdin_and_checks_model(self):
        run = self.prepare()
        self.authorize()
        with patch.object(argon, "api_call", side_effect=AssertionError("billable API")), patch.object(cli.subprocess, "Popen") as proc:
            fake = self.process(proc, self.response())
            result = self.send(run)
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["model_verified"])
            self.assertNotIn("Review this claim.", " ".join(proc.call_args.args[0]))
            self.assertIn(b"Review this claim.", fake.communicate.call_args.args[0])
        self.assertEqual((run / "response.md").read_text(encoding="utf-8"), "Independent opinion")

    def test_environment_removes_payg_and_vertex_credentials(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-key", "GOOGLE_API_KEY": "synthetic-key",
                        "GOOGLE_GENAI_USE_VERTEXAI": "true", "GOOGLE_APPLICATION_CREDENTIALS": "fake.json"}):
            env = cli.environment()
            for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_APPLICATION_CREDENTIALS"):
                self.assertNotIn(key, env)
            self.assertEqual(os.environ["GEMINI_API_KEY"], "synthetic-key")

    def test_levels_are_passed_to_cli_configuration(self):
        self.authorize()
        for level in ("low", "medium", "high"):
            run = self.prepare(level, "--thinking", level)
            with patch.object(cli.subprocess, "Popen") as proc:
                self.process(proc, self.response())
                self.send(run)
            config = argon.read_json(run / "cli-workspace" / ".gemini" / "settings.json")
            generation = config["modelConfigs"]["customOverrides"][0]["modelConfig"]["generateContentConfig"]
            self.assertEqual(generation["thinkingConfig"]["thinkingLevel"], level.upper())
            self.assertEqual(config["security"]["auth"]["enforcedType"], "oauth-personal")
            self.assertEqual(config["tools"]["core"], [])

    def test_api_requires_explicit_payg_flag(self):
        run = self.prepare("api", "--backend", "api")
        with patch.object(argon, "api_call", side_effect=AssertionError("billable API")):
            with self.assertRaises(argon.WrapperError):
                self.send(run)

    def test_unknown_model_no_fallback(self):
        run = self.prepare()
        self.authorize()
        with patch.object(argon, "api_call", side_effect=AssertionError("billable API")), patch.object(cli.subprocess, "Popen") as proc:
            self.process(proc, {"error": {"message": "Model not found: gemini-4-argon", "code": 404}})
            self.assertEqual(self.send(run)["status"], "model_unavailable")
            self.assertEqual(proc.call_count, 1)

    def test_response_from_different_model_is_rejected(self):
        run = self.prepare()
        self.authorize()
        with patch.object(cli.subprocess, "Popen") as proc:
            self.process(proc, self.response(model="gemini-3.8-flash"))
            self.assertEqual(self.send(run)["status"], "model_mismatch")

    def test_no_model_metadata_is_not_verified(self):
        run = self.prepare()
        self.authorize()
        with patch.object(cli.subprocess, "Popen") as proc:
            self.process(proc, {"response": "I am Argon", "session_id": "x"})
            self.assertEqual(self.send(run)["status"], "model_unverified")

    def test_followup_contains_prior_question_and_response(self):
        run = self.prepare()
        self.authorize()
        with patch.object(cli.subprocess, "Popen") as proc:
            self.process(proc, self.response())
            self.send(run)
        followup = self.prepare("followup", "--previous-run", str(run))
        self.assertIn("Independent opinion", argon.read_json(followup / "request.json")["input"])
        with patch.object(cli.subprocess, "Popen", side_effect=AssertionError("repeat send")):
            argon.resume(argon.parser().parse_args(["resume", "--run", str(run)]))
            with self.assertRaises(argon.WrapperError):
                self.send(run)

    def test_cli_timeout_preserves_unknown_state_without_retry(self):
        run = self.prepare()
        self.authorize()
        with patch.object(cli.subprocess, "Popen") as proc:
            fake = self.process(proc, self.response())
            fake.communicate.side_effect = [cli.subprocess.TimeoutExpired("gemini", 1), (b"partial", b"timeout")]
            with self.assertRaises(argon.WrapperError):
                self.send(run)
            fake.kill.assert_called_once()
            self.assertEqual(argon.read_json(run / "state.json")["status"], "submission_unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
