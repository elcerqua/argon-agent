# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Cerqua (elcerqua)
"""OAuth-only Antigravity CLI transport for the user's Google AI subscription."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

WORKSPACE = Path.home() / ".codex" / "gemini-argon-agy-workspace"


def command():
    exe = shutil.which("agy")
    native = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
    if exe:
        return [exe]
    if native.is_file():
        return [str(native)]
    raise RuntimeError("Antigravity CLI assente. Usa l'installer ufficiale https://antigravity.google/cli/install.ps1")


def oauth_settings():
    # Read configuration metadata only; never inspect token profiles or keyrings.
    directory = Path.home() / ".gemini"
    settings_file = directory / "antigravity-cli" / "settings.json"
    data = json.loads(settings_file.read_text(encoding="utf-8-sig")) if settings_file.is_file() else {}
    provider = data.get("modelProvider")
    auth_type = data.get("auth", {}).get("type")
    config_file = directory / "config" / "config.json"
    config = json.loads(config_file.read_text(encoding="utf-8-sig")) if config_file.is_file() else {}
    if provider not in (None, "", "antigravity", "google") or auth_type not in (None, "", "oauth-personal"):
        raise RuntimeError("Antigravity e configurato con un provider diverso dall'account personale. Nessun fallback API: seleziona Login with Google nella CLI.")
    if config.get("userSettings", {}).get("enableAdc"):
        raise RuntimeError("ADC abilitato in Antigravity. Per usare il piano personale seleziona OAuth Google; configurazione non modificata.")
    return {"provider_configuration": provider or "default", "api_fallback": False}


def environment():
    env = os.environ.copy()
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "AGY_ADC_AUTH",
                 "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA", "GEMINI_CLI_HOME",
                 "GEMINI_CLI_SYSTEM_SETTINGS_PATH", "GEMINI_CLI_SYSTEM_DEFAULTS_PATH",
                 "GEMINI_SYSTEM_MD", "GEMINI_WRITE_SYSTEM_MD", "GEMINI_CLI_USE_COMPUTE_ADC"):
        env.pop(name, None)
    return env


def local_status():
    try:
        executable = command()
    except RuntimeError:
        executable = None
    try:
        metadata = oauth_settings()
    except RuntimeError:
        metadata = {"provider_configuration": "requires_oauth_configuration", "api_fallback": False}
    return {"backend": "antigravity-cli", "cli_installed": executable is not None,
            "workspace": str(WORKSPACE), "authentication": "Google account OAuth (shared Antigravity session)",
            "auth_access_verified": False, "model_access_verified": False,
            "argon_access_verified": False, "network_calls": 0, **metadata}


def login(write_json=None):
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    oauth_settings()
    return subprocess.call(command(), cwd=WORKSPACE, env=environment())


def thinking_level(model, thinking=None):
    if not isinstance(model, str) or not model.strip() or model != model.strip() or model.startswith("-"):
        raise RuntimeError("--model richiede uno slug esplicito non vuoto, senza spazi esterni.")
    encoded_level = None
    for level in ("low", "medium", "high"):
        if model.endswith("-" + level):
            encoded_level = level
            break
    if thinking is not None and thinking not in ("low", "medium", "high"):
        raise RuntimeError("--thinking ammette low, medium o high.")
    if encoded_level and thinking is not None and encoded_level != thinking:
        raise RuntimeError("Il livello nel model slug e diverso da --thinking; scegli valori coerenti.")
    return thinking or encoded_level or "high"


def slug(model, thinking):
    level = thinking_level(model, thinking)
    # Preserve the historical Argon shorthand; all other slugs stay exact.
    if model == "gemini-4-argon":
        return model + "-" + level
    return model


def read_events(stdout):
    events = []
    for line in stdout.decode("utf-8-sig").splitlines():
        if line.strip():
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("Non-object CLI event")
            events.append(event)
    return events


def classify(events, returncode, selected):
    results = [e["result"] for e in events if e.get("event") == "result" and isinstance(e.get("result"), dict)]
    result = results[-1] if results else {}
    message = str(result.get("error", "")).lower()
    if returncode or result.get("status") != "SUCCESS":
        if any(term in message for term in ("auth", "sign in", "login", "credential")):
            return "login_required", result
        if any(term in message for term in ("model", "not found", "unavailable", "404")):
            return "model_unavailable", result
        return "cli_failed", result
    configs = [e.get("init", {}) for e in events if e.get("event") == "init"]
    if not configs or configs[0].get("model") != selected:
        return "model_unverified", result
    if any(e.get("step_update", {}).get("step_type") == "tool" for e in events):
        return "unexpected_tool_use", result
    if not str(result.get("response", "")).strip():
        return "empty_response", result
    return "completed", result


def send(run, state, payload, write_json, wrapper_error, max_seconds):
    oauth_settings()
    exe = command()
    selected = slug(payload["model"], state["thinking"])
    work = run / "agy-workspace"
    agents = work / ".agents" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    agent = agents / "gemini-argon-review.md"
    agent.write_text("---\nname: gemini-argon-review\ndescription: Review only the supplied dossier.\n"
                     "tools: []\nmainAgent: true\nsubagent: false\ncommandExecutionPolicy: \"off\"\n"
                     "mcpServers: []\nskills: []\nplugins: []\n---\n" + payload["system_instruction"], encoding="utf-8")
    args = exe + ["--model", selected, "--effort", state["thinking"], "--agent", "gemini-argon-review",
                  "--mode", "plan",
                  "--input-format", "stream-json", "--output-format", "stream-json",
                  "--disable-slash-commands", "--print-timeout", f"{max_seconds}s"]
    state.update(status="submitting", backend="antigravity-cli", model_verified=False, cli_model_slug=selected)
    write_json(run / "state.json", state)
    write_json(run / "cli-command.json", {"argv": args, "cwd": str(work), "authentication": "Google account OAuth",
               "api_fallback": False, "note": "Model pinned; no silent fallback by headless CLI contract. Prompt sent on stdin."})
    prompt = json.dumps({"event": "user", "message": {"content": payload["input"]}}, ensure_ascii=False) + "\n"
    try:
        process = subprocess.Popen(args, cwd=work, env=environment(), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        state.update(status="in_progress", cli_pid=process.pid)
        write_json(run / "state.json", state)
        stdout, stderr = process.communicate(prompt.encode("utf-8"), timeout=max_seconds + 15)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        (run / "cli-stdout.txt").write_bytes(stdout)
        (run / "cli-stderr.txt").write_bytes(stderr)
        state.update(status="submission_unknown", error="Timeout Antigravity CLI; nessun retry automatico.")
        write_json(run / "state.json", state)
        raise wrapper_error("Timeout Antigravity CLI. Output parziali conservati; nessun nuovo invio automatico.")
    except OSError as exc:
        state.update(status="cli_failed", error=str(exc))
        write_json(run / "state.json", state)
        raise wrapper_error("Avvio Antigravity CLI fallito; controlla installazione e log.") from None
    (run / "cli-stdout.txt").write_bytes(stdout)
    (run / "cli-stderr.txt").write_bytes(stderr)
    try:
        events = read_events(stdout)
    except (ValueError, UnicodeError):
        events = []
    status, result = classify(events, process.returncode, selected)
    if status == "cli_failed" and any(x in stderr.decode("utf-8", errors="replace").lower()
                                      for x in ("sign in", "authenticat", "credential", "login")):
        status = "login_required"
    state.update(status=status, session_id=result.get("conversation_id"), usage=result.get("usage"),
                 cli_returncode=process.returncode, model_verified=status == "completed",
                 returned_model=selected if status == "completed" else None,
                 model_verification="CLI init configuration plus SUCCESS; not server attestation")
    text = str(result.get("response", ""))
    state["text_available"] = bool(text.strip())
    (run / "response.md").write_text(text, encoding="utf-8")
    write_json(run / "response-0001.json", {"events": events, "result": result})
    write_json(run / "state.json", state)
    return state
