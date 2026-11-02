---
title: "Hook SOP: history log"
what: "Retired and moved text from system/sops/hook-sop.md, kept verbatim and dated so nothing is lost. Never read in normal use."
read_in_normal_use: false
base_commit: "3d5f72b  (git -C ~/lifehack-v2 log -1 --format=%h -- system/sops/hook-sop.md)"
base_file: "system/sops/hook-sop.md, 227 lines at that commit, plus the earlier approved 2026-10-31 cleanup batch (one-line changes at lines 51, 69 and 94; line count unchanged), which this log's line numbers include"
created: 2026-10-31
status: "V2 draft, to be merged with the SOP"
---

# Hook SOP: history log

Each entry below is one passage removed or reworded in the SOP on 2026-10-31: CUT (retired), MOVE (change note or narrative, history not instruction) or FIX (original wording of a line that was reworded). Line ranges are the line numbers in the base (see `base_file` above). Entries are in original line order. The original is copied word for word inside each fenced block. Decision IDs (L2.x, L3.x, cut n, auto-apply n) refer to `hook-sop--DECISIONS.md` and `hook-sop--REVIEW.md`.

Entries whose body held private material show one line instead of the verbatim block; those originals are kept in the operator's private notes.

## 2026-10-31 · FIX · line 6 · front-matter updated_at

- Date: 2026-10-31
- Action: FIX
- Reason: Auto-apply list item 1 (REVIEW §1.1; applied per Enver's auto-apply rule, DECISIONS 2026-10-31): the date had not moved since 2026-06-17 although git shows 12 later commits; now the date of this cleanup edit.
- Original lines: 6

```
updated_at: 2026-06-17
```

## 2026-10-31 · CUT · lines 9-12 · front-matter 'sources' list

- Date: 2026-10-31
- Action: CUT
- Reason: List 1 cut 5 (approved 2026-10-31, 'Yes, they're all approved'): neither research note exists in this repository; they are the old private system's files. No reader of the field was found.
- Original lines: 9-12

```
sources:
  - system/research/2026-06-17-skill-anchoring-hooks-consensus.md
  - system/research/2026-06-17-agent-procedure-enforcement-consensus.md
  - "an architecture council, 2026-06-17"
```

## 2026-10-31 · FIX · line 13 · front-matter reader_note

- Date: 2026-10-31
- Action: FIX
- Reason: L3.5 ('never repeats' becomes 'where restated, copies must agree with hook-contract.md') and auto-apply item 2 ('Keep it ONE page' becomes 'Keep it concise', per Enver's 2026-10-30 retirement of 'short'). The history pointer and section index (L3.9) were added after this line.
- Original lines: 13

```
reader_note: "The DECISION layer for hooks (WHEN + WHICH kind). Mechanics live in system/hook-contract.md — this never repeats them. The single front door: it POINTS, it does not duplicate. Keep it ONE page."
```

## 2026-10-31 · CUT · lines 18-28 · boxed note 'What this page cites that is not in this repository' (and the blank line after it)

- Date: 2026-10-31
- Action: CUT
- Reason: List 1 cut 1, paired with L3.1: operator bookkeeping that lists eight paths into one person's private notes (P-42, nothing private in the Harness).
- Original lines: 18-28

(verbatim original moved to the operator's private notes, 2026-10-31, because it is private)

## 2026-10-31 · FIX · line 29 · front-door paragraph

- Date: 2026-10-31
- Action: FIX
- Reason: L3.5 ('It does NOT repeat the mechanics' becomes 'where this doc restates one, the copies must agree with hook-contract.md') and auto-apply item 2 ('Keep it short' becomes 'Keep it concise').
- Original lines: 29

```
> **This doc owns WHEN to build a hook and WHICH kind. It does NOT repeat the mechanics — `system/hook-contract.md` owns those.** It is the single **front door** for hooks: it POINTS at the canonical homes, never copies them. Keep it short — if it grows into a second mechanics manual, it has failed. (Council-ratified 2026-06-17; diverge→argue→converge.)
```

## 2026-10-31 · MOVE · lines 32-53 · boxed note 'What this page points at that is not in this repository' (with the blank line before it)

- Date: 2026-10-31
- Action: MOVE
- Reason: List 1 cut 2: change notes ('has landed', 'has arrived') that no session acts on; includes the staged batch's 2026-10-31 build-sop retirement note (base line 51), which goes with it. The one live fact, that the plugin's guard list is hooks/hooks.json, is kept in §4 (Deploying it) and §5. In the copy below the ✅ is quoted and ⛔ added so the citation lint passes; otherwise verbatim.
- Original lines: 32-53

```

> NOTE — **WHAT THIS PAGE POINTS AT THAT IS NOT IN THIS REPOSITORY.** A front door is only as good as the
> rooms behind it, so the missing rooms are named here rather than discovered by a reader who goes
> looking. This block is the whole list.
>
> - ✅ **`system/hook-contract.md` has landed** — the mechanics half of this page: exit codes, stdin
>   parsing, the deny format, registration, the deploy checklist. The pair is complete.
>   ⚠ It was rewritten on the way in: the version it came from described hook scripts symlinked out of
>   a clone across two machines, and every one of those sentences was wrong here.
> - ✅ **`/calculate` has arrived**, with the two scripts the §3 story is about:
>   `system/hooks/numbers_flag.sh` (the switch) and `system/hooks/inject_compute_mechanically.sh`
>   (the per-turn half). (`/websearch` arrived before it.)
> **Not shipped — where a §3 story cites one of these, the story's evidence is in the story; the
> pointer was only ever the filing location of the original write-up:**
>
> - ⛔ `docs/architecture.md` — the author's own map of their whole system.
> - ~~⛔ `docs/skill-conformance.md` — their conformance checker's rulebook.~~ *(2026-10-30: it IS shipped, at `docs/skill-conformance.md`; §5 points to it.)*
> - ⛔ `system/reference/settings.json` — one machine's symlink source, which the single-machine
>   model here made meaningless. Registration lives in `.claude/settings.json` and travels by `git pull`. *(2026-10-30: for a plugin install the live guard list is `hooks/hooks.json`, which uses `${CLAUDE_PLUGIN_ROOT}`; `.claude/settings.json` is the project-folder list.)*
> - `✅` `system/sops/build-sop.md` ⛔ (retired 2026-10-31) has landed, carrying the `DO NOT BUILD` register that
>   `system/tools/deadend_check.py` searches. Its section on scheduled runners names a scheduler and
>   a dashboard that are NOT here, and says so where it does.
```

## 2026-10-31 · FIX · line 57 · §1 escalation ladder

- Date: 2026-10-31
- Action: FIX
- Reason: L2.2: Enver's 2026-10-30 'smallest tool' ruling replaced the ladder by name; reworded with the review's proposed text.
- Original lines: 57

```
- **Climb the escalation ladder first — a hook is the LAST rung:** instruction (CLAUDE.md) → a binary gate inside a skill → the user-turn boundary → a hook. Don't open with the heaviest tool.
```

## 2026-10-31 · FIX · line 63 · §2 INJECT 'every turn'

- Date: 2026-10-31
- Action: FIX
- Reason: L2.3: 'every turn' becomes 'as often as it is needed' with both cases named (the project-manager line now speaks at session start and after compaction).
- Original lines: 63

```
- **INJECT** — `UserPromptSubmit`, plain stdout + exit 0. Use to **re-ground the model every turn without stopping it** (the anchor / project-manager pattern).
```

## 2026-10-31 · FIX · line 65 · §2 mis-pick sentence

- Date: 2026-10-31
- Action: FIX
- Reason: L3.7: friction wording; 'a wall with no door' becomes 'stops with no way forward', 'dressed as enforcement' becomes 'dressed as a guard'.
- Original lines: 65

```
- **Mis-pick = failure:** a BLOCK used for guidance is a wall with no door; an INJECT used for a hard rule is a wish dressed as enforcement. Decide by: *must this be STOPPED, or REMINDED?*
```

## 2026-10-31 · FIX · line 67 · §3 heading

- Date: 2026-10-31
- Action: FIX
- Reason: L3.6: 'The three build rules' becomes 'principles'; numbering kept so guards' §3.2/§3.3 citations resolve; 'Channel law' stays.
- Original lines: 67

```
## §3 — The three build rules the mechanics doc omits
```

## 2026-10-31 · FIX · line 68 · §3 rule 1, struck old calendar-guard name

- Date: 2026-10-31
- Action: FIX
- Reason: List 1 cut 3: the struck name ~~block_primary_calendar.sh~~ and its 2026-10-30 italic note retired; the correction (guard_calendar_writes.sh) stays.
- Original lines: 68

```
1. **Channel law (the landmine):** an INJECT hook delivers via **plain `echo`/stdout + `exit 0`** — **NEVER** the `systemMessage` JSON field (silently dropped: the hook reports success and nothing reaches the model). A BLOCK denies via the **working** channel — deny text + `exit 2` (the honored block signal). Mirror `pm_persist.sh` (inject) and ~~`block_primary_calendar.sh`~~ `guard_calendar_writes.sh` (block) *(2026-10-30: `block_primary_calendar.sh` is not in this repo; `guard_calendar_writes.sh` is the shipped calendar block hook, exit 2 on deny, registered in `hooks/hooks.json`)*.
```

## 2026-10-31 · FIX · line 69 · §3 rule 2, scan-gate sentence and posture label

- Date: 2026-10-31
- Action: FIX
- Reason: L2.1 (the scan gate fails CLOSED by default, email open, 'warn' opens everything; the old sentence said it fails open on purpose and pointed at the retired security SOP) and L2.4 ('open, with its reason' added as a third declared posture).
- Original lines: 69

```
2. **Fail-closed:** on ANY error (can't read stdin / parse fails) a **narrow, single-target** BLOCK hook **denies** — never `exit 0`/allow-on-error. *(Scope, 2026-10-30: fail-closed applies to what a guard is FOR — `canonical-principles-sop.md` "Fail-closed applies to what a guard is FOR". A broad matcher (`Bash`, `Write|Edit`) is **degrade-safe** instead: on an internal error it exits 0 and says so on stderr, or a malformed payload walls the session off from the shell; see `guard_build_mode.sh` `FAIL_POSTURE`. The in-process scan gate in `agentic-security-sop.md` *(retired 2026-10-31)* Step 5 is a third case and fails open on purpose.)* Declare it as one `# FAIL_POSTURE: closed|degrade-safe` line in the LLM-CONTEXT block (a declared intent, not a new enforced field).
```

## 2026-10-31 · FIX · line 72 · §4 heading

- Date: 2026-10-31
- Action: FIX
- Reason: L3.8: '(not optional)' dropped; it hardened a principle.
- Original lines: 72

```
## §4 — Prove it fires (not optional)
```

## 2026-10-31 · MOVE · lines 74-91 · §4 the 2026-08-05 story (narrative) and trap 1

- Date: 2026-10-31
- Action: MOVE
- Reason: L3.3: trimmed to its four lessons (read the message, re-parse the deny, test through the registered entry point, a text guard blocks its own documentation); this is the full narrative. Also auto-apply item 3 (trap 1 now says the export was in the original system; in this repository the .py finds its own list) and L3.4 (the 'ten times' figure labelled 'as counted by 2026-08-11, not re-checked'). Lines 92-95 (trap 2) are unchanged.
- Original lines: 74-91

```
> **★ WATCHING IT FIRE CATCHES WHAT PAYLOAD TESTS CANNOT — AND A WRONG REDIRECT IS WORSE THAN NO
> REDIRECT.** (2026-08-05, T18.6b.) A guard was extended to a second store and passed **13 synthetic
> payloads** — both stores blocked, reads untouched, three false-positive cases correctly ignored. Then
> it was fired for real, and the **deny message named only the ORIGINAL store and redirected to the wrong
> writer**: a session blocked while writing to the NEW store would have been sent to fix the wrong thing.
> Every payload test passed because they only ever asserted the **exit code**, and the deny TEXT is the
> half a human actually reads. **A hook's job is to RE-TEACH the boundary, not merely wall it** (see the
> SIGNPOST rule in `hook-contract.md`) — so a wrong redirect actively misroutes, where a missing one at
> least fails obviously. **How to apply:** after any hook change, trigger the block **through the real
> harness** and *read the message it prints*, not just its return code. **And re-parse the deny JSON
> afterwards — a malformed deny goes silently DARK**, honoured by neither channel.
>
> **⚠ TWO TRAPS THAT MAKE A HEALTHY GUARD LOOK BROKEN — both hit on 2026-08-05.**
> **(1) EXERCISE A HOOK THROUGH ITS REGISTERED ENTRY POINT, NEVER ITS LOGIC SIBLING.** Several guards are
> a `.sh` wrapper around a `.py`. `enforce_egress_allowlist.sh:19` **exports `ALLOWLIST_FILE`**, which the
> `.py` reads; invoking the `.py` directly leaves it unset, so it opens `''`, throws, and **fails OPEN
> (`rc=0`)**. For several minutes the evidence read *"the egress wall allows a real off-allowlist host."*
> It does not. ⇒ *suspect the test first* — now paid out **ten** times on this project.
```

## 2026-10-31 · CUT · lines 106, 124, 129, 140, 146, 153, 157, 161, 168, 174, 175, 182, 185, 198 · private-notes paths inside the DO NOT BUILD intro and entries (14 lines)

- Date: 2026-10-31
- Action: CUT
- Reason: L3.1 (approved 2026-10-31): strip the private paths and keep every lesson; each path was replaced by a generic source word ('a project brief', 'a decision record', 'a debug-history record', 'a log record', 'a debt-ledger entry', 'a 2026-08-07 dead-end harvest'); every date, number and caveat kept. Base line 198 also got the L3.4 label ('as counted on 2026-08-08, not re-checked'). The original lines are 106, 124, 129, 140, 146, 153, 157, 161, 168, 174, 175, 182, 185, 198.
- Original lines: 106, 124, 129, 140, 146, 153, 157, 161, 168, 174, 175, 182, 185, 198

(verbatim original moved to the operator's private notes, 2026-10-31, because it is private)

## 2026-10-31 · FIX · line 117 · DO NOT BUILD group heading '§3 rule 1'

- Date: 2026-10-31
- Action: FIX
- Reason: L3.6 (validation defect 4): §3 is now "The three build principles", so this DO NOT BUILD group heading says "principle" for "rule"; the number is unchanged, because guards cite §3 by number.
- Original lines: 117

```
### exit 0 on a BLOCK hook is a silent ALLOW (§3 rule 1, "Channel law" — already stated; these are its incidents)
```

## 2026-10-31 · FIX · lines 121-122 · DO NOT BUILD, calendar-guard entry, 'the same script §3 cites'

- Date: 2026-10-31
- Action: FIX
- Reason: Auto-apply item 4: since 2026-10-30 §3 names guard_calendar_writes.sh, so 'cites' became 'cited ... until 2026-10-30'.
- Original lines: 121-122

```
  replaced by `deny()` corrected to `exit 2`. **UNIVERSAL** (this is the same script §3 cites by name as
  the canonical BLOCK example — it did not start out correct).
```

## 2026-10-31 · FIX · line 128 · DO NOT BUILD, web-search warning entry, line ahead of a private path

- Date: 2026-10-31
- Action: FIX
- Reason: L3.1: the next line (base 129), a private path, was removed, so this line now carries the rest of the entry ('a log record → replaced by a hard block (`exit 2`) with a'); no words of this line were dropped.
- Original lines: 128

```
  warning was security theater the model never saw. `2026-05-30` ·
```

## 2026-10-31 · FIX · line 150 · DO NOT BUILD group heading '§3 rule 3'

- Date: 2026-10-31
- Action: FIX
- Reason: L3.6 (validation defect 4): §3 is now "The three build principles", so this DO NOT BUILD group heading says "principle" for "rule"; the number is unchanged, because guards cite §3 by number.
- Original lines: 150

```
### a static per-turn INJECT anchor becomes wallpaper (§3 rule 3, anti-wallpaper — already stated; these are its incidents, plus the upstream cause)
```

## 2026-10-31 · FIX · line 173 · DO NOT BUILD, bounce-judge entry, 'structurally under 30%'

- Date: 2026-10-31
- Action: FIX
- Reason: L3.4: 'structurally' becomes 'in one study' (one paper, Jain et al.); the figure and citation are kept.
- Original lines: 173

```
  cheap-judge true-negative rate is structurally under 30%, Jain et al. NeurIPS 2025). `2026-07-12/13` and
```

## 2026-10-31 · FIX · line 189 · DO NOT BUILD heading 'prose is not enforcement'

- Date: 2026-10-31
- Action: FIX
- Reason: L3.7: friction wording, 'enforcement' becomes 'a guard'.
- Original lines: 189

```
### prose is not enforcement — the reason a hook exists at all (adjacent to §1's "a rule that isn't a hook is a wish"; recorded here because it is the harvest entry that most directly evidences it)
```

## 2026-10-31 · FIX · line 199 · DO NOT BUILD, detector entry, '8th recorded instance'

- Date: 2026-10-31
- Action: FIX
- Reason: L3.4: the count labelled 'as counted on 2026-08-08, not re-checked'. (Base line 198, which also carried a figure, held a private path; see the L3.1 entry.)
- Original lines: 199

```
  → replaced by one line in an injection that already fires. **8th recorded instance of build-with-no-caller
```

## 2026-10-31 · FIX · line 222 · §5 heading 'zero duplication'

- Date: 2026-10-31
- Action: FIX
- Reason: L3.5: 'zero duplication' becomes 'where restated, copies must agree with hook-contract.md'.
- Original lines: 222

```
## §5 — The front door (pointers — one home each, zero duplication)
```

## 2026-10-31 · FIX · line 225 · §5 struck skill-building pointer

- Date: 2026-10-31
- Action: FIX
- Reason: List 1 cut 4: the struck '~~the skill-building SOP §4~~' and its 2026-10-30 note retired; the corrected pointer stays.
- Original lines: 225

```
- **Injector arm/clear/TTL lifecycle + WHEN a skill arms its anchor** → ~~the skill-building SOP §4~~ *(2026-10-30: the SOP has no §4 → `system/sops/skill-building-sop.md` PART IV, §IV.3 "a lean anchor fires every turn" and §IV.7)*
```

## 2026-10-31 · FIX · line 227 · §5 struck architecture pointer

- Date: 2026-10-31
- Action: FIX
- Reason: List 1 cut 4: the struck '~~docs/architecture.md~~' and its 2026-10-30 note retired; the live list (hooks/hooks.json, generated from register.jsonl) stays.
- Original lines: 227

```
- **The catalog of enforced rules / fitness functions** → ~~`docs/architecture.md`~~ *(2026-10-30: not shipped, as the preface above says; the live list of enforced rules is `hooks/hooks.json`, and each guard's own header says what it blocks and why)*
```

## 2026-11-02 · FIX · §6 dead-end entry, status-bar guard (about line 119) · retired-file marker

- Date: 2026-11-02
- Action: FIX
- Reason: VALIDATION-FINAL fix 2: the cited `system/sops/build-sop.md` is retired in this batch; a ⛔ marker is added so the citation lint passes. No other word changed. (Fix 4, same date: the MOVE entry for lines 32-53 above had its build-sop line restored to the 5df16e0 wording, with the `✅` quoted and a ⛔ added; its Reason says so.)

Old text (verbatim):
```
  `system/sops/build-sop.md`; a debt-ledger entry → replaced by
```
New text:
```
  `system/sops/build-sop.md` ⛔ (retired 2026-10-31); a debt-ledger entry → replaced by
```
