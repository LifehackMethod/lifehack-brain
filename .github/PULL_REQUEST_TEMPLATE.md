<!--
Thanks for opening a PR. Fill in what applies and delete the rest of this comment block.
CONTRIBUTING.md (repo root) walks through everything below in more detail — worth a read
before your first PR here, especially the "What CI checks" and "action_required" sections.
-->

## Branch routing — decide this before you branch

<!--
This is the one page GitHub puts in front of every author at the exact moment the base
branch gets picked. Get it right here; CONTRIBUTING.md has the full rule if you want it.
-->

- **`main` is the DEFAULT.** One atomic fix, ships to students now; the system retires
  the branch after merge. Almost every PR belongs here.
- **`V2` is a NAMED TEMPORARY EXCEPTION** — the version-release batch only, and it
  retires at release. It is NOT a permanent lane, NOT a staging area, and NOT where
  ordinary fixes go. ⚠ **When V2 ships, this section comes out of this template.**
- A feature branch is ONE change, off `main`.

- [ ] Base branch: `main` (default) — or, if `V2`, say which release batch this belongs to:

## What this changes, and why

<!-- One or two sentences. What was broken or missing, and what this does about it. -->

## Issue

<!--
Only if this PR fixes a specific OPEN issue on the tracker, and your diff's own added
lines already say so (a comment/commit line with "fixes"/"closes"/"resolves"/etc. next to
that issue's #N) — put the real GitHub closing phrase here. This is not decoration: a
CI check (fix-citation-required.yml) will fail this PR if that shape appears in your diff
without the matching phrase appearing here.

    Fixes #123

If this PR doesn't fix a specific open issue, delete this section entirely — most PRs
don't need it.
-->

## Testing

<!-- What you ran locally, and what it showed. At minimum: -->

- [ ] `bash system/tools/run-all-tests.sh` — passed / failed (paste the summary line)
- [ ] `bash system/tools/smoke-check.sh` — passed / failed
- [ ] Tested on: <!-- macOS / Linux / Windows -->

## Anything a reviewer should know

<!--
- Known limitation, or a thing you deliberately left out of scope.
- If this touches Windows-specific code and you could only test on one platform, say so.
- If this is a security-relevant fix, do NOT put exploit details here — see
  CONTRIBUTING.md's "Reporting a security issue" section instead, and keep this PR's
  description to the fix itself.
-->

## Checklist

- [ ] I did not commit anything from my own AI Brain / notes folder (`data/`, `.brain-root`,
      `local.settings.json`, `.claude/settings.local.json`, `CLAUDE.local.md`, or a legacy  ⛔ absent from this repo by design — that is the point
      `memory/` folder) — see CONTRIBUTING.md §2.
- [ ] I ran the local test suite and smoke check before opening this PR.
- [ ] Branch is off `main` (or the stated `V2` exception above) and doesn't include
      unrelated changes.
