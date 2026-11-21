"""The smoke check's honesty and output contract.

Companion to ``test_harness_smoke.py`` (which breaks each harness config in
turn). These tests pin the rest of ``scripts/harness-smoke.py``'s promises:

* a skipped check is never a pass, and ``--require`` can refuse a skip;
* results on stdout, diagnostics on stderr, pure JSON under ``--json``;
* exit 1 for user errors, never the environment-reserved exit 2;
* the live stage reads only the harness's answer on stdout;
* a failed external tool (steward, guild) can never look verified.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from tests.smoke_support import REPO_ROOT, SMOKE, fake_tool, smoke

# --- honesty: a skipped check is never a pass -----------------------------


def test_unavailable_harness_binaries_skip_loudly_and_are_not_passes() -> None:
    """The live stage must announce what it did NOT verify."""
    env = dict(os.environ, PATH="")
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--repo", str(REPO_ROOT), "--stage", "live"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout
    # Results on stdout, diagnostics on stderr (the repo's CLI contract).
    assert "NOT VERIFIED" in proc.stderr
    assert "NOT VERIFIED" not in proc.stdout
    for name in ("claude", "pi", "qwen", "colleague"):
        assert f"[SKIP  ] live/{name}" in proc.stdout
    assert "PASS" not in proc.stdout


def test_require_turns_a_skipped_stage_into_a_failure() -> None:
    """--require live is how a local run refuses to accept a silent skip."""
    env = dict(os.environ, PATH="")
    proc = subprocess.run(
        [
            sys.executable,
            str(SMOKE),
            "--repo",
            str(REPO_ROOT),
            "--stage",
            "live",
            "--require",
            "live",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 1
    assert "--require named stage(s) that skipped: live" in proc.stderr
    assert "ERROR:" not in proc.stdout


# --- the CLI output/exit-code contract ------------------------------------


def test_a_clean_run_writes_nothing_to_stderr() -> None:
    """Diagnostics on stderr must not fire when every check passed."""
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--repo", str(REPO_ROOT), "--stage", "config"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stderr == ""
    assert "summary:" in proc.stdout


def test_failure_diagnostics_go_to_stderr_not_stdout(clone: Path) -> None:
    """A failing run keeps its explanation off the results stream."""
    (clone / "QWEN.md").write_text("", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--repo", str(clone), "--stage", "config"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "FAILED:" in proc.stderr
    assert "FAILED:" not in proc.stdout


def test_json_mode_stdout_stays_pure_json_when_a_check_fails(clone: Path) -> None:
    (clone / "QWEN.md").write_text("", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--repo", str(clone), "--stage", "config", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)  # would raise if diagnostics leaked in
    assert payload["failed"] >= 1


def test_an_unknown_stage_is_a_user_error_exit_1_not_environment_exit_2() -> None:
    """Exit 2 is reserved for environment/system failures, not bad input."""
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--repo", str(REPO_ROOT), "--stage", "nosuchstage"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stderr
    assert "unknown stage(s): nosuchstage" in proc.stderr
    assert proc.stdout == ""


# --- the live stage reads the answer, not the noise -----------------------


def _live_spec(harness: str) -> dict:
    data = yaml.safe_load((REPO_ROOT / "docs" / "harness-invocations.yaml").read_text("utf-8"))
    return data["harnesses"][harness]


def test_a_yes_no_probe_requires_exactly_yes() -> None:
    """A hedged or negative sentence mentioning 'yes' is not an affirmative."""
    pattern, described = smoke._expectation(_live_spec("claude"))
    assert described == "exactly 'yes'"
    assert pattern.search("Yes")
    assert pattern.search("yes.")
    assert not pattern.search("No, but the answer would be yes for CLAUDE.md")
    assert not pattern.search("warning: yes/no probes may be flaky")


def test_only_stdout_can_satisfy_a_live_expectation() -> None:
    """stderr is kept for diagnostics; it must never answer the probe."""
    assert smoke._answer_lines("") == []
    assert smoke._answer_lines("\n  Yes \n\n") == ["Yes"]
    pattern, _ = smoke._expectation(_live_spec("claude"))
    # The affirmative lives only on stderr — stdout says no.
    stdout, stderr = "no\n", "note: expected answer is yes\n"
    assert not any(pattern.search(line) for line in smoke._answer_lines(stdout))
    assert "yes" in stderr  # present, and deliberately not consulted


# --- a failed external tool can never look verified -----------------------


def test_steward_exiting_nonzero_with_empty_findings_json_is_a_failure(
    on_path: Path, clone: Path
) -> None:
    """Success-shaped JSON must not launder a failed run into a PASS."""
    fake_tool(on_path, "steward", "[]", "boom", 1)
    result = smoke.check_steward_doctor(clone, 30)
    assert result.status == "FAIL", result.detail
    assert "exited 1" in result.detail


def test_steward_exiting_zero_with_empty_findings_json_passes(on_path: Path, clone: Path) -> None:
    """The honest success path is unchanged."""
    fake_tool(on_path, "steward", "[]", "", 0)
    result = smoke.check_steward_doctor(clone, 30)
    assert result.status == "PASS", result.detail


def test_steward_exiting_nonzero_with_no_output_skips_loudly(on_path: Path, clone: Path) -> None:
    """An unavailable tool is a SKIP — reported as not-verified, never a pass."""
    fake_tool(on_path, "steward", "", "steward: command failed", 1)
    result = smoke.check_steward_doctor(clone, 30)
    assert result.status == "SKIP", result.detail


def test_guild_exiting_nonzero_with_a_valid_plan_is_a_failure(on_path: Path, clone: Path) -> None:
    """A dry-run that exits nonzero did not succeed, whatever it printed."""
    payload = json.dumps(
        {
            "applied": False,
            "prompt_file": "CLAUDE.md",
            "plan": {"steps": ["write CLAUDE.md"]},
        }
    )
    fake_tool(on_path, "guild", payload, "guild: backend unavailable", 1)
    results = smoke.check_guild_create(clone, smoke.load_invocations(clone), 30)
    assert results, "expected one result per harness"
    assert all(r.status == "FAIL" for r in results), [r.detail for r in results]
    assert all("exited 1" in r.detail for r in results)


def test_guild_exiting_nonzero_with_no_output_skips_loudly(on_path: Path, clone: Path) -> None:
    fake_tool(on_path, "guild", "", "guild: not installed", 127)
    results = smoke.check_guild_create(clone, smoke.load_invocations(clone), 30)
    assert all(r.status == "SKIP" for r in results), [r.detail for r in results]
