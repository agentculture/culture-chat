# QWEN.md

This file provides guidance to Qwen Code when working with code in this
repository. Qwen Code's context loader reads `QWEN.md` and `AGENTS.md` in a
directory. In this repo **`AGENTS.md` is the shared, harness-neutral base** —
what `culture-chat` is, its product boundaries, commands and conventions — so
read it as part of your context. This file adds only what is specific to a Qwen
Code session.

## This project in one line

`culture-chat` is the new chat app of AgentCulture — the human-and-agent chat
surface for the mesh, replacing agentirc and absorbing irc-lens (see
[culture-agents#2](https://github.com/agentculture/culture-agents/issues/2)).
Today it is still the agent-template scaffold; no chat server exists yet.

## You are a local tool session, not the mesh resident

`culture.yaml` declares `backend: claude`, so the mesh daemon reads
`CLAUDE.md`, not this file. Running Qwen Code here neither requires nor changes
that declaration, and must never rewrite `culture.yaml` or other tracked files
just to "select" a harness (see `docs/harness-selection.md`).

## Prompt files by harness

| Harness | Reads |
|---------|-------|
| Claude Code | `CLAUDE.md` |
| colleague | `AGENTS.md` → `AGENTS.colleague.md` |
| Qwen Code | `QWEN.md` (this file) + `AGENTS.md` |
| Pi / associate | `AGENTS.override.md` + `.pi/SYSTEM.md` |

## Qwen-specific notes

- Skills: `.qwen/skills` is a symlink to the one canonical `.claude/skills/`
  tree. Those skills are vendored verbatim — do not edit them.
- `.qwen/settings.json.example` is the template for local Qwen settings; keep
  real settings untracked.
- `CLAUDE.md` is the fullest write-up of workflow conventions (worktree layout,
  memory discipline, `ask-colleague`, the `cicd` PR lane); they apply to work
  in this repo regardless of harness.
