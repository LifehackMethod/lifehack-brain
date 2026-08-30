---
topic: [build-process]
title: Machine Readiness Checklist
record_type: reference
desk: root
created_at: 2026-07-02
status: active
authority: user
---

# Machine Readiness Checklist

> **Hard rule: a machine may NOT be reported "ready" with any artifact class below neither VERIFIED nor
> explicitly marked OUT-OF-SCOPE. No silent gaps. "All criteria met" is false if any class is unexamined.**

---

## Why this exists

On 2026-07-02 a machine handoff to NYC was declared "NY-ready — all 6 criteria met." The criteria list
never included `~/.claude/plans/` (plan-mode plan files). That class was machine-local with no backup
lane — the Drive symlink had been retired 2026-06-16 and no replacement existed. A plan
(`nifty-wandering-dusk.md`) was stranded on the Mac Studio and unreachable from NYC. A `mirror_plans.sh`
Stop hook was proposed as the immediate fix (2026-07-02), but the deeper failure was structural: a handoff
checklist that did not enumerate every machine-local class allowed a whole class to be silently unbacked
and still produce a "complete" result.

⛔ **CORRECTED 2026-08-25:** `system/hooks/mirror_plans.sh` and its pull-side counterpart,
`system/tools/recover_studio_plans.sh`, do **not exist in this repo** (0 files, verified this session
against the working tree and `upstream/main`). They exist only in prose here and in the donor system this
repo migrated from. **The gap the 2026-07-02 incident found is still real and still unaddressed** — plan
files under `~/.claude/plans/` have no backup lane on this system. Row 1 below is corrected to say so
plainly rather than pointing at a tool that does not run.

**This checklist closes that hole.** Every machine-local artifact class is listed. A handoff is only
"ready" when every row has a status in the STATUS column: either VERIFIED (the operator confirmed it on
the target machine) or OUT-OF-SCOPE (explicitly reasoned as not needed).

---

## Artifact classes

| # | Class | Path | Backup lane | How to verify on target machine | STATUS |
|---|---|---|---|---|---|
| 1 | **Plan-mode plans** | `~/.claude/plans/` | ⛔ NONE — no mirror hook exists in this repo (`mirror_plans.sh` is prose-only, see banner above) | `ls ~/.claude/plans/` on the source machine before wipe/handoff; there is no automated pull path, so any plan not manually copied off is lost | OUT-OF-SCOPE-BY-GAP (real risk, no tool — manually copy `~/.claude/plans/*.md` off the source machine before handoff) |
| 2 | **Schedule registrations — crontab** | `crontab -l` (managed by `system/tools/install-schedulers.sh` from `system/pulse-config.md`) | Git (versioned in `pulse-config.md` → `install-schedulers.sh` replays it) | `crontab -l` on target shows the `CLAUDEOPS SCHEDULERS` block; if not: `bash system/tools/install-schedulers.sh --install` | VERIFY |
| 3 | **Schedule registrations — LaunchAgents** | `~/Library/LaunchAgents/ai.claudeops.*.plist` | Git-versioned plists in `system/tools/` or Drive; installed by `install-schedulers.sh` or `bootstrap-machine.sh` | `ls ~/Library/LaunchAgents/ \| grep claudeops` — compare against `system/pulse-config.md` §"Launchd-owned schedulers"; load missing ones with `launchctl load` | VERIFY |
| 4 | **Secrets / auth tokens** | `~/.config/claudeops/` (gws creds, claude-oauth-token, cadence state, <utility-provider>-password, etc.) | None — secrets are re-issued on rebuild by design; `gws auth login --full` + any per-service re-auth | On target: `gws auth status` passes; `claude` auth valid; per-desk re-auth done if needed | OUT-OF-SCOPE (re-auth-on-rebuild by design) |
| 5 | **Third-party skill packs** | `~/.claude/skills/<pack>/` (real dirs, not symlinks) — 12 packs per `system/skills-manifest.md` ⏳ unruled — not yet ported to this repo | None — installed from source; manifest is git-versioned at `system/skills-manifest.md` ⏳ unruled — not yet ported to this repo | `bash system/tools/bootstrap-machine.sh` ⏳ unruled — not yet ported to this repo reports MISSING packs; install each from `system/skills-manifest.md` ⏳ unruled — not yet ported to this repo install commands | VERIFY |
| 6 | **Sentinel-paused sources** | `~/.config/claudeops/sentinel-paused-sources` | None — fail-open by design; absent file = no paused sources = resume normal ingest | No action needed: a missing file on target is safe (fail-open); any DANGER item re-pauses within one tick | OUT-OF-SCOPE (fail-open by design) |
| 7 | **obsidian-brain search index** | `~/.local/share/obsidian-brain/kg.db` | None — index is rebuilt from the Drive vault on demand | `npx obsidian-brain index` rebuilds it; P5 search degrades gracefully until rebuilt | OUT-OF-SCOPE (rebuildable from Drive vault) |
| 8 | **Git clone parity** | `~/claudeops-config/` | GitHub (canonical origin) | `git status` clean; `git log --oneline -3` matches GitHub HEAD; if behind: `git pull --rebase` | VERIFY |
| 9 | **Drive content sync** | `$DRIVE/` (`_ClaudeOps/`) — records, canon, state, journal, diary, registry | Google Drive (authoritative; no 2nd copy) | Drive mount present at `~/Library/CloudStorage/…/_ClaudeOps/`; `ls $DRIVE/state/open-loops.md` exists; spot-check a recent record | VERIFY |
| 10 | **Persona / desk launchers** | ~/Desktop/*.command (machine-local copies of launchers; canonical in the AI Brain's Drive, at a `system/personas/` ⛔ path there — not this repo, so it has no repo-relative home to check) | Drive (system/personas/Personas/ — same: a Drive/AI-Brain path, not a path in this repo) | Copy `.command` files from Drive onto Desktop; `chmod +x *.command` | VERIFY |
| 11 | **Pulse state** | `/tmp/claudeops-pulse-state.json` — last-run timestamps + BREAKER auto-trip state (`fails:`/`disabled:`/`retry_at:`) only | None — ephemeral `/tmp`; Pulse rebuilds on first run | No action: Pulse self-initializes; jobs run once on the next interval after first tick | OUT-OF-SCOPE (ephemeral, self-heals) |
| 11b | **Pulse deliberate-park marker** | `$DRIVE/state/pulse-parked-jobs.json` — a HUMAN's decision to switch a job off (`pulse-park.sh`), NOT breaker state; split out from row 11 (T18.5, 2026-08-04) because a reboot silently erasing this marker WAS the bug (see `system/organism/elements/pulse-cron.md` §circuit breaker mechanics ✅ — corrected path; no `git-autopush.md` exists in this repo) | Google Drive (content tier, same as every other `state/` file) | `pulse.sh --status` on the target shows the same PARKED jobs as the source; absence of the file is safe (reads as "nothing parked") | VERIFY (same as any other Drive-synced `state/` file — row 9) |
| 12 | **Git hooks (pre-commit)** | `core.hooksPath` → `system/githooks/pre-commit` | Git-versioned (hook lives in the clone; activation is a local `git config`) | `git config --get core.hooksPath` returns `system/githooks`; if not: `git config core.hooksPath system/githooks` (also run by `bootstrap-machine.sh` Step 8) | VERIFY |

---

## How to use this checklist

1. Before declaring a machine "ready," copy this table (or keep it open).
2. Work through every row. For each: confirm the artifact is present/working (VERIFIED) or explicitly
   record why it is not needed (OUT-OF-SCOPE with a one-line reason).
3. A row left blank = the handoff is not complete, regardless of how everything else looks.
4. Paste the filled table into the handoff note or machine-log entry so the decision is auditable.

---

## Related files

- `system/tools/bootstrap-machine.sh` ⏳ unruled — not yet ported to this repo — wires symlinks + checks third-party packs; does NOT cover plans, schedules, or secrets
- `system/tools/install-schedulers.sh` — installs the crontab block from `pulse-config.md`
- ⛔ `system/hooks/mirror_plans.sh` and `system/tools/recover_studio_plans.sh` do not exist in this repo — see the CORRECTED banner in "Why this exists" above; row 1's plan-backup gap is real and currently unaddressed
- `system/skills-manifest.md` ⏳ unruled — not yet ported to this repo — authoritative list of third-party packs + install commands
- `docs/architecture.md §7` ⛔ — that donor doc is parked, never ported here
  (`system/parked/2026-08-23-donor-spillover/docs/architecture.md`); residency topology and machine-local
  subsystem inventory now live in `system/organism/elements/where-things-live.md` and this checklist instead
