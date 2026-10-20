# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Cerqua (elcerqua)
"""OAuth-only Gemini CLI transport. Never calls the billable REST transport."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

CLI_HOME = Path.home() / ".codex" / "gemini-argon-cli"
WORKSPACE = Path.home() / ".codex" / "gemini-argon-workspace"


def command():
    # Launch Node directly on Windows: avoids cmd.exe shell expansion and limits.
    candidates = [Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@google" / "gemini-cli"]
    located = shutil.which("gemini")
    if located:
        candidates.append(Path(located).resolve().parent / "node_modules" / "@google" / "gemini-cli")
    for root in candidates:
        package = root / "package.json"
        if package.is_file() and shutil.which("node"):
            metadata = json.loads(package.read_text(encoding="utf-8"))
            relative = metadata.get("bin", {}).get("gemini")
            if relative and (root / relative).is_file():
                return [shutil.which("node"), str(root / relative)]
    if located and Path(located).suffix.lower() not in {".ps1", ".cmd", ".bat"}:
        return [located]
    raise RuntimeError("Gemini CLI assente. Installa il pacchetto ufficiale: npm install -g @google/gemini-cli")


def settings(model="gemini-4-argon", thinking="high", max_output=65536, login=False):
    auth = {"enforcedType": "oauth-personal"}
    if not login:
        auth["selectedType"] = "oauth-personal"
    return {
        "security": {"auth": auth},
        "general": {"enableAutoUpdate": False, "enableAutoUpdateNotification": False,
                    "retryFetchErrors": False, "maxAttempts": 1},
        "advanced": {"ignoreLocalEnv": True}, "tools": {"core": []},
        "mcp": {"allowed": []}, "hooksConfig": {"enabled": False},
        "skills": {"enabled": False}, "telemetry": {"enabled": False},
        "context": {"fileName": "__argon_explicit_context_only__.md"},
        "model": {"name": model, "maxSessionTurns": 3},
        "modelConfigs": {"customOverrides": [{"match": {"model": model}, "modelConfig": {
            "model": model, "generateContentConfig": {"thinkingConfig": {"thinkingLevel": thinking.upper()},
                                                       "maxOutputTokens": max_output}}}]},
    }


def setup_home(write_json, login=False):
    directory = CLI_HOME / ".gemini"
    directory.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    # This profile belongs only to this wrapper. Credential caches remain CLI-owned.
    write_json(directory / "settings.json", settings(login=login))


def environment(system_file=None):
    env = os.environ.copy()
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
                 "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA", "GEMINI_CLI_SYSTEM_SETTINGS_PATH",
                 "GEMINI_CLI_SYSTEM_DEFAULTS_PATH", "GEMINI_SYSTEM_MD", "GEMINI_WRITE_SYSTEM_MD",
                 "GEMINI_CLI_USE_COMPUTE_ADC", "GEMINI_API_ENDPOINT", "GOOGLE_GEMINI_BASE_URL"):
        env.pop(name, None)
    env["GEMINI_CLI_HOME"] = str(CLI_HOME)
    env["NO_COLOR"] = "1"
    if system_file:
        env["GEMINI_SYSTEM_MD"] = str(system_file)
    if sys.platform == "win32":
        # Prevent the bundled pwsh modules leaking into Gemini's Windows PowerShell ACL check.
        env["PSModulePath"] = str(Path(os.environ.get("WINDIR", r"C:\Windows")) /
                                  "System32" / "WindowsPowerShell" / "v1.0" / "Modules")
    return env


def local_status():
    try:
        executable = command()
    except RuntimeError:
        executable = None
    # Never open credential caches; only report whether the CLI created one.
    return {"backend": "gemini-cli", "cli_installed": executable is not None,
            "cli_home": str(CLI_HOME), "workspace": str(WORKSPACE),
            "oauth_cache_file_present": (CLI_HOME / ".gemini" / "oauth_creds.json").is_file(),
            "auth_access_verified": False, "argon_access_verified": False,
            "authentication": "Login with Google (oauth-personal)", "api_fallback": False,
            "network_calls": 0}


def login(write_json):
    setup_home(write_json, login=True)
    return subprocess.call(command() + ["--skip-trust"], cwd=WORKSPACE, env=environment())


def cli_models(result, events):
    models = result.get("stats", {}).get("models", {})
    used = []
    if isinstance(models, dict):
        for model, values in models.items():
            count = values.get("api", {}).get("totalRequests", 0)
            tokens = values.get("tokens", {}).get("total", 0)
            if count or tokens:
                used.append(model)
    # init.model records the requested model, not proof that it generated a response.
    return used


def classify(result, events, model, returncode):
    if result.get("error") or returncode:
        message = json.dumps(result.get("error", ""), ensure_ascii=False).lower()
        if any(word in message for word in ("auth", "login", "credential", "sign in", "code\": 41")):
            return "login_required"
        if any(word in message for word in ("not found", "not available", "not supported", "unknown model", "404")):
            return "model_unavailable"
        return "cli_failed"
    used = cli_models(result, events)
    if used and any(name.removeprefix("models/") != model for name in used):
        return "model_mismatch"
    if not used:
        return "model_unverified"
    if not str(result.get("response", "")).strip():
        return "empty_response"
    return "completed"


def send(run, state, payload, write_json, wrapper_error, max_seconds):
    executable = command()  # Fail before consuming the prepared run if not installed.
    setup_home(write_json)
    if not (CLI_HOME / ".gemini" / "oauth_creds.json").is_file():
        state.update(status="login_required", backend="gemini-cli",
                     error="Profilo OAuth assente. Esegui Gemini_Argon.py login in un terminale interattivo.")
        write_json(run / "state.json", state)
        return state
    work = run / "cli-workspace"
    config_dir = work / ".gemini"
    config_dir.mkdir(parents=True, exist_ok=True)
    write_json(config_dir / "settings.json", settings(payload["model"], state["thinking"],
                                                     payload["generation_config"]["max_output_tokens"]))
    system_path = run / "system.md"
    system_path.write_text(payload["system_instruction"], encoding="utf-8")
    # Use JSON output, stdin for potentially large dossiers, no shell.
    args = executable + ["--model", payload["model"], "--output-format", "json", "--skip-trust",
                         "--prompt", "Review the complete dossier supplied on standard input. Do not use tools."]
    state.update(status="submitting", backend="gemini-cli", model_verified=False)
    write_json(run / "state.json", state)
    write_json(run / "cli-command.json", {"argv": args, "cwd": str(work),
               "authentication": "oauth-personal", "api_fallback": False,
               "note": "Full dossier passed on stdin, not shell arguments. Separate explicit transcript for follow-ups."})
    try:
        process = subprocess.Popen(args, cwd=work, env=environment(system_path), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        state.update(status="in_progress", cli_pid=process.pid)
        write_json(run / "state.json", state)
        stdout, stderr = process.communicate(payload["input"].encode("utf-8"), timeout=max_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        (run / "cli-stdout.txt").write_bytes(stdout)
        (run / "cli-stderr.txt").write_bytes(stderr)
        state.update(status="submission_unknown", error="Timeout CLI; nessun retry automatico.")
        write_json(run / "state.json", state)
        raise wrapper_error("Timeout CLI. Conservati output parziali; nessun nuovo invio automatico.")
    except OSError as exc:
        state.update(status="cli_failed", error=str(exc))
        write_json(run / "state.json", state)
        raise wrapper_error("Avvio Gemini CLI fallito; controlla installazione e log.") from None
    (run / "cli-stdout.txt").write_bytes(stdout)
    (run / "cli-stderr.txt").write_bytes(stderr)
    try:
        result = json.loads(stdout.decode("utf-8-sig"))
        if not isinstance(result, dict):
            raise ValueError("Not a JSON object")
    except (ValueError, UnicodeError):
        auth_failed = any(term in stderr.decode("utf-8", errors="replace").lower()
                          for term in ("authenticat", "sign in", "credentials"))
        result = {"error": {"message": "Authentication required" if auth_failed else "Output CLI non JSON; consultare cli-stderr.txt"}}
    # Error messages are stored locally, never print possible OAuth URLs/tokens to the chat.
    state.update(status=classify(result, [], payload["model"], process.returncode),
                 session_id=result.get("session_id"), usage=result.get("stats"),
                 used_models=cli_models(result, []), cli_returncode=process.returncode,
                 model_verified=False)
    state["model_verified"] = state["status"] == "completed"
    state["returned_model"] = payload["model"] if state["model_verified"] else None
    text = str(result.get("response", ""))
    state["text_available"] = bool(text.strip())
    (run / "response.md").write_text(text, encoding="utf-8")
    write_json(run / "response-0001.json", result)
    write_json(run / "state.json", state)
    return state
