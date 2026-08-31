# Security Policy

## Reporting a vulnerability

If you find a security issue in this repo — especially anything that could let client or
personal data leak through the publish pipeline — please report it privately, not in a
public issue or PR.

**How:** Use GitHub's private vulnerability reporting for this repo — go to the **Security**
tab → **Report a vulnerability**. This opens a private advisory only the maintainers can see.

If that option isn't available yet, email the maintainer directly (see the repo owner's
GitHub profile for contact info) instead of opening a public issue.

## What's in scope

Anything that could cause private material to be published or exposed, including:

- The shipping/publish lane (`/ship`, `system/tools/` scrub and gate scripts)
- The publish gate that scrubs client names, paths, and other personal data before
  anything goes public
- Guards and hooks that are supposed to block risky actions (deletion, force-push,
  secret leaks, egress)
- Anything that lets a crafted input (a file, an email, a web page) make the harness do
  something it shouldn't

## What to expect

We'll acknowledge your report within a few days and let you know if it's confirmed, along
with a rough plan and timeline for a fix. You don't need to have a patch ready — a clear
description of the issue and how to reproduce it is enough.

## Please don't

- Don't open a public GitHub issue with a working exploit or proof-of-concept — that
  publishes the hole before it's fixed.
- Don't test the vulnerability against anyone else's real data or account.
- Don't publish or share the issue publicly until a fix has shipped and we've confirmed
  it's safe to disclose.

Thanks for helping keep this safe for everyone running it.
