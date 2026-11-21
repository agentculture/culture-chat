# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`culture-chat` is **the communication product of AgentCulture**: the
human-and-agent chat surface for the mesh. It replaces
[`agentirc`](https://github.com/agentculture/agentirc) (the custom IRCd) and
absorbs [`irc-lens`](https://github.com/agentculture/irc-lens) (console, web UI,
CLI/MCP inspection). Its scope and boundaries are set by the cross-repo design
issue
[culture-agents#2](https://github.com/agentculture/culture-agents/issues/2) —
read it before designing anything non-trivial here.

**Today the repo is still the scaffold** cloned from
[`culture-agent-template`](https://github.com/agentculture/culture-agent-template)
(0.10.0): an agent-first CLI with identity/introspection verbs only, the mesh
identity, the vendored skill kit, and the CI/deploy baseline. No chat server,
storage, or UI exists yet. Keep that distinction honest — see
[Roadmap](#roadmap-planned).

## Product boundaries (from culture-agents#2)

| culture-chat owns | culture-chat must not own |
|-------------------|---------------------------|
| Rooms, participants, presence, threads, messaging | Agent cognitive runs — dispatch, supervision, steer/cancel (that is **culture-agents**) |
| Durable history, reconnect and replay | Declarative workflows, triggers, scheduling (that is **culture-rules**) |
| Bot/event surfaces, identities, federation and trust boundaries where required | Sensing, realtime voice, turn-taking (that is **embodiment**) |
| Console, web UI, CLI/MCP inspection and browser automation (from irc-lens) | Workspace / operator composition (that is **culture**) |

Non-negotiables that shape every design choice here:

- **Agents must be able to exist and run without joining chat.** Chat is an
  optional transport to culture-agents, never a dependency of it. A dead chat
  server must not kill an agent run.
- **Chat messages are untrusted data.** Quoting imperative text in a message
  must never turn it into a control command; any side effect is reauthorized
  by its owning service.
- **AI-SDK chat hooks are not a multi-party communication server** — durable
  rooms/threads/history, replay, presence and federation are this repo's job.
- **Cutover must not silently break mesh participants**: keep legacy
  IRC-facing endpoints alive or ship a documented protocol/data migration.
  agentirc and irc-lens are not archived until replacements pass compatibility,
  recovery and data-migration tests (delivery gates D3 and D6 in the issue).

## Commands

```bash
uv sync                                              # install (dev group included)
uv run pytest -n auto                                # full suite, parallel
uv run pytest tests/test_cli.py::test_version_flag -v   # a single test
uv run pytest -n auto --cov=culture_chat --cov-report=term   # with coverage (fail_under=60)

# lint — the same set CI's `lint` job runs
uv run black --check culture_chat tests
uv run isort --check-only culture_chat tests
uv run flake8 culture_chat tests
uv run bandit -c pyproject.toml -r culture_chat
markdownlint-cli2 "**/*.md" "#node_modules" "#.local" "#.claude/skills" "#.teken"
python3 scripts/scan-secrets.py                      # committed secrets / non-localhost endpoints
python3 scripts/check-file-length.py                 # 400-line cap per tracked .py file
uv run teken cli doctor . --strict                   # agent-first rubric gate

# harness + identity checks
uv run python scripts/harness-smoke.py --stage config   # all four harness configs (offline)
uv run culture-chat doctor                           # prompt-file-present / backend-consistency
```

`culture.yaml`'s `gate` section mirrors the setup/test commands as argv lists
for tooling (e.g. a PR fixer) — keep it in sync if those commands change.

## Architecture (as it exists today)

- **`culture_chat/cli/`** — the agent-first CLI, cited (cite-don't-import) from
  teken's `python-cli` reference; the runtime package has **no third-party
  dependencies** (`teken` is dev-only). `cli/__init__.py` builds the argparse
  tree, calling each verb module's `register(sub)` from `cli/_commands/`
  explicitly (a new verb or noun group must be wired in there);
  `_output.py` / `_errors.py` hold the output contract. Contract:
  every command supports `--json`; results to stdout, errors/diagnostics to
  stderr (never mixed); exit `0` success, `1` user error, `2` environment
  error, `3+` reserved. New chat-facing verbs must follow the same contract —
  `teken cli doctor . --strict` enforces it in CI.
- **`culture_chat/explain/catalog.py`** — markdown bodies for `explain <path>`;
  every new noun/verb needs an entry so `explain` (and the agent-first rubric)
  can describe it.
- **Identity** — `culture.yaml` declares `suffix: culture-chat`,
  `backend: claude`, which makes this file the **mesh-resident prompt**.
  `whoami`/`doctor` read it at runtime; `doctor` mirrors `steward doctor`'s
  invariants. Its `_PROMPT_FILE` map must agree with the vendored
  `.claude/skills/agent-config/data/backend-fingerprints.yaml` and
  `docs/harness-invocations.yaml` (`tests/test_harness_registries.py`).
- **Harness smoke** — `scripts/harness-smoke.py` is the entry point; its stages
  live in `scripts/_harness_smoke/` and run the invocations in
  `docs/harness-invocations.yaml` (the single source of truth — edit there,
  never re-type them).

## Prompt files by harness

Each harness reads its own file; one shared base sits under two of them:

| Harness | Reads |
|---------|-------|
| Claude Code | `CLAUDE.md` (this file) — does **not** read `AGENTS.md` |
| colleague | `AGENTS.md` → `AGENTS.colleague.md` (its cascade) |
| Qwen Code | `QWEN.md` + `AGENTS.md` |
| Codex / other AGENTS.md tools | `AGENTS.md` |
| Pi / associate | `AGENTS.override.md` (replaces `AGENTS.md` here) + `.pi/SYSTEM.md` |

`AGENTS.md` is the **harness-neutral** base (what culture-chat is, boundaries,
commands, conventions); the harness files add only what is specific to that
harness. When you change a convention or the product scope, update `CLAUDE.md`
**and** `AGENTS.md` (and `AGENTS.override.md` if Pi's read-only context is
affected) in the same PR. The smoke check fails if `AGENTS.md` goes missing.

Interactive harness ≠ mesh resident: any of the harnesses can be run in this
clone at any time; `culture.yaml`'s `backend` only picks which one the Culture
daemon starts. See `docs/harness-selection.md` and
`docs/automation-contract.md`.

## Conventions

- **Every PR bumps the version** — even docs/config/CI. Use the `version-bump`
  skill (updates `pyproject.toml` + `CHANGELOG.md`); CI's `version-check` job
  blocks merge otherwise.
- **PRs go through the `cicd` skill** (`devex pr` + SonarCloud gating). Its
  scripts resolve the nick from `culture.yaml` and sign posts as
  `- culture-chat (Claude)` — don't sign bodies by hand.
- **File length**: every tracked Python file (package, `scripts/`, `tests/`)
  stays at or under **400 lines**, enforced in CI's `lint` job by
  `scripts/check-file-length.py` (cap = `MAX_LINES`; `.claude/skills/` exempt).
  Split into focused modules before crossing it — `scripts/_harness_smoke/`
  is the worked example.
- **Style**: black + isort (profile black), line length 100; flake8 ignores
  E203/W503.
- **Vendored skills** under `.claude/skills/` are cited verbatim from
  guildmaster (some originate in devague / colleague) — never edit or reformat
  them; re-sync instead (`docs/skill-sources.md`). `.qwen/skills`,
  `.colleague/skills`, `.pi/skills` are symlinks to that one tree. Tooling:
  `devex` (cicd) and `agtag` (communicate) on PATH; `colleague` optional.
- **Reach for `ask-colleague` reflexively** — `review` before presenting a
  non-trivial committed diff, `explore` for a fresh read of an unfamiliar area.
  Both are read-only; `write --apply` / `write --pr` need the user's go-ahead.
  Its output is a second opinion to verify, never authority.
- **Cross-repo work** (culture-agents, culture-rules, agentirc, irc-lens,
  embodiment) goes through the `communicate` skill — file a brief on the
  sibling repo rather than editing it from here.
- **Deploy**: push to `main` publishes to PyPI via Trusted Publishing
  (`.github/workflows/publish.yml`); PRs do a TestPyPI dry-run.
- Keep this file grounded in what's on disk; anything not built yet goes under
  the Roadmap heading, marked planned.

## Worktrees

Worktrees you create live in `../.worktrees.culture-chat/<name>/`, never a
shared `../worktrees/`:

```bash
git worktree add ../.worktrees.culture-chat/<name> -b <scoped-branch>
```

Scope branch prefixes to the work (`chat/rooms`, not `agent/t2`). The vendored
`assign-to-workforce` skill's example uses `../worktrees/` and `agent/<id>` —
override both. `ask-colleague`'s throwaway worktrees under `${TMPDIR:-/tmp}`
are self-cleaning and exempt. Remove finished trees with
`git worktree remove <path>`; never `rm -rf` one you didn't create.

## Memory

Recall before, remember after: run `/recall` for the area you're about to touch
before non-trivial work, and `/remember` non-obvious decisions, constraints and
gotchas as they surface. Records default to the in-repo, committed public store
`.eidetic/memory/` (shared with the colleague backend and mesh peers);
`--visibility private` keeps one in `$HOME/.eidetic/memory`. Don't store what
the repo or git history already records.

## Roadmap (planned)

Not built yet — tracked in culture-agents#2 (gate **D3 — communication split**,
then **D6 — migration and deprecation**):

- Communication server: rooms/threads/presence, stored messages, replay,
  federation and bot/event APIs; agents attach optionally.
- Inventory of agentirc protocol/federation/transport behaviors to preserve vs
  sunset (decision 4 in the issue), plus history/identity/bot-client migration.
- irc-lens consolidation: console, web UI, CLI/MCP inspection, permissions.
- Test: disconnecting culture-chat mid-run leaves culture-agents runs intact.
