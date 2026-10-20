# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Cerqua (elcerqua)
"""Offline behavioral tests. No credentials, network, or billed calls."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

SPEC = importlib.util.spec_from_file_location("argon", Path(__file__).with_name("Gemini_Argon.py"))
argon = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(argon)


class ArgonTests(unittest.TestCase):
    def setUp(self):
        # Keep fixtures inside the caller's writable workspace, including on Codex Windows sandboxes.
        fixture_parent = Path.cwd().resolve() / ".tmp"
        fixture_parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="argon-tests-", dir=fixture_parent)
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to(fixture_parent))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "report.md").write_text("Prima riga\nSeconda riga: perche il test e fallito.\n", encoding="utf-8")
        self.keys = patch.object(argon, "key_info", return_value=("", None))
        self.keys.start()
        self.addCleanup(self.keys.stop)

    def prepare(self, *options, name="run"):
        args = argon.parser().parse_args(["prepare", "--backend", "api", "--root", str(self.root), "--out", str(self.root / name),
                                         "--prompt", "Rivedi le evidenze.", *options])
        argon.prepare(args)
        return self.root / name

    def send_args(self, run):
        return argon.parser().parse_args(["send", "--run", str(run), "--allow-paid-api"])

    def reply(self, status="completed", model=argon.MODEL, texts=("Parere uno.", "Parere due.")):
        return {"id": "interaction-123", "status": status, "model": model,
                "steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]} for text in texts],
                "usage": {"total_input_tokens": 15, "total_output_tokens": 20}}

    def authorized(self):
        return patch.object(argon, "need_key", return_value="test-key-not-real")

    def test_levels_and_explicit_file_manifest(self):
        for level in ("low", "medium", "high"):
            run = self.prepare("--thinking", level, "--attach", "report.md", "--attach", "report.md", name=level)
            payload = argon.read_json(run / "request.json")
            manifest = argon.read_json(run / "manifest.json")
            self.assertEqual(payload["generation_config"]["thinking_level"], level)
            self.assertEqual(payload["model"], argon.MODEL)
            self.assertEqual(len(manifest["files"]), 1)
            self.assertIn("2: Seconda riga", payload["input"])
            self.assertEqual(manifest["request_sha256"], argon.digest((run / "request.json").read_bytes()))
            self.assertNotIn("tools", payload)

    def test_prepare_is_offline_and_needs_no_key(self):
        with patch.object(argon, "api_call", side_effect=AssertionError("network")):
            run = self.prepare()
        self.assertEqual(argon.read_json(run / "state.json")["status"], "prepared")

    def test_files_from_includes_only_selected_files(self):
        (self.root / "unselected.md").write_text("DO NOT INCLUDE", encoding="utf-8")
        (self.root / "files.json").write_text('["report.md"]', encoding="utf-8")
        run = self.prepare("--files-from", str(self.root / "files.json"))
        self.assertNotIn("DO NOT INCLUDE", (run / "dossier.txt").read_text(encoding="utf-8"))

    def test_root_escape_and_credentials_rejected(self):
        with self.assertRaises(argon.WrapperError):
            self.prepare("--attach", str(Path(__file__).resolve()))
        (self.root / ".env").write_text("SAFE_PLACEHOLDER", encoding="utf-8")
        with self.assertRaises(argon.WrapperError):
            self.prepare("--attach", ".env")
        (self.root / "secret.md").write_text("AIza" + "X" * 35, encoding="utf-8")
        with self.assertRaises(argon.WrapperError):
            self.prepare("--attach", "secret.md")

    def test_budget_and_binary_and_existing_destination(self):
        (self.root / "large.md").write_text("x" * 4000, encoding="utf-8")
        with self.assertRaises(argon.WrapperError):
            self.prepare("--attach", "large.md", "--max-input-bytes", "1024")
        (self.root / "binary.txt").write_bytes(b"hello\x00world")
        with self.assertRaises(argon.WrapperError):
            self.prepare("--attach", "binary.txt")
        self.prepare()
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_missing_key_does_not_consume_prepared_run(self):
        run = self.prepare()
        with self.assertRaises(argon.WrapperError):
            argon.send(self.send_args(run))
        self.assertEqual(argon.read_json(run / "state.json")["status"], "prepared")

    def test_pending_then_resume_uses_one_post_and_get(self):
        run = self.prepare()
        with self.authorized(), patch.object(argon, "api_call", side_effect=[self.reply("in_progress", texts=()), self.reply()]) as api:
            first = argon.send(self.send_args(run))
            self.assertEqual(first["status"], "in_progress")
            final = argon.resume(argon.parser().parse_args(["resume", "--run", str(run), "--wait-seconds", "0"]))
            self.assertEqual(final["status"], "completed")
            self.assertTrue(final["model_verified"])
            self.assertEqual([c.args[0] for c in api.call_args_list], ["POST", "GET"])
        self.assertEqual((run / "response.md").read_text(encoding="utf-8"), "Parere uno.\n\nParere due.")
        self.assertEqual(len(list(run.glob("response-*.json"))), 2)

    def test_duplicate_send_and_tampering_never_call_api(self):
        run = self.prepare()
        with self.authorized(), patch.object(argon, "api_call", return_value=self.reply()) as api:
            argon.send(self.send_args(run))
            with self.assertRaises(argon.WrapperError):
                argon.send(self.send_args(run))
            self.assertEqual(api.call_count, 1)
        other = self.prepare(name="tamper")
        with (other / "request.json").open("ab") as f:
            f.write(b" ")
        with patch.object(argon, "api_call", side_effect=AssertionError("network")):
            with self.assertRaises(argon.WrapperError):
                argon.send(self.send_args(other))

    def test_post_timeout_stays_ambiguous_without_retry(self):
        run = self.prepare()
        with self.authorized(), patch.object(argon, "api_call", side_effect=argon.WrapperError("timeout")) as api:
            with self.assertRaises(argon.WrapperError):
                argon.send(self.send_args(run))
            with self.assertRaises(argon.WrapperError):
                argon.send(self.send_args(run))
            with self.assertRaises(argon.WrapperError):
                argon.resume(argon.parser().parse_args(["resume", "--run", str(run)]))
            self.assertEqual(api.call_count, 1)
        self.assertEqual(argon.read_json(run / "state.json")["status"], "submission_unknown")

    def test_followup_and_unfinished_previous(self):
        run = self.prepare()
        with self.assertRaises(argon.WrapperError):
            self.prepare("--previous-run", str(run), name="notyet")
        with self.authorized(), patch.object(argon, "api_call", return_value=self.reply()):
            argon.send(self.send_args(run))
        followup = self.prepare("--previous-run", str(run), "--thinking", "medium", name="followup")
        self.assertEqual(argon.read_json(followup / "request.json")["previous_interaction_id"], "interaction-123")
        self.assertEqual(argon.read_json(followup / "state.json")["thinking"], "medium")

    def test_model_mismatch_not_accepted(self):
        run = self.prepare()
        with self.authorized(), patch.object(argon, "api_call", return_value=self.reply(model="different-model")):
            with self.assertRaises(argon.WrapperError):
                argon.send(self.send_args(run))
        self.assertEqual(argon.read_json(run / "state.json")["status"], "model_mismatch")

    def test_exit_codes_pending_incomplete_and_empty(self):
        for status, texts, expected in [("in_progress", (), 3), ("incomplete", ("partial",), 4),
                                         ("completed", (), 4), ("completed", ("done",), 0),
                                         ("requires_action", ("need tools",), 4)]:
            run = self.prepare(name=f"exit-{status}-{expected}")
            with self.authorized(), patch.object(argon, "api_call", return_value=self.reply(status, texts=texts)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(argon.main(["send", "--run", str(run), "--allow-paid-api"]), expected)

    def test_lock_prevents_parallel_send(self):
        run = self.prepare()
        with argon.run_lock(run), patch.object(argon, "api_call", side_effect=AssertionError("network")):
            with self.assertRaises(argon.WrapperError):
                argon.send(self.send_args(run))

    def test_get_failure_preserves_id_for_recovery(self):
        run = self.prepare()
        with self.authorized(), patch.object(argon, "api_call", return_value=self.reply("in_progress", texts=())):
            argon.send(self.send_args(run))
        with self.authorized(), patch.object(argon, "api_call", side_effect=argon.WrapperError("offline")):
            with self.assertRaises(argon.WrapperError):
                argon.resume(argon.parser().parse_args(["resume", "--run", str(run)]))
        self.assertEqual(argon.read_json(run / "state.json")["interaction_id"], "interaction-123")

    def test_http_transport_header_and_response_redaction(self):
        class Reply:
            def __enter__(self):
                return io.BytesIO(json.dumps({"id": "x", "echo": "synthetic-secret"}).encode())
            def __exit__(self, *args):
                pass
        with patch.object(argon.request, "build_opener") as factory:
            factory.return_value.open.return_value = Reply()
            result = argon.api_call("GET", "synthetic-secret", interaction_id="id/with?chars")
            req = factory.return_value.open.call_args.args[0]
            self.assertNotIn("synthetic-secret", req.full_url)
            self.assertEqual(req.get_header("X-goog-api-key"), "synthetic-secret")
            self.assertTrue(req.full_url.endswith("id%2Fwith%3Fchars"))
            self.assertEqual(result["echo"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main(verbosity=2)
