# Where your own standing instructions go — `CLAUDE.local.md`

> **The short version.** Put your personal, standing instructions to the AI in a file named
> `CLAUDE.local.md` at the root of this repo. Claude Code auto-loads it alongside `CLAUDE.md` at the
> start of every session. Git does not track it, so an update can never overwrite it — and nothing you
> write in it can ever be published by accident.
>
> **Do not put them in `CLAUDE.md`.** That file ships with the product. Your next `git pull` will
> either overwrite your additions or hand you a merge conflict, and `UPDATE.md` is explicit that a
> conflict here is not something a session should resolve on your behalf.

## Why this file needs to exist at all

The harness ships one always-loaded instruction file, `CLAUDE.md`, and it belongs to the product.
Anything an operator wants every session to know about **their own** way of working — house rules,
standing preferences, hard constraints — has nowhere sanctioned to live. Left undocumented, the
obvious place to put it is `CLAUDE.md`, which is the one place it must not go.

`CLAUDE.local.md` is the answer, and it already works — it just was not written down anywhere.

## Verified behaviour

**It auto-loads.** Measured, not assumed: a sentinel string was written into `CLAUDE.local.md`, a
brand-new session was opened, and — before it read any file or ran any tool — it reported the string
present in its startup context and quoted it back. Claude Code lists it as *"user's private project
instructions, not checked in"*, loaded alongside `CLAUDE.md`.

**Both files load together**, not one or the other. They stack: the product's file explains the
machinery, yours says how to work with you.

> **If you run this test yourself, use a token the testing session has never seen.** A sentinel whose
> value also appears in the prompt you paste proves nothing — it reached the session by two routes and
> you cannot tell them apart. Generate a fresh random string, and ask the new session only for *any*
> line matching a prefix. It can only produce the value by genuinely having the file loaded.

## The trade-off, stated plainly

`CLAUDE.local.md` lives in the repo and git ignores it. That is what makes it safe from updates — and
it is also its one real limitation:

| | auto-loads? | survives `git pull`? | reaches your other machines? |
|---|---|---|---|
| `CLAUDE.md` | yes | **no — it is the product's file** | yes, via `git pull` |
| **`CLAUDE.local.md`** | **yes** | **yes — untracked** | **no — per-machine, by design** |
| a file in your notes folder | only if a hook loads it | yes | yes, if the folder is synced |

**It does not sync.** It is in the repo, not in your notes folder, so it neither travels on a `git
pull` nor rides along with a cloud-synced notes folder. **A second machine needs its own copy.**

⚠ **Drift between two machines is silent** — nothing compares them. If you run more than one install,
keep a copy of the file in your synced notes folder and note its checksum, so a later session can tell
whether the two have parted company:

```bash
shasum -a 256 CLAUDE.local.md
```

Re-copy it in the same act as any edit, or the two machines quietly stop agreeing.

## Why it is gitignored rather than merely untracked

Being untracked by default is not the same as being protected. `guard_git_add_class.sh` already blocks
the bulk-add class (`git add .`, `-A`, `--all`, `-u`, bare `git add`, `git add *`, `git add :/`, and
`git commit -a`), so no AI session can sweep it in. The residual exposure is a person running `git add
.` in a plain terminal outside Claude Code, or naming the file explicitly. A `.gitignore` line closes
that, and costs nothing.

**It also prevents a collision.** If a copy of `CLAUDE.local.md` were ever committed upstream, every
install that already has an untracked file at that path would have its next `git pull` refused —
*"untracked working tree file would be overwritten"*. Ignoring the path keeps that from happening.

## What belongs in it, and what does not

- **Belongs:** your standing rules and constraints, how you want work delivered, the checks you want
  applied to every output. Keep it ranked — a model retrieves reliably from the start and end of a
  context and degrades in the middle, so where a rule sits decides whether it fires.
- **Does not belong:** anything you would not want loaded into every single session. This file is paid
  for on every turn, so length has a running cost. Evidence, case histories and reference material
  belong in your notes folder, not here.
- **Also does not belong:** secrets. It is untracked, not encrypted.
