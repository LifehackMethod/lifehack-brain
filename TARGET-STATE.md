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
test -d .claude && test -d system && test -d shared \
  && [ "$(git branch --show-current)" = "migration-1" ] \
  && [ "$(git config core.hooksPath)" = "system/githooks" ] \
  && ! git fsck --full 2>&1 | grep -Eqi 'error|missing|corrupt' \
  && echo "FACT 1: OK"
```
**Meaning:** this folder — not one above it, not one below it — IS the Lifehack Harness: the right
code, the right branch, the safety catch turned on, and nothing broken inside the repository itself.

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
**Meaning:** when a skill asks "where do my notes live," it is answering from this install's own
pointer file — not a leftover machine-wide setting or a `$LIFEHACK_ROOT` left set by something else.

### 4. The notes folder is cloud-synced — any service counts
```bash
python3 shared/brain_root.py --quiet | tr '[:upper:]' '[:lower:]' \
  | grep -Eq 'google drive|my drive|shared drives|cloudstorage|dropbox|onedrive|icloud' \
  && echo "FACT 4: OK"
```
**Meaning:** your notes live somewhere a sync service is actively backing up — Drive, OneDrive, Dropbox
or iCloud, whichever the person already uses. Losing the laptop does not mean losing the notes.

### 5. A write to the notes folder lands, and reads back
```bash
N="$(python3 shared/brain_root.py --quiet)" && F="$N/.target-state-writetest" \
  && printf 'ok\n' > "$F" && [ "$(cat "$F")" = "ok" ] && rm -f "$F" && echo "FACT 5: OK"
```
**Meaning:** the connection is not just a path string that looks right — a real file can be written into
the notes folder and read back out again.

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
