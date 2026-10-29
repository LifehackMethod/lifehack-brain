---
element: shared-layer
title: "shared-layer — element detail (ground/base altitude)"
subsystem: build-discipline
altitude: base
record_type: organism-element
maturity_label: LIVE
generated_from:
  - shared/
  - system/register/toolbox.py
  - system/register/toolbox.md
  - system/register/register.jsonl
  - system/githooks/pre-commit
  - system/hooks/guard_build_mode.sh
  - system/hooks/lib/build_mode.py
  - system/hooks/build_mode_sops.conf
  - system/hooks/inject_sop_before_build.sh
created_at: 2026-10-29
updated_at: 2026-10-29
status: active
authority: user
---

# shared-layer — element detail

> **One-line:** a tool that should behave the same everywhere exists ONCE, under `shared/`; desks call it and
> never copy it. Added by v2 plan step 2.5, after 68 drifted copies were found.

## What is in `shared/`

Top-level helpers: `shared/brain_root.py` (the only resolver of the AI Brain path), `shared/paths.py` (scratch
path), `shared/registry.py`, `shared/bounded_input.py`, `shared/cal_config.py`. Folders: `shared/gate/` (the
ingest gate and the Sentinel verdict half), `shared/notify/` (`notify-governor.py`, `notify-send.sh`),
`shared/emit/verdicts.py` (the CANNOT-READ convention), `shared/tools/` (email, store and sync, intake reader,
model ids). Tests sit beside the code (`test_*.py`).

## How the register and the toolbox list it

- Every shared tool is a `type: tool` row in `system/register/register.jsonl` (`system/register/schema-v1.md`,
  the `shared/` addendum). Hand-registering is not needed: `python3 system/register/harvest.py --update-register
  system/register/register.jsonl` adds the rows.
- `system/register/toolbox.py` generates `system/register/toolbox.md` from the register plus each tool's own
  header. It is generated, never hand-edited; `python3 system/register/toolbox.py --check` fails when the file is
  stale. To change a line, change the tool's header and regenerate.
- The list is the place to look BEFORE writing a new tool.

## The commit gate refuses an unregistered tool

`system/githooks/pre-commit`, "NEW-TOOL REGISTRATION GATE": a commit that ADDS a `.py`/`.sh` under
`system/tools/` or `shared/` must carry its row in `register.jsonl`, or the commit is refused with the harvest
command to run. Added files only (an existing backlog never blocks an unrelated commit); test-class files exempt.

## The guard_build_mode copy block

`system/hooks/guard_build_mode.sh` (logic in `system/hooks/lib/build_mode.py`), PreToolUse on
Bash/Write/Edit/MultiEdit:

- **Copy block (HARD, exit 2):** a `cp`/`mv`/`rsync` whose source is under `<code>/shared/`, or a desk file
  created with a DISTINCTIVE shared-tool basename (names read from the register at run time). Generic names
  (`paths`, `registry`, `verdicts`) get a once-per-session speed bump instead. A thin wrapper (12 lines or fewer
  naming `/shared/`, or a `# wraps-shared:` marker in the first 10 lines) passes.
- **Speed bump:** the first attempt per kind (skill, job, hook, desk) per session is denied with "read the SOP,
  or use /build"; the identical retry passes. SOP paths live in `system/hooks/build_mode_sops.conf`.
- Fail-open on any internal error. A speed bump, not a boundary: Bash is matched as text.

## Use, don't copy

The rule is `system/sops/canonical-principles-sop.md` §9: "If something should work the same way everywhere, it
exists once, in the shared layer. Desks use it; they never copy it." Reminders, in the order a builder meets
them: the harness brief (`CLAUDE.md`, organism map), the prompt hook `inject_sop_before_build.sh` (building
language points to `toolbox.md` and `/build`), then the guard above at write time. A desk that needs a shared
tool imports or calls it from the code root, or wraps it in a few lines.

## Limits

- The brief and the prompt hook are pointers (honor); only the copy block and the commit gate are mechanical.
- The prompt hook is a keyword match on build verbs near a noun; a request phrased otherwise gets no pointer.
