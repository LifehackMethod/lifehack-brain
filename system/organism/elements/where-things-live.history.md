# History log for where-things-live.md

Text cut or moved out of the SOP, copied verbatim first. Append-only.

## 2026-10-31 - reason: Enver 2026-10-31 ruling (Round D, A.5): symlinks into ~/.claude are allowed and recommended, not prescribed; the 'Do NOT symlink' ban (Bekim 2026-08-12, 6f9ecc2, never tested) is removed.

~~~~
  - INSTALL.md (the AI Brain setup authority; the no-symlink-into-~/.claude rule)

~~~~

## 2026-10-31 - reason: Enver 2026-10-31 ruling (Round D, A.5): symlinks into ~/.claude are allowed and recommended, not prescribed; the 'Do NOT symlink' ban (Bekim 2026-08-12, 6f9ecc2, never tested) is removed.

~~~~
**And it cannot be closed by a symlink either.** `INSTALL.md` states plainly: *"⛔ Do NOT symlink
anything into `~/.claude/`. Symlinks are Mac-coupled and this has to work on Windows too."* Symlinking
`~/.claude/skills/<name>` out to a Drive-backed folder — the obvious workaround — is exactly the move
that rule forecloses, and for a real reason, not caution for its own sake: a symlink is a filesystem
feature that behaves differently (or not at all) across operating systems, and this product ships to
both.


~~~~

## 2026-10-31 - reason: Enver 2026-10-31 ruling (Round D, A.5): symlinks into ~/.claude are allowed and recommended, not prescribed; the 'Do NOT symlink' ban (Bekim 2026-08-12, 6f9ecc2, never tested) is removed.

~~~~
   skills and the no-symlink rule), or the guard's rationale for blocking is revisited. Not resolved

~~~~

## 2026-10-31 - reason: Enver 2026-10-31 ruling (Round D, A.5): symlinks into ~/.claude are allowed and recommended, not prescribed; the 'Do NOT symlink' ban (Bekim 2026-08-12, 6f9ecc2, never tested) is removed.

~~~~
                                     symlinking — a real, live inconsistency with the no-symlink rule

~~~~

- Reason: Enver's 2026-10-31 ruling (Round D, A.5): the four entries above (lines 11, 197-203, 354, 392 of where-things-live.md) quoted or leaned on the removed INSTALL.md symlink ban; reworded to the allowed-not-prescribed note.
