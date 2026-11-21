# AGENTS.override.md

This file is the **context layer** for the Pi harness (the `pi` CLI, and the
`associate` non-coding harness modelled on it) when it runs inside this repo.
Pi's context loader concatenates `AGENTS.md` or `CLAUDE.md` from its user-level
config directory, each parent directory, and the working directory — but an
`AGENTS.override.md` present in a directory replaces that directory's
`AGENTS.md`/`CLAUDE.md` entry outright rather than adding to it. So Pi reads
**this file instead of** the root `AGENTS.md` (the shared base colleague and
Qwen Code read) and instead of `CLAUDE.md` (the Claude Code guidance, which
assumes a coding session with repo-write authority Pi's lane does not have).

The identity and behavioral bounds for that lane — who Pi is here, what it may
and may not do — live in Pi's **system prompt** file,
[`.pi/SYSTEM.md`](.pi/SYSTEM.md), which replaces Pi's default coding-assistant
system prompt entirely. This file is project *context* only: what the repo is
and how it is laid out, not who is reading it.

## What this project is

`culture-chat` is the communication product of AgentCulture: the
human-and-agent chat surface for the mesh. It replaces `agentirc` (the custom
IRCd) and absorbs `irc-lens` (console, web UI, CLI/MCP inspection), per
[culture-agents#2](https://github.com/agentculture/culture-agents/issues/2).

It **owns** rooms, participants, presence, threads, messaging, history and
replay, bot/event surfaces and federation where required. It does **not** own
agent runs (culture-agents), workflows (culture-rules), or sensing and
realtime voice (embodiment). Agents must be able to run without joining chat.

**Today the repo is still the scaffold** from `culture-agent-template`: an
agent-first CLI with identity/introspection verbs only, a mesh identity, a
vendored skill kit, and CI/deploy. If asked about chat features, report that
they are planned, not present.

## Prompt files by harness

- **Claude Code** reads [`CLAUDE.md`](CLAUDE.md) — the fullest write-up.
- **colleague** reads [`AGENTS.md`](AGENTS.md) then
  [`AGENTS.colleague.md`](AGENTS.colleague.md).
- **Qwen Code** reads [`QWEN.md`](QWEN.md) plus `AGENTS.md`.
- **Pi / associate** reads this file plus `.pi/SYSTEM.md`.

## Identity

`culture.yaml` declares `suffix: culture-chat`, `backend: claude`, so
`CLAUDE.md` is the live mesh-resident prompt. A Pi session here is a **local
tool session**, not the mesh resident; running `pi` neither requires nor
changes that declaration.

## Layout (what you can read/find/summarize here)

```text
culture_chat/             agent-first CLI (cited from teken's python-cli reference)
  cli/                    parser, error/output contract, _commands/ (verbs)
  explain/                markdown catalog for `explain`
tests/                    pytest suite
scripts/                  harness-smoke (+ _harness_smoke/), check-file-length, scan-secrets
docs/                     harness selection/automation contract, skill provenance
.claude/skills/           vendored guildmaster skill kit (cite-don't-import)
culture.yaml              mesh identity (suffix + backend) and `gate` commands
.github/workflows/        tests + deploy (PyPI Trusted Publishing)
```

## Conventions worth knowing before you answer a question about this repo

- The vendored skills under `.claude/skills/` are cited **verbatim** — never
  propose editing their scripts; the fix belongs upstream
  (`docs/skill-sources.md`).
- Every tracked Python file stays at or under 400 lines
  (`scripts/check-file-length.py`, run in CI).
- Every PR bumps the version (`version-bump` skill); CI's `version-check` job
  blocks merge otherwise.
- This file describes the repo **as it exists on disk today**.
