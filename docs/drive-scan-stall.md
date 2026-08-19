# The AI Brain cannot be searched by walking it

**Status:** open — reported with measurements, remedy proposed, one design decision needs a call
**Affects:** every install on macOS, which is every install (INSTALL.md ships no Windows path)
**First reported:** a working install where `/read` and ad-hoc greps hang; reproduced on a second
brain on the same machine

---

## The short version

We require the AI Brain to live in a Google Drive folder. On macOS that folder is mounted through
the FileProvider framework, where **listing a directory is a network round-trip, not a local read**.
Any recursive scan of it — `grep -r`, `find`, `Glob` with `**`, `os.walk` — does not run slow. Past a
certain depth it **blocks inside the `readdir` syscall** and never comes back.

Three things make this worse than it sounds:

1. **It does not warm up.** The same scan was measured stalling identically on three consecutive
   runs — same depth, same entry count, every time. This is not a first-run cost that amortises.
2. **No timeout in the scanning process can stop it.** Not a wall-clock check, not `SIGALRM`. The
   interpreter never gets a turn while the syscall is blocked. The only thing that works is killing
   the process doing the walk from outside it.
3. **`/read` — the skill whose whole job is finding things — is built on exactly this.** Its
   §3.1 is "Glob by name first, grep full-text as the fallback" over five `**` paths, with no guard.

## What makes this a system-level bug and not one person's slow laptop

The repo has already met this failure mode and hardened against it — but only on the machine-written
side of the same folder:

- `system/tools/emit_finding.py` — `WRITE_TIMEOUT_S = 15`, and its message says it outright:
  *"the brain root's mount likely wedged … this is a hang"*
- `system/tools/health_line.py` — `FINDINGS_READ_TIMEOUT_S = 8`, *"a wedged mount blocks instead of raising"*
- `system/organism/elements/hospital.md` — the measured **EDEADLK-on-7/8-runs** failure mode
- `shared/tools/item_store_window.py` — *"~2.03 s/file on the Drive mount — putting a real 7-day
  window at ~59 min"*
- `system/tools/checkin/board_check.py` — a live **false green**: a readability probe passed while
  the real read failed

So the system knows the mount hangs, and guards its own state files against it. **The note-search
path — the one a person actually uses — has no such guard.** That asymmetry is the bug.

## Measurements

Two AI Brains, same Mac, same Drive account, same session. Brain A is a Shared drive in daily use;
Brain B is a My Drive folder used less often.

| | Brain A (18,986 files) | Brain B |
|---|---|---|
| full recursive `find` | **1s**, 21,237 entries | **TIMED OUT at 60s**, reached 11,585 |
| `find -maxdepth 5`, three consecutive runs | — | **30s / 60s / 60s**, identical 3,421 entries each |
| `grep -rl <word>` | 16s cold, 1s warm | never completes — cannot traverse |
| `mdfind -onlyin` by name | 0s | **0s**, 260 results |
| `mdfind -onlyin` by content | 0s, 5,326 hits | **1s**, 5,764 hits |
| files present but not downloaded | **0 of 18,986** | 1 at depth ≤ 4 |

**The "undownloaded Google Docs" theory is wrong.** That was the intuitive explanation and it does
not survive measurement: there is essentially nothing dataless in either tree, and zero `.gdoc` stubs
in Brain A. The cost is **per-directory enumeration**. Brain B is directory-heavy — 1,447 directories
against 1,038 files in its top four levels — and each cold directory is its own round-trip.

**`grep` is separately, unrelatedly slow.** Identical corpus copied to the internal SSD, 17,609 files:

| | files matched | time |
|---|---|---|
| `grep -rl <word>` | 3,437 | **14s** |
| `rg -l <word>` | 3,436 | **0.79s** |

Same answer, 18× apart, with the mount taken out of the picture entirely. The repo currently mentions
`rg` nowhere.

## Reproducing it

```bash
python3 system/tools/brain_scan_probe.py
```

Read-only, bounded, and it cannot itself hang — the walk happens in a child process it kills. On a
healthy brain it prints `WALKABLE`; on an affected one it names the depth that stalled and exits 1.

## Proposed remedy

`system/tools/brain_search.py` — search the brain **without walking it**.

- **`mdfind` answers from the Spotlight index**, which macOS already maintains for that folder. 1s
  where a walk times out at 60s, and it reads inside PDF and `.docx` that `grep` cannot open at all.
- **The index only narrows candidates.** Every hit is then read back off the live file, so what gets
  reported is never a cached copy.
- **Files newer than the index are swept separately** by mtime, closing the ~3s window measured
  between saving a file and Spotlight seeing it.
- **Candidates it cannot verify are listed, not dropped** — a PDF the index matched is a hit nobody
  can confirm by reading text, and silently discarding it would make the tool quietly worse than the
  index under it.
- **It degrades honestly.** No Spotlight (Linux, or indexing off) means a bounded walk in a killable
  child, and output that says so. A search that could not look never gets spelled like a search that
  looked and found nothing.

## The decision that is not mine to make

`.claude/skills/read/SKILL.md` says, deliberately and in bold: **"There is one tier, and it is this
one … Do not add an adapter for it. Live files, every time."** That line was written against a
semantic-index tier, and it gave two reasons. Both are addressed above — `mdfind` fetches no external
package, and live files are still what get read — but **the line is Enver's and the call to relax it
should be too.**

The tools in this PR are additive and change no existing behaviour. The one behavioural change is the
`/read` §3.1 edit. If that edit is wrong, drop that commit: the probe and the search tool stand on
their own and the bug report is still on the record.

## Not fixed here

- **Windows and Linux.** `mdfind` is macOS-only. The fallback is a bounded walk that will truncate on
  a large tree and say so — honest, not equivalent.
- **`rg` is not adopted.** The 18× is real and free, but swapping the search engine everywhere is a
  bigger change than this bug needs.
- **The other recursive-scan sites** — `system/tools/architecture_reason.py` (its `BRIEF_GLOB` sweep
  over project briefs), `system/tools/canon_conflict_scan.py` (`os.walk`), and `.claude/agents/archivist.md`, which is
  pinned to `Read, Grep, Glob` and told to walk the notes folder end to end. Same exposure, left alone
  so this PR stays reviewable.
