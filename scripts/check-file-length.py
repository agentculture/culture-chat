#!/usr/bin/env python3
"""Fail when a tracked source file grows past the line cap.

Every tracked Python file in this repo — the package, ``scripts/`` and
``tests/`` alike — must stay at or under ``MAX_LINES`` lines. Long files are
where review attention runs out; the cap forces a split into focused modules
before that happens, rather than after.

Excluded:

* ``.claude/skills/**`` — the guildmaster skill kit is cited verbatim and must
  never be edited here, so it cannot be held to this repo's cap (re-sync from
  upstream instead; see ``docs/skill-sources.md``).

Usage:
    check-file-length.py                 # check all tracked files (git ls-files)
    check-file-length.py path [path...]  # check specific files
    check-file-length.py --max N         # override the cap (default 400)

Output contract (the repo's): a one-line result on stdout; each offending file
on stderr as ``path: N lines (max M)``. Exit 0 when every file is within the
cap; 1 when any file exceeds it or on bad input (an unknown flag, a ``--max``
that is not a positive integer, or a path outside the repo); 2 only when
``git ls-files`` cannot run — exit 2 is reserved for environment failures.
Explicit paths that are not checked (not ``.py``, or excluded) are named on
stderr rather than silently counted as passing.
"""

from __future__ import annotations

import argparse
import subprocess  # nosec B404 - fixed git invocation only
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The cap. One place to change it.
MAX_LINES = 400

#: Which tracked files count as source code held to the cap.
CHECKED_SUFFIXES = (".py",)

#: Path prefixes (repo-relative, POSIX) never checked — see the docstring.
EXCLUDED_PREFIXES = (".claude/skills/",)


def is_checked(rel: str) -> bool:
    """Whether a repo-relative path is held to the cap."""
    return rel.endswith(CHECKED_SUFFIXES) and not rel.startswith(EXCLUDED_PREFIXES)


def tracked_files(repo: Path) -> list[str]:
    """Repo-relative paths of every tracked file, via ``git ls-files``."""
    proc = subprocess.run(  # nosec B603,B607 - fixed git invocation
        ["git", "ls-files", "-z"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    return [p for p in proc.stdout.decode("utf-8").split("\0") if p]


def count_lines(path: Path) -> int:
    """Physical line count: every line, terminated or not.

    Equals ``wc -l`` for a file ending in a newline. For a file whose last line
    has no trailing newline it is ``wc -l`` + 1, because ``wc -l`` counts
    newline characters and so misses that last line (``"a\\nb"`` → 2 here,
    1 from ``wc -l``). Deliberate: an unterminated line is still a line.
    """
    data = path.read_bytes()
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def find_oversized(repo: Path, paths: list[str], max_lines: int) -> list[tuple[str, int]]:
    """``(path, lines)`` for each checked file over ``max_lines``, in input order."""
    oversized: list[tuple[str, int]] = []
    for rel in paths:
        if not is_checked(rel):
            continue
        path = repo / rel
        if not path.is_file():  # deleted in the worktree but still tracked
            continue
        lines = count_lines(path)
        if lines > max_lines:
            oversized.append((rel, lines))
    return oversized


class UsageError(Exception):
    """Bad user input — reported on stderr and mapped to exit 1."""


class _Parser(argparse.ArgumentParser):
    """An ArgumentParser whose usage errors exit 1, not argparse's default 2.

    This repo's CLI contract reserves exit 2 for environment/system failures;
    a bad flag is user input. Same reasoning as ``scripts/harness-smoke.py``.
    """

    def error(self, message: str) -> None:  # type: ignore[override]
        raise UsageError(message)


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"{value!r} must be at least 1")
    return number


def _repo_relative(raw: str, repo: Path) -> str:
    try:
        return Path(raw).resolve().relative_to(repo).as_posix()
    except ValueError:
        raise UsageError(f"{raw} is outside the repo ({repo})") from None


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _main(argv: list[str] | None) -> int:
    parser = _Parser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="Files to check (default: all tracked files).")
    parser.add_argument(
        "--max",
        type=_positive_int,
        default=MAX_LINES,
        help=f"Line cap, a positive integer (default {MAX_LINES}).",
    )
    parser.add_argument("--repo", default=str(REPO_ROOT), help="Repo root.")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if args.paths:
        paths = [_repo_relative(p, repo) for p in args.paths]
        for rel in paths:
            if not is_checked(rel):
                print(f"{rel}: not checked (not a .py file, or excluded)", file=sys.stderr)
    else:
        try:
            paths = tracked_files(repo)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"error: could not list tracked files: {exc}", file=sys.stderr)
            return 2

    checked = [p for p in paths if is_checked(p)]
    oversized = find_oversized(repo, checked, args.max)
    for rel, lines in oversized:
        print(f"{rel}: {lines} lines (max {args.max})", file=sys.stderr)

    if oversized:
        print(f"file length: {len(oversized)} of {len(checked)} file(s) over {args.max} lines")
        return 1
    print(f"file length: all {len(checked)} file(s) within {args.max} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
