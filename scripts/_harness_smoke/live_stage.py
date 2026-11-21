"""Stage ``live`` — run each harness's documented invocation verbatim."""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404 - runs fixed, repo-local tool invocations
from pathlib import Path
from typing import Any

from _harness_smoke.common import FAIL, HARNESSES, PASS, SKIP, Result


def _expectation(spec: dict[str, Any]) -> tuple[re.Pattern[str], str]:
    """Derive what the harness's own documented probe must answer.

    The three model probes are yes/no questions whose affirmative answer is
    only reachable from this clone's config; ``colleague agents list`` instead
    prints the file it resolved. Both expectations are derived from the YAML
    entry rather than hard-coded per harness.

    The yes/no probes ask for *exactly one word*, so the pattern is anchored
    to the whole (stripped) answer rather than merely searched for: a reply
    of "no, because ..." contains no bare ``yes``, but a diagnostic line or a
    hedged sentence easily could, and a substring search would read that as a
    pass.
    """
    args = " ".join(str(a) for a in spec.get("args") or [])
    if "yes or no" in args.lower():
        return re.compile(r"^yes[.!]?$", re.IGNORECASE), "exactly 'yes'"
    resolved = [Path(str(p)).name for p in spec.get("resolves") or []]
    pattern = "|".join(re.escape(n) for n in resolved) or r"(?!x)x"
    return re.compile(pattern), f"one of {', '.join(resolved)}"


def _answer_lines(stdout: str) -> list[str]:
    """Non-empty stdout lines, stripped — the harness's actual answer.

    Only stdout is matched against the expectation. stderr is kept for
    failure diagnostics but must never satisfy the assertion: a harness that
    exits 0 while answering "no" on stdout would otherwise pass whenever any
    warning on stderr happened to contain the expected word or filename.
    """
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def stage_live(repo: Path, harnesses: dict[str, Any], timeout: int) -> list[Result]:
    results: list[Result] = []
    for name in HARNESSES:
        spec = harnesses[name]
        binary = str(spec["binary"])
        argv = [binary] + [str(a) for a in spec.get("args") or []]

        if shutil.which(binary) is None:
            results.append(
                Result(
                    "live",
                    name,
                    SKIP,
                    f"{binary!r} is not on PATH — this harness's real invocation was "
                    "NOT run (stock CI runners ship none of the four agent CLIs)",
                )
            )
            continue

        before = _git_status(repo)
        try:
            proc = subprocess.run(  # nosec B603 - argv is read verbatim from the tracked YAML
                argv,
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            results.append(Result("live", name, FAIL, f"{binary} timed out after {timeout}s"))
            continue

        pattern, described = _expectation(spec)
        diagnostic = f"stdout={proc.stdout.strip()[:300]!r} stderr={proc.stderr.strip()[:300]!r}"
        answered = any(pattern.search(line) for line in _answer_lines(proc.stdout))
        if proc.returncode != 0:
            results.append(
                Result("live", name, FAIL, f"{binary} exited {proc.returncode}: {diagnostic}")
            )
        elif not answered:
            results.append(
                Result(
                    "live",
                    name,
                    FAIL,
                    f"{binary} did not answer on stdout with {described}: {diagnostic}",
                )
            )
        elif spec.get("read_only") and _git_status(repo) != before:
            results.append(
                Result("live", name, FAIL, f"{binary} is documented read_only but dirtied the tree")
            )
        else:
            results.append(
                Result("live", name, PASS, f"{' '.join(argv[:3])}… answered with {described}")
            )
    return results


def _git_status(repo: Path) -> str:
    try:
        proc = subprocess.run(  # nosec B603,B607 - fixed git invocation
            ["git", "status", "--porcelain"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return proc.stdout
