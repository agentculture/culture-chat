"""Shared fixtures and helpers for the ``scripts/harness-smoke.py`` tests.

Imported by ``test_harness_smoke.py`` (config-stage break tests) and
``test_harness_smoke_contract.py`` (output contract, live and toolchain
honesty). The pytest fixtures themselves live in ``conftest.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE = REPO_ROOT / "scripts" / "harness-smoke.py"


def load_smoke():
    """Import scripts/harness-smoke.py by path (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("harness_smoke_under_test", SMOKE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_smoke()

#: Everything a fixture clone needs for the offline ``config`` stage. Copied
#: from the real repo so the fixture cannot drift into a private fiction.
FIXTURE_FILES = (
    "docs/harness-invocations.yaml",
    "CLAUDE.md",
    "AGENTS.md",
    "AGENTS.override.md",
    "AGENTS.colleague.md",
    "QWEN.md",
    ".pi/SYSTEM.md",
    ".claude/skills/agent-config/data/backend-fingerprints.yaml",
    ".claude/skills/cicd/SKILL.md",
)

FIXTURE_SYMLINKS = (
    (".qwen/skills", "../.claude/skills"),
    (".colleague/skills", "../.claude/skills"),
    (".pi/skills", "../.claude/skills"),
)


def build_fixture(dest: Path) -> Path:
    for rel in FIXTURE_FILES:
        src = REPO_ROOT / rel
        assert src.is_file(), f"fixture source {rel} vanished from the repo"
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    for rel, target in FIXTURE_SYMLINKS:
        link = dest / rel
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, link)
    return dest


def run_smoke(repo: Path) -> tuple[int, dict[str, str], str]:
    """Run the config stage over ``repo``; return (rc, harness->status, stdout)."""
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--repo", str(repo), "--stage", "config", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout)
    statuses = {r["check"]: r["status"] for r in payload["results"]}
    return proc.returncode, statuses, proc.stdout


def fake_tool(bin_dir: Path, name: str, stdout: str, stderr: str, code: int) -> None:
    """Plant a fake ``name`` on PATH that prints ``stdout`` and exits ``code``."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / name
    # Written against the interpreter running the tests rather than /bin/sh:
    # PATH is emptied down to bin_dir, so a shell script could not find `cat`.
    script.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"sys.stdout.write({stdout!r})\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({code})\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
