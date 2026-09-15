# Codex adapter — scope, not a build

**This document describes what someone would need to build to run the Lifehack Harness's skills from
Codex instead of Claude Code. It is not that adapter.** No `AGENTS.md`, no `SKILL.md`, no adapter code
ships here or anywhere near it. If you came here looking for a drop-in file, this isn't it — this is
the map you'd read before writing one yourself.

**Why this exists:** an outside reporter — not this repo, not its maintainer — built a local adapter
that got Codex routing to some of this package's skills. That report is the only evidence behind this
document. Nobody on this project has built, run, or verified a Codex adapter. Treat every claim below
about "how the reported adapter worked" as secondhand, and every claim about "what Codex looks for" as
underverified unless marked otherwise. Where this document doesn't know something, it says so — a
confident-sounding guess here would be worse than a gap.

## What this package assumes about the reader

Everything in this repo — the skills under `.claude/skills/`, the SOPs, `INSTALL.md` itself — is
written for **Claude Code** specifically. `INSTALL.md` says this outright in its first section: "This
setup only works in Claude Code... and no other app can load any of them." A Codex adapter is a
different, unsupported path, built and maintained by whoever wants Codex to reach this same material.
This document exists so that person starts from an accurate picture instead of guessing.

## What Codex actually looks for on disk

**UNVERIFIED — this repo has not run Codex, does not maintain a Codex integration, and this section is
inference from public documentation and the reporter's account, not from a check run in this session.**

The commonly described shape (as of general Codex/agentic-CLI conventions, not confirmed against a
live Codex instance from inside this session) is:

- **`AGENTS.md`** at the root of a project — a single instructions file Codex reads to understand the
  project and how it wants to be worked with. This is the rough analog of what a `CLAUDE.md` does for
  Claude Code, but the two are not drop-in equivalents: their loading rules, precedence, and what they
  can trigger are not the same, and nobody has verified the overlap here.
- **`.agents/skills/<name>/SKILL.md`** — a per-skill instruction file, one directory per skill, each
  presumably read on demand rather than always-loaded (mirroring the Claude Code skill shape of
  `.claude/skills/<name>/SKILL.md`, which this repo does use — see below).

Both of these are named in the row that produced this document, on the strength of the outside
report. **This repo's own conventions have not been checked against them.** If you are building this
adapter, verify the actual on-disk contract against Codex's current documentation before relying on
anything above — Codex's own docs are the authority, not this paragraph.

## The real routing surface in this repo

This is what actually exists, checked this session by listing `~/lifehack-brain/.claude/skills/`
and reading each named skill's frontmatter. The plugin manifest (`.claude-plugin/plugin.json`) confirms
skills are served from `./.claude/skills` — there is no second, different skill location in this repo.

The row that produced this document named eight skills as the ones the reported local adapter routed.
Here is what each one actually is, read from its own `SKILL.md` frontmatter:

| Trigger | Skill file | What it actually does |
|---|---|---|
| `/read` | `.claude/skills/read/SKILL.md` | Loads the relevant parts of your notes into the session — a directed search against what was actually written, not the model's memory of it. |
| `/save` | `.claude/skills/save/SKILL.md` | Routes what a session produced to the right home in your notes — records / state / journal / ledger / canon — writing reversible tiers on its own authority and stopping to confirm only for canon. |
| `/ingest` | `.claude/skills/ingest/SKILL.md` | The bulk personal-corpus ingestion flow (led by "Vera the Curator" persona) — turns a chat export or pile of notes into this package's folder schema, in four phases. |
| `/checkin` | `.claude/skills/checkin/SKILL.md` | Re-orients on the active project: reconciles the desired outcome, the last-saved state, and what actually happened, then proposes the next scope. |
| "project" → `/project-manager` | `.claude/skills/project-manager/SKILL.md` | Maintains one living project document per multi-session project — the current operating state, not a transcript. |
| `/research` | `.claude/skills/research/SKILL.md` | Fans out several blind, isolated web searches on a load-bearing "what's the best way" question and synthesizes where independent sources converge. |
| `/build` | `.claude/skills/build/SKILL.md` | The autonomous executor — runs Execute → Verify → done on every task in an existing plan without stopping at ordinary seams. |
| `/council` | `.claude/skills/council/SKILL.md` | Convenes a debate across the user's own subject folders on a decision that cuts across several of them, one real subagent per subject. |

Two things worth flagging about that table:

- **`council` and `advisory-council` are different skills that both live in this directory** — `council`
  debates across your own subject folders; `advisory-council` (`.claude/skills/advisory-council/SKILL.md`)
  convenes a saved roster of expert advisors on one decision. The row that produced this document named
  "council," and this table follows that — but a real adapter build should decide, deliberately, which
  one (or both) it wants to expose, because the names are easy to confuse.
- Several of these skills declare `allowed-tools` in their frontmatter (e.g. `read` is
  `[Read, Glob, Grep, Bash]`, `save` is `[Read, Write, Edit, Glob, Bash]`, `research` is
  `[Read, Write, Glob, Bash, Task]`). Those tool grants are Claude-Code-specific plugin mechanics.
  **How — or whether — Codex's skill/tool model maps onto that same restriction is unverified here.**
  A skill written assuming it can spawn a `Task` subagent (like `research`) will not work the same way
  if the host environment has no equivalent primitive.

## How the reported local adapter routed these — as far as this document can verify

This is the part where honesty matters most: **this document has no direct access to the reporter's
adapter code, only a secondhand account passed down through the task that produced this row.** What can
be said with any confidence:

- The reported adapter's job was **dispatch, not reimplementation** — an `AGENTS.md` (or equivalent)
  that told Codex "when the user says X, go read and follow the instructions in this repo's
  `.claude/skills/<name>/SKILL.md`," rather than rewriting each skill's logic in Codex's own format.
  That is the only routing model consistent with "routed... to the existing skill files in this repo,"
  which is the phrase this row was given.
- Whether the reported adapter copied skill content into `.agents/skills/<name>/SKILL.md` files, or
  instead pointed at this repo's `.claude/skills/` files directly (via a relative path, a symlink, or
  some other mechanism), is **not known from anything checked this session.** Both are plausible; they
  have very different sync properties (see below), and a real build has to pick one deliberately rather
  than falling into whichever is easiest to type first.
- Nothing here confirms which subset of each skill's behavior transferred. A skill like `save` or
  `checkin` leans on this repo's own conventions — the AI Brain root, `shared/brain_root.py`, the
  `system/organism/` map — that Codex has no independent reason to know about unless the adapter also
  carries that context over. Whether the reported adapter did this, or only forwarded the top-level
  `SKILL.md` prose, is unknown.

**If you are the person building this:** treat the table above as your starting inventory, not as
confirmation that a working adapter already exists in a form you can inspect. Nobody currently
maintaining this repo has seen the reported adapter's source.

## What has to stay in sync, and what breaks when it drifts

Whichever routing mechanism a real adapter uses, it is taking on a maintenance burden this repo does
not currently carry for it. Concretely:

- **Skill file paths and names.** This table is accurate as read on 2026-09-07. Skills get added,
  renamed, retired (see `.claude/skills/`'s own naming — e.g. the retired `cal-daily-retired-2026-08-20`
  pattern used elsewhere in this ecosystem shows skills do get formally retired in place). Any adapter
  that hardcodes a skill list or copies file content will silently go stale the next time a skill is
  added, renamed, or its `SKILL.md` is edited — there is no notification mechanism between this repo
  and an external adapter.
- **Frontmatter contracts** (`triggers`, `allowed-tools`, `shape`) are read by Claude Code's own plugin
  loader. If an adapter parses or depends on this frontmatter shape, a change to how this repo's
  frontmatter is structured (a new required field, a renamed key) would break that parsing without any
  warning surfacing here — this repo's CI does not know a Codex adapter exists and cannot flag it.
- **Cross-references inside skill files.** Several skills reference other repo machinery directly —
  brain-root resolution (`shared/brain_root.py`), the organism map (`system/organism/manual.md`,
  `system/organism/elements/`), hooks, SOPs under `system/sops/`. A skill's instructions read correctly
  inside Claude Code partly *because* Claude Code's session has this whole repo, its hooks, and its
  `CLAUDE.md` loaded alongside it. Forwarding only a skill's `SKILL.md` text to Codex, without the
  surrounding repo context and without Codex's own equivalent of this repo's hook/guard layer, means the
  skill's instructions may reference files, tools, or safety rails that either don't exist in Codex's
  environment or behave differently there. This is the single biggest unknown in porting any of these
  skills — not just a sync problem, but a "does the safety model even carry over" problem — and this
  document is not the place that resolves it.
- **Versioning.** This repo bumps `.claude-plugin/plugin.json`'s `version` field on skill changes (there
  is a CI check for it — `.github/workflows/plugin-version-bump-required.yml`). A Codex adapter has no
  hook into that version bump; nothing here pings an external adapter maintainer when the version moves.
  Pin to a specific commit or tag, not "latest," if freshness matters, and re-diff manually.

## What this document is not saying

It is not saying the reported adapter doesn't work — it may work fine for its builder's own use. It is
not specifying a Codex integration contract this repo will honor going forward — no such commitment
exists. It is not a substitute for reading the actual skill files before routing to them; the table
above is a map of what exists, not a summary that replaces reading `.claude/skills/<name>/SKILL.md`
directly when building against it.
