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
> The plugin itself is never lost: reinstall it. Part 1 applies to everyone.

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

> Operator-only recovery steps were moved to the operator's private notes (2026-10-31).
