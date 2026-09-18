# Contributing

Thanks for sending something back. This is the short version — a first-PR guide, not a
policy essay. If something you need isn't covered here, ask in your PR rather than
guessing.

## 1. Branch routing

This is the authority; `.github/PULL_REQUEST_TEMPLATE.md` is the reminder you see at the
exact moment GitHub makes you pick a base branch.

- **`main` is the default.** Almost every PR belongs here: one atomic fix or improvement,
  off `main`, that ships to students as soon as it merges. The branch retires after merge
  — it isn't kept around.
- **`V2` is a named, temporary exception** — the version-release batch only, and it
  retires when that release ships. It is not a permanent lane, not a staging area, and
  not where ordinary fixes go. If you're not sure your change belongs to a named release
  batch, it doesn't — open against `main`.
- **One feature branch, one change.** Don't bundle an unrelated fix or a drive-by
  refactor into a PR about something else, even a small one — it makes the PR harder to
  review and harder to revert if only part of it turns out to be wrong.

## 2. Don't commit anything from your own notes folder

This repo is the machinery (skills, tools, hooks) — everything *you* write once you're
running it (your own notes, records, project state) lives outside the repo, in your own
AI Brain folder. None of it belongs in a PR. The following paths are already gitignored
for exactly this reason — don't force-add over the ignore:

- `data/` — your AI Brain, when it's set up to live inside this checkout
- `.brain-root` — the per-install pointer to your AI Brain's location (a personal path)
- `local.settings.json` — your own credentials/settings
- `.claude/settings.local.json` — ⛔ same as above, under the Claude Code config folder; never committed here, by design — this line names the absence on purpose, it is not a broken pointer
- `CLAUDE.local.md` — your own personal instruction file
- a legacy `memory/` folder — the pre-2026-08-12 home for the same material

If your diff touches any of these, drop that part of the change before opening the PR.

## 3. What CI checks

Every PR runs through some or all of these, defined under `.github/workflows/`. Each is a
caller around a script that already exists under `system/tools/` or `.github/scripts/` —
read that script's own header for the exact rules it enforces; this is only the map of
which check does what and when it runs.

- **Citation Lint (whole tree)** (`citation-lint-whole-tree.yml`) — runs on every PR and
  push to `main`. Calls `system/tools/citation_lint.py` over the whole tree: proves every
  file, skill, and hook this repo's own documents name either exists, or has a line saying
  what happened to it.
- **Exercise Loop** (`exercise-loop.yml`) — runs on every PR and push to `main` (and
  `migration-1`). Two independent jobs: the aggregate test runner
  (`system/tools/run-all-tests.sh`) and the smoke check (`system/tools/smoke-check.sh`,
  confirms every tool answers `--help` and every hook is executable). Run both locally
  before opening a PR — the PR template's Testing section asks you to paste the result.
- **Fix Citation In PR Body Required** (`fix-citation-required.yml`) — runs on every PR
  against `main`, but only ever *fires* on one shape: your diff's own added lines already
  read like a fix for a specific, currently-open tracker issue (a comment or commit line
  with "fixes/closes/resolves #N", or similar). If that shape appears, this check fails
  unless your PR body also has the real GitHub closing phrase (`Fixes #123`) — see the
  template's "Issue" section. Most PRs never trip this at all.
- **No Internal Leakage** (`no-internal-leakage.yml`) — runs on every PR and push to
  `main` (and `migration-1`). Scans the files your PR actually changes for anything that
  looks like a maintainer's personal material leaking into the public repo (usernames,
  absolute local paths, third-party hostnames, credential locations). This one is about
  *our* material accidentally landing in a diff, not yours — see §2 above for the mirror
  rule about your own material.
- **No Internal Leakage - Whole-Tree Baseline** (`no-internal-leakage-baseline.yml`) — the
  same scan, run over every tracked file instead of just a diff. This one does **not** run
  on your PR at all — it's a weekly scheduled sweep (plus manual trigger) that catches
  drift already sitting in the tree, independent of any single contributor's change.
- **Plugin Version Bump Required** (`plugin-version-bump-required.yml`) — runs on every PR
  against `main`. This repo ships as a Claude Code plugin, and students only pick up a
  change once `.claude-plugin/plugin.json`'s version number goes up. If your PR changes
  anything that actually ships to students, this check fails until you bump that version.
  A PR that only touches `.github/`, `docs/`, or a root-level `*.md` file (like this one)
  is exempt — nothing a student's installed copy runs differently changed.

## 4. `action_required`

If a check on your PR shows `action_required` instead of a pass or fail, that's not this
repo's own CI logic — it's GitHub's own gate for public repositories: workflows don't run
automatically the first time someone without write access opens a PR, until a maintainer
clicks "Approve and run workflows" on it. You'll see this most often on your very first PR
here. It isn't a rejection and there's nothing to fix on your end — it just means the run
is waiting on a maintainer, and it'll resolve once they've had a chance to look.

## 5. Reporting a security issue

If what you found is a security issue — especially anything that could let personal or
client data leak through the publish pipeline — don't put it in a public PR or issue, and
don't include exploit or proof-of-concept detail anywhere public. See `SECURITY.md` at the
repo root for how to report it privately and what to expect back. An ordinary bug that
isn't security-sensitive is fine to open as a normal PR or issue.
