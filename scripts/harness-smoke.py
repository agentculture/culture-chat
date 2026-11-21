#!/usr/bin/env python3
"""Per-harness smoke check — prove all four harness configs are correct.

All four harnesses (Claude Code, Pi/associate, colleague, Qwen Code) are live
for interactive use over the *same* clone at all times, independent of what
``culture.yaml`` declares as the mesh resident. So all four configs must be
correct at all times, and nothing else in this repo checks more than the one
config the declared backend uses. That is what this script exists for: it
exercises **all four**, and fails when **any one** of them is broken.

The invocations come from ``docs/harness-invocations.yaml`` — the single source
of truth — and are run ``binary`` + ``args`` **verbatim**, never re-typed here.

Three stages, selected with ``--stage``:

``config`` (offline, always runnable — the load-bearing stage)
    Per harness: the config file(s) that harness resolves are present and
    non-empty, the harness's *skills discovery* wiring points at the one
    canonical ``.claude/skills`` tree, and every resolved prompt path is
    registered in the vendored backend-fingerprint registry. Plus one global
    check that ``AGENTS.md`` — the shared base colleague and Qwen Code cascade
    from — is present and non-empty.

``live`` (needs the four harness binaries on PATH)
    Runs each harness's documented invocation verbatim in the repo and asserts
    the answer proves that harness resolved this clone's config. Not available
    on a stock CI runner — it reports **SKIPPED**, never a pass.

``toolchain`` (needs ``steward`` and ``guild``, or ``uvx`` to fetch them)
    - ``steward doctor --scope self`` over this repo, which must report no
      findings beyond the known-accepted, pre-existing portability finding in
      the vendored ``recall``/``remember`` skills (reported as WAIVED, loudly,
      never silently folded into a pass).
    - ``guild create --harness X --json`` dry-runs for all four harnesses,
      checking each names the prompt file it says it writes.

Exit status is 0 unless some check FAILED, 1 on a failure or a bad argument.
Exit 2 is reserved for environment/system failures and is never used for user
input. A skipped check is never counted as a pass: it is printed as SKIP,
listed again under "NOT VERIFIED", and ``--require <stage>`` turns a skip in
that stage into a failure.

Output contract (the repo's, shared with the CLI): **results on stdout**
(the status table, the counts summary, or pure JSON under ``--json``);
**diagnostics on stderr** (the FAILED / NOT VERIFIED / WAIVED expansions and
the ``--require`` error). Redirecting stdout therefore captures outcomes
without diagnostics mixed in, and ``--json`` stdout stays parseable even when
checks fail.

Usage:
    harness-smoke.py [--repo DIR] [--stage config|live|toolchain|all]
                     [--require STAGE] [--json] [--timeout SECONDS]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# scripts/ is not a package. Put it on sys.path so the stage modules in
# scripts/_harness_smoke/ import the same way whether this file is run as a
# script or loaded by path (as the tests do). Appended, not prepended: when the
# tests load this file, scripts/ stays on sys.path for the whole session, and
# appending guarantees nothing in scripts/ can ever shadow the stdlib or an
# installed package. `_harness_smoke` is a unique name, so it still resolves.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(_SCRIPTS_DIR))

from _harness_smoke.common import (  # noqa: E402
    CANONICAL_SKILLS_REL,
    FAIL,
    FINGERPRINTS_REL,
    GUILD_HARNESS,
    HARNESS_BACKEND,
    HARNESSES,
    INVOCATIONS_REL,
    PASS,
    SKIP,
    STEWARD_WAIVED_PORTABILITY_PATHS,
    WAIVED,
    Result,
    load_invocations,
    registry_prompts_by_backend,
)
from _harness_smoke.config_stage import SKILLS_WIRING, stage_config  # noqa: E402
from _harness_smoke.live_stage import _answer_lines, _expectation, stage_live  # noqa: E402
from _harness_smoke.toolchain_stage import (  # noqa: E402
    check_guild_create,
    check_steward_doctor,
    stage_toolchain,
)

#: Re-exported so callers (and tests) can keep treating this script as the one
#: entry point, regardless of which stage module a name now lives in.
__all__ = [
    "CANONICAL_SKILLS_REL",
    "FAIL",
    "FINGERPRINTS_REL",
    "GUILD_HARNESS",
    "HARNESS_BACKEND",
    "HARNESSES",
    "INVOCATIONS_REL",
    "PASS",
    "SKILLS_WIRING",
    "SKIP",
    "STAGES",
    "STEWARD_WAIVED_PORTABILITY_PATHS",
    "WAIVED",
    "Result",
    "_answer_lines",
    "_expectation",
    "check_guild_create",
    "check_steward_doctor",
    "load_invocations",
    "main",
    "registry_prompts_by_backend",
    "report",
    "run",
    "stage_config",
    "stage_live",
    "stage_toolchain",
]

REPO_ROOT_DEFAULT = _SCRIPTS_DIR.parent

# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

STAGES = ("config", "live", "toolchain")


def run(repo: Path, stages: list[str], timeout: int) -> list[Result]:
    harnesses = load_invocations(repo)
    results: list[Result] = []
    if "config" in stages:
        results.extend(stage_config(repo, harnesses))
    if "live" in stages:
        results.extend(stage_live(repo, harnesses, timeout))
    if "toolchain" in stages:
        results.extend(stage_toolchain(repo, harnesses, timeout))
    return results


def report(results: list[Result], repo: Path, required: set[str]) -> int:
    """Print the human-readable report; return the process exit code.

    Results go to **stdout**, diagnostics to **stderr** — the repo's CLI
    output contract. The per-check status table and the counts summary are the
    result; the NOT-VERIFIED / WAIVED expansions and the --require error are
    explanations of what went wrong, so redirecting stdout to a file leaves a
    clean record of outcomes and still shows the operator why.
    """
    lines = [f"harness smoke check — repo: {repo}"]
    for res in results:
        lines.append(f"[{res.status:<6}] {res.label:<28} {res.detail}")

    failed = [r for r in results if r.status == FAIL]
    skipped = [r for r in results if r.status == SKIP]
    waived = [r for r in results if r.status == WAIVED]
    passed = [r for r in results if r.status == PASS]

    lines.append("")
    lines.append(
        f"summary: {len(passed)} passed, {len(waived)} waived, "
        f"{len(skipped)} skipped, {len(failed)} failed"
    )

    diagnostics: list[str] = []
    if failed:
        diagnostics.append("FAILED:")
        for res in failed:
            diagnostics.append(f"  - {res.label}: {res.detail}")
    if skipped:
        diagnostics.append("NOT VERIFIED (a skipped check is not a pass):")
        for res in skipped:
            diagnostics.append(f"  - {res.label}: {res.detail}")
    if waived:
        diagnostics.append("WAIVED (known-accepted, reported every run):")
        for res in waived:
            diagnostics.append(f"  - {res.label}: {res.detail}")

    exit_code = 1 if failed else 0
    unmet = sorted({r.stage for r in skipped} & required)
    if unmet:
        diagnostics.append(f"ERROR: --require named stage(s) that skipped: {', '.join(unmet)}")
        exit_code = 1

    print("\n".join(lines))
    if diagnostics:
        print("\n".join(diagnostics), file=sys.stderr)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=str(REPO_ROOT_DEFAULT), help="Repo root to check.")
    parser.add_argument(
        "--stage",
        default="config",
        help="Comma-separated stages to run: config, live, toolchain, or all. Default: config.",
    )
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        help="Stage whose checks must not skip (repeatable). Turns a SKIP into a failure.",
    )
    parser.add_argument("--json", action="store_true", help="Emit results as JSON.")
    parser.add_argument("--timeout", type=int, default=600, help="Per-command timeout in seconds.")
    args = parser.parse_args(argv)

    requested = [s.strip() for s in args.stage.split(",") if s.strip()]
    stages = list(STAGES) if "all" in requested else requested
    unknown = sorted(set(stages) - set(STAGES))
    if unknown:
        # Deliberately NOT parser.error(), which exits 2. This repo's CLI
        # contract reserves 2 for environment/system failures; a bad --stage
        # value is user input, which is exit 1.
        print(
            f"error: unknown stage(s): {', '.join(unknown)}; "
            f"choose from {', '.join(STAGES)}, all",
            file=sys.stderr,
        )
        return 1

    repo = Path(args.repo).resolve()
    results = run(repo, stages, args.timeout)

    if args.json:
        failed = [r for r in results if r.status == FAIL]
        skipped_stages = {r.stage for r in results if r.status == SKIP}
        unmet = sorted(skipped_stages & set(args.require))
        print(
            json.dumps(
                {
                    "repo": str(repo),
                    "stages": stages,
                    "results": [r.as_dict() for r in results],
                    "failed": len(failed),
                    "unmet_requirements": unmet,
                },
                indent=2,
            )
        )
        return 1 if failed or unmet else 0

    return report(results, repo, set(args.require))


if __name__ == "__main__":
    sys.exit(main())
