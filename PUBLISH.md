# Pubblicazione su GitHub / Publishing to GitHub

Repository ufficiale / Official repository:
[elcerqua/argon-agent](https://github.com/elcerqua/argon-agent).

Il branch di pubblicazione è `main`. Il repository remoto esiste già e contiene
la licenza GPL-3.0. Il pacchetto installabile resta `skills/gemini-argon` e il nome
di invocazione in Codex resta `$gemini-argon`.

The publication branch is `main`. The remote repository already exists and
contains the GPL-3.0 license. The installable package remains
`skills/gemini-argon`, invoked in Codex as `$gemini-argon`.

## Controlli locali / Local checks

```powershell
python -m unittest discover -s skills/gemini-argon/scripts -p 'test_*.py' -v
python -m compileall -q skills/gemini-argon/scripts scripts
git status --short
git diff --check
git ls-files
```

Il repository ignora cache Python, configurazioni locali, credenziali e risultati
dei run. Verifica i file effettivamente versionati prima del push.

The repository ignores Python caches, local configuration, credentials, and run
artifacts. Review the tracked files before pushing.

## Pubblicare gli aggiornamenti / Push updates

Configura `origin` solo se non punta già al repository corretto:

Set `origin` only if it does not already point to the correct repository:

```powershell
git remote set-url origin https://github.com/elcerqua/argon-agent.git
```

Dopo aver verificato e committato le modifiche / After checking and committing changes:

```powershell
git push -u origin main
```

## Verifica / Verification

```powershell
git status --short --branch
git log -1 --oneline
git ls-remote origin refs/heads/main
gh run list --repo elcerqua/argon-agent --limit 3
```
