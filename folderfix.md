# Let's fix your folders — about ten minutes, and it does the work for you

Something in the setup instructions was wrong, and it's my fault, not yours. Your files ended up in a shape that stops the tool from working properly. **Nothing is lost and nothing is broken** — it's in the wrong place, and this fixes it.

**What to do:** open Claude the way you normally do, drag this file into the chat, and say **"fix my folders."**

Then answer its questions. There are only two moments it needs you, and it'll say so clearly. It does everything else itself — **you will not have to move a single file or type a single command.**

⚠ **One thing worth knowing before you start.** Claude sometimes stops and asks permission before it does something — a little box with an **Allow** button. **If it goes quiet, that's what happened.** It isn't stuck or broken; it's waiting on you. Click Allow and it carries on.

---
---
---

# ⬇ EVERYTHING BELOW THIS LINE IS FOR CLAUDE. YOU DON'T NEED TO READ IT.

*(It's the repair instructions. It's meant to look like this.)*

---
---
---

# INSTRUCTIONS FOR CLAUDE

**You are repairing a non-technical person's folder layout. Read all of this before doing anything.**

> ## ⛔⛔ THEY MUST NEVER SEE A COMMAND. THIS IS THE WHOLE BRIEF.
>
> This person did not open a terminal to get here — they typed a sentence.
>
> - ⛔ **Never print a command, never ask them to run one, never ask them to approve one.** Run it and say in one plain sentence what happened.
> - ⛔ **Never show a status token.** Not `OK`, not a tick, not an exit code. Whole sentences.
> - ⛔ **Never invent a result.** If you couldn't check something, say so. They cannot tell a confident guess from a fact and they will act on it.
> - ⛔ **Never say "some checks failed."** Name the thing, in words they can repeat to someone helping.

> ## ⛔⛔ THIS FILE MOVES SOMEBODY'S ONLY COPY OF THEIR OWN WRITING. TREAT IT THAT WAY.
>
> - ⛔ **Never delete a file you cannot prove is redundant.** The one deletion permitted below requires a byte-for-byte match against a copy that still exists. Everything else moves.
> - ⛔ **Never merge into an existing folder.** If the destination already exists, STOP and ask.
> - ⛔ **If any step fails, STOP.** Do not improvise a recovery, do not try a second approach. Tell them plainly what failed and that nothing further will be touched.

---

## THE SHAPE WE ARE BUILDING — memorise this, everything below serves it

    AI Brain/              <- LOCAL folder. NEVER inside Google Drive / OneDrive / Dropbox.
    ├── lifehack-brain/       the tool. a git repository. NOT backed up.
    └── data/                 everything they write. Backup mirroring points HERE and nowhere else.

⛔ **EXACTLY TWO FOLDERS INSIDE `AI Brain`. Not three. No spare folder, no quarantine folder, no leftovers.** If you finish and there is a third thing at that level, you have not finished.

**Why each rule exists — say these if they ask, don't recite them unprompted:**
- **`AI Brain` is local** because it contains a git repository, and cloud sync fights with git. Git creates and deletes hundreds of tiny files as it works; the sync tool grabs them mid-operation. It never fails loudly — it corrupts quietly.
- **`data` is the only thing backed up** because it is the only thing that is theirs and irreplaceable. The tool can always be downloaded again.
- ⭐ **"Backup mirroring" means the folder is a REAL, PERMANENT folder on their hard drive that a service copies upward.** It does NOT mean the folder lives inside Google Drive. That distinction is the whole reason we are here.

---

## STEP 0 — Say what's happening, get a go

Tell them in about four sentences: their folders are in the wrong shape and it's stopping the tool working; you're going to move things into the right shape; it takes about ten minutes; nothing gets deleted and you'll show them everything before you move it. Then ask if they're ready and **wait**.

---

## STEP 1 — Find out what they actually have. Assume NOTHING.

⛔ **Do not assume the folder is called "AI Brain."** Some people named it something else.
⛔ **Do not assume they have backup set up.** Most don't, even the ones who think they do.

**Work out quietly, then report in plain sentences:**

**1. What machine is this?**

    uname -s 2>/dev/null || echo "Windows"

`Darwin` = Mac. Anything else, treat as Windows. **Everything below has a Mac path and a Windows path. Pick one and never show them the other.**

**2. Where is their stuff?** Ask: *"Which folder have you been opening when you use this? If you're not sure, drag it into the chat."* Call that their **current folder**.

**3. Is their current folder inside a cloud service?** Check the path for any of: `Library/CloudStorage` · `My Drive` · `Shared drives` · `OneDrive` · `Dropbox` · `iCloud` · `Mobile Documents` · a bare drive letter like `G:\`

⛔ **Do not just look for the word "Google" — on Windows, Google Drive appears as `G:\My Drive\...` with no occurrence of "Google" anywhere in the path.**

**4. Is there a git repository inside it?**

    find "<their current folder>" -maxdepth 2 -name .git -type d

If yes **and** it's inside a cloud service — **that is the core problem.** Say so plainly: *"The tool is sitting inside your cloud storage, and those two fight each other in a way that damages files quietly. That's what we're fixing."*

**5. Do they have real backup mirroring?** On a Mac:

    sqlite3 "$HOME/Library/Application Support/Google/DriveFS/root_preference_sqlite.db" "SELECT last_seen_absolute_path FROM roots;" 2>/dev/null

An empty result means **no backup at all**, whatever they believe. **Tell them honestly** — it's the most important thing they'll learn today.

⛔ **SPECIAL CASE — a Google SHARED drive** (`G:\Shared drives\...`). Google can only *stream* those, never keep real files. Their files may be placeholders that fail when something needs them. **Say so explicitly and move them off it. Not optional.**

**Then summarise back to them, in sentences:** where their stuff is, whether it's in the cloud, whether the tool is tangled up in it, and whether they actually have a backup. **Ask them to confirm before you move anything.**

---

## STEP 2 — Show them what's filed in the wrong place

Before moving anything, look for things in the wrong folder — this happens a lot and they need to see it.

**Their material stuck inside the tool folder** — anything git isn't tracking:

    cd "<the repo>" && git ls-files --others --exclude-standard

Usually a ChatGPT export, or notes saved into the wrong window. **It goes into `data`.**

**Our machinery sitting in their data folder** — a file whose name also exists inside the repo. **Show them the list.** Say what each one is, in plain words.

⛔ **Do not move anything yet, and do not delete anything yet.** This step only shows.

---

## STEP 3 — Build the new home

Pick the destination **for their operating system** and tell them the full path before creating it.

**Mac:** `~/AI Brain`

**Windows:** `%USERPROFILE%\Documents\AI Brain` — ⛔ **NOT the top-level home folder.** Windows refuses write access there in this app; a real student hit it and had to be relocated mid-install.

⚠ **If they'd rather it went elsewhere, fine — but re-run STEP 1's cloud check on their choice first. A folder they picked themselves is exactly the one most likely to be inside Google Drive.**

⛔ **If that folder already exists, STOP.** Do not merge into it. Tell them it's there and ask whether to use a different name.

    mkdir -p "<new root>"

---

## STEP 4 — Move everything. Straight moves.

⛔ **Order matters and it is load-bearing. Do these in exactly this sequence.**

**4a. Their files out of the tool folder first**, before anything else moves:

    mkdir -p "<new root>/data"
    mv "<each untracked file from STEP 2>" "<new root>/data/"

**4b. Their data folder.** If `<new root>/data` already exists because of 4a, merge into it; otherwise move it whole:

    mv "<their data folder>" "<new root>/data"
    # or, if <new root>/data already exists:
    rsync -a "<their data folder>/" "<new root>/data/" && rm -rf "<their data folder>"

**4c. The tool folder.**

    mv "<the repo>" "<new root>/lifehack-brain"

⭐ **Moving a git repository is completely safe — verified.** Same history, same connection to GitHub, no re-login. Nothing about a repo depends on where it sits. **Say that if they look worried.**

**4d. NOW clean up the misfiled machinery — and only now.**

⚠ **This must come AFTER 4c, because it compares each stray against the repo's own copy. Run it before the repo has moved and it finds nothing to compare against and silently leaves everything in place.**

For each stray from STEP 2, find the file of the same name inside the moved repo and compare:

    cmp -s "<new root>/data/<name>" "<the repo's copy>"

- **Identical** → delete the stray. It's a duplicate and the real one is safe in the repo. Say which file you deleted and why.
- **Not identical, or no match found** → **LEAVE IT WHERE IT IS** and tell them: *"This one looks like part of the tool but it isn't the same as ours, so I've left it alone for a human to look at."*

⛔ **Those are the only circumstances in which anything is deleted, ever.**

---

## STEP 5 — Reconnect their backup

**If STEP 1 found an existing backup entry** — repoint it. They don't have to do anything.

    cp "$HOME/Library/Application Support/Google/DriveFS/root_preference_sqlite.db" "$HOME/drivefs-backup-$(date +%s).db"
    osascript -e 'quit app "Google Drive"'
    sleep 6
    sqlite3 "$HOME/Library/Application Support/Google/DriveFS/root_preference_sqlite.db" "UPDATE roots SET root_path='<new root minus leading slash>/data', last_seen_absolute_path='<new root>/data', title='data' WHERE root_id=<the id>;"
    open -a "Google Drive"

⚠ **Four things to get right:** quit Drive first and wait for it to actually exit · back up that database before touching it · update **only** the row matching their folder · and note the format quirk: **`root_path` has no leading slash, `last_seen_absolute_path` does.** Get that wrong and Drive can't find the folder.

**Then verify**, and if Drive still says the folder is missing, tell them to click the **Locate** button in Drive's notification and pick `<new root>/data`. **One click. Don't apologise at length.**

**If there was no backup** — set one up. This is the one thing they do themselves.

- **Google Drive:** *"Click the Drive icon in your menu bar, then the gear, then Preferences. On the left choose 'Folders from your computer'. Click Add folder, pick `<new root>/data`, and tick 'Sync with Google Drive'."*
- **OneDrive:** ⚠ **OneDrive can only back up Desktop, Documents and Pictures — there is no 'add any folder' option.** So on Windows the new root must be inside `Documents` (STEP 3 already does this), and their backup comes from OneDrive's Documents backup: *"Click the OneDrive cloud icon, then Settings, then 'Sync and backup', then 'Manage backup', and make sure Documents is switched on."*
- **Dropbox:** same shape as Google Drive — it can back up a chosen folder from its preferences.

⛔ **BACK UP `data` AND NOTHING ELSE. Never the folder above it.** That one holds the git repository, and backing it up recreates the exact problem we just fixed.

---

## STEP 6 — Check your own work, out loud

Verify each of these and tell them the result in plain sentences. **If any is wrong, say so — never round it up.**

- The new root holds **exactly two folders**: `lifehack-brain` and `data`. Nothing else.
- Neither the new root nor the tool folder is inside any cloud service path.
- The tool folder still has its `.git` folder, and `git status` runs without error.
- Their files are in `data` — name the ones you moved.
- Nothing of theirs is left inside the tool folder: `git ls-files --others --exclude-standard` returns nothing.
- The old location no longer holds a `data` folder or a repo.

---

## STEP 7 — Hand it back

> **"You're fixed. From now on, open Claude on the folder called `AI Brain` — that one, not the ones inside it. Everything the tool needs is in there. Your own writing lives in `data`, and that's the part being backed up."**

Then **stop.** Do not run anything else, do not offer to start an ingest.

---

# IF SOMETHING GOES WRONG

**1. It stopped and nothing is happening.** Almost always a permission box waiting for an **Allow** click. Look for it.

**2. A move failed partway.** ⛔ **Stop. Do not attempt a repair.** Tell them exactly which file failed and where the rest ended up, and have them send that message on. **A half-repaired folder that someone then improvises on is much worse than one that stopped cleanly.**

**3. Drive says the folder is missing after the move.** Expected if the automatic repoint didn't take. Click **Locate** in Drive's notification and pick the `data` folder. One click.

**4. `python` opens the Microsoft Store instead of working.** Windows ships decoy `python.exe` and `python3.exe` files and puts them early on the PATH, so they beat the real one. Fix: Settings → Apps → **Advanced app settings** → **App execution aliases** → switch off `python.exe` and `python3.exe`. ⭐ **Then open a NEW window — it won't take effect in one that's already open, and it will look like the fix failed.**
