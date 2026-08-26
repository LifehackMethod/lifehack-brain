# The closed verdict sets

> Moved out of SKILL.md 2026-08-23. Each phase names the tools it runs;
> this is the full table for reference. **Reading this is not a substitute for running the phase.**

Each comes from a tool's exit code. **Quote the token in the receipt** — its absence is then provable.

| tool | verdicts |
|---|---|
| `checkin_open.py print` | `RUNGS <n>` 0 · `BAD-RANGE <why>` 2 · `CANNOT-READ` 4 |
| `pad_archive.py state` | `PAD-EMPTY` 0 · `PAD-DIRTY <chars>` 2 · `PAD-ARCHIVED-UNCLEARED` 3 · `CANNOT-READ` 4 |
| `gauge_check.py check` | `ONE-GAUGE` 0 · `COMPETING-GAUGES` / `OVERSIZED` / `STALE` 2 · `NO-GAUGE` 3 · `CANNOT-READ` 4 |
| `board_check.py` | `BOARD-CLEAN` 0 · `STALE-OPEN <ids>` / `RUNG-ORPHANED <id>` 2 · `NO-BOARD` 3 · `CANNOT-READ` 4 |
| the blind reader | `CAN PROCEED` · `BLOCKED — <n>` · `CONTRADICTION — <n>` · `NOT RUN` |
| `save_step_ledger.py report --ns checkin` | rc 0 clean · rc 1 a mandatory step **MISSED** · rc 2 applicability **UNKNOWN** |

⛔ **rc 2 is not a softer rc 0.** *"I could not tell"* must never be machine-readable as *"fine"*.

