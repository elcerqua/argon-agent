#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Cerqua (elcerqua)
"""Install the bundled Codex skill locally. No downloads or authentication."""
import argparse
from pathlib import Path
import shutil
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path.home() / ".agents" / "skills",
                        help="Parent skills directory (default: ~/.agents/skills).")
    parser.add_argument("--update", action="store_true",
                        help="Overwrite bundled files in an existing installation; preserve extra files.")
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parents[1] / "skills" / "gemini-argon"
    target = (args.dest.expanduser() / "gemini-argon").resolve()
    if target == source or target.is_relative_to(source):
        parser.error("Choose a destination outside the packaged skill directory.")
    if target.exists() and not args.update:
        parser.error(f"Skill already exists: {target}. Use --update to update it explicitly.")
    try:
        shutil.copytree(source, target, dirs_exist_ok=args.update,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".tmp"))
    except OSError as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Installed gemini-argon: {target}")
    print("Use $gemini-argon in Codex on your next turn. Restart Codex if it is not listed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
