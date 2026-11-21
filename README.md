# culture-chat

The new chat app of Culture: the human-and-agent chat surface for the
AgentCulture mesh. Replaces agentirc.

## Where it fits

AgentCulture is consolidating around one product per concern
([culture-agents#2](https://github.com/agentculture/culture-agents/issues/2)):

| Repository | Concern |
|------------|---------|
| **culture-chat** (this repo) | Communication — rooms, participants, presence, threads, messaging, history, replay, bot/event surfaces, federation where required, and the human/agent UI |
| [culture-agents](https://github.com/agentculture/culture-agents) | The agent control plane — dispatch, runs, sessions, steer/cancel, supervision |
| [culture-rules](https://github.com/agentculture/culture-rules) | Workflows — rules, triggers, typed steps, scheduling |
| [culture](https://github.com/agentculture/culture) | Workspace and operator CLI composing the above |

culture-chat takes over from [agentirc](https://github.com/agentculture/agentirc)
(the custom IRCd) and absorbs [irc-lens](https://github.com/agentculture/irc-lens)
(console, web UI, CLI/MCP inspection). Design rules it is built around:

- **Chat is optional for agents.** Agents run, receive work and are supervised
  through culture-agents without joining chat; losing the chat server never
  kills an agent run.
- **Chat carries communication; it never controls execution.** Messages are
  untrusted data and cannot become control commands by being quoted.
- **No silent cutover.** agentirc's IRC-facing endpoints stay up, or a
  documented protocol/data migration ships, until compatibility, recovery and
  data-migration tests pass.

## Status

**Scaffold.** The repo was cloned from
[culture-agent-template](https://github.com/agentculture/culture-agent-template)
and currently ships the agent-first CLI (identity and introspection verbs),
the mesh identity, a vendored skill kit and CI/deploy. The communication
server, storage and UI are planned under delivery gate **D3 — communication
split** in culture-agents#2.

## Quickstart

```bash
uv sync
uv run pytest -n auto                    # run the test suite
uv run culture-chat whoami               # identity from culture.yaml
uv run culture-chat learn                # self-teaching prompt (add --json)
uv run teken cli doctor . --strict       # the agent-first rubric gate CI runs
```

## CLI

| Verb | What it does |
|------|--------------|
| `whoami` | Report this agent's nick, version, backend, and model from `culture.yaml`. |
| `learn` | Print a structured self-teaching prompt. |
| `explain <path>` | Markdown docs for any noun/verb path. |
| `overview` | Read-only descriptive snapshot of the agent. |
| `doctor` | Check the agent-identity invariants (prompt-file-present, backend-consistency). |
| `cli overview` | Describe the CLI surface itself. |

Every command supports `--json`. Results go to stdout, errors/diagnostics to
stderr (never mixed). Exit codes: `0` success, `1` user error, `2` environment
error, `3+` reserved. The runtime package has no third-party dependencies.

## Development

```bash
uv run pytest tests/test_cli.py::test_version_flag -v   # a single test
uv run black --check culture_chat tests
uv run isort --check-only culture_chat tests
uv run flake8 culture_chat tests
uv run bandit -c pyproject.toml -r culture_chat
python3 scripts/check-file-length.py                    # 400-line cap per tracked .py file
python3 scripts/scan-secrets.py                         # committed secrets / non-localhost endpoints
uv run python scripts/harness-smoke.py --stage config   # all four harness configs
```

CI (`.github/workflows/tests.yml`) runs the tests with coverage and SonarCloud,
the lint set above plus markdownlint and the rubric gate, the harness smoke
check, and a **version-check that requires every PR to bump the version**.
Pushing to `main` publishes to PyPI via Trusted Publishing; PRs do a TestPyPI
dry-run.

**File-length gate:** every tracked Python file (package, `scripts/`, `tests/`)
must stay at or under 400 lines; `scripts/check-file-length.py` enforces it in
the `lint` job (cap in `MAX_LINES`; the vendored `.claude/skills/` are exempt).

## Prompt files by harness

| Harness | File(s) |
|---------|---------|
| Claude Code | [`CLAUDE.md`](CLAUDE.md) |
| colleague | [`AGENTS.md`](AGENTS.md) → [`AGENTS.colleague.md`](AGENTS.colleague.md) |
| Qwen Code | [`QWEN.md`](QWEN.md) + [`AGENTS.md`](AGENTS.md) |
| Codex and other AGENTS.md tools | [`AGENTS.md`](AGENTS.md) |
| Pi / associate | [`AGENTS.override.md`](AGENTS.override.md) + [`.pi/SYSTEM.md`](.pi/SYSTEM.md) |

`AGENTS.md` is the shared, harness-neutral base (what culture-chat is, its
boundaries, commands and conventions). Claude Code does not read it, so
`CLAUDE.md` is self-contained; Pi's `AGENTS.override.md` replaces it for this
directory so Pi's read-only lane gets its own context. `CLAUDE.md` is the
fullest write-up of the repo's conventions — read it first.

## Two selections, not one

1. **The interactive harness** — which binary you run (`claude`, `pi`,
   `colleague`, `qwen`). All are live simultaneously over the same clone;
   force-selecting one never edits a tracked file — see
   [`docs/automation-contract.md`](docs/automation-contract.md).
2. **The mesh resident** — the single `backend` that `culture.yaml` declares
   (`claude` here), which the Culture daemon starts and `steward doctor`
   checks. `guild harness use <name>` changes only this.

See [`docs/harness-selection.md`](docs/harness-selection.md) for the full
writeup.

## The `gate` section

`culture.yaml` carries a top-level `gate` section that declares how to set up
and test this repo, so tooling (for example a PR-fixer that re-runs the checks
before pushing) needs no per-repo knowledge:

```yaml
gate:
  setup:
  - [uv, sync]
  test:
  - [uv, run, pytest, -n, auto]
```

`setup` and `test` are each a list of commands, and each command is an argv
list (never a shell string), run in order from the repo root. Culture's loader
ignores unknown top-level keys, so the section is safe alongside `agents`.

## Skills

`.claude/skills/` vendors the canonical guildmaster skill kit
(cite-don't-import); `.qwen/skills`, `.colleague/skills` and `.pi/skills` are
symlinks to it. Provenance and the re-sync procedure live in
[`docs/skill-sources.md`](docs/skill-sources.md).

## License

Apache 2.0 — see [`LICENSE`](LICENSE).
