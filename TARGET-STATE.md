# TARGET-STATE — what "correctly installed" actually means

**This file is the single source of truth for "correctly installed."** `INSTALL.md` builds toward
these six facts on a fresh machine. `REPAIR.md` reconciles an existing, possibly messy machine toward
the same six facts. Neither file restates the facts in its own words — they check them, and point
here. **If the install's shape ever changes, this file is the one that gets edited first** — then
`INSTALL.md` and `REPAIR.md` are updated to still land on what it says.

Run each check from the top of the Harness folder (`git rev-parse --show-toplevel` gets you there).
A healthy install prints the marker for all six; anything else names exactly which fact is false.

---

### 1. The Harness repo is at the top of the opened folder, on the right branch, hooks wired, not damaged
```bash
# The migration-1 arm is TRANSITIONAL. It comes out the day migration-1 merges into main, in the
# same edit that drops "-b migration-1" from INSTALL.md STEP 5. The two move together or not at all.
BR="$(git branch --show-current)"; BR="${BR:-(none - detached, not on any branch)}"
test -d .claude && test -d system && test -d shared \
  && { case "$BR" in
         main|migration-1) : ;;
         *) echo "FACT 1: NO - the release branch is $BR, expected main"; false ;;
       esac; } \
  && [ "$(git config core.hooksPath)" = "system/githooks" ] \
  && ! git fsck --full 2>&1 | grep -Eqi 'error|missing|corrupt' \
  && echo "FACT 1: OK"
```
**Meaning:** this folder — not one above it, not one below it — IS the Lifehack Harness: the right
code, the right branch, the safety catch turned on, and nothing broken inside the repository itself.

⚠ **Why a branch is checked at all, and why two names pass.** The clause is load-bearing: `INSTALL.md`
STEP 5 clones a *named* branch precisely because the default one is *"an older release with known
bugs"*, so this is the check that catches an install which quietly fetched the wrong code. **`main` is
the name this check is built around** — after the merge that is simply what a correct fresh install is
sitting on. The second name is scaffolding, and the comment in the block says when to remove it.

⚠ **A detached checkout is named, not swallowed.** `git branch --show-current` prints *nothing* on a
detached HEAD, so the old single-name test compared an empty string and failed with no output at all —
indistinguishable from a hooks or `fsck` failure. It now says which branch it found. A detached install
is genuinely wrong: it cannot take the `git pull --ff-only` that `UPDATE.md` depends on.

### 2. `.brain-root` exists at the repo root, is gitignored, and points at a real folder
```bash
test -f .brain-root && git check-ignore -q .brain-root && test -d "$(cat .brain-root)" && echo "FACT 2: OK"
```
**Meaning:** there is a one-line pointer to your AI Brain, it will never be uploaded to git, and the
folder it names actually exists.

### 3. The resolver answers through THIS repo's own pointer, not a stale global or an env var
```bash
python3 shared/brain_root.py | grep -q "(source: repo-pointer)" && echo "FACT 3: OK"
```
**Meaning:** when a skill asks "where is the AI Brain," it is answering from this install's own
pointer file — not a leftover machine-wide setting or a `$LIFEHACK_ROOT` left set by something else.

### 4. The AI Brain is cloud-synced — any service counts
```bash
python3 shared/brain_root.py --quiet | tr '[:upper:]' '[:lower:]' \
  | grep -Eq 'google drive|my drive|shared drives|cloudstorage|dropbox|onedrive|icloud' \
  && echo "FACT 4: OK"
```
**Meaning:** the AI Brain sits somewhere a sync service is actively backing up — Drive, OneDrive,
Dropbox or iCloud, whichever the person already uses. Losing the laptop does not lose the AI Brain.

### 5. A write to the AI Brain lands, and reads back
```bash
N="$(python3 shared/brain_root.py --quiet)" && F="$N/.target-state-writetest" \
  && printf 'ok\n' > "$F" && [ "$(cat "$F")" = "ok" ] && rm -f "$F" && echo "FACT 5: OK"
```
**Meaning:** the connection is not just a path string that looks right — a real file can be written into
the AI Brain and read back out again.

### 6. Nothing personal is staged in git
```bash
[ -z "$(git status --porcelain)" ] && echo "FACT 6: OK" || echo "FACT 6: NOT CLEAN — read the output before doing anything else"
```
**Meaning:** no export, note, credential, or stray file of the person's is sitting in the Harness repo
waiting to be committed. On a fresh install this must be completely empty; mid-development on the repo
itself it will legitimately show tracked files under edit — that is a different situation from a
person's own material appearing here, which is what this check exists to catch.

---

**Verified on this rig, 2026-08-17:** facts 1–5 print OK against a real repo-pointer and a real Drive
test folder (`AI Brain 2 TEST DATA/rig-data`). Fact 6 correctly reports NOT CLEAN while this repo has
editorial changes in flight — expected here, and exactly the signal a real install should never show.

## FACT 7 — the brain is the RIGHT house, says its human
The AI Brain this harness points at is the person's real one — confirmed by them, not
inferred from green plumbing. Check: ask. A connected empty scaffold passes facts 1-6; only the
human can pass fact 7. (Added after a live repair connected everything perfectly to a folder
created twenty minutes earlier.)

## FACT 8 — one engine, unambiguous names, no live lookalikes
Exactly one harness on this machine points at this brain, the harness and brain carry names a
person cannot mistake, and every other brain-shaped folder is archived (e.g. zz-archive- prefix)
or has a one-line explanation. A machine that passes 1-7 with two live engines or five lookalike
folders is not repaired — it is confusion on a delay timer. (The operator's standard, 2026-08-17:
"buttoned up, radically clear." Repair is not done until this is true.)
