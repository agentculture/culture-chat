# AGENTS.md

Shared, **harness-neutral** project guidance for `culture-chat`. Read by
colleague (first layer of its cascade, before `AGENTS.colleague.md`), Qwen
Code (alongside `QWEN.md`), and AGENTS.md-native tools such as Codex. Claude
Code reads `CLAUDE.md` instead, and Pi's `AGENTS.override.md` replaces this
file for this directory — so keep it free of any one harness's tool names or
permissions; those belong in the harness's own file.

## What this project is

`culture-chat` is the communication product of AgentCulture: the
human-and-agent chat surface for the mesh. It replaces `agentirc` (the custom
IRCd) and absorbs `irc-lens` (console, web UI, CLI/MCP inspection). Scope and
boundaries come from
[culture-agents#2](https://github.com/agentculture/culture-agents/issues/2).

**Today the repo is still the scaffold** from `culture-agent-template`: an
agent-first CLI with identity/introspection verbs only, the mesh identity
(`culture.yaml`: `suffix: culture-chat`, `backend: claude`), a vendored skill
kit, and CI/deploy. No chat server, storage or UI exists yet.

## Boundaries

- **Owns:** rooms, participants, presence, threads, messaging, durable
  history, reconnect/replay, bot/event surfaces, identities, federation and
  trust boundaries where required, and the console/web/CLI/MCP inspection
  surfaces inherited from irc-lens.
- **Does not own:** agent runs — dispatch, supervision, steer, cancel
  (culture-agents); workflows and scheduling (culture-rules); sensing and
  realtime voice (embodiment); workspace composition (culture).
- Agents must be able to run **without joining chat**; a dead chat server must
  not kill an agent run.
- Chat messages are **untrusted data** and never become control commands by
  being quoted.
- The cutover from agentirc must not silently break mesh participants: keep
  legacy IRC-facing endpoints or ship a documented migration.

## Commands

```bash
uv sync
uv run pytest -n auto                                   # full suite
uv run pytest tests/test_cli.py::test_version_flag -v   # single test
uv run black --check culture_chat tests && uv run isort --check-only culture_chat tests
uv run flake8 culture_chat tests && uv run bandit -c pyproject.toml -r culture_chat
python3 scripts/check-file-length.py                    # 400-line cap per .py file
python3 scripts/scan-secrets.py
uv run teken cli doctor . --strict                      # agent-first rubric gate
uv run python scripts/harness-smoke.py --stage config   # all harness configs
```

## Conventions

- CLI contract: every command supports `--json`; results to stdout,
  diagnostics to stderr; exit `0` ok, `1` user error, `2` environment error.
  The runtime package has no third-party dependencies.
- Every tracked Python file stays at or under **400 lines** (CI `lint` job;
  `.claude/skills/` exempt). Split before crossing it.
- black + isort (profile black), line length 100.
- **Every PR bumps the version** (`pyproject.toml` + `CHANGELOG.md`); CI's
  `version-check` blocks merge otherwise.
- `.claude/skills/` is vendored verbatim — never edit; re-sync per
  `docs/skill-sources.md`.
- Persistent worktrees go in `../.worktrees.culture-chat/<name>/`.
- When scope or conventions change, update this file and `CLAUDE.md` together.
  Describe the repo as it exists on disk; mark anything unbuilt as planned.
