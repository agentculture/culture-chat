"""Markdown catalog for ``culture-chat explain <path>``.

Each entry is verbatim markdown. Keys are command-path tuples. The empty tuple
and ``("culture-chat",)`` both resolve to the root entry.

Keep bodies self-contained: an agent reading one entry should get enough
context without chaining reads.
"""

from __future__ import annotations

_ROOT = """\
# culture-chat

A clonable template for AgentCulture mesh agents. It carries an agent-first CLI
(cited from the teken `python-cli` reference), a mesh identity (`culture.yaml` +
`CLAUDE.md`), the canonical guildmaster skill kit under `.claude/skills/`, and a
buildable/deployable package baseline. Clone it, rename the package, edit
`culture.yaml`, and you have a new agent.

## Verbs

- `culture-chat whoami` — identity probe from `culture.yaml`.
- `culture-chat learn` — structured self-teaching prompt.
- `culture-chat explain <path>` — markdown docs for any noun/verb.
- `culture-chat overview` — descriptive snapshot of the agent.
- `culture-chat doctor` — check the agent-identity invariants.
- `culture-chat cli overview` — describe the CLI surface.

## Exit-code policy

- `0` success
- `1` user-input error
- `2` environment / setup error
- `3+` reserved

## See also

- `culture-chat explain whoami`
- `culture-chat explain doctor`
"""

_WHOAMI = """\
# culture-chat whoami

Reports the agent's identity from `culture.yaml`: nick (`suffix`), backend,
served model, and the package version. Read-only.

## Usage

    culture-chat whoami
    culture-chat whoami --json
"""

_LEARN = """\
# culture-chat learn

Prints a structured self-teaching prompt covering purpose, command map,
exit-code policy, `--json` support, and the `explain` pointer.

## Usage

    culture-chat learn
    culture-chat learn --json
"""

_EXPLAIN = """\
# culture-chat explain <path>

Prints markdown documentation for any noun/verb path. Unlike `--help` (terse,
positional), `explain` is global and addressable by path.

## Usage

    culture-chat explain culture-chat
    culture-chat explain whoami
    culture-chat explain --json <path>
"""

_OVERVIEW = """\
# culture-chat overview

Read-only descriptive snapshot of the agent: identity (from `culture.yaml`), the
verb surface, and the sibling-pattern artifacts the template carries. Accepts an
ignored `target` so a stray path never hard-fails.

## Usage

    culture-chat overview
    culture-chat overview --json
"""

_DOCTOR = """\
# culture-chat doctor

Checks the agent-identity invariants `steward doctor` verifies:
prompt-file-present and backend-consistency (`claude` → `CLAUDE.md`), plus a
skills-present check. Exits 1 when unhealthy.

prompt-file-present requires the *resident* prompt the declared backend
actually reads. Other harness prompt files recognized under the same backend
name (`AGENTS.override.md`, `.pi/SYSTEM.md`, `QWEN.md`) belong to
interactively available harnesses the mesh daemon never loads; they are
reported by the informational harness-prompts check and never substituted.

## Usage

    culture-chat doctor
    culture-chat doctor --json
"""

_CLI = """\
# culture-chat cli

Noun group for CLI-surface introspection. `cli overview` describes the CLI
itself (distinct from the global `overview`, which describes the agent).

## Usage

    culture-chat cli overview
    culture-chat cli overview --json
"""


ENTRIES: dict[tuple[str, ...], str] = {
    (): _ROOT,
    ("culture-chat",): _ROOT,
    ("whoami",): _WHOAMI,
    ("learn",): _LEARN,
    ("explain",): _EXPLAIN,
    ("overview",): _OVERVIEW,
    ("doctor",): _DOCTOR,
    ("cli",): _CLI,
    ("cli", "overview"): _CLI,
}
