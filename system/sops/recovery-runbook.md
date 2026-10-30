---
topic: [system-architecture]
id: system-playbook-recovery-runbook
title: Recovery Runbook — get your personal code and notes back after a failure
record_type: playbook
desk: root
created_at: 2026-06-22
updated_at: 2026-07-28
status: active
authority: user
---

# Recovery Runbook

> Two things of yours can be lost, and they are kept in different places. **Your personal code** lives in
> your personal code folder (default `~/lifehack-personal-code`; the pointer file
> `~/.config/lifehack/personal-code` says where, and `python3 <plugin>/shared/personal_code_root.py --quiet`
> prints it). **Your notes** live in your notes folder (the AI Brain; `python3 <plugin>/shared/brain_root.py --quiet`).
> The plugin itself is never lost: reinstall it. Part 1 applies to everyone. Part 2 is the maintainer's
> own GitHub-backed setup, kept as an optional reference (for the maintainer the personal code folder is ClaudeOps).

# Part 1. Everyone

## 1. Your personal code folder
- **Local git history (on by default).** Setup runs `git init` in the folder, so every commit you make is
  a point you can return to: `git -C "$(python3 <plugin>/shared/personal_code_root.py --quiet)" log --oneline`
  to see them, `git -C <folder> restore <file>` to bring back one file, `git -C <folder> checkout <commit> -- <file>`
  for an older version.
- **Backup (pick one, or both).** Time Machine covers the whole folder with no account. Or add a GitHub
  remote you own: create an empty private repo, then `git -C <folder> remote add origin <url>` and
  `git -C <folder> push -u origin main`. Push after you commit; a commit alone is not a backup.
- **Folder deleted or the pointer is wrong.** `personal_code_root.py` says `POINTER-MISSING` and does NOT
  switch to the default (that would split your history). Restore the folder from Time Machine or your
  remote (`git clone <url> <folder>`), or fix the one line in `~/.config/lifehack/personal-code`.
- **Nothing set up yet.** Run `python3 <plugin>/system/tools/bootstrap.py`: it creates the folder and
  pointer if they are missing and never overwrites an existing pointer.

## 2. Your notes folder
- Notes in Google Drive: Drive web, right-click, **Version history** or **Restore** (30-day window).
- Notes in a plain local folder: Time Machine, or dated copies you made yourself.
- If the notes folder moved, repoint it: `python3 <plugin>/shared/brain_root.py --set <path>`.

## 3. The plugin
- Reinstall or update it (see `UPDATE.md` and `REPAIR.md`). It holds no personal code and no notes.

# Part 2. Optional: the maintainer's GitHub-backed setup (ClaudeOps)

> This is the maintainer's own arrangement, kept here as a worked example for anyone who wants GitHub
> as their backup. The commands below name `~/claudeops-config` as the code clone; for the maintainer that
> is the ClaudeOps repo, i.e. the personal code folder. Replace `<your-gh-user>` with your own GitHub
> username wherever it appears. The system is two tiers (P9): **code = the git clone
> `~/claudeops-config` (origin: GitHub `<your-gh-user>/claudeops-config`, PRIVATE); content = Google Drive
> `_ClaudeOps/`** (synced by Google Drive for Desktop). Three independent recoveries exist: GitHub (code),
> Drive 30-day history (content), and the dated archives under `_ClaudeOps/state/archive/` (point-in-time
> backups). Sessions launch from the clone; skills read content via absolute `$DRIVE/…` paths.

## A. A machine dies / new machine
> **⚡ REHEARSED FOR THE FIRST TIME 2026-07-28 (S2.5). It had never once been executed — and steps 1–2
> were both unrunnable as written.** Corrected below from live measurement, not memory. **Steps 0 and 2a
> are NEW and are the difference between this working and stalling.**

0. **GitHub credentials FIRST — this is where a real cold restore stalls.** *(NEW 2026-07-28.)* The repo is
   **PRIVATE — verified via an unauthenticated GitHub API call returning HTTP 404.** A blank Mac has no SSH
   key and no credential helper, so **step 2 cannot run until you can authenticate.** Do ONE of:
   - `gh auth login` (install first: `brew install gh`) — easiest on a fresh machine; or
   - generate an SSH key (`ssh-keygen -t ed25519`), add the public key at github.com → Settings → SSH keys,
     then use the SSH URL in step 2.
   > ⚠ **A `git clone https://…` that "works" on an EXISTING machine proves nothing** — the macOS keychain
   > helper silently supplies cached credentials. When rehearsing this, an anonymous `git ls-remote` test
   > reported the repo PUBLIC and was **WRONG**; only the unauthenticated API call exposed the truth.
   > **Verify visibility with `curl -s -o /dev/null -w '%{http_code}' https://api.github.com/repos/<your-gh-user>/claudeops-config` — 404 means private.**
1. Install: Homebrew, then **`brew install googleworkspace-cli`** (⚠ **the formula is NOT called `gws`** —
   `brew install gws` fails; the binary `gws` is what that formula provides, currently 0.22.5), the `claude`
   CLI (⚠ **NOT a brew formula** — it installs to `~/.local/share/claude/versions/` via the native installer,
   so `brew install claude` will not work), and Google Drive for Desktop (sign in → let `_ClaudeOps/` sync
   down — **wait for the sync to finish; a partially-synced Drive fails step 6 confusingly**).
   *(Previously this step read `` gws (`brew install ...`) `` — a literal ellipsis nobody could execute.)*
2. Clone the code tier — **needs step 0 done first**:
   `git clone https://github.com/<your-gh-user>/claudeops-config.git ~/claudeops-config`
   (or the SSH form `git@github.com:<your-gh-user>/claudeops-config.git`, which is what a working machine actually uses).
3. Wire `~/.claude/*` symlinks → clone: `bash ~/claudeops-config/system/tools/bootstrap-machine.sh`.
4. Rebuild gws auth (see D). Rebuild the headless cron token (see E) if this machine runs Pulse/runners.
5. Restore the OS schedule from the versioned manifest — **do not hand-add cron lines**:
   `bash ~/claudeops-config/system/tools/install-schedulers.sh --install`
   This reads `system/jobs.md` (the enforced single source of truth for all crontab + launchd jobs)
   and installs the correct schedule for this machine. If this machine should be the Pulse writer (primary vs secondary),
   flip the primary-machine marker first: `bash ~/claudeops-config/system/tools/claudeops-lead.sh primary`
   (or `mba`). The marker lives at `state/primary-machine` ⛔ in the maintainer's personal code folder, not shipped in the plugin.
6. Verify: `python3 ~/claudeops-config/system/tools/verify-connections.py` (board) +
   `python3 ~/claudeops-config/system/tools/check-content-paths.py` (P9 clean).

## B. The clone is corrupt / history broken (single machine)
- Re-clone from GitHub: `mv ~/claudeops-config ~/claudeops-config.bad && git clone …`. GitHub is canonical
  for code. Then re-run `bootstrap-machine.sh`.
- If GitHub itself is wrong (e.g. a bad force-push), restore from the newest bundle in
  `_ClaudeOps/state/archive/*-pre-*/` : `git clone <bundle> ~/claudeops-config` then `git push --force`.

## C. Content (Drive) lost or a file clobbered
- Single file/folder: Google Drive web → right-click → **Version history** / **Restore** (30-day window).
- A whole subtree: restore from the relevant `_ClaudeOps/state/archive/YYYY-MM-DD-*/` dated backup
  (byte-identical copies, `diff`-proven at creation).
- Canon/records live ONLY on Drive (P9) — never look for them in the clone; the clone holds only pointers.

## D. gws (Google) auth broken
- Verify first: `gws auth status`. NEVER `gws auth logout` or touch `~/.config/gws/` (destroys creds for all
  windows). Recovery is one path: user runs `! gws auth login --full` from a GUI session, then `gws auth status`.
- For headless cron (keychain-unreachable): from a GUI session,
  `gws auth export --unmasked > ~/.config/claudeops/gws-credentials.json && chmod 600 "$_"` (machine-local,
  NEVER on Drive). See `system/tools/gws-reauth.sh` ⏳ unruled — not yet ported to this repo header for the isolation rationale — corrected
  path; no `emily-breakdown-run.sh` exists in this repo (`emily-breakdown` is a supervised-manual
  skill with no crontab runner script).

## E. Headless cron token (claude)
- `claude setup-token` → save the `sk-ant-oat01-…` to `~/.config/claudeops/claude-oauth-token` (chmod 600,
  machine-local, never Drive). Runners export it as `CLAUDE_CODE_OAUTH_TOKEN`.

## F. The secondary machine is out of sync (e.g. after a history rewrite)
- The secondary machine is a peer clone + observer (single-writer = the primary machine owns scheduled Drive writes). To resync after a
  normal change: `cd ~/claudeops-config && git pull --ff-only`. **After a history rewrite/force-push** a pull
  will fail — instead: `git fetch origin && git reset --hard origin/main && git gc --prune=now`.

## G. Sanity checklist (any recovery)
> **⚡ REHEARSED 2026-07-28 — BOTH BARS FAILED, AND NEITHER FAILURE MEANT THE RECOVERY WAS BROKEN.**
> That is the worst possible property in a recovery check: it fires on a healthy system, so a real
> operator mid-recovery cannot tell "my restore failed" from "this bar was always wrong." Corrected to
> bars that can actually pass. **Measured, not recalled.**

- **`verify-connections.py` → expect `5/6` on the secondary machine today, NOT 6/6.** *(Was "6/6 desk tiles GREEN" — an
  **unpassable** condition.)* The 6th is **dobby**, reported STALE at **584.2 h ≈ 24.3 days**, which exactly
  matches the primary machine being dark since 2026-07-04. **dobby is machine-local to the primary machine and was ruled
  DORMANT by design (`c08f554`) — its red is CORRECT, not a defect.** A recovery bar that can only go green
  when a deliberately-offline machine is online is the same unfalsifiable-condition defect this system's
  audit keeps finding. **⇒ Read the LIST, not the ratio: every tile except a known-dormant one must be
  fresh.** If dobby ever matters again, it is tracked in `<notes>/state/debt-ledger.md`, under the person's own
  notes folder (never committed here), not here.
- **`check-content-paths.py` → currently reports 55 bare CONTENT paths and exits 1.** *(Was "P9 clean (0 bare
  content paths)".)* **⇒ Do NOT treat a non-zero count as a failed recovery.** These are pre-existing
  doc-prose violations across the repo, not something a restore introduces. **The recovery-relevant assertion
  is the DELTA: run it before and after and confirm the count did not GROW**, plus `0 content tracked in git`,
  which is the half that genuinely indicates a broken restore.
- A fresh desk session loads its persona + canon (canon comes from `$DRIVE/desks/{desk}/canon/`).
- `/save` writes under `$DRIVE/…`, never the clone. ⛔ `/save` — harness skill, since removed from
  this repo by the source cutover and served by the plugin instead.

> Drive pointer: a copy of this lives at `_ClaudeOps/system/sops/` is LEGACY — canonical is the clone
> (`~/claudeops-config/system/sops/recovery-runbook.md`). When abroad and only Drive is reachable, the
> clone is also on GitHub — clone it fresh per §A.
