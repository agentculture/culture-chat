"""The per-harness smoke check must fail when ANY ONE harness config breaks.

This is the load-bearing property of ``scripts/harness-smoke.py`` (t12
criterion 4). All four harnesses are live for interactive use over the same
clone at all times, so a check that only exercises the harness ``culture.yaml``
declares would let three-quarters of a clone's configs rot unnoticed.

Each break test builds a faithful fixture clone from the real repo's own files,
breaks exactly one harness's config, and asserts:

* the whole check fails (non-zero exit), and
* the broken harness — and only the broken harness — is reported FAIL.

The second half matters as much as the first: it proves the check discriminates
between harnesses rather than collapsing on any perturbation.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from tests.smoke_support import REPO_ROOT, SMOKE, run_smoke

# --- the baseline: an intact clone passes ---------------------------------


def test_smoke_passes_on_an_intact_clone(clone: Path) -> None:
    rc, statuses, out = run_smoke(clone)
    assert rc == 0, out
    assert set(statuses) == {
        "claude",
        "pi",
        "qwen",
        "colleague",
        "fingerprint-registry",
        "agents-md-shared-base",
    }
    assert all(status == "PASS" for status in statuses.values()), out


def test_smoke_passes_on_the_real_repo() -> None:
    """The fixture is a stand-in; the real tree must pass too."""
    rc, statuses, out = run_smoke(REPO_ROOT)
    assert rc == 0, out
    assert all(status == "PASS" for status in statuses.values()), out


# --- criterion 4: break each harness in turn ------------------------------


def _assert_only_broken(statuses: dict[str, str], rc: int, broken: str, out: str) -> None:
    assert rc != 0, f"the smoke check passed with {broken} broken:\n{out}"
    assert statuses[broken] == "FAIL", out
    for name in ("claude", "pi", "qwen", "colleague"):
        if name != broken:
            assert statuses[name] == "PASS", f"{name} collapsed too:\n{out}"


def test_smoke_fails_when_the_claude_config_is_broken(clone: Path) -> None:
    """Claude Code resolves CLAUDE.md; an empty one is not a config."""
    (clone / "CLAUDE.md").write_text("\n", encoding="utf-8")
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "claude", out)


def test_smoke_fails_when_the_pi_config_is_broken(clone: Path) -> None:
    """Pi's system prompt is .pi/SYSTEM.md; without it Pi is a stock agent."""
    (clone / ".pi" / "SYSTEM.md").unlink()
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "pi", out)


def test_smoke_fails_when_the_qwen_config_is_broken(clone: Path) -> None:
    """Qwen Code resolves QWEN.md."""
    (clone / "QWEN.md").unlink()
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "qwen", out)


def test_smoke_fails_when_the_colleague_config_is_broken(clone: Path) -> None:
    """colleague's prompt cascade resolves AGENTS.colleague.md."""
    (clone / "AGENTS.colleague.md").unlink()
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "colleague", out)


# --- the skills-discovery half of each harness's config -------------------


def test_smoke_fails_when_pi_settings_points_at_a_home_directory(clone: Path) -> None:
    link = clone / ".pi" / "skills"
    link.unlink()
    link.symlink_to("/opt/elsewhere/skills")  # absolute: breaks clone portability
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "pi", out)


def test_smoke_fails_when_qwen_skills_is_a_forked_real_directory(clone: Path) -> None:
    link = clone / ".qwen" / "skills"
    link.unlink()
    link.mkdir()
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "qwen", out)


def test_smoke_fails_when_colleague_skills_symlink_is_absolute(clone: Path) -> None:
    link = clone / ".colleague" / "skills"
    link.unlink()
    os.symlink(str(clone / ".claude" / "skills"), link)
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "colleague", out)


def test_smoke_fails_when_the_canonical_skill_tree_is_gone(clone: Path) -> None:
    """Removing the one kit breaks every harness's discovery at once."""
    shutil.rmtree(clone / ".claude" / "skills")
    rc, statuses, out = run_smoke(clone)
    assert rc != 0
    assert [statuses[n] for n in ("claude", "pi", "qwen", "colleague")] == ["FAIL"] * 4, out
    assert statuses["fingerprint-registry"] == "FAIL", out


# --- global invariants ----------------------------------------------------


def test_smoke_fails_when_the_shared_agents_md_is_missing(clone: Path) -> None:
    """colleague and Qwen Code cascade from AGENTS.md; losing it must fail."""
    (clone / "AGENTS.md").unlink()
    rc, statuses, out = run_smoke(clone)
    assert rc != 0, out
    assert statuses["agents-md-shared-base"] == "FAIL", out


def test_smoke_fails_when_the_shared_agents_md_is_empty(clone: Path) -> None:
    (clone / "AGENTS.md").write_text("  \n", encoding="utf-8")
    rc, statuses, out = run_smoke(clone)
    assert rc != 0, out
    assert statuses["agents-md-shared-base"] == "FAIL", out


def test_smoke_fails_when_a_prompt_file_is_unregistered(clone: Path) -> None:
    """A prompt file no registry knows is a config that tooling cannot see."""
    registry = clone / ".claude/skills/agent-config/data/backend-fingerprints.yaml"
    registry.write_text(
        registry.read_text(encoding="utf-8").replace("QWEN.md", "QWEN-typo.md"),
        encoding="utf-8",
    )
    rc, statuses, out = run_smoke(clone)
    _assert_only_broken(statuses, rc, "qwen", out)


def test_smoke_refuses_to_run_when_the_yaml_drops_a_harness(clone: Path) -> None:
    """A harness deleted from the YAML must abort, never silently shrink."""
    path = clone / "docs" / "harness-invocations.yaml"
    text = path.read_text(encoding="utf-8")
    head, _, _tail = text.partition("\n  qwen:")
    path.write_text(head + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--repo", str(clone), "--stage", "config"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "qwen" in proc.stderr
