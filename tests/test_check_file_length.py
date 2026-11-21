"""``scripts/check-file-length.py`` must catch an oversized file — and only that."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check-file-length.py"


def _load():
    """Import scripts/check-file-length.py by path (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("check_file_length", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cfl = _load()


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


def _write_lines(path: Path, n: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n" * n, encoding="utf-8")
    return path


def test_the_cap_is_400() -> None:
    assert cfl.MAX_LINES == 400


def test_the_real_repo_is_within_the_cap() -> None:
    """The gate CI runs: every tracked source file is at or under 400 lines."""
    proc = _run()
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert "within 400 lines" in proc.stdout


def test_a_file_at_the_cap_passes_and_one_over_fails(tmp_path: Path) -> None:
    _write_lines(tmp_path / "at.py", 400)
    _write_lines(tmp_path / "over.py", 401)
    found = cfl.find_oversized(tmp_path, ["at.py", "over.py"], 400)
    assert found == [("over.py", 401)]


def test_an_oversized_file_fails_with_its_name_on_stderr(tmp_path: Path) -> None:
    _write_lines(tmp_path / "big.py", 401)
    proc = _run("--repo", str(tmp_path), str(tmp_path / "big.py"))
    assert proc.returncode == 1
    assert "big.py: 401 lines (max 400)" in proc.stderr
    assert "big.py" not in proc.stdout


def test_max_overrides_the_cap(tmp_path: Path) -> None:
    _write_lines(tmp_path / "mid.py", 50)
    proc = _run("--repo", str(tmp_path), "--max", "40", str(tmp_path / "mid.py"))
    assert proc.returncode == 1
    assert "mid.py: 50 lines (max 40)" in proc.stderr


def test_an_unterminated_last_line_counts(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a\nb", encoding="utf-8")
    (tmp_path / "b.py").write_text("a\nb\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("", encoding="utf-8")
    assert cfl.count_lines(tmp_path / "a.py") == 2
    assert cfl.count_lines(tmp_path / "b.py") == 2
    assert cfl.count_lines(tmp_path / "c.py") == 0


def test_vendored_skills_and_non_python_files_are_not_checked() -> None:
    assert cfl.is_checked("culture_chat/cli/__init__.py")
    assert cfl.is_checked("scripts/harness-smoke.py")
    assert cfl.is_checked("tests/test_cli.py")
    assert not cfl.is_checked(".claude/skills/version-bump/scripts/bump.py")
    assert not cfl.is_checked("CHANGELOG.md")
    assert not cfl.is_checked("uv.lock")


# --- the exit-code contract: 1 for user error, 2 only for the environment ---


def test_a_non_integer_max_is_a_user_error_exit_1_not_2() -> None:
    proc = _run("--max", "abc")
    assert proc.returncode == 1, proc.stderr
    assert "error:" in proc.stderr
    assert "is not an integer" in proc.stderr
    assert proc.stdout == ""


def test_a_max_below_one_is_rejected(tmp_path: Path) -> None:
    for bad in ("0", "-5"):
        proc = _run("--repo", str(tmp_path), "--max", bad)
        assert proc.returncode == 1, (bad, proc.stderr)
        assert "must be at least 1" in proc.stderr


def test_an_unknown_flag_is_a_user_error_exit_1() -> None:
    proc = _run("--no-such-flag")
    assert proc.returncode == 1, proc.stderr
    assert "error:" in proc.stderr


def test_a_path_outside_the_repo_is_a_clean_user_error(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = _write_lines(tmp_path / "elsewhere.py", 3)
    proc = _run("--repo", str(repo), str(outside))
    assert proc.returncode == 1, proc.stderr
    assert "is outside the repo" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_a_failed_git_ls_files_is_an_environment_error_exit_2(tmp_path: Path) -> None:
    """Not a git repo: the tracked-file list cannot be read — exit 2."""
    proc = _run("--repo", str(tmp_path))
    assert proc.returncode == 2, proc.stderr
    assert "could not list tracked files" in proc.stderr


def test_an_explicit_unchecked_path_is_named_not_silently_passed(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("# hi\n", encoding="utf-8")
    proc = _run("--repo", str(tmp_path), str(tmp_path / "notes.md"))
    assert proc.returncode == 0
    assert "notes.md: not checked" in proc.stderr


# --- the gate is actually wired into CI ---


def test_the_ci_lint_job_runs_the_gate() -> None:
    """Removing the step from tests.yml must not silently disable the cap."""
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    )
    runs = [step.get("run", "") for step in workflow["jobs"]["lint"]["steps"]]
    assert any("scripts/check-file-length.py" in run for run in runs), runs
