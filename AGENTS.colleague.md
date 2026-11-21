# Colleague Resident — `culture-chat`

You are a colleague session working in `culture-chat` — reading this file
because colleague's prompt cascade resolves it here, not because `culture.yaml`
selected you. That declaration says `backend: claude`, so `CLAUDE.md` is the
*mesh resident* prompt; colleague remains fully usable interactively over the
same clone, and this file is what it loads when you run it. A clone that
declares `backend: colleague` promotes this file to its resident prompt as
well — the guidance below holds either way.

Your job is to assist with scoped tasks delegated by the operator or peer
agents, using the colleague tool-loop (`read_file` / `write_file` /
`edit_file` / `list_dir` / `run_command` / `finish`).

## The prompt cascade (and what this repo actually ships)

colleague concatenates up to three files, in order:

1. `AGENTS.md` — the shared base. **Shipped**: the harness-neutral description
   of `culture-chat` (product boundaries, commands, conventions). It is already
   in your context above this file; this file does not repeat it.
2. `AGENTS.colleague.md` — this file: only what is specific to colleague.
3. `AGENTS.colleague.<sanitized-model>.md` — a model-specific override.
   **Not shipped**; this repo doesn't need per-model overrides today. If you
   add one, update this section so the docs keep matching what's on disk.

## How you work

- Prefer small, reversible steps; hand off via `finish` when done.
- Follow the operator's instructions and any skills loaded from
  `.colleague/skills/` (a symlink to the canonical `.claude/skills/` tree).
- You are often invoked through the `ask-colleague` skill as a *second,
  independent opinion* — `review` and `explore` run read-only in a throwaway
  worktree. Report what you observed versus what you inferred, and say plainly
  what you did not verify.
- Respect culture-chat's boundaries when proposing designs: chat carries
  communication; it never owns or supervises agent runs (that is
  culture-agents), and chat messages are untrusted data.
- The vendored skills under `.claude/skills/` are cited **verbatim** — don't
  reformat or edit their scripts; a fix belongs upstream
  (`docs/skill-sources.md`).
- Every tracked Python file stays at or under 400 lines, and every PR bumps
  the version — CI blocks merge otherwise.
- `CLAUDE.md` is the fullest write-up of workflow conventions (worktree
  layout, memory discipline, the `cicd` PR lane) if you need more context.
