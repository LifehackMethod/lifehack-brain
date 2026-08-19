# TARGET-STATE — what "correctly installed" actually means

**This file is the single source of truth for "correctly installed."** `INSTALL.md` builds toward
these six facts on a fresh machine. `REPAIR.md` reconciles an existing, possibly messy machine toward
the same six facts. Neither file restates the facts in its own words — they check them, and point
here. **If the install's shape ever changes, this file is the one that gets edited first** — then
`INSTALL.md` and `REPAIR.md` are updated to still land on what it says.

Run each check from the top of the Harness folder (`git rev-parse --show-toplevel` gets you there).
A healthy install prints the marker for all six; anything else names exactly which fact is false.

⚠ **No fact below may pass on a path inside the Harness repo itself.** A tester's entire AI Brain once
lived inside the repo, in a folder literally named `My Drive`, and five of eight facts went green —
"cloud-synced" matched the folder's NAME, and "a write lands and reads back" wrote into git. Facts 2,
3, 4 and 5 each independently resolve the AI Brain path and independently refuse it if it IS the
Harness repo or is INSIDE it — real path resolution (`os.path.realpath`, so a `/tmp` vs `/private/tmp`
symlink cannot hide it), never a string-prefix comparison on the raw input. Each uses the same
`harness_root()` that `shared/brain_root.py --set` itself refuses against, so there is one definition
of "inside," not four drifting copies of the idea. Folded into the facts that already resolve a path,
not a ninth standalone fact — a standalone fact is one a partial copy-paste run of this file can skip;
these cannot, because they gate the very checks that would otherwise go green on the bad path.

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

### 2. `.brain-root` exists at the repo root, is gitignored, and points at a real folder OUTSIDE the Harness
```bash
BRAIN="$(cat .brain-root 2>/dev/null)"
if ! test -f .brain-root; then
  echo "FACT 2: NO - .brain-root does not exist at the repo root"
elif ! git check-ignore -q .brain-root; then
  echo "FACT 2: NO - .brain-root exists but is not gitignored -- it could get committed"
elif ! test -d "$BRAIN"; then
  echo "FACT 2: NO - .brain-root points at '$BRAIN', which is not a real folder"
elif python3 -c "
import sys, os
sys.path.insert(0, 'shared')
import brain_root
h = os.path.realpath(brain_root.harness_root())
t = os.path.realpath(sys.argv[1])
sys.exit(0 if (t == h or t.startswith(h + os.sep)) else 1)
" "$BRAIN"; then
  echo "FACT 2: NO - '$BRAIN' is INSIDE the Harness repo (or is the repo root itself) -- the AI Brain must live outside it, or it gets wiped the day the repo is updated or deleted"
else
  echo "FACT 2: OK"
fi
```
**Meaning:** there is a one-line pointer to your AI Brain, it will never be uploaded to git, the
folder it names actually exists, and — the part a name-only install used to miss — that folder is not
secretly sitting inside the program folder itself.

### 3. The resolver answers through THIS repo's own pointer, not a stale global, an env var, or a path inside the Harness
```bash
SRC_LINE="$(python3 shared/brain_root.py)"
BRAIN="$(python3 shared/brain_root.py --quiet)"
if ! printf '%s' "$SRC_LINE" | grep -q "(source: repo-pointer)"; then
  echo "FACT 3: NO - resolver answered from somewhere other than this repo's own pointer: $SRC_LINE"
elif [ -z "$BRAIN" ]; then
  echo "FACT 3: NO - resolver reported repo-pointer as the source but returned no usable path"
elif python3 -c "
import sys, os
sys.path.insert(0, 'shared')
import brain_root
h = os.path.realpath(brain_root.harness_root())
t = os.path.realpath(sys.argv[1])
sys.exit(0 if (t == h or t.startswith(h + os.sep)) else 1)
" "$BRAIN"; then
  echo "FACT 3: NO - resolved path '$BRAIN' is inside the Harness repo -- not a valid AI Brain location"
else
  echo "FACT 3: OK"
fi
```
**Meaning:** when a skill asks "where is the AI Brain," it is answering from this install's own
pointer file — not a leftover machine-wide setting, not a `$LIFEHACK_ROOT` left set by something
else, and not a path that happens to live inside the program folder.

### 4. The AI Brain is cloud-synced — checked against a real mount on this machine, never a name
```bash
BRAIN="$(python3 shared/brain_root.py --quiet)"
if [ -z "$BRAIN" ]; then
  echo "FACT 4: NO - brain_root.py could not resolve a path"
else
  python3 -c "
import sys, os, glob
brain = sys.argv[1]
sys.path.insert(0, 'shared')
import brain_root
h = os.path.realpath(brain_root.harness_root())
t = os.path.realpath(brain)
if t == h or t.startswith(h + os.sep):
    print('FACT 4: NO - ' + repr(brain) + ' is inside the Harness repo, so it cannot be a real cloud-sync target')
    sys.exit(1)
home = os.path.expanduser('~')
candidates = sorted(glob.glob(os.path.join(home, 'Library/CloudStorage/*')))
candidates.append(os.path.join(home, 'Library/Mobile Documents/com~apple~CloudDocs'))
candidates.append(os.path.join(home, 'Dropbox'))
candidates.append(os.path.join(home, 'OneDrive'))
matched = None
for c in candidates:
    if not os.path.isdir(c):
        continue
    rc = os.path.realpath(c)
    if t == rc or t.startswith(rc + os.sep):
        matched = c
        break
if matched:
    print('FACT 4: OK - under real sync mount ' + matched)
    sys.exit(0)
print('FACT 4: NO - ' + repr(brain) + ' does not sit under any real cloud-sync mount found on this machine (checked ~/Library/CloudStorage/*, iCloud Drive, ~/Dropbox, ~/OneDrive) -- a folder merely NAMED My Drive no longer counts')
sys.exit(1)
" "$BRAIN"
fi
```
**Meaning:** the AI Brain sits somewhere a real, currently-mounted sync service on THIS machine is
backing it up — checked by walking to the actual provider folder on disk, never by reading words out
of the path's name. Losing the laptop does not lose the AI Brain.

⚠ **What this still cannot catch, honestly.** It only knows macOS's own sync-provider mount points
(`~/Library/CloudStorage/*` — Google Drive, and modern Dropbox/OneDrive when they use the File
Provider framework — plus legacy `~/Dropbox`, `~/OneDrive`, and iCloud Drive). It cannot tell whether
that provider is actually online and syncing right now versus paused or signed out — sitting *under*
the mount is necessary but not sufficient for "backed up this second." It knows nothing about Linux or
Windows sync-client conventions. And a cloud service this list has never heard of, mounted somewhere
else, will still read NOT SYNCED even if it genuinely is synced. It is real-mount-membership, not a
live sync-health check.

### 5. A write to the AI Brain lands, and reads back — never inside the Harness
```bash
N="$(python3 shared/brain_root.py --quiet)"
if [ -z "$N" ]; then
  echo "FACT 5: NO - brain_root.py could not resolve a path"
elif python3 -c "
import sys, os
sys.path.insert(0, 'shared')
import brain_root
h = os.path.realpath(brain_root.harness_root())
t = os.path.realpath(sys.argv[1])
sys.exit(0 if (t == h or t.startswith(h + os.sep)) else 1)
" "$N"; then
  echo "FACT 5: NO - resolved path '$N' is inside the Harness repo -- refusing to write a test file into the repository itself"
else
  F="$N/.target-state-writetest"
  if printf 'ok\n' > "$F" 2>/dev/null && [ "$(cat "$F" 2>/dev/null)" = "ok" ]; then
    rm -f "$F"
    echo "FACT 5: OK"
  else
    echo "FACT 5: NO - could not write to and read back from $F"
  fi
fi
```
**Meaning:** the connection is not just a path string that looks right — a real file can be written
into the AI Brain (first confirmed to be a folder outside the program itself) and read back out again.

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
