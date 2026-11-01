# GUARD-CLAUDE-WRITES — what a headless `claude -p` actor will try to write under the TR1.7 guard

Written 2026-10-31, TR1.7, staging. **Every row is UNVERIFIED.** `claude` was not executed, not even
`claude --version`. The list comes from three sources: (a) the names of the paths that exist under `~/.claude`,
`~/.claude.json*` and `~/Library/Caches` (names only, no contents read); (b) general knowledge of how Claude Code
behaves; (c) the guard's own census of the FAKE pipeline (it writes nothing outside scratch).
**Owed to Phase 2, the TR2.0 probe:** run one real `claude -p` under the guard profile with NO extra allowance, read
the denials (`guard.sh denials`, see guard-denials.txt in the run dir), and replace this table with the observed list.

**None of these allowances are in the profile.** guard.sh allows the canonical scratch plus /dev/null, /dev/tty,
/dev/dtracehelper, /dev/fd and bash's /tmp here-doc files. A real actor run today would therefore produce
SEAM-DENIED lines and fail. That is the safe direction: the guard is never quietly widened.

## The rule for adding any allowance in Phase 2
1. Observed first: a path is allowed only after the TR2.0 probe has seen it denied.
2. Narrowest form that works: `literal` before `regex` before `subpath`, and never a parent of any seam root (the
   state root, the skill roots, hooks.json, the notes stand-in).
3. Written in the profile BEFORE the stand-in, rig and seam-root denies, so those still win (last matching rule wins).
4. Logged in guard.sh's header with its reason, like the existing allowances.

## Candidate writes, with the narrowest allowance to try first

| # | path (as it exists on this machine) | why a headless session plausibly writes it | narrowest allowance to try first | status | VERIFIED by probe |
|---|---|---|---|---|---|
| 1 | `~/.claude/projects/<cwd-slug>/<session-uuid>.jsonl` (83 project dirs exist; the slug is the cwd with `/` → `-`) | the session transcript, appended per turn | `regex` on `^~/.claude/projects/-Users-<name>-lifehack-scratch-skill-tester-rig-runs-[^/]+/` (the actor's cwd is RUN_DIR, so the slug is known). Better: set `CLAUDE_CONFIG_DIR` to a per-run dir in scratch if Phase 2 proves it is honoured; then rows 1–8 need NO allowance at all | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 2 | `~/.claude.json` (+ `~/.claude.json.tmp.<pid>.<hex>` siblings, seen on disk) | per-project state, startup counters, tips, cached account and feature flags; written by temp-then-rename | `literal ~/.claude.json` plus `regex ^~/.claude\.json\.tmp\.[0-9]+\.[0-9a-f]+$`. Also `~/.claude.json.backup` if it is rewritten | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 3 | `~/.claude/todos/` (not present today) or `~/.claude/tasks/<session-uuid>/` (10 entries) | todo/task-list state per session | `regex` on the session-uuid subdir; or none if the actor's tools never create todos (it has `--allowedTools Read`) | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 4 | `~/.claude/shell-snapshots/snapshot-<shell>-<ms>-<rand>.sh` (9 exist) | a shell environment snapshot, taken when the Bash tool initialises | probably NONE (the actor has no Bash tool); if seen: `regex ^~/.claude/shell-snapshots/snapshot-` | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 5 | `~/.claude/statsig/` or similar feature-flag cache (no `statsig` dir today; `policy-limits.json*`, `remote-settings.json*` exist) | feature-flag / policy cache refresh at startup | `literal` per file actually seen; never `subpath ~/.claude` | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 6 | `~/.claude/session-env/<session-uuid>/` (479 entries) | per-session environment record | `regex` on the session-uuid subdir | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 7 | `~/.claude/file-history/<session-uuid>/` (33), `~/.claude/paste-cache/` (217), `~/.claude/history.jsonl`, `~/.claude/debug/`, `~/.claude/logs/`, `~/.claude/telemetry/` | edit checkpoints, paste cache, prompt history, debug and telemetry logs | file-history and paste-cache: likely NONE (Read-only actor, `-p` prompt); history.jsonl: `literal` if seen; debug/logs/telemetry: `literal`/`regex` per file seen | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 8 | `~/.claude/.last-cleanup`, `~/.claude/.last-update-result.json`, `~/.claude/backups/`, `~/.claude/cache/`, `~/Library/Caches/claude-cli-nodejs/` | startup housekeeping: cleanup stamp, auto-update check, caches | `literal` per stamp file; `subpath ~/Library/Caches/claude-cli-nodejs` is acceptable (not seam scope); auto-update should be disabled in lab settings rather than allowed | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 9 | `$TMPDIR` (run.sh points it at `$SCRATCH/tmp/<run>`, already allowed) and `/private/var/folders/.../T/` via `confstr(_CS_DARWIN_USER_TEMP_DIR)` (Node/libuv may bypass TMPDIR) | temp files for tool output, node module caches | none if TMPDIR is honoured; else `subpath` of the per-user temp dir's `claude-*`/`node-*` children only, never the whole `/private/var/folders` | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 10 | macOS keychain (`~/Library/Keychains/login.keychain-db`, written through `securityd`, not by the process) | OAuth credential refresh, if the keychain is the credential store | probably NONE: keychain writes are made by `securityd` (outside the sandboxed tree), and run.sh passes `CLAUDE_CODE_OAUTH_TOKEN` from `~/.config/lifehack/claude-oauth-token`. If Mach lookups for `com.apple.SecurityServer` are denied, that is a `mach-lookup` rule, which the guard does not touch (`allow default`) | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 11 | **hooks and plugins the actor's session runs** (`~/.claude/settings.json`, `~/.claude/hooks/`, the lifehack-brain plugin): `.push-signpost.*` files in `~/.claude` (dozens exist), `~/.claude/state/`, `~/.claude/run/`, `~/.claude/jobs/`, and possibly Drive `state/` | user hooks fire on SessionStart, PreToolUse, Stop and so on, and run shell that writes | **NO ALLOWANCE.** This is exactly what the guard exists to catch: a hook write to the notes root must be SEAM-DENIED. Phase 2 must decide whether `lab-settings.template.json` disables hooks (`disableAllHooks` or similar, UNVERIFIED) so that a clean actor run is clean, or whether hook writes are part of what the rig measures. Either way, never widen the guard for them | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |
| 12 | `~/.claude/plugins/` (marketplace refresh, plugin cache) | plugin auto-update at startup | none: disable auto-update for the lab session; if it still writes, `subpath ~/.claude/plugins/cache` only | UNVERIFIED · Phase 2 | UNVERIFIED (no real probe run yet) |

## What the guard already gives Phase 2
- Every denial carries the run's tag and is listed by path in `RUN_DIR/guard-denials.txt` and as `SEAM-DENIED <path>`
  lines, so the TR2.0 probe is ONE real run under the unchanged profile, then a read of that list.
- `log show` cannot run inside a sandbox. The denial read already happens in the unguarded parent runner, so a real
  actor changes nothing there.
- UNVERIFIED as well: whether `claude` runs under `sandbox-exec` at all (nested-sandbox refusal; Claude Code's own
  sandboxing). If it does not, `SEAM_GUARD=off:<reason>` and every change stays SEAM-LEAK (CONTRACT §3a rule 1).

## TR2.0b: how the "VERIFIED by probe" column gets filled (2026-11-01)
Filled ONLY from a real run of `probe-actor-writes.sh` (the main window runs it; a builder never launches `claude`).
Until then every row says UNVERIFIED. The probe launches ONE real actor with run.sh's exact launch shape
(`actor.lib.sh`), which changes the picture for most rows:
- **ONE throwaway HOME per run (design (b), ruled 2026-11-01).** run.sh gives every ai step of a run
  `HOME=<scratch>/actor-home/<run-id>`, with the run dir at `$HOME/.claude/run/skill-tester/<run-id>/` (the Harness ingest
  gate trusts `$HOME/.claude`), `LHB_JOURNAL_PATH` inside it and `CLAUDE_CONFIG_DIR` unset. The actor is denied Read of
  `$HOME/.claude/{projects,sessions,session-env}/**` (F-M5: no rebuilding state from prior transcripts). The cc-socks socket
  and the fswatch probe stay DENIED (guard-ruled-denies.txt names them `SEAM-DENIED-RULED`; nothing is allowed). Rows 1–8
  and 12 then name paths under THAT home, which lies
  inside the scratch allow root, so they need no allowance at all. The probe reports them as class `a-home`. Expect
  the column to read `a-home (per-run, no allowance)` for those rows, or `not seen` if the actor never wrote them.
- **The real `~/.claude`, `~/.claude.json`, `~/Library/...` and Drive** are class `c` if the probe sees ANY write there.
  `c` is flagged `⛔ REAL-STATE` and must stay DENIED; it needs a ruling (find and stop the writer), never an allowance.
- **Row 9 (system temp)** is class `b` if Node bypasses TMPDIR. The probe writes a PROPOSED narrow regex patch for
  guard.sh. The patch resolves the per-user temp dir at run time and is never applied without a ruling.
- **Row 11 (hooks)**: the Harness now loads through `--plugin-dir`, and its hooks run under the throwaway HOME. Any hook
  write outside the per-run tree shows up as `b`/`c` by path.
Column values to use: `a-home (per-run, no allowance)` · `a-run` · `b: patch proposed <file>` · `c: DENIED, ruling
needed` · `not seen (census complete)`, each with the probe's out dir `probe-actor-writes/<ts>/`. A census whose actor
did not finish (`WRITELIST: CANNOT-RUN census-incomplete`) verifies nothing.
