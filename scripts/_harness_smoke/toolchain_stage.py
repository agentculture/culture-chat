"""Stage ``toolchain`` — ``steward doctor`` plus four ``guild create`` dry-runs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404 - runs fixed, repo-local tool invocations
from pathlib import Path
from typing import Any

from _harness_smoke.common import (
    FAIL,
    GUILD_HARNESS,
    HARNESSES,
    INVOCATIONS_REL,
    PASS,
    SKIP,
    STEWARD_WAIVED_PORTABILITY_PATHS,
    WAIVED,
    Result,
)


def _tool_argv(binary: str, dist: str) -> list[str] | None:
    """Prefer an installed CLI; otherwise let uvx fetch the published dist."""
    if shutil.which(binary):
        return [binary]
    if shutil.which("uvx"):
        return ["uvx", "--from", dist, binary]
    if shutil.which("uv"):
        return ["uv", "tool", "run", "--from", dist, binary]
    return None


def _run(argv: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 - argv is assembled from fixed literals above
        argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )


_FINDING_PATH = re.compile(r"(?:^|\s)([\w./-]+\.(?:md|yaml|yml|toml|json)):\d+")


def check_steward_doctor(repo: Path, timeout: int) -> Result:
    base = _tool_argv("steward", "steward-cli")
    if base is None:
        return Result(
            "toolchain",
            "steward-doctor",
            SKIP,
            "neither `steward` nor `uvx`/`uv` is available — `steward doctor "
            "--scope self` was NOT run",
        )
    argv = base + ["doctor", "--scope", "self", str(repo), "--json", "--no-write-reports"]
    try:
        proc = _run(argv, repo, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Result("toolchain", "steward-doctor", SKIP, f"could not run steward doctor: {exc}")
    if not proc.stdout.strip():
        if "PosixPath' and 'list'" in proc.stderr:
            return Result(
                "toolchain",
                "steward-doctor",
                SKIP,
                "the resolved steward predates list-valued `prompt` entries in "
                "backend-fingerprints.yaml (it reads the registry of whatever "
                "checkout it is run from, i.e. this one) and crashed — check NOT "
                "run. It needs a steward release carrying `_agents._prompt_list`; "
                "re-run once one is published.",
            )
        return Result(
            "toolchain",
            "steward-doctor",
            SKIP,
            f"steward doctor unavailable (exit {proc.returncode}): {proc.stderr.strip()[:300]}",
        )
    try:
        findings = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return Result(
            "toolchain",
            "steward-doctor",
            FAIL,
            f"steward doctor emitted unparseable JSON: {proc.stdout.strip()[:300]}",
        )

    # A nonzero exit is expected when steward reports findings, and those are
    # judged below. A nonzero exit with an *empty* findings array is a failed
    # run wearing success-shaped JSON — it must never reach the PASS branch.
    if proc.returncode != 0 and not findings:
        return Result(
            "toolchain",
            "steward-doctor",
            FAIL,
            f"steward doctor exited {proc.returncode} but reported no findings; "
            f"the run failed rather than passing: {proc.stderr.strip()[:300]}",
        )

    unexpected: list[str] = []
    waived: list[str] = []
    for finding in findings:
        check = str(finding.get("check", "?"))
        message = str(finding.get("message", ""))
        paths = set(_FINDING_PATH.findall(message))
        if check == "portability" and paths and paths <= STEWARD_WAIVED_PORTABILITY_PATHS:
            waived.append(f"{check} ({', '.join(sorted(paths))})")
        else:
            unexpected.append(f"{check}: {message.strip()[:300]}")

    if unexpected:
        return Result("toolchain", "steward-doctor", FAIL, " | ".join(unexpected))
    if waived:
        return Result(
            "toolchain",
            "steward-doctor",
            WAIVED,
            "0 unexpected findings while carrying all four harness prompt files; "
            f"{len(waived)} known-accepted finding(s) waived: {'; '.join(waived)} "
            "(pre-existing, byte-verbatim vendored skills — upstream's to fix)",
        )
    return Result(
        "toolchain",
        "steward-doctor",
        PASS,
        "0 findings while carrying all four harness prompt files",
    )


def check_guild_create(repo: Path, harnesses: dict[str, Any], timeout: int) -> list[Result]:
    base = _tool_argv("guild", "guild-cli")
    if base is None:
        return [
            Result(
                "toolchain",
                "guild-create",
                SKIP,
                "neither `guild` nor `uvx`/`uv` is available — the four `guild "
                "create` dry-runs were NOT run",
            )
        ]

    results: list[Result] = []
    for name in HARNESSES:
        guild_name, expected = GUILD_HARNESS[name]
        resolves = [str(p) for p in harnesses[name].get("resolves") or []]
        if expected not in resolves:
            results.append(
                Result(
                    "toolchain",
                    f"guild-create/{name}",
                    FAIL,
                    f"{expected} is not among this harness's resolves {resolves} in "
                    f"{INVOCATIONS_REL}",
                )
            )
            continue

        argv = base + [
            "create",
            "--agent",
            "agentculture/harness-smoke-probe",
            "--desc",
            "dry-run probe for the culture-chat harness smoke check",
            "--harness",
            guild_name,
            "--json",
        ]
        try:
            proc = _run(argv, repo, timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append(
                Result("toolchain", f"guild-create/{name}", SKIP, f"could not run guild: {exc}")
            )
            continue
        if proc.returncode != 0:
            # A dry-run that exits nonzero did not succeed, whatever it wrote
            # to stdout: with no payload the tool is unavailable (SKIP, never
            # a pass), and with a payload it ran and failed (FAIL). Neither
            # may fall through to the plan-shape checks below.
            status = SKIP if not proc.stdout.strip() else FAIL
            detail = (
                f"guild create unavailable (exit {proc.returncode})"
                if status == SKIP
                else f"guild create exited {proc.returncode} for --harness {guild_name}"
            )
            results.append(
                Result(
                    "toolchain",
                    f"guild-create/{name}",
                    status,
                    f"{detail}: {proc.stderr.strip()[:300]}",
                )
            )
            continue
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            results.append(
                Result(
                    "toolchain",
                    f"guild-create/{name}",
                    FAIL,
                    f"guild create --json emitted unparseable output: {proc.stdout[:300]}",
                )
            )
            continue

        if payload.get("applied"):
            results.append(
                Result(
                    "toolchain",
                    f"guild-create/{name}",
                    FAIL,
                    "guild create reported applied=true for a dry-run",
                )
            )
            continue
        named = payload.get("prompt_file")
        steps = " ".join(str(s) for s in (payload.get("plan") or {}).get("steps") or [])
        if named != expected:
            results.append(
                Result(
                    "toolchain",
                    f"guild-create/{name}",
                    FAIL,
                    f"--harness {guild_name} named prompt_file {named!r}, expected {expected!r}",
                )
            )
        elif expected not in steps:
            results.append(
                Result(
                    "toolchain",
                    f"guild-create/{name}",
                    FAIL,
                    f"--harness {guild_name} declares prompt_file {expected!r} but no "
                    f"planned step writes it: {steps[:300]}",
                )
            )
        else:
            results.append(
                Result(
                    "toolchain",
                    f"guild-create/{name}",
                    PASS,
                    f"--harness {guild_name} names and writes {expected}",
                )
            )
    return results


def stage_toolchain(repo: Path, harnesses: dict[str, Any], timeout: int) -> list[Result]:
    return [check_steward_doctor(repo, timeout)] + check_guild_create(repo, harnesses, timeout)
