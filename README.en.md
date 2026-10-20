# Gemini in Codex through Antigravity CLI

[Italiano](README.md) · **English**

**Use Gemini as a collaborating agent within your Codex workflow, signing in
to your monthly Google AI plan through Antigravity CLI. The default path
requires no API key and uses no pay-as-you-go API billing.**

Codex prepares a task and the relevant files, invokes Gemini through the official
`agy` CLI, reads the saved response, and checks its recommendations. Ask for a
second opinion on code, an independent review, analysis of results, or a proposal
to discuss and apply with Codex.

The skill keeps the name **`gemini-argon`** while supporting other Gemini models
through **`--model`**. Argon remains the default for compatibility. Gemini is an
external collaborator invoked by the skill, not a native `spawn_agent` model.
The wrapper works from the supplied dossier and returns text and proposals;
Codex coordinates any changes to the project.

## Monthly plan and authentication

Google sign-in uses Antigravity's official session and the quotas associated with
your account's plan. This path requires neither a Gemini API key nor an
API-billed Google Cloud project. Your plan may cost money: this skill does not
promise free or unlimited access. Model access, terms, and quotas depend on Google
and your account. See the official documentation for
[authentication](https://www.antigravity.google/docs/install?tab=cli),
[models](https://www.antigravity.google/docs/models/), and
[plans](https://www.antigravity.google/docs/plans/).

Google documents Argon access for paid, non-trial Google AI Pro and for Ultra.
Other models may have different requirements. `agy models` lists the slugs;
a completed request verifies actual access at that time. The wrapper never
automatically switches models, uses Vertex/ADC, or falls back to a billed API
when your plan or remaining quota does not allow a request.

Antigravity can consume additional AI credits if you have enabled **AI Credit
Overages**. Select **Never** in Antigravity settings to stay within the included
quota; the wrapper does not change this preference. See the
[credit details](https://www.antigravity.google/docs/plans/#overages).

## Requirements

- Codex with local command execution and network access.
- Python **3.10+**. The wrapper uses only the standard library; no `pip install`.
- The [official Antigravity CLI](https://www.antigravity.google/docs/getting-started/)
  (`agy`), installed and signed in to the Google account associated with your plan.
- Git to clone this repository. On Windows, the wrapper also detects
  `%LOCALAPPDATA%\agy\bin\agy.exe` before you restart the terminal.

## Install in Codex

### From a local clone

Clone the repository:

```powershell
git clone https://github.com/elcerqua/argon-agent.git
cd argon-agent
python scripts/install.py
```

The installer copies only the skill into `~/.agents/skills/gemini-argon`, the user
location in the [Codex documentation](https://learn.chatgpt.com/docs/build-skills).
It does not install `agy`, sign in, or send any material to Gemini. Use `python3`
on Linux/macOS if `python` is unavailable.

For a project-scoped skill, run from this repository's directory:

```powershell
python scripts/install.py --dest 'D:\my-project\.agents\skills'
```

Use `--update` to update an existing installation. If your Codex version or
configuration still uses `~/.codex/skills`, specify that location:

```powershell
python scripts/install.py --dest "$env:USERPROFILE\.codex\skills" --update
```

`--dest` always names the directory **containing the skills**. Updates overwrite
the bundled files and preserve additional files. Avoid duplicate installations
with the same name. The skill is available on the next turn; restart Codex if it
does not appear.

### Using Codex Skill Installer

Ask Codex:

```text
$skill-installer install the skill from GitHub repository elcerqua/argon-agent,
path skills/gemini-argon, branch main.
```

## First use

PowerShell example for the default user installation:

```powershell
$geminiWrapper = Join-Path $env:USERPROFILE '.agents\skills\gemini-argon\scripts\Gemini_Argon.py'
python $geminiWrapper status
python $geminiWrapper login
agy models
```

Adjust the path if you used `--dest`. `login` needs an interactive terminal:
complete the browser flow with your plan's Google account. Antigravity manages
credentials in the OS keyring. `status` checks installation and local metadata
only; it does not verify the subscription or the validity of the session.

Then ask Codex:

```text
Use $gemini-argon for an independent review of the changed files.
Select gemini-3.8-flash-medium with medium thinking through Antigravity's Google
sign-in. Cite files and lines and save the review.
```

Or: `Use $gemini-argon to ask Argon for a refactoring proposal, thinking high.`
Codex prepares the required context: Gemini does not inherit the conversation.

## Select the model and reasoning effort

Use the exact slugs shown by `agy models`. These examples depend on account
availability and are not a guaranteed catalog.

| Parameter | Behavior |
| --- | --- |
| No `--model` | `gemini-4-argon`, thinking `high` |
| `--model gemini-4-argon --thinking medium` | Sends `gemini-4-argon-medium` |
| `--model gemini-3.8-flash-medium` | Keeps the slug and infers `medium` thinking |
| `--model gemini-3.1-pro-high --thinking high` | Keeps the slug and explicit effort |
| Slug without an effort suffix | Keeps the slug; thinking defaults to `high` |
| Conflicting suffix and `--thinking` | Local error before submission |

Supported effort levels are `low`, `medium`, and `high`. The wrapper passes the
level to the CLI; the server may reject unsupported combinations. Only the
historical Argon shorthand adds an effort suffix. Copy the full slug for other
models.

Optional minimal probe, **making one real request that consumes quota**, without
project files:

```powershell
python $geminiWrapper probe --model gemini-3.8-flash-medium --out .gemini-runs/access-01
```

Omit `--model` to probe Argon. Every probe needs a new output directory. It checks
the CLI-selected model and the exact reply `GEMINI_ACCESS_OK`; it does not attest
to the server's internal model identity.

## Dossiers and manual calls

```powershell
python $geminiWrapper prepare --root . --prompt 'Review the code and suggest justified improvements.' --attach src/main.py --model gemini-3.8-flash-medium --out .gemini-runs/review-01
python $geminiWrapper send --run .gemini-runs/review-01
python $geminiWrapper resume --run .gemini-runs/review-01
```

Replace `src/main.py` with a real file. `prepare` is offline and saves the
line-numbered dossier, SHA256 manifest, and parameters. `send` uses the saved
model and submits once. For CLI runs, `resume` reads local state only. For a
follow-up, prepare a new directory with `--previous-run`, repeating the same
`--model` and selected effort. The local transcript is included explicitly.
Start a new conversation to change models.

Use `--prompt-file`, `--system-file`, repeated `--attach`, or `--files-from` with
a JSON array of explicit files. No recursive scans. The default payload limit
is 3,000,000 bytes (`--max-input-bytes`). The `send` timeout is 900 seconds
(`--cli-timeout`). `--max-output-tokens` does not cap Antigravity output.

Results: `response.md`, `state.json`, `response-0001.json`, and CLI logs inside
the run directory. Exit codes: **0** successful, **2** local/backend error,
**3** pending, **4** invalid or ambiguous outcome. Never automatically repeat
a failed submission.

## Scope and data

The default transport requires Google OAuth, removes API/Vertex/ADC environment
variables from its child process, and rejects API/ADC provider settings. It does
not change permanent preferences. The wrapper does not read or copy Antigravity
credentials.

The agent runs in `plan` mode in a separate workspace, declaring `tools: []`
without automatic approvals. CLI 1.4.2 may still expose its tool catalog: this is
not a sandbox. Tool use reported in the event stream invalidates the response.
Model verification checks CLI configuration and completion, not server attestation.

Select shareable files only; secret detection is partial. Dossiers, responses,
and logs remain local and may contain private material; the repository ignores
them. The historical `gemini-cli` and REST backends remain explicit options.
REST **uses pay-as-you-go APIs** and requires both `--backend api` and
`send --allow-paid-api`; see the [API reference](skills/gemini-argon/references/api-backend.md)
(in Italian).

## Development and publication

```powershell
python -m unittest discover -s skills/gemini-argon/scripts -p 'test_*.py' -v
python -m compileall -q skills/gemini-argon/scripts scripts
```

Tests are offline with simulated processes and transports. No sign-in, `agy`,
or billed calls are required. GitHub Actions runs the suite on Windows and Linux
with Python 3.10 and 3.14. This does not establish live access to every model.

The repository contains `skills/gemini-argon/` (installable package),
`scripts/install.py`, both READMEs, the GPL-3.0 license, and CI.
See [PUBLISH.md](PUBLISH.md) for GitHub CLI and Git push commands.

Original author: **Cerqua ([elcerqua](https://github.com/elcerqua))**.
Official repository: [elcerqua/argon-agent](https://github.com/elcerqua/argon-agent).
Pull requests are welcome under the same license as the project.

Independent project, not affiliated with Google or OpenAI.
Copyright © 2026 Cerqua. [GNU GPL version 3](LICENSE) (`GPL-3.0-only`).
