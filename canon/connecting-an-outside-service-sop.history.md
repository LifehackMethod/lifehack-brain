# History log for connecting-an-outside-service-sop.md

Text cut or moved out of the SOP, copied verbatim first. Append-only.

- 2026-11-16: landed in round four, canon-files checked, on Enver's 'land it'.

## 2026-11-16 - reason: landing-commit citation check; a per-person file named without its directory path, since it is never in the repo
Line 67 (before): "A key kept in `.claude/settings.local.json` (each person's own file, not shipped) is an exception to the line above: the file sits inside the repo folder, chosen deliberately for this release (`.gitignore:34-44`), and only `.gitignore` keeps it out of commits (passive conformance friction: no message, it simply is not staged)." ⛔ the path quoted here is each person's own file, not shipped.
Line 164 (before): "- `.gitignore` — keeps `.claude/settings.local.json` and `local.settings.json` (each person's own files, not shipped) out of commits (passive; no message)." ⛔ the paths quoted here are each person's own files, not shipped.

## 2026-11-16 - reason: step 4b (round five), OS2 (FIX: a stale citation or detail, no change of meaning), on Enver's 'land it' (old wording, word for word)

~~~~
2. **Do:** before turning on a connector that can send, write or delete (mail, calendar, tasks, sheets, files), the person decides whether to accept those actions, and mail is never sent without the person's approval of that send (drafts are fine).
~~~~

## 2026-11-16 - reason: step 4b (round five), CJ1 (UP-ruled: an appeal he already ruled), on Enver's 'land it' (old wording, word for word)

~~~~
1. **Do:** first check whether a raw call is needed — reading a web page goes through `system/tools/safe_fetch.py`, which does not use this list; reading mail goes through `shared/tools/email_fetch.py`, because Python that speaks a mail protocol (IMAP, POP, SMTP, the Gmail API client) is refused whatever the list says (`system/hooks/enforce_egress_allowlist.py:92-110`, switch `email_reader_block`, on in `system/hooks/roundB.conf`).
~~~~

~~~~
- `shared/tools/email_fetch.py` — the one shared mail reader; holds the Google mail credential.
~~~~

## 2026-11-16 - reason: step 4b (round five), OS1 (FIX: a stale citation or detail, no change of meaning), on Enver's 'land it' (old wording, word for word)

~~~~
- **not built yet:** guards on connectors' own send, write and delete actions, matching the shell-command write guards (`system/hooks/guard_gmail_send.sh` and its siblings). Serves: not yet in canon.
~~~~
