---
element: hook-plane
title: "hook-plane — element detail (ground/base altitude)"
subsystem: enforcement
altitude: base
record_type: organism-element
maturity_label: PARTIAL
# generated_from is DERIVED, not hand-typed: regenerate with
#   python3 -c "import json,re; d=json.load(open('system/reference/settings.json')); \
#   paths=set(); \
#   [paths.add(m.group(0)) for node in [d.get('hooks',{})] for m in \
#   re.finditer(r'system/hooks/[A-Za-z0-9_.-]+\.(sh|py)', json.dumps(node))]; \
#   [print('  - '+p) for p in sorted(paths)]"
# (equivalently: grep -oE 'system/hooks/[A-Za-z0-9_.-]+\.(sh|py)' system/reference/settings.json | sort -u)
# — every path below is a hook script with a live settings.json registration, verified 2026-08-01.
# The two non-hook sources (settings.json itself, hook-contract.md) are kept as bookends since they
# are the registry + the house standard this element also describes.
generated_from:
  - system/reference/settings.json
  - system/hook-contract.md
  - system/hooks/announce_plan_write.sh
  - system/hooks/auto_register_skill.sh
  - system/hooks/block_primary_calendar.sh
  - system/hooks/enforce_egress_allowlist.sh
  - system/hooks/enforce_multiphase_contract.sh
  - system/hooks/enforce_skill_frontmatter.sh
  - system/hooks/guard_agent_return_channel.sh
  - system/hooks/guard_canon_write.sh
  - system/hooks/guard_egress.sh
  - system/hooks/guard_git_add_class.sh
  - system/hooks/guard_gmail_destructive.sh
  - system/hooks/guard_gws_logout.sh
  - system/hooks/guard_hook_sop_read.sh
  - system/hooks/guard_ledger_discipline.sh
  - system/hooks/guard_marc_narrative.sh
  - system/hooks/guard_organism_map.sh
  - system/hooks/guard_plan_structure.sh
  - system/hooks/guard_router_writes.sh
  - system/hooks/guard_sheet_formula_writes.sh
  - system/hooks/guard_sheet_writes.sh
  - system/hooks/guard_statusline_lock.sh
  - system/hooks/guard_tasks_writes.sh
  - system/hooks/guard_throughline_write_scope.sh
  - system/hooks/guard_write_paths.sh
  - system/hooks/ingest_gate_enforce.sh
  - system/hooks/inject_compute_mechanically.sh
  - system/hooks/inject_delegation_standing.sh
  - system/hooks/inject_sop_before_build.sh
  - system/hooks/mirror_plans.sh
  - system/hooks/nudge_flow_drift.sh
  - system/hooks/observability_logger.sh
  - system/hooks/plan_flag.sh
  - system/hooks/pm_persist.sh
  - system/hooks/rating_capture.sh
  - system/hooks/save_routing_hint.sh
  - system/hooks/scratch_capture_gate.sh
  - system/hooks/scratch_sweep_nudge.sh
  - system/hooks/session_context_loader.sh
  - system/hooks/session_flight_recorder.sh
  - system/hooks/skill_anchor_inject.sh
  - system/hooks/translator_gate.sh
  - system/hooks/validate_on_write.sh
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# hook-plane — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#hook-plane ; ground truth → the live artifacts (system/hooks/ + system/reference/settings.json)**

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the entire hook fleet — every
> category, trigger, enforcement posture, and known gap. The MIDDLE manual (`system/organism/manual.md`)
> carries only a one-line pointer here. The TIP schematic shows only its box + arrows.
>
> **One-line:** the system's immune layer — 37 registered hooks in 5 event categories that intercept every
> Claude tool call at runtime to enforce behavioral invariants autonomously, without asking the human.
>
> **Step grammar:** `actor → port/tool → store/file → gate`
> Enforcement tags: `[hook]` (a real PreToolUse/PostToolUse/Stop/SessionStart/UserPromptSubmit guard fires,
> mechanically, on every match) · `[skill]` (mandatory script step, not a harness event) · `[honor]` (prose
> instruction only, no mechanical enforcement) · `[human]` (deliberate human-in-the-loop pause).

> **⚑ WHERE THE PATHS THIS FILE NAMES ENDED UP HERE** (destination note, 2026-08-15). The description below is the DONOR's, ported unchanged and deliberately not rewritten — it is a record of how that system works. These lines add only the destination's answer for each path it cites, and they hold for every occurrence of that path anywhere below.
> - ⛔ `system/reference/settings.json` — donor layout only. The hook registry is `.claude/settings.json` here, and it is present.
> - ⛔ `state/telos.md`, `state/pulse-brief.md`, `state/debt-ledger.md` — the person's own notes content, which lives under the notes folder (`docs/data-layout.md`) and is never a repo file.
> - ⛔ `system/flight-log.jsonl`, `system/observability/YYYY-MM-DD.jsonl`, `system/learnings.md`, `system/learnings/`, `system/learnings-signals.jsonl`, `system/logs/sentinel-events.jsonl` — runtime-generated, created on first run under the notes root by `system/hooks/session_flight_recorder.sh` and `system/hooks/rating_capture.sh`; never committed.
> - ⛔ `system/translator-rubric.md` — never shipped. The gate it graded for is DELETED here, as E3 below already records; a rubric with no grader had nothing to come for.
> - ⛔ `system/organism/elements/*/generated_from` — not a path at all: `generated_from` is a YAML key INSIDE each `system/organism/elements/*.md`, and those files are here.
> - ✅ `system/organism/map-format-specs.md` — **it is here.** *(Was `⏳ unruled` earlier on 2026-08-15; `T9.4c` landed the file the same day, 579 lines, ported from the donor with its `§` numbering preserved so the six existing citations still resolve. Marker flipped rather than left deferring a file that had arrived — a manifest describing the past is one nobody checks against the present.)*

---

## AUTHORED   (human-only)

### REGISTRATION MECHANICS

The hook-plane's ground truth is a TWO-LAYER artifact:

1. **`.claude/settings.json`** (git-tracked, in this repo) — the REGISTRY. The harness only fires hooks it finds here. A hook script that exists on disk but is absent from `settings.json` is inert dead code — the harness never sees it.
   > ⚠ **CORRECTED: the CITATIONS block above already flags `system/reference/settings.json` as
   > "donor layout only," but this REGISTRATION MECHANICS section previously kept describing a
   > two-machine symlink model (`~/.claude/settings.json` symlinked to a tracked
   > `system/reference/settings.json`, a separate fleet clone at `~/lifehack-brain/system/hooks/`)
   > that contradicts its own citation and does not describe this repo. `system/reference/settings.json`
   > does not exist anywhere in this tree (verified this session). What this repo actually ships is a
   > single tracked file, `.claude/settings.json`, at the repo's own root — no symlink, no second
   > machine, no separate clone. A student's `git clone` gets this file directly; there is nothing else
   > to wire up. Verified live this session: it registers 48 hook commands across 6 event categories
   > (SessionStart 1, UserPromptSubmit 11, UserPromptExpansion 1, PreToolUse 31, PostToolUse 2, Stop 2).
2. **`system/hooks/*.sh`** (git-tracked) — the FLEET, 54 `.sh` files in this repo (counted live this session). Both the fleet and its registration travel together with the repo itself via `git clone`/`git pull` — there is no separate sync step and no symlink to keep "in lockstep," because there is only the one tracked copy of each.

**Two-machine dark risk:** this section previously described a risk from broken `~/.claude/settings.json`/`~/.claude/hooks/` symlinks on a second machine. That scenario is specific to a maintainer running the same clone across two machines with a home-directory symlink setup — it does not describe this public repo's single-clone student install, and no such symlink exists here to break. The general caution still worth keeping: whatever a student's actual, live `.claude/settings.json` contains is the only thing that matters — a stale note about it, or an out-of-sync second copy anywhere else, is not.

**Deny-block protocol (house standard per `system/hook-contract.md`):** the canonical blocking signal is JSON on `stderr` + `exit 2`. Also accepted: `{"decision":"block",...}` JSON on `stdout` + `exit 0` (used in Stop hooks — `translator_gate.sh` and `scratch_capture_gate.sh` both use this form; `exit 0` is what the live code does and what works). NOTE: `hook-contract.md`'s exit-code table lists `exit 1` for this case — a possible stale-doc mismatch; the live-code form (`exit 0`) is authoritative. DARK TRAP: JSON on `stderr` + `exit 1` is silently swallowed by the harness — a guard accidentally using that pattern appears to run but never blocks.

**`--dangerously-skip-permissions` bypass:** the `permissions.deny[]` block in `settings.json` is bypassed in headless/non-interactive sessions launched with that flag. PreToolUse hooks are NOT bypassed by it. Therefore the PreToolUse blocking guards — specifically `guard_gws_logout.sh` and `block_primary_calendar.sh` — are the REAL backstops for headless sessions; the `permissions.deny[]` entries for those same operations are a belt-and-suspenders convenience for interactive sessions only.

**Fleet snapshot (2026-07-23):** ~~37 hooks registered in `settings.json` across 5 event categories (PreToolUse entries covering 17 blocking guards + 1 non-blocking recorder (`plan_flag.sh`) = 18 distinct PreToolUse scripts, 5 PostToolUse, 1 SessionStart, 9 UserPromptSubmit, 4 Stop). 50 `.sh` files exist in `system/hooks/`; 13 are UNREGISTERED (see "Dead Code" section below).~~ **CORRECTED — computed live this session against this repo's own `.claude/settings.json` and `system/hooks/`:**
48 hook commands registered across 6 event categories (SessionStart 1, UserPromptSubmit 11,
UserPromptExpansion 1, PreToolUse 31, PostToolUse 2, Stop 2). 54 `.sh` files exist in `system/hooks/`.
The 37/5 figure above is stale and does not match this tree; the UserPromptExpansion category and the
exact per-category counts were not accounted for in the original. The harness fires nothing unregistered.

---

### CATEGORY A — PreToolUse HARD GUARDS (blocking)

These fire BEFORE the tool executes. Exit 2 (or stdout block JSON) aborts the tool call. The harness enforces them unconditionally on every matching tool call. Every guard listed here is `[hook]`.

#### A1. guard_organism_map.sh
**Matcher:** Write
**Step chain:** `Claude → Write tool → system/organism/manual.md OR system/organism/map-format-specs.md → guard_organism_map.sh parses file_path + content field → if tool=Write AND content field present AND path matches either protected file → DENY exit 2 [hook]`
**Stores protected:** `system/organism/manual.md`, `system/organism/map-format-specs.md` (the self-schematic backbone).
**Gate logic:** Python3 reads stdin JSON; case-matches the file_path; blocks ONLY when the `content` field is present (a full-content Write that would wholesale-overwrite the file). Edit tool calls (which carry `old_string`/`new_string` instead of `content`) exit 0 — edits are allowed, wholesale overwrites are not.
**Fail posture:** CLOSED — JSON parse error → deny.
**Known gap:** only the Write tool is matched; a Bash heredoc or shell redirect targeting either file bypasses this hook entirely (`guard_write_paths.sh` backstops at the Write/Edit layer but ALSO does not cover Bash writes).

#### A2. block_primary_calendar.sh
**Matcher:** Bash
**Step chain (DEFAULT-DENY since 2026-08-01, organism-audit T8.4):** `Claude → Bash → any gws calendar command → block_primary_calendar.sh strips the command HEAD (everything from the first flag or quote is payload) → HEAD matches the RECOGNISED-READS list (events list|get|instances · calendarList list|get · calendars get · acl list|get · freebusy query · colors get · settings list|get · +agenda · help) → exit 0 → OTHERWISE (write verb OR a verb this guard does not recognise) → Agent Ops calendarId must appear in the FULL command → else DENY exit 2 [hook]`
**Why default-deny, and what the old shape cost:** until 2026-08-01 this hook matched an ALLOWLIST of write spellings and ended the test with `|| exit 0` — so every spelling not on the list failed OPEN. Fire-tested: `gws calendar events insert --calendar primary` → rc=2 (correct), `gws calendar +insert --calendar primary` → **rc=0, walked straight through** — and `+insert` is gws's OWN documented helper, not an exotic evasion. Also open by the same mechanism: `events delete`, `calendars clear` (wipes a whole calendar), `acl insert`, `calendarList delete`, and any verb gws adds in future. The test is now inverted: recognise reads, require the Agent Ops id for everything else; an unknown verb is unknown-therefore-DENIED. The trailing `|| exit 0` is deliberately absent and must not be restored.
**Stores protected:** Google Calendar write target — forces all writes to the Agent Ops calendar (`<agent-ops-calendar-id>`).
**Why this is the real enforcer (not `permissions.deny[]`):** the `permissions.deny[]` entries for `mcp__claude_ai_Google_Calendar__create_event` etc. cover only the MCP path AND are bypassed by `--dangerously-skip-permissions`. This hook covers the gws CLI path and is NOT bypassed by that flag.
**Fail posture:** CLOSED — unreadable stdin or unparseable JSON → deny. (`jq` was replaced by a python parse with an explicit `__ERR__` sentinel in the same 2026-08-01 pass: `jq -r '.x // ""'` exits 0 with empty output on EMPTY stdin, so the command fell through the not-a-calendar-command test and exited 0.)
⚠ **This repo's equivalent guard is `guard_calendar_writes.sh`, not `block_primary_calendar.sh`** (the
latter does not exist here — verified this session). It shares the default-deny core and the HEAD/READ
mechanics. Its fail posture on unparseable/empty stdin was previously `exit 0` (a silent ALLOW on the
exact "exit 0 on a BLOCK hook" defect class `hook-sop.md` documents) — **corrected in this pass**: an
unreadable payload now denies (`exit 2`) via the same `deny()` path as every other verdict in this
guard, so "Fail posture: CLOSED" now DOES describe this repo's copy too, on this axis. It also resolves
the target calendar id from `shared/cal_config.py` / `<notes>/config/cal.md` rather than hardcoding it,
and denies outright when no calendar has been configured.

#### A3. guard_gws_logout.sh
**Matcher:** Bash
**Step chain:** `Claude → Bash → any command matching (^|[[:space:]]|/)gws[[:space:]]+auth[[:space:]]+logout → guard_gws_logout.sh extracts command → DENY exit 2 [hook]`
**Stores protected:** `~/.config/gws/` — the auth keychain; destroying it breaks every desk simultaneously.
**Why this is the real enforcer:** the `permissions.deny[]` entry `"Bash(gws auth logout:*)"` is bypassed by `--dangerously-skip-permissions`; this PreToolUse hook is NOT. The hook header explicitly states this — it exists specifically because persona/headless sessions can't rely on the deny rule.
**Fail posture:** CLOSED — parse error → deny.
**Exit channel:** was previously non-standard (stdout + exit 1); corrected to stderr + exit 2 per 2026-06-16 council audit. Now house-standard.

#### A4. guard_egress.sh
**Matcher:** Bash
**Step chain:** `Claude → Bash → any command with outbound mechanism (curl/wget/nc/ncat/netcat/telnet/urllib.request/requests.*/httpx/http.client/socket) AND credential pattern (sk-ant-/AKIA.../ghp_/xox*/ANTHROPIC_API_KEY/AWS_SECRET_ACCESS_KEY) → DENY exit 2 [hook]`
**Coverage:** catches both shell and inline Python HTTP exfiltration vectors. Updated 2026-06-03 to extend the egress MECHANISM vocabulary (added Python HTTP libs: urllib.request, requests.*, httpx, http.client, socket — closing the python-exfil gap from the search-api audit). The credential gate was unchanged by that update.
**Fail posture:** OPEN on parse error or empty command — rationale: false-positive risk on transient parse failure; `enforce_egress_allowlist.sh` and LuLu (OS-layer) are complementary backstops.

#### A5. enforce_egress_allowlist.sh → enforce_egress_allowlist.py
**Matcher:** Bash
**Step chain:** `Claude → Bash → raw outbound call (curl/wget/nc/etc.) to a host NOT in system/egress-allowlist.md → enforce_egress_allowlist.sh execs enforce_egress_allowlist.py → extract host from URL → check allowlist → DENY exit 2; block events logged to Drive/system/logs/sentinel-events.jsonl [hook]`
**Stores read:** `system/egress-allowlist.md` (allowlist source, between markers; `ALLOWLIST_FILE` env override supported).
**Fail posture:** OPEN when no host is extractable from the command — stated, documented; LuLu is the OS-layer fail-closed backstop for that case. OPEN on JSON parse error.

#### A6. guard_tasks_writes.sh
**Matcher:** Bash
**Step chain:** `Claude → Bash → gws tasks tasks (insert|update|patch|delete|move|clear) on the Life Map tasklist (<google-resource-id>) → unless Daily Win parent (<google-resource-id>) also present AND verb is insert/update/patch/move (not delete/clear) → DENY exit 2 [hook]`
**Stores protected:** Google Tasks Life Map list (read-only by doctrine; one carve-out for Daily Win subtasks).
**Fail posture:** CLOSED — jq parse error → deny.

#### A7. guard_router_writes.sh — ⛔ DOES NOT EXIST HERE (verified: no file by this name anywhere in
this repo, and zero registrations in `.claude/settings.json`). Entry kept as history per house rule;
the ASUS-router write-guard this section describes is not part of the currently-shipped fleet.
**Matcher:** Bash
**Step chain:** `Claude → Bash → command touching <lan-ip> or router.asus.com WITH client verb (curl/wget/requests/urllib/http.client/aiohttp/nc/asusrouter) AND write CGI endpoint (appSet.cgi/apply.cgi/reboot.cgi/nvram set/async_set/set_settings) → DENY [hook]`
**Stores protected:** ASUS router admin API write surfaces.
**DEVIATION:** uses exit 1 + stdout JSON (not house-standard exit 2 + stderr). Hook-contract.md states both work; the harness treats exit 1 as deny. Minor inconsistency; no functional impact confirmed.
**Fail posture:** CLOSED on parse error (Python parse failure → exit 1 block).

#### A8. guard_statusline_lock.sh
**Matcher:** Bash
**Step chain:** `Claude → Bash → (a) sed -i targeting settings.json containing "statusLine" (delimiter-agnostic), OR (b) redirect/tee targeting settings.json with "statusLine", OR (c) rm/mv/tee/truncate/ln -s targeting statusline.sh, OR (d) "statusline-setup" invocation → DENY exit 2 [hook]`
**Stores protected:** `system/statusline.sh` and the `statusLine` pointer in `settings.json`.
**Note:** delimiter-agnostic sed match was fixed 2026-07-23 (conformance-lab found a bypass proof via non-standard sed delimiters; fix verified by the lab's adversarial probe suite).
**Fail posture:** OPEN on parse error — rationale: narrow scope, low harm; a blanket deny-all-Bash on transient glitch is worse; `guard_write_paths.sh` backstops at the Write/Edit layer for the settings.json path.

#### A9. enforce_skill_frontmatter.sh
**Matcher:** Write
**Step chain:** `Claude → Write → skills/*/SKILL.md → Python3 checks: (a) YAML frontmatter block present, (b) description field non-empty and non-placeholder, (c) line count ≤ 500 → DENY exit 2 on any violation [hook]`
**Stores protected:** `skills/*/SKILL.md` files — the skill registration surface.  ⛔ not shipped to the public subset — private-clone only.
**Scope note:** fires ONLY on full-content Write (content field present), not Edit. YAML parse via `yaml.safe_load`; regex fallback if yaml not installed. Non-SKILL.md targets exit 0 (correct scoping).
**Fail posture:** OPEN on JSON parse failure — not a security gate; quality enforcement only.

#### A10. guard_write_paths.sh
**Matcher:** Write|Edit
**Step chain:** `Claude → Write/Edit → any file → Python3 extracts file_path → checks against the RESIDENCY DECISION TABLE [hook]`

The residency decision table (in resolution order):
1. `~/.claude/hooks/` or `~/.claude/settings.json` → DENY
2. Drive `system/hooks/` → DENY (legacy Drive copy; edit in the clone, not here)
3. Drive spine `Lifehack/` → ALLOW (Drive content is permitted)
4. `~/.claude/skills/` or `commands/` → resolve realpath; ALLOW only if it resolves into the clone
5. `~/.claude/CLAUDE.md` → ALLOW
6. `~/.claude/plans/` → ALLOW
7. `~/.claude/projects/` (auto-memory) → DENY
8. Clone content classes (`state/`, `records/`, `system/journal.md`, etc.) → DENY (content lives on Drive, not in the clone)
9. Clone non-content → ALLOW
10. Everything else → DENY

**Stores protected:** auto-memory, hooks self-modification, Drive content classes in the wrong location.
**Fail posture:** CLOSED since 2026-06-18 — `__PARSE_ERROR__` sentinel → deny. Was previously fail-open (silent bypass on parse error; patched).
**KNOWN GAP (documented in hook header, accepted 2026-07-14):** Bash file-writes (echo >, tee, cp, heredoc) bypass this hook entirely — it only matches Write|Edit tools. Discipline + code review are the mitigations; no mechanical backstop for the Bash path.

#### A11. guard_ledger_discipline.sh
**Matcher:** Write|Edit
**Step chain:** `Claude → Write/Edit → state/debt-ledger.md → Python3 reconstructs the ## Open section after the proposed edit → counts FORBIDDEN lines (✅/RESOLVED/CLEARED/FIXED) in ## Open → if new count > current count → DENY exit 2 [hook]`
**Stores protected:** `state/debt-ledger.md` `## Open` section — enforces deletion-not-annotation discipline (resolved items must be DELETED from `## Open`, not ✅-marked in place).
**Fail posture:** OPEN for non-ledger targets or parse failure — a bug must never block the whole edit surface.

#### A12. guard_throughline_write_scope.sh
**Matcher:** Write|Edit
**Step chain:** `Claude → Write/Edit → any file → check throughline_flag for this session (~/.claude/run/eval/eval-<key>.flag) → if NOT armed: pure NO-OP exit 0 → if ARMED: allow ONLY writes to .../evaluator/scratchpads/; all others → DENY exit 2 [hook]`
**Stores protected:** everything except evaluator scratchpads, during a `/throughline` session.
**Activation:** conditional — the guard is a pure no-op unless `throughline_flag.sh arm` was called this session. Prevents throughline evaluation sessions from writing anywhere outside their scratchpad.
**Fail posture:** CLOSED on parse error while armed; exit 0 (no-op) if not armed.
**DEVIATION:** uses mixed exit signals — parse-error deny uses exit 2 + stderr (house-standard), but the outer non-scratchpad deny uses exit 1 + stdout JSON (non-standard). Functionally works; inconsistent within the same script.

#### A13. guard_sheet_writes.sh
**Matcher:** Bash
**Step chain:** `Claude → Bash → gws sheets → (1) check LIFEHACK_SHEET_CONFIRM=1 bypass → (2) READ branch (values get/batchget/metadata): if command names _LLM_GUIDE/LLM/README/instructions → record per-sheet marker at ~/.claude/run/sheet-llm/<SHEET_ID> (TTL 12h) → (3) WRITE branch: check marker freshness → DENY (deny_llm) if not fresh → (4) spreadsheets.batchUpdate → DENY (deny_struct) → (5) values clear/delete/batchclear → DENY (deny_destr) → (6) values batchUpdate → DENY (deny_destr) → (7) values update with column-range (A:Z pattern) → DENY (deny_destr) [hook]`
**Stores protected:** any Google Sheet via gws. The marker system mechanically enforces the "read the LLM guide tab FIRST" invariant before any write is permitted on that sheet.
**Three deny tiers:** `deny_llm` (LLM guide not read first) · `deny_struct` (structural schema change) · `deny_destr` (destructive value write).
**Bypass:** `LIFEHACK_SHEET_CONFIRM=1` in the command (for pre-approved cron writers with no human-in-loop).
**Fail posture:** CLOSED — jq parse error → deny.

#### A14. guard_sheet_formula_writes.sh
**Matcher:** Bash
**Step chain:** `Claude → Bash → gws sheets values (update|batchUpdate) → check LIFEHACK_SHEET_CONFIRM=1 bypass → extract sheet ID + target ranges → gws LIVE read-back with valueRenderOption=FORMULA → if any target cell starts with "=" or contains lock emoji 🔒 → DENY exit 2 [hook]`
**Stores protected:** formula cells and lock-emoji-marked cells in any Google Sheet.
**Live API call:** makes an actual `gws` call AT guard time (during PreToolUse) to read the live cell content before the proposed write executes. This is the strongest formula-protection mechanism in the fleet — reads truth, not command text.
**Fail posture:** CLOSED — any `gws`/`jq`/parse error → deny.
**Known edge:** ARRAYFORMULA spill cells read blank (gws returns empty for spill children); a write to a spill range is NOT caught by this guard. Mitigated by the append-only skill rule + lock emoji header strategy.

#### A15. guard_plan_structure.sh
**Matcher:** ExitPlanMode
**Step chain:** `ExitPlanMode event → guard_plan_structure.sh extracts plan text from tool_input.plan → grep for Phase, Task, Verify (case-insensitive) → if any missing → DENY exit 2 [hook]`
**Purpose:** quality gate — enforces the Phase→Feature→Task+Verify structure mandated by the planning SOP.
**Fail posture:** OPEN on empty/unparseable plan text — deliberate; this is a quality gate, not a security control. A transient parse failure must not block a valid plan.

---

#### ExitPlanMode non-blocking recorder (always exits 0 — NOT a blocking guard)

#### A16. plan_flag.sh record (ExitPlanMode, non-blocking)
**Matcher:** ExitPlanMode
**Step chain:** `ExitPlanMode event → plan_flag.sh record → reads plan text from stdin, extracts H1 heading, finds newest ~/.claude/plans/*.md by mtime → writes ~/.claude/run/plan/plan-<key>.flag with name + plan_file + armed_at + session [hook, state-writer]`
**Purpose:** state recorder, not a gate. Arms the plan HUD (visible in `session_context_loader.sh` + the statusline) and provides the plan-file path for the `/save` Step 8 Wake Routine handoff. This hook fires under ExitPlanMode (same event category as `guard_plan_structure.sh`) but exits 0 unconditionally — it records state, never blocks.
**Always exits 0** — advisory, not blocking.

#### A17. ingest_gate_enforce.sh (unified external-read gate)
**Matchers:** Bash · WebFetch · WebSearch · Read · Grep · Glob — **SIX tools.** The registration SHAPE differs between repos: the donor carries four separate `settings.json` entries (Bash, WebFetch, WebSearch, Read); the destination carries ONE PreToolUse entry with `"matcher": "Bash|WebFetch|WebSearch|Read|Grep|Glob"`. Grep and Glob are not dead registration — they carry their target under `path` rather than Read's `file_path`, so the hook handles `Read|Grep|Glob` as a single case that tries `file_path` first and `path` second, then runs the same downstream pipeline: file-type check, scratch-dir reader-actor lock, carve-outs, trusted-zone comparison. A path-less Grep or Glob names nothing external and falls through to the same `exit 0` an empty Read `file_path` already does.
**This is the hook-plane's most complex guard.** Full mechanics live in the `security-ingest-gate` element (`elements/security-ingest-gate.md`); summary here for the hook-plane's category picture.

**Step chain by channel:**
- `model → WebFetch → (network) → BLOCK unconditionally → redirect: safe_fetch.py [hook]`
- `model → WebSearch → (network) → BLOCK unconditionally → redirect: /websearch or safe_search_api.sh [hook]`
- `model → Read(.pdf/.docx/.doc/.xlsx/.xls/.csv) → file → BLOCK → redirect: safe_pdf/docx/xlsx/csv.py [hook]`
- `model → Read(external .txt/.md OUTSIDE trusted zone: clone + ~/.claude + Drive Lifehack) → file → BLOCK → redirect: safe_read.py [hook]`
- `MAIN session → Read(/tmp/rdr, /tmp/ingest_body) → sanitized scratch → BLOCK (reader-actor lock); SUB-AGENT (agent_id set) → ALLOW exit 0 [hook]`
- `model → Read(state/email-summary/threads-v2/*) → BLOCK → redirect: email_service_read.py [hook]`
- `model → Read(state/item-store/*) → BLOCK → redirect: item_store_read.py [hook]`
- `model → Bash(gws gmail messages.get format:full/minimal/raw) → email body → BLOCK → email_convert.py [hook]`
- `model → Bash(gws calendar events list) → invite free-text → BLOCK → safe_calendar.py [hook]`
- `model → Bash(gws tasks tasks list/get) → task free-text → BLOCK → safe_tasks.py [hook]`
- `model → Bash(gws drive files export, raw) → client Doc body → BLOCK → safe_read/safe_docx/safe_pdf.py [hook]`
- `model → Bash(export LIFEHACK_SKIP_*) → env → BLOCK (sanitizer-bypass var an injection reaches for) [hook]`
- `MAIN session → Bash(cat/head/tail/less/xxd /tmp/rdr or /tmp/ingest_body) → scratch → BLOCK (shell reader-actor lock) [hook]`
- `non-janitor → Bash(write to email-summary/ or item-store/) → store → BLOCK (single-writer invariant) [hook]`
- `MAIN session → Bash(cat/head/tail email-summary/threads-v2/ or item-store/) → store → BLOCK → matching adapter [hook]`

**Subsumption history:** `ingest_gate_enforce.sh` was built at Window-5 (2026-07-04) to unify six predecessor guards. Those six are now UNREGISTERED DEAD CODE on disk: `enforce_email_sanitize.sh`, `guard_web_fetch.sh`, `guard_web_search.sh`, `guard_file_reads.sh`, `sanitize_calendar_reads.sh`, `guard_skip_safe_backdoor.sh`. They have no `settings.json` entry and never fire. The consolidation is complete and correct.
**~~Known guidance gap:~~ NOT TRUE HERE — corrected 2026-08-15.** ~~The WebSearch case deny message directs blocked callers to `safe_search.sh` (the Chrome fallback) rather than `safe_search_api.sh` (the Serper primary). A wrong redirect — not a false-positive/negative, but misdirects the model to the slower fallback path.~~ **CORRECTION, read from the live hook this session (`system/hooks/ingest_gate_enforce.sh` lines 122-124):** the WebSearch deny message here already redirects to `bash <repo>/system/tools/safe_search_api.sh` — the Serper primary — and goes further than the donor by naming the sub-agent case out loud ("The /websearch skill wraps it; a sub-agent cannot run a skill, so it calls the script directly"). The donor's wrong redirect was not carried over. The struck sentence is left visible because it was true of the donor when this element was written.
**Fail posture:** CLOSED — unparseable JSON input → deny.

#### A18. guard_canon_write.sh
**Matcher:** Write|Edit
**Step chain:** `Claude → Write/Edit → **/canon/** file → Python3 checks: (a) stale markers (shelf-life, expires, tier:snapshot) → DENY; (b) for Write: authority:user absent → DENY; ~~(c) for Edit: authority:skill or authority:archivist present → DENY~~; else → ALLOW exit 0 [hook]`
**Stores protected:** any file under `**/canon/**` — the permanent ground-truth store.
**Fail posture:** CLOSED — parse error → deny.
> **⚠ CORRECTED:** step (c) above no longer denies. Verified live in the shipped hook: an Edit
> carrying `authority: skill` or `authority: archivist` onto a canon file now ALLOWS (exit 0) with
> only an advisory message. The script's own comment states it plainly: "This is a speed bump, not
> a block (T9.5d, 2026-08-15) — the authority:user rail was dropped 2026-08-11 because it was
> self-attestation a machine types as easily as a person." So this is a map fix, not a new defect:
> the code made a deliberate, dated decision to downgrade this rail from a block to an advisory, and
> this doc never caught up. Stale-marker blocking (a) and the Write-side `authority:user` check (b)
> are unaffected and still deny live.

#### A19. guard_gmail_destructive.sh
**Matcher:** Bash
**Step chain:** `Claude → Bash → gws gmail (messages|threads) (delete|batchDelete|trash) → guard_gmail_destructive.sh scope-gates on "a gws binary is NAMED anywhere" + "gmail is named" → passes the command to system/hooks/lib/gws_guard.py --service gmail --require-any messages,threads --destructive delete,batchDelete,trash → parser rc=7 → DENY exit 2 [hook]`
**Stores protected:** the Gmail mailbox itself. Gmail deletion is IRREVERSIBLE; a label move is not. The ingest skills move mail by LABEL ONLY and their own hard rule says "NEVER delete. NEVER trash." — until 2026-07-28 nothing enforced that, and a repo-wide search found no guard on Gmail delete or trash anywhere. Prose was the only thing between an autonomous cron job and a wiped inbox. Measured the same week: a cron circuit-breaker bug half-opened an ingest job and it processed 43 threads it was never handed. An ingest job CAN run away; if the runaway verb had been `delete` instead of `read`, nothing would have stopped it.
**Gate logic:** blocks ALL of `delete` / `batchDelete` / `trash` on messages/threads, from every desk and skill, **with no confirm path** — an unattended cron has nobody to confirm to. `untrash` is checked FIRST and always passes (it is recovery, and "untrash" contains "trash" as a substring — the positive-token-inside-the-negative-state trap). `modify` (label moves) and every read verb pass untouched. The redirect names the sanctioned reversible operation: `gws gmail users threads modify --add-label-ids … --remove-label-ids …`. If mail genuinely must be removed, a HUMAN does it in the Gmail UI.
**Why the shared parser:** matching a POSITION, not a keyword. The first version grepped the whole command and false-positived on its own author within an hour of shipping — it blocked a python heredoc that was WRITING that text into a plan file; nothing was being executed, the words were data. The parser now lives in one place (`system/hooks/lib/gws_guard.py`) because three other guards needed exactly this and each got it wrong differently: it splits at real shell separators, only considers a segment whose first word is the gws binary, **strips assignment prefixes** (`ID=18abc gws gmail users threads trash …` used to be ALLOWED — `seg.split()[0]` returned the assignment, failed the `^gws$` test and skipped the segment), keeps command substitutions visible so indirection is still detectable, and treats an unresolvable command as UNKNOWN → fails closed.
**Fail posture:** CLOSED — unreadable stdin, a JSON parse failure, or a missing/unreadable `lib/gws_guard.py` all DENY. A guard protecting an irreversible act must never allow when it cannot read its own input; the cost of a false block (retry with a label move) is trivially smaller than a false allow.
⚠ **This guard is present and registered in BOTH repos** — it is not new here. The staleness it fixes is in this element: `guard_gmail_destructive.sh` has been listed in `generated_from:` since 2026-08-01 while Category A enumerated A1–A18 and had no body entry for it.
⚠ **Speed bump, not a boundary** (the hook's own header, measured 2026-08-14): this guard reads a command as TEXT, and a shell has infinite equivalent spellings, so a text matcher is always one phrasing behind. Four guards were fire-tested then attacked by two independent auditors — the first found 20 bypasses in ~20 minutes, the second found 13 more after a rewrite, and after three rounds of hardening 1 of 27 tested attack forms still passes. Every hole was in a guard reading a command STRING. A control that must not be bypassed belongs on a typed tool, not here.

---

### CATEGORY B — PostToolUse ADVISORIES (never block; always exit 0)

PostToolUse hooks fire AFTER the tool completes. The harness executes them after the call and uses their stderr output as advisory context. They CANNOT block. All correctly exit 0.
> **⚠ CORRECTED: only 2 of the 5 hooks this category names actually exist and are registered** —
> `validate_on_write.sh` (B2) and `observability_logger.sh` (B4). `nudge_flow_drift.sh` (B1),
> `auto_register_skill.sh` (B3), and `guard_marc_narrative.sh` (B5) do not exist anywhere in this
> repo and have zero registrations. The mechanism described for the 2 that exist (fires after the
> tool, cannot block, exits 0) is confirmed true; the roster is overstated by 3 entries. Entries kept
> below as history per house rule.

#### B1. nudge_flow_drift.sh — ⛔ DOES NOT EXIST HERE (verified: no file, no registration)
**Matcher:** Write|Edit
**Step chain:** `Write/Edit completes → nudge_flow_drift.sh reads file_path → searches system/organism/elements/*.md for any entry whose generated_from list contains the basename → if match: stderr advisory message citing affected element [honor]`
**Purpose:** surface when an edit touches a file that is the source-of-truth for an organism element — prompting the author to check whether the element entry needs updating.
**Stores read:** `system/organism/elements/` (read-only scan).

#### B2. validate_on_write.sh
**Matcher:** Write|Edit
**Step chain:** `Write/Edit completes → validate_on_write.sh → python3 system/tools/validate_frontmatter.py on the written file_path → if REQUIRED_FIELDS missing: stderr advisory reminder [honor]`
**Historical note (LIVE CODE vs PROSE conflict):** was INERT until 2026-07-21. The old version sent advisory output to stdout and used `|| true`, swallowing it entirely. Fixed to emit on stderr — the advisory now surfaces. The file header says "Currently ADVISORY — does not block."
**Current vs TARGET:** advisory nudge in its current posture. The outstanding TARGET-state item (defect d in the gap-and-health audit) is to flip this to blocking PreToolUse enforcement AFTER cleaning ~526 existing frontmatter violations in the tree (the prerequisite rename of `type:` → `record_type:` on ~526 files). The operator's decision: MAKE IT REAL ENFORCEMENT (option A). This flip is OPEN — not yet executed. This is the most concrete reason for the PARTIAL label on this element.
**Exit-code contract (the destination delta):** `validate_frontmatter.py` at the destination returns THREE answers, not two — `0` valid-or-skipped, `1` a real missing required field, `2` cannot evaluate (not markdown, file gone) — and `validate_on_write.sh` there tests `if [ "$?" = "1" ]`, so only a genuine violation speaks. The donor's wrapper uses `if MSG=$(…); then : else printf …`, which treats ANY non-zero as something to say and therefore conflates "cannot evaluate" with "violation": every `.py` write produces "cannot evaluate: not markdown → add the missing field(s)," which is both constant and nonsense advice, and constant nonsense is how a real reminder gets skimmed past. The destination also resolves the validator through `${CLAUDE_PROJECT_DIR}` where the donor hardcodes an absolute clone path.

#### B3. auto_register_skill.sh — ⛔ DOES NOT EXIST HERE (verified: no file, no registration)
**Matcher:** Write|Edit
**Step chain:** `Write/Edit completes on */skills/*/SKILL.md → if global skill (clone or Drive root): log + skip (already symlinked); if desk skill: create ~/.claude/commands/<name>.md stub [hook, automation]`
**Note:** the hook's own script header says "matcher: Write" but the live `settings.json` registration is `Write|Edit` — the settings.json registration is ground truth for what actually fires.
**Purpose:** when a new desk skill is written, automatically create the command stub that makes it invocable without a full restart.
**Always exits 0.** Not a guard — an automation convenience.

#### B4. observability_logger.sh
**Matcher:** * (all tools)
**Step chain:** `Every tool call completes → Python3 builds compact JSON line (ts, tool, desk, session; if Bash+gws: full gws_command) → appends to /tmp/lifehack-observability-buffer.jsonl [hook, audit trail]`
**Stores written:** `/tmp/lifehack-observability-buffer.jsonl` (buffer). Flushed to Drive `system/observability/YYYY-MM-DD.jsonl` at session end by `session_flight_recorder.sh` (Stop hook).
**Purpose:** per-session tool-call log; the gws command capture enables after-the-fact capability-boundary audits.
**Always exits 0.**

#### B5. guard_marc_narrative.sh — ⛔ DOES NOT EXIST HERE (verified: no file, no registration)
**Matcher:** Write|Edit
**Step chain:** `Write/Edit to desks/marc/organism/narratives/*.md or scenarios/*.md → Python3 marc-narrative-check.py validates C5 contract (frontmatter, closed vocab, axis wall) → if fail: stderr advisory message [honor]`
**Scope:** narrowly scoped to the Marc desk's narrative/scenario registry.
**Misnomer:** named `guard_` but is a PostToolUse advisory (cannot block). The hard stop lives in the weekly gather-gate, not here.
**Always exits 0.**

---

### CATEGORY C — SessionStart LOADERS (non-blocking; context injection)

SessionStart hooks fire once when the session opens. They emit to stdout, injecting context before the first model turn. They cannot block.

#### C1. session_context_loader.sh
**Matcher:** (empty — fires on all sessions)
**Step chain:** `Session starts → resolves CWD from stdin JSON → detects desk from path (*/desks/<desk>/*) → emits desks/<desk>/canon/*.md OR records/canon/*.md → emits state/telos.md → emits state/pulse-brief.md (if present and not NO_ACTION) → all to stdout as injected context [hook, context-inject]`
**Stores read:** `desks/{desk}/canon/*.md` OR `records/canon/*.md`, `state/telos.md`, `state/pulse-brief.md`.
**Purpose:** the CLAUDE.md pyramid's "always-loaded floor" — ensures every session starts with desk-appropriate canon and strategic context without manual `/read`. This hook IS the mechanical enforcement of the canon-loads-on-session-start invariant.
**Always exits 0.**

---

### CATEGORY D — UserPromptSubmit INJECTORS (non-blocking; emit to stdout before model responds)

These fire on every user prompt turn, before the model's response. They emit advisory/context text to stdout (injected into the model's context). None can block. All exit 0.

#### D1. rating_capture.sh
**Purpose:** detect 1–10 ratings in the prompt (patterns: `N/10`, `N - comment`, bare `N`); log to `Drive/system/learnings-signals.jsonl`; for ratings ≤ 3, write a failure-capture file to `Drive/system/learnings/`. Quality-signal observer — no injection. `[honor]`

#### D2. pm_persist.sh
**Purpose:** the most important UserPromptSubmit hook. On every turn: (a) re-injects PM orientation ("project-manager ACTIVE" + doc path + anchor excerpt from the armed brief's `## CURRENT STATE` or `## NEXT ACTION` section — NOT `## SCRATCHPAD`) so the brief stays alive across context compaction; (b) refreshes TTL (`armed_at`) on pm/plan/scratch flags to prevent mid-session expiry; (c) injects huddle-room reminder if huddle flag active.
**State read:** `~/.claude/run/pm/pm-<key>.flag` (written by `pm_flag.sh arm`).
**The brief is not auto-loaded by magic — pm_persist.sh is the mechanical carrier.** `[honor]` (outputs advisory text; cannot block).

#### D3. skill_anchor_inject.sh
**Purpose:** re-injects the armed skill's LEAN anchor text every turn (anti-context-rot). Truncated to 1,200 chars; strips control/zero-width/bidi chars. Prevents skill framing from sinking as context accumulates.
**State read:** `~/.claude/run/anchor/anchor-<key>.flag` (written by `skill_anchor.sh`, called at skill launch). `[honor]`

#### D4. inject_compute_mechanically.sh
**Purpose:** fires for (a) finance/billing desks (deryl, clair) auto-arm; (b) numbers-mode flag; or (c) hard math token in prompt (currency/percent/digit-op-digit regex). Injects "compute mechanically" doctrine reminder. `[honor]`

#### D5. simplify_anchor_inject.sh — ⛔ DELETED 2026-08-05 (failed experiment; fired EVERY turn, not 1-in-10). Entry kept as history; the hook does not exist.
**Purpose:** always-on (no flag). Rotates among 10 variants (RANDOM % 10) of the "translator register" reminder (lead-with-answer, numbered what-needs-you, billionaire-attention model, etc.). Anti-wallpaper by rotation. (Updated 2026-07-23 to 10 variants — variants 8 and 9 added.) `[honor]`

#### D6. inject_sop_before_build.sh
**Purpose:** detects build-verb + tracked noun (skill/hook/desk/sheet/dashboard/cron/ingest) in the prompt; injects a hard pointer to the relevant SOP (`skill-building-sop.md`, `hook-sop.md`, `desk-building-sop.md`, etc.) before the model responds. `[honor]`

#### D7. scratch_sweep_nudge.sh
**Purpose:** active when scratch_flag OR pm_flag is armed; reads transcript_path for token count; at ≥ 600k tokens fires once per 100k-bucket → injects "context deep, consider /save and fresh session" warning.
**Settings anomaly:** the `settings.json` entry for this hook is missing the `"matcher"` key (present as empty `""` in all other UserPromptSubmit entries); minor JSON anomaly with no functional impact. `[honor]`

#### D8. announce_plan_write.sh
**Purpose:** diffs `~/.claude/plans/*.md` mtimes vs a per-session state file. For NEW plans: injects "📋 plan written: <name>" to stdout AND writes a durable pointer into the active project brief's `## SCRATCHPAD` (or `~/.claude/run/plan-ledger.md` fallback). State-writer + injector. `[honor]`

#### D9. save_routing_hint.sh
**Purpose:** regex-matches prompt for save-verb phrases (save/remember/capture + demonstrative); bails if prompt looks like a handoff reload (`## SCRATCHPAD` or `/checkin` fingerprint); if save intent: injects routing hint pointing to pm_flag-armed brief's `## SCRATCHPAD`, or asks "No project active — save to standalone scratchpad, or which project's brief?" The CLAUDE.md save-routing rule is the always-loaded backstop for this behavior. `[honor]`

---

### CATEGORY E — Stop GATES AND RECORDERS

Stop hooks fire when the session ends. Most are recorders (always exit 0). Two are conditional gates that can emit `{"decision":"block",...}` to bounce the stop.

#### E1. session_flight_recorder.sh
**Step chain:** `session stops → reads transcript_path for tool_calls count + Write/Edit count + duration + /save presence → appends one JSON line to system/flight-log.jsonl → flushes /tmp/lifehack-observability-buffer.jsonl to system/observability/YYYY-MM-DD.jsonl → stubs system/learnings.md if missing → nudges if /save not called → ~~clears ~/.claude/current_email_lane (security: prevents stale email lane from leaking to next session)~~ [hook, recorder]`
**Stores written:** `system/flight-log.jsonl`, `system/observability/YYYY-MM-DD.jsonl`, `system/learnings.md` (stub only), ~~`~/.claude/current_email_lane` (cleared)~~.
> **⚠ CORRECTED:** the script does NOT clear `current_email_lane`. Its own comment states the
> donor's clearing logic was never ported — that mechanism was already retired in the donor system
> itself and does not exist in this repo at all. The claim that this prevents a stale email lane
> from leaking to the next session is not true of the shipped hook.
**Always exits 0.**

#### E2. mirror_plans.sh — ⛔ DOES NOT EXIST HERE (verified: no file anywhere in this repo). Entry
kept as history; the hook never shipped in this repo, only in the donor system it describes.
**Purpose (donor description, not this system):** would have rsynced `~/.claude/plans/` → a
per-hostname Drive folder on session stop, so a plan built on one machine survived a handoff. No such
hook runs here. The gap this would have covered is real and unaddressed: `~/.claude/plans/` has no
backup lane on this system.

#### E3. translator_gate.sh
**Step chain:** `session stops → if stop_hook_active: exit 0 (loop-safe) → check per-session arm flag (~/.claude/run/translator-gate/<sid>.arm) OR global OBSERVE-ALL flag → if neither: exit 0 (DORMANT) → if armed: extract last_assistant_message → mechanical pre-check (≥5 bold sections OR ≥6 file-path coordinates → mech fail) → else: grade via claude -p with claude-haiku-4-5-20251001 (70s timeout) → parse JSON verdict from last {...} block → OBSERVE mode: log only → ENFORCE mode + verdict=fail: emit {"decision":"block","reason":...} [hook, conditional gate]`
**Purpose:** grades the last reply's voice compliance against the translator rubric. Bounces the turn in ENFORCE mode when the reply fails.
**⛔ DELETED — the hook does not exist here. Entry kept as history** (same convention as D5 above). The Haiku grader was RETIRED per debt-ledger entry [TRANSLATOR-GATE-RIP] (state:parked, 2026-07-14): it rubber-stamped replies and added ~60s/turn latency, and the ask-gate moved to the prompt layer. The donor then left the script on disk and still registered in `settings.json` — deprecated-in-place, non-functional as a real gate, "awaiting removal." **The housekeeping practice here is the opposite one: a retired hook is deleted outright** — script removed from `system/hooks/`, registration removed from `settings.json`, no `.bak` file left beside it, nothing dormant and nothing "awaiting removal." Verified: `system/hooks/` contains no `translator_gate.sh`, no `guard_plan_fork.sh` and no `.bak` files at all, and `settings.json` has zero references to either. The reason is the one this element documents everywhere else — a registered-but-inert script reads as the active control to every presence-based audit, which is precisely the false-green the hook-plane exists to kill.
**Dormancy design:** DORMANT unless explicitly armed per-session. No arm file → exits 0 immediately.
**Loop-safe:** `stop_hook_active` guard prevents infinite bounce.

#### E4. scratch_capture_gate.sh
**Step chain:** `session stops → if stop_hook_active: exit 0 (loop-safe) → resolve active pad (scratch_flag override > pm_flag brief) → if no pad armed: exit 0 (dormant) → read transcript for token count → compute bucket (TOK / 100k) → if bucket > last recorded bucket in .cap-sess-<id>.state: compute ADDED lines (current ## SCRATCHPAD section minus last .pad sidecar) → emit {"decision":"block","reason":"SCRATCHPAD CHECKPOINT..."} with added lines + request receipt [hook, conditional gate]`
**Purpose:** prevents context loss — bounces the session stop once per ~100k-token bucket when new scratchpad content has accumulated, forcing the model to emit a capture receipt before closing.
**Fires whenever a pad is armed + the token bucket advances** — no per-session arm flag required (unlike `translator_gate`).
**Loop-safe:** `stop_hook_active` guard.

---

### FLEET DEAD CODE (files in system/hooks/, NOT in settings.json — INERT)

The following scripts exist on disk but are NOT registered in `settings.json`. They NEVER fire.

**Superseded by `ingest_gate_enforce.sh` at Window-5 (2026-07-04):**
- `enforce_email_sanitize.sh` — subsumed into ingest_gate Bash branch (c)
- `guard_web_fetch.sh` — subsumed into ingest_gate WebFetch case
- `guard_web_search.sh` — subsumed into ingest_gate WebSearch case
- `guard_file_reads.sh` — subsumed into ingest_gate Read case
- `sanitize_calendar_reads.sh` — subsumed into ingest_gate Bash branch (d)
- `guard_skip_safe_backdoor.sh` — subsumed into ingest_gate Bash branch (a)

The six headers have not been updated to say "SUPERSEDED" — they read as if they are the active control. They are not. The consolidation is complete.

**Retired — and retirement means DELETED, not dormant:**
- `guard_plan_fork.sh` — donor-only. It survives in the donor carrying a RETIRED banner in its script header ("DO NOT RE-REGISTER"), which is exactly the shape this list exists to warn about. Here the script is gone from `system/hooks/` entirely, along with `translator_gate.sh` and every `.pre-*.bak` sidecar. A banner asks the next reader not to re-register; deletion makes re-registration impossible.

**Utility flag managers (not hooks; invoked by hooks as helper commands):**
- `huddle_flag.sh` — invoked by `pm_persist.sh`
- `pm_flag.sh` — invoked by multiple hooks; also called by `plan_flag.sh` internally (but `pm_flag.sh` itself is not a harness event)
- `scratch_flag.sh` — invoked by `scratch_capture_gate.sh`
- `numbers_flag.sh` — invoked by `inject_compute_mechanically.sh`
- `throughline_flag.sh` — invoked by `guard_throughline_write_scope.sh`
- `skill_anchor.sh` — invoked by skills at launch; not a harness event

---

### PERMISSION LAYER (settings.json — NOT hooks; a separate control tier)

The `permissions.deny[]` block in `settings.json` hard-denies operations BEFORE any hook fires — at a lower layer. Covered operations:
- Bash: `gws auth logout` (bare + full-path variants)
- Read/Edit/Write: `~/.ssh/`, `~/.gnupg/`, `~/.config/gws/`, `~/.aws/`, `~/.kube/`, `**/.env`, `**/.env.local`, `~/Library/Keychains/`
- Write/Edit: `~/.claude/skills/`, `agents/`, `commands/`, `hooks/`, `settings.json`
- MCP: all Obsidian write operations; all Google Calendar write MCP ops; Gmail `create_draft`; all Asana write ops; Google Drive create/copy; Gmail `get_thread`; Drive `read_file_content` / `download_file_content`; Calendar `list_events` / `get_event`

**Critical limitation:** `permissions.deny[]` entries are bypassed by `--dangerously-skip-permissions`. The PreToolUse hooks (especially `guard_gws_logout.sh` and ~~`block_primary_calendar.sh`~~ its live successor `guard_calendar_writes.sh` [renamed; `block_primary_calendar.sh` does not exist on disk — see A2 above]) are the real backstops for non-interactive sessions because PreToolUse hooks are NOT bypassed by that flag.

---

### ENFORCEMENT MATURITY MAP

**LIVE + fire-testable (blocking PreToolUse guards):**
- `block_primary_calendar` → ⛔ does not exist here; live successor is `guard_calendar_writes.sh`,
  which now denies (exit 2) on unparseable/empty stdin too, since the fail-open bug in that path was
  closed in this pass — see A2 above
- `guard_gws_logout`: fail-closed; regex match; corrected exit channel (stderr+exit 2, post-2026-06-16); the ONLY real backstop for headless sessions
- `guard_write_paths`: fail-CLOSED since 2026-06-18 (parse error → deny); realpath resolution for symlinks; broadest file-write control in the fleet
- `guard_ledger_discipline`: full Python simulation of the edit before checking; fail-open only for non-ledger targets
- `guard_canon_write`: fail-CLOSED on parse error and on the stale-marker/authority:user checks;
  ~~the authority:skill/authority:archivist Edit-deny is no longer live~~ — see A18 above (that
  specific rail was downgraded to advisory-only 2026-08-15)
- `guard_organism_map`: fail-CLOSED; correctly distinguishes Write vs Edit
- `guard_tasks_writes`: fail-CLOSED; jq + grep; carve-out logic verified
- `guard_sheet_writes`: fail-CLOSED; TTL marker system + three deny tiers; makes LIVE gws call at guard time (guard_sheet_formula_writes.sh)
- `guard_sheet_formula_writes`: fail-CLOSED; live API read-back at guard time; formula protection strongest in the fleet
- `guard_plan_structure`: fail-OPEN (documented; quality gate, not security)
- `ingest_gate_enforce`: fail-CLOSED; 6 registered matchers (Bash · WebFetch · WebSearch · Read · Grep · Glob); all sub-cases branch to deny or exit 0; agent_id routing verified live 2026-07-04

**LIVE but with noted anomalies:**
- `guard_router_writes` → ⛔ does not exist here (verified: no file, no registration anywhere).
  Entry kept as history; the description below is the donor's.
  ~~uses exit 1 + stdout JSON (not house-standard); functions correctly; minor inconsistency~~
- `guard_throughline_write_scope`: mixed exit signals within the same script (exit 2 on parse, exit 1 on deny); inconsistent but functional
- `guard_egress`: fail-OPEN on parse error — intentional; LuLu is OS-layer backstop
- `enforce_egress_allowlist`: fail-OPEN when host unextractable — intentional; LuLu backstop
- `guard_statusline_lock`: fail-OPEN on parse (narrow scope; guard_write_paths backstops); delimiter-agnostic sed fix recently verified by conformance lab (2026-07-23)
- `validate_on_write` (PostToolUse): was INERT until 2026-07-21; now advisory; NOT yet blocking enforcement

**CONDITIONAL GATES (armed only; DORMANT by default):**
- `translator_gate` (Stop): **donor-only — DELETED here.** Retired per [TRANSLATOR-GATE-RIP]; the donor left it registered-but-inert, this fleet removed the script and its registration outright. `scratch_capture_gate` is the only live conditional gate.
- `scratch_capture_gate` (Stop): fires whenever a pad is armed + token bucket advances; always active with an armed project

**ADVISORY (PostToolUse/UserPromptSubmit/SessionStart/Stop recorders):**
All exit 0. Cannot block. Represent behavioral nudges and state-writing, not enforcement.

**HONOR-SYSTEM (no hook enforces these doctrine rules):**
The "doctrine outpaced enforcement" finding from the prior audit applies to the hook-plane directly. Named rules with NO hook backstop (the ~40 honor-system rules; the next-phase scope item hooks only the 3–5 with the highest blast radius):
- CLAUDE.md "Task tracker on command" and "Planning Output ALWAYS" — zero hook enforcement
- `skills/project-manager` SKILL.md JOURNAL-FIRST hard rule — no hook backstop
- `system/confidence-model.md` "machine NEVER assigns type:rule" — convention only
- `system/google-policy.md` — 23 of 26 hard prohibitions are prompt-only; no runtime block

---

### KNOWN GAPS (source-documented; not prose speculation)

1. **Bash file-write bypass** (`guard_write_paths.sh` `KNOWN-GAP` comment, 2026-07-14, option a accepted): Bash file-writes (`echo >`, `tee`, `cp`, heredoc) bypass BOTH `guard_write_paths.sh` AND `guard_organism_map.sh` entirely — both only match Write|Edit tools. Mitigation: discipline + code review. No mechanical backstop for the Bash path.

2. **guard_egress fail-open on parse error** (intentional): acceptable because LuLu is the OS-layer backstop; false-positive risk of blanket deny outweighs the risk.

3. **enforce_egress_allowlist fail-open on unextractable host** (intentional): LuLu backstop.

4. **guard_sheet_formula_writes ARRAYFORMULA spill cells** (known edge): spill-range cells read blank; a write to a spill range is not caught. Mitigated by append-only skill rule + lock emoji strategy.

5. **~~ingest_gate_enforce wrong redirect message~~ — NOT A GAP HERE; corrected 2026-08-15.** ~~(guidance-accuracy gap): the WebSearch case deny message (line 59 of `ingest_gate_enforce.sh`) directs blocked callers to `safe_search.sh` (the Chrome fallback) instead of `safe_search_api.sh` (the Serper primary). Not a false-positive/negative; misdirects the model to the slower fallback path.~~ **CORRECTION:** the live hook was read this session — `system/hooks/ingest_gate_enforce.sh` lines 122-124 redirect to `safe_search_api.sh`, the Serper primary. The line number in the struck text was also wrong for this repo (the WebSearch case is at 122, not 59). Struck rather than deleted so the donor-era finding stays legible.

6. **validate_on_write not yet blocking** (OPEN defect d from the audit): the flip to PreToolUse blocking enforcement awaits a ~526-file frontmatter cleanup (`type:` → `record_type:` rename). This is the most concrete PARTIAL→LIVE gap for this element as a whole.

7. **settings.json scratch_sweep_nudge missing "matcher" key** (minor JSON anomaly): all other UserPromptSubmit entries have `"matcher": ""`; this entry is missing that key. No functional impact on current harness behavior.

8. **Six superseded hook headers not updated** (documentation debt): `enforce_email_sanitize.sh`, `guard_web_fetch.sh`, `guard_web_search.sh`, `guard_file_reads.sh`, `sanitize_calendar_reads.sh`, `guard_skip_safe_backdoor.sh` headers read as if they are the active control; they are inert dead code.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** intercept every Claude tool call at runtime to enforce behavioral invariants autonomously, without asking the human. The human approves the hook DESIGN at creation; enforcement then runs mechanically. This is the system's immune system — the layer that makes it safe to give Claude broad permissions, because the rails enforce themselves.

**Historical note from the prior audit (identity.md §Claim 3):** the hook-plane is the MOST COMPLETE and MOST SELF-SUSTAINING layer in the codebase — more tooling-mature than the memory flywheel (the stated core). This is a sequencing observation: you build the immune system first, or the heart gets corrupted. It is a structural choice, not an accident.

**Current state → PARTIAL, for a precise reason:**
- The blocking PreToolUse guard fleet is LIVE and substantial: 17 distinct guards covering calendar, tasks, egress, file-writes, sheets, canon, plans, skill quality, and the unified ingest gate.
- What pulls the plane below LIVE:
  1. `validate_on_write.sh` is still advisory (PostToolUse), not blocking PreToolUse enforcement — the OPEN defect-d flip is the most concrete gap.
  2. ~40 stated doctrine rules remain honor-system with no hook backstop; the next-phase enforcement build is a TARGET item (scope.md §5K-5: hook the 3–5 rules with the highest blast radius, NOT all 40).
  3. Three noted anomalies (router guard exit code, throughline guard mixed exits, allowlist fail-open) are minor but documented.

**TARGET:**
1. Flip `validate_on_write.sh` to blocking PreToolUse after the ~526-file `type:` → `record_type:` rename (the prerequisite; tracked in the project brief's `## OPEN LOOPS`). Re-register under PreToolUse Write|Edit.
2. Next-phase enforcement: identify the 3–5 highest-blast-radius honor-system rules and build hooks for them (scope.md §5K-5). NOT all 40.
3. Fix the six superseded hook headers to say "SUPERSEDED BY ingest_gate_enforce.sh."
4. Fix `guard_router_writes.sh` to use exit 2 + stderr (house-standard).
5. Fix `guard_throughline_write_scope.sh` to use exit 2 + stderr for the outer deny (house-standard throughout).
6. ~~Fix the `ingest_gate_enforce.sh` WebSearch case deny message to point to `safe_search_api.sh` (not `safe_search.sh`).~~ **ALREADY TRUE HERE — struck 2026-08-15.** Verified against the live `system/hooks/ingest_gate_enforce.sh` (lines 122-124) this session: the redirect already names `safe_search_api.sh`. Nothing is owed on this target.

---

### INTEROP SEAMS (shared-state edges to other elements)

**PreToolUse guards (Write/Edit matchers):**

GUARDED-BY `save` · `guard_write_paths`, `guard_canon_write`, `guard_ledger_discipline`, `guard_throughline_write_scope` wall every write `/save` performs; without these guards, `/save`'s writes to `canon/`, `state/debt-ledger.md`, and the Drive spine would be ungated.

GUARDED-BY `canon` · `guard_canon_write` enforces `authority:user` + no stale/fast-stale content on every write to any `**/canon/**` file; the canon element is the downstream protected store.

GUARDED-BY `project-manager` · `guard_ledger_discipline` protects `state/debt-ledger.md` (the debt side of the project management plane); `guard_throughline_write_scope` gates `/throughline` scratchpad-only writes while the flag is armed.

GUARDED-BY `skill-system` · `enforce_skill_frontmatter` blocks a malformed `SKILL.md` at birth; `guard_write_paths` blocks Write/Edit to `~/.claude/skills/` (symlinked clone path) protecting the skill-registration store.

GUARDED-BY `organism-map` · `guard_organism_map` blocks full-content Write to `system/organism/manual.md` and `map-format-specs.md`; the self-schematic protects its own attack surface with a hook in the fleet it describes.

**PreToolUse guards (Bash matchers):**

GUARDED-BY `gws-plane` · `block_primary_calendar`, `guard_tasks_writes`, `guard_sheet_writes`, `guard_sheet_formula_writes`, `guard_gws_logout` wall every gws write in the tool plane; the gws-plane element is the channel these guards gate.

GUARDED-BY `security-ingest-gate` · `ingest_gate_enforce.sh` IS the security-ingest-gate element's physical body — the hook-plane provides the enforcement carrier; the security-ingest-gate element is the detailed description of that same artifact.

READS `egress-allowlist-wall` · `enforce_egress_allowlist.sh/py` reads `system/egress-allowlist.md` on every Bash call; the allowlist is the hook's shared policy store.

WRITES-> `sentinel` · `enforce_egress_allowlist.py` appends blocked-host events to `system/logs/sentinel-events.jsonl` on every deny; the sentinel element's security event log is the downstream store for these block records.

GUARDED-BY `egress-allowlist-wall` · `guard_egress` + `enforce_egress_allowlist` gate all raw outbound Bash calls; the egress-allowlist-wall element is the downstream policy store these hooks enforce.

**PostToolUse nudges:**

FEEDS `skill-system` · `auto_register_skill` writes `~/.claude/commands/<name>.md` stub after a desk `SKILL.md` write; the skill-system's registration store is the downstream consumer.

FEEDS `organism-map` · `nudge_flow_drift` reads `system/organism/elements/*/generated_from` and emits an advisory when an edited file is cited there; the organism element files are the shared store.

FEEDS `helm` · `observability_logger` (all tools) appends to `/tmp/lifehack-observability-buffer.jsonl` on every call; `session_flight_recorder` flushes that buffer to `system/observability/YYYY-MM-DD.jsonl` at Stop; helm reads those for its Security/observability tile.

FEEDS `validate` (frontmatter system) · `validate_on_write` reads each written file via `validate_frontmatter.py`; all save/archivist/memory-read elements depend on frontmatter being well-formed; advisory today, TARGET is blocking.

**SessionStart:**

FEEDS `claude-md-pyramid` · `session_context_loader` reads `desks/{desk}/canon/*.md` + `state/telos.md` and injects them into session context; this hook IS the mechanical enforcement of the canon-loads-on-session-start invariant. The hook-plane provides both the guard (write side, via `guard_canon_write`) and the injector (read side, via `session_context_loader`) for the canon store.

**UserPromptSubmit injectors:**

SHARES `pm-flag` · `pm_persist.sh` reads `~/.claude/run/pm/pm-sess-<id>.flag` (written by `pm_flag.sh`); the flag store is shared between the pm-flag element (writer) and this hook (reader-injector) every turn.

SHARES `project-manager` · `pm_persist.sh` injects the active brief's `## SCRATCHPAD` section every turn; the brief (the project-manager element's primary store) is the shared file; `pm_persist` is the bridge that keeps the brief alive across context compaction.

SHARES `skill-system` · `skill_anchor_inject.sh` reads `~/.claude/run/anchor/anchor-<key>.flag` (written by `skill_anchor.sh`, called by skills at launch); the anchor flag store is shared between the skill-system element and this hook.

SHARES `build-plan-plane` · `announce_plan_write` monitors `~/.claude/plans/` (written by plan mode / `plan_flag.sh`) and injects a visible pointer to new plans; the plan file store is shared with the build-plan-plane element.

FEEDS `save` · `save_routing_hint` injects routing context on any save-phrase; reads `pm_flag` status to route correctly — the pm-flag store is the shared arbiter; the hook mediates the gap between "save this" natural language and the full `/save` flow.

**ExitPlanMode:**

GUARDED-BY `build-plan-plane` · `guard_plan_structure` blocks a malformed plan before the user sees the approval dialog; `plan_flag.sh record` then arms the plan flag; both fire on ExitPlanMode; the plan file store is the shared downstream.

FEEDS `helm` · `plan_flag.sh` (armed by the ExitPlanMode hook) writes `~/.claude/run/plan/plan-<key>.flag`; `statusline.sh` (the Helm bar) reads it; the run-flag store is the bridge between the hook-plane and the Helm display layer.

**Stop gates:**

WRITES→ `helm` · `session_flight_recorder` flushes the observability buffer → `system/observability/YYYY-MM-DD.jsonl` + `system/flight-log.jsonl`; Helm/security-health reads those for its observability tile.

ADVISES via stderr · `session_flight_recorder` emits a nudge to stderr (NOT to `system/learnings.md`) when `/save` was not called; it stubs `system/learnings.md` only if the file is missing but does not append the nudge there. The nudge is advisory stderr output only.

FEEDS `save` · `session_flight_recorder` nudges `/save` when it was not called — the hook-plane's Stop gate is the anti-loss backstop for the save element. `[honor]`

WRITES→ `two-machine-residency` · ⛔ CORRECTED: `mirror_plans.sh` does not exist in this repo (see E2 above) — there is no hook providing the plan store's cross-machine residency; `~/.claude/plans/` has no backup lane.

READS `project-manager` · `scratch_capture_gate.sh` reads pm_flag status at Stop to resolve the active brief's `## SCRATCHPAD`; it bounces the turn to force a pad capture when the token bucket overflows; the brief store (project-manager element) is the shared target.

DEPRECATED → `claude-md-pyramid` (voice layer) · `translator_gate` was the grading gate for voice compliance (rubric: `system/translator-rubric.md`) but is deprecated-in-place — the Haiku grader was RETIRED per [TRANSLATOR-GATE-RIP] (2026-07-14); the hook remains registered but does not enforce. `[honor]`

**Cross-cutting (the hook-plane's own registration store):**

KEYS-OFF `two-machine-residency` · `settings.json` IS the hook-plane's own registration store; ~~it travels to both machines via git because it is symlinked from the clone; a broken symlink silently darkens every hook on that machine~~ — the two-machine-residency element is the physical transport for the hook-plane's own existence.
> **⚠ CORRECTED:** `.claude/settings.json` is a real, tracked file in this repo, not a symlink (see
> REGISTRATION MECHANICS above). It travels with the repo itself via `git clone`/`git pull` like any
> other tracked file — there is no separate symlink to break.

FEEDS `label-checker` · hook-plane's `settings.json` + guard scripts are the input source `label_checker.py` reads and fire-tests; the hook-plane's registration store and script bodies are what this element validates — flow runs FROM the hook-plane INTO label-checker.

FEEDS `sentinel` (security-health) · hook scripts + `settings.json` registration are the artifacts sentinel's health checkers read to produce the Security tile; `health_invariants.py` checks that critical guard scripts are present, non-empty, and not git-dirty; `security-health.py` checks hook registration in `settings.json`; flow runs FROM the hook-plane INTO sentinel.

FEEDS `rating-capture` · `rating_capture.sh` writes `system/learnings-signals.jsonl` and `system/learnings/<failure>.md`; these stores are shared with the save element on session close. (Note: `rating-capture` is NOT in the ranked element list — see New Candidates below.)

---

### NEW LOAD-BEARING PARTS DISCOVERED (NOT in the ranked element list)

1. **`rating-capture`** (`rating_capture.sh` + `system/learnings-signals.jsonl` + `system/learnings/` store): the UserPromptSubmit feedback-capture loop. Writes a durable quality-signal log that is not named as a standalone element. Could be a full element or folded into the `helm` observability element.

2. **`conformance-lab`** (`system/tools/conformance-lab/` — `bakeoff.py`, `probes/guard.py`, `driver.py`): the adversarial fire-test harness that proves hooks are not theater. Distinct from `label_checker.py` (which checks registration + fires single probes); the lab runs adversarial probe suites and was the source of the 2026-07-23 guard_statusline_lock fix. Currently folded under `label-checker` in the ranked list but does significantly more work. Worth splitting into its own element.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL
- **check_detail:** LIVE blocking guards (PreToolUse) confirmed: `block_primary_calendar` · `guard_gws_logout` · `guard_write_paths` (fail-CLOSED 2026-06-18) · `guard_ledger_discipline` · `guard_canon_write` · `guard_organism_map` · `guard_tasks_writes` · `guard_sheet_writes` + `guard_sheet_formula_writes` (live gws read-back) · `ingest_gate_enforce` (6 matchers — Bash · WebFetch · WebSearch · Read · Grep · Glob, fail-CLOSED) · `guard_plan_structure` (fail-OPEN intentional). Known anomalies: `guard_router_writes` exit 1/stdout (non-standard, functional); `guard_throughline_write_scope` mixed exit signals; `guard_egress` + `enforce_egress_allowlist` fail-OPEN on parse/unextractable host (intentional, LuLu backstop). PostToolUse advisories: all exit 0, all correctly non-blocking; `validate_on_write.sh` INERT until 2026-07-21 (now advisory). PARTIAL because: (1) `validate_on_write.sh` still advisory (not yet blocking PreToolUse enforcement — defect-d is OPEN, prerequisite: ~526-file type→record_type rename); (2) ~40 stated doctrine rules remain honor-system; (3) minor exit-code inconsistencies in two guards; (4) six superseded hook headers read as active. Blocking PreToolUse fleet is solid and covers the highest-blast-radius surfaces. Mixed → **PARTIAL**.
