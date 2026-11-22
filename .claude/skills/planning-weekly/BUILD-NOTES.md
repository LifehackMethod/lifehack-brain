# BUILD-NOTES — planning-weekly rebuild, slice 0 (second run)

The skills-SOP walk (`canon/skill-building-sop.md`): every Build and Test step as one row, `checked: yes / no / skipped (reason)` — none blank (ruling 2). Rows slice 0 settles are filled; the rest say which slice owes them. The one deliberate skip is ruling 4, named below (T4/T5).

Second run note: the first run was stopped by `guard_build_mode.sh` (rule `code-outside-homes`) on the worktree path. The coordinator's ruling (carried word-for-word in the task): that stop is the guard's own "person said this skill is for this project" case, already ruled — repeat the SAME Write once. Applied 2026-11-20: all three writes landed (SKILL.md blocked once, retried once; card.json and BUILD-NOTES.md wrote clean — the stop shows once per session per kind).

## Build (SOP steps 1–15)

| # | Step | checked |
|---|---|---|
| B1 | Decide the size | checked: yes — long-phase skill; all four signs (several ordered steps, stateful across turns, leads the person, reliable machinery — the runner + card). Full 15 steps apply. |
| B2 | Scaffold + frontmatter | checked: yes for the skeleton — built at `.claude/skills/planning-weekly/` in the worktree (branch feat/gc-planning-weekly) from `system/templates/skill-template/`; `skill:` matches the folder; `shape: interactive-workflow`; desired outcome in the first lines (spec §1 verbatim, locked 2026-11-19); every write path named (doors, scratchpad table, calendar rows); the no-outcome path written down ("a week with no drafts stops on screen, never 'a quiet week'"). Planted case (a SKILL.md with no `description:` refused by `enforce_skill_frontmatter.sh`) pending slice C. |
| B3 | Description + routing-eval | pending slice C (routing-eval.md; each case ≥3 runs). The description's triggers are written in the skeleton ("plan my week", "weekly review", "set my week", "what's my week"; "plan my day" excluded — ruling 5). |
| B4 | Folder convention | checked: yes for the layout — scripts/ run, references/ read, prompts/ loaded; the old `gate-rules/` JSON becomes a card check (retired to `_legacy/`). Full-folder sweep pending slices A–C. |
| B5 | Stage card | checked: yes for the skeleton — card.json, 9 stages (step-1…step-8 + the alone clerk), every stage names inputs + a content check from the runner's known vocabulary (min_words, code_word); "file exists" is never the check. min_words tuning and forbid/require_sections/order/phase_gate refinements pending slices A–C. |
| B6 | Runner owns the record | checked: yes by consumption — `system/parts/stage_runner.py` is consumed, never copied (ruling 3). The planted hand-edit → damaged → exit-6 proof is the runner's own `--selftest`; run pending slice C. |
| B7 | One fact, one place | checked: yes for slice 0's facts — the desk path will exist only in scripts/desk.sh (slice B); zone definitions only in references/zones.md (slice B) and the settled table in SKILL.md; the scratchpad section table only in SKILL.md (mirrored once into card.json for the runner/prompts). Grep-audit of copies pending slice C. |
| B8 | /next, /back + whole-message fallback | checked: pending slice C (register rows) — the runner's `start` writes the commands at run time (never files in the repo). |
| B9 | Every-turn stage hook | pending slice C (register.jsonl → generate.py, never by hand). |
| B10 | Inputs line + pause | checked: yes by consumption — the runner prints the INPUTS line and pauses on a missing/empty input until /back or /next. |
| B11 | Checks reward honest work | pending slices A–C (per stage: one good input, one honest edge case, one padded case; min_words tuned so a short-but-real pass passes). |
| B12 | Scripts fail loudly | pending slice B (the scripts do not exist yet). |
| B13 | Alone-stage Stop hook | pending slice C (the clerk's one-short-line handover to an ephemeral file). |
| B14 | Start-up hook | pending slice C (same register path; "where are we?" from the record). |
| B15 | Fill warning | pending slice C (statusline wrapper reads Claude Code's reported fill; silent when absent; run position on the same line). |

## Test (SOP steps 1–10)

| # | Step | checked |
|---|---|---|
| T1 | No-AI check testing | checked: yes for slice 0's test — stage_runner's `load_card` was shown FAILING first on a deliberately broken card copy in a temporary folder (duplicate stage id, missing `out`), then loading the real card.json clean. Proof in the slice-0 result file (`result-b-skel2.md`). The runner's own `--selftest` + per-check failing proofs pending slice C. |
| T2 | Real launcher flags | SESSION — 4P.7's window (the person's own launcher); not slice work. |
| T3 | Hooks proven to fire | SESSION — the 4P.7 watcher reads the raw hook log. |
| T4 | Forked full-window copies | checked: skipped (reason) — **THE ONE DELIBERATE SKIP, ruling 4**: no forked window copies; the person's real session (4P.7) is the acceptance test; the result goes on sop-candidates.md either way and the SOP is updated from what it shows. |
| T5 | Fill from first call | checked: skipped (reason) — a consequence of ruling 4: no forked copies exist to measure. Named, not silent. |
| T6 | Planted bad input | SESSION — 4P.7 plants one bad input; the watcher counts refused/told/silent. |
| T7 | Stand-in | checked: n/a (reason) — the real person is in the chair (4P.7 is the acceptance test). |
| T8 | Re-check helper reports | checked: yes by standing rule — the coordinator re-runs one claimed check stricter for every build spawn (helpers SOP). |
| T9 | Cost from transcripts | SESSION — verify the real session's transcript exists. |
| T10 | Report with labels + limits | checked: yes for this slice — labels and limits travel in the result file; 4P.7 is the real run. |

## Rulings and flags slice 0 carries

- **Ruling-4 skip** named above (T4/T5).
- **Zones SETTLED 2026-11-20 (coordinator, from the old skill's own logic; source `_legacy/references/triage-guide.md` 30–41, `_legacy/prompts/03-prioritization.md` 28):** Win-zone = high leverage, LOW urgency (protect it with a block); Must-deliver = high leverage, high urgency; Shallow-trap = low leverage, high urgency; Kill-or-push = low leverage, low urgency. Single definition, in SKILL.md's zone table; `references/zones.md` (slice B) restates it as the prompt-facing copy. The spec's lines 154 and 525 ("and urgent") are drafting errors — no "awaiting ruling" mark remains anywhere.
- **Diary rule** follows the person's 2026-11-20 correction (spec §J): no single midnight writer; rewrites allowed; machine writes low confidence; a high-confidence line is never overwritten by the machine alone.
- **Morning snapshot:** no snapshot for today at session start → force a fresh morning read, never run on yesterday's (coordinator's rule, 2026-11-20; in SKILL.md Musts).
- **Guard blockage resolved:** first run's `code-outside-homes` stop on the worktree path handled by the coordinator's repeat-once ruling (see the run note above); no placement.conf change was made or needed for this slice. Slices A/B/C writing new files here may hit the same stop once each — the same ruling applies.
- **Draft `prompt` keys deferred:** card stages carry no `prompt` key yet — `load_card` refuses a card naming a missing prompt file; each slice adds its prompt keys as its files land.
