# Contributing

Thank you for looking at this. There has not, until now, been a documented route in — this file
is that route. **The goal: you should be able to follow it start to finish without asking the
maintainer anything.** If a step here turns out to be wrong or missing something you needed, that
is a bug in this file — open an issue about the file itself.

The project lives at `LifehackMethod/lifehack-brain` on GitHub. That is the repo your fork and PR
go against, whatever else it may be called locally.

---

## 1. Fork, clone, branch

1. Fork `LifehackMethod/lifehack-brain` on GitHub.
2. Clone your fork locally.
3. Create a branch off `main`. There is no branch-naming rule enforced by any check in this repo
   — a short, descriptive name is enough (`fix-...`, `windows-...`, whatever names the change).
   Do not work directly on `main`.

## 2. Before you write anything that touches your own AI Brain

If you also run this project as a *user* (installed it for yourself, connected an AI Brain folder
in Google Drive), that AI Brain is a **separate folder outside this repo** — never inside your
clone, never committed. `INSTALL.md` and `UPDATE.md` are the authority on that split; this file
only restates the parts that matter for a contribution:

- Updates to your own clone are `git pull`, never delete-and-re-clone — that would discard your
  `.brain-root` pointer and anything else you'd added locally.
- **Never `git add -f` anything `.gitignore` covers.** In particular: `.brain-root`, `data/`,
  `local.settings.json`, `.claude/settings.local.json`, `CLAUDE.local.md`, and (if you have an  ⛔ none of these exist in this repo, by design — that absence IS the protection
  older install) anything under a legacy `memory/` folder. Every one of those is a personal file —
  yours or another contributor's — and `-f` is the only thing that can put it in front of git's
  own protection.
- If you run `/ship` or otherwise interact with `system/shipping-lane/` — that machinery
  (`scrub.py`, `push_gate.py`, `identity_rules.py`) is how the maintainer personally moves content
  from a private working tree into public history. It reads an identity file
  (`<your notes>/config/ship-identity.md`) that names *you* — your own name, handle, email, project
  names — so it can refuse to publish them. **That file is never committed, on purpose.** ⛔ **You never need this, and neither does any other
  contributor.** Opening a PR *is* your approval of what's in it, so nothing of yours needs
  scrubbing. If you were told during install to create a `ship-identity.md`, that instruction
  was wrong and has been removed — you can delete the file.

## 3. Run the tests locally before opening a PR

```bash
bash system/tools/run-all-tests.sh
```

This finds every `test_*.py` and `test_*.sh` in the repo and runs each one under a timeout,
printing one pass/fail/skip summary at the end. A few notes so the output makes sense:

- It exports its own throwaway `LIFEHACK_ROOT` for the run, so a test that forgets to sandbox
  itself still can't reach a real data folder. It does **not** sandbox the network.
- One file is skipped by name on purpose: `system/tools/test_safe_readers.py` makes a real
  outbound call to a search API. Seeing it skipped is expected, not a problem with your setup.
- Default per-file timeout is 90s; override with `TEST_TIMEOUT_SECS=<seconds>` if your machine is
  slower.

Also run the smoke check — it answers a dumber, cheaper question ("does everything still start")
that the test suite doesn't cover:

```bash
bash system/tools/smoke-check.sh
```

It checks that every tool under `system/tools/` answers `--help` without crashing, and that every
hook under `system/hooks/` is both executable and actually parses. **It is supposed to fail on its
first-ever run in a given environment** — a green first run there means the check isn't looking,
not that everything's fine.

Both scripts are also what CI runs on your PR (see §5) — running them first locally means you find
out before a maintainer does.

### If you're on Windows

Be aware going in: there are currently **9 open issues on the tracker whose titles start with
"Windows"** (covers install preflight gaps, CRLF breaking the pulse-config parser, a
drive-letter brain-root path being rejected, BSD-vs-GNU command flag mismatches, and more) — this
is not a hidden problem, it's a known, tracked one. The test suite is written and mostly exercised
on macOS/Linux; several Windows-shaped defects have been found by contributors running the real
thing on Windows, not by the suite catching them first. If something fails only on your machine
and looks Windows-specific, it's very likely real and worth its own issue (or a PR) rather than
something to work around quietly.

## 4. Commit and PR conventions

- Commit messages: no format is enforced by any check here. Write a clear, specific message that
  says what changed and, ideally, why — this repo's own history favors a plain descriptive
  sentence over a conventional-commits prefix, but nothing blocks either style.
- Open the PR against `main`.
- Fill in the PR template (`.github/PULL_REQUEST_TEMPLATE.md`) — it will be pre-loaded when you
  open the PR.
- **If your change fixes a specific open issue, and your diff's own commit/comment text already
  says so** (a word like "fixes"/"closes"/"resolves"/"patched"/"restored" sitting next to that
  issue's `#N`), your **PR body** must also contain a real GitHub closing phrase for that same
  issue: `Fixes #N`, `Closes #N`, or `Resolves #N` (case-insensitive), naming the issue currently
  open on the tracker. See §5's citation gate for exactly why and exactly what satisfies it. If
  your diff doesn't already narrate a fix for an open issue this way, this rule never applies to
  you and you can ignore it.

## 5. What CI checks, and what you'll see

Every PR against `main` runs these checks automatically. None of them require anything installed
on your side — they run entirely on GitHub's runners.

**Aggregate test runner and smoke check** (`exercise-loop.yml`) — runs the exact two commands from
§3. A red check here means one of those two scripts failed on your PR the same way it would fail
locally; the fix is to reproduce it locally and rerun.

**No Internal Leakage** (`no-internal-leakage.yml`) — scans every line your PR *adds* (not the
whole file, just the new lines) for three things: (1) a changed file living somewhere this repo
treats as a working-note path (`migration-audit/**`, or a root-level `HANDOFF*`/`KIMI-*`/`*-log.md`
file), (2) an absolute home-directory path (`/Users/<anyone>` or `/home/<anyone>`) added anywhere,
and (3) a term identifying the maintainer personally. **If it fails, the failure message will
never show you the matched text** — the maintainer's identity terms are never stored in this repo
and the CI log is public, so a rule-3 hit is reported with the matched text replaced by
`[REDACTED]`; you'll get the file, the line number, and which rule fired, not the string itself.
That's deliberate, not a bug in the check — if you're confused why a line was flagged, look at
what you actually wrote on that line: an absolute path, or anything that could identify a specific
person, is the shape it's looking for. This check also runs on a PR from a **fork** with one known
side effect: fork PRs don't receive repo secrets, so this specific check will show as "cannot
evaluate" (red) on a fork PR rather than silently passing — that is intentional (an unevaluated
run must never look clean) and is not something you broke.

**Fix Citation In PR Body Required** (`fix-citation-required.yml`) — this almost never fires. It
only activates when your diff's own added lines already contain a corrective phrase
(fix/fixes/closes/resolved/patched/addressed/restored/"no longer trusting"/"load-bearing", etc.)
sitting on the same line as a real `#N` reference to an issue that is *currently open* on the
tracker. If that shape shows up in your diff, the check then looks at your **PR body** (not your
commits, not your code) for a GitHub-recognized closing phrase — `close`/`closes`/`closed`/
`fix`/`fixes`/`fixed`/`resolve`/`resolves`/`resolved` immediately followed by `#N` for that same
issue number. If you never mention "fixes an open issue" in your diff at all, this check does
nothing and you'll never see it. Example that satisfies it on the first try — diff adds:

```
# Fixes #58: the resolver now walks every variable-path spelling instead of
# only the literal one.
```

— and the PR body includes the line:

```
Fixes #58
```

That's the whole requirement. A version string, a percentage, a hex color, or a
"prohibition #13"-style numbered-list reference will not trip this gate — those shapes are
filtered out before the corrective-phrase check even runs.

## 6. `action_required` — what it means and who clears it

The first time you (a new contributor, from a fork) open a PR, GitHub itself — not this repo's
config — holds the workflow runs at status `action_required` rather than running them
automatically. This is GitHub's own fork-PR approval gate, not something this repo's maintainers
chose to add on top. **Only someone with write access to the repo can clear it**, by opening the
PR's checks / the repo's Actions tab and clicking Approve on the pending run(s). There is nothing
you can do from a fork to clear this yourself — if your PR sits with checks showing
`action_required` and nothing seems to be happening, that is expected and is on the maintainer's
side, not a sign your PR is broken or ignored.

## 7. How review works, and what "closed" does and doesn't mean

A maintainer reviews PRs by hand; there's no auto-merge. Expect it to take longer than a single
sitting — the maintainer works on this alongside everything else. If your PR sits for a while with
no comment, that is very likely a backlog problem, not a rejection.

**A closed PR with no comment is not necessarily a verdict on the work.** It has happened before
that a PR got closed without an explanation attached. If that happens to yours and you don't know
why, it is completely reasonable to comment on the closed PR (or open a fresh issue linking to it)
asking what happened — reopening the conversation is expected, not pushy.

## 8. Reporting a security issue — privately, not in a public PR or issue

This repo's leakage gate (§5) exists because real personal and client data has leaked through this
pipeline before — that is the whole reason the gate was built. If you find a way *around* that
gate, or any other hole that could expose someone's data (a real example: a security hole was once
found in the publish gate by a user running this on Windows, protecting her own clients' data by
hand because the tooling didn't) — **please do not open a public issue or PR demonstrating it.** A
public repro of a data-leak bypass is itself a leak.

⚠ **Note for whoever reviews this before publishing:** as of this writing, GitHub's private
vulnerability reporting is **not enabled** on this repository (verified via the GitHub API this
session), and there is no `SECURITY.md`. That means there is currently no working private channel
to point a contributor to, and this file cannot honestly claim one exists. Until that's set up,
the safest instruction to a contributor is: **open an issue with the barest possible description —
"potential security issue in \<area\>, withholding details, please advise on a private channel" —
and stop there**, rather than either publishing exploit details or being told to email someone
whose contact info this file is not allowed to contain. **Recommend enabling GitHub's private
vulnerability reporting for this repo** (Settings → Security → Private vulnerability reporting) so
this section can point to `Security` → `Report a vulnerability` directly.
