# Level 2 — sealing ordinary web reads to a list of domains

This is the switch for the middle of the three outbound levels described in
`docs/OUTSIDE-SERVICES.md`. **It ships OFF in the package; THIS install has it ON** (armed 2026-10-27, see the list below). Turning it on is a decision
this package leaves to you, and nothing here turns it on by itself.

## What it does when it is on

Every ordinary web read goes through `system/tools/safe_fetch.py` — that is what `/websearch`,
`/research` and every content-reading skill actually use. When this switch is on, that tool refuses
any URL whose host is not one of the domains listed below, **before the socket opens**. Nothing is
fetched and nothing is sent.

**Its neighbours, so you know what this one is not.** Level 1 is `system/egress-allowlist.md` — a
different list, governing raw `curl`/`wget`/inline-Python calls, on by default, and it fails OPEN.
Level 3 is your operating system's own firewall, which is not part of this package and is the only
one of the three that is a hard wall. This file is the middle: narrower than Level 1 in what it
covers, stricter than it in what it does when unsure.

## The switch

One word between the markers. `on` or `off`, nothing else.

<!-- L2-MODE-START -->
on
<!-- L2-MODE-END -->

## The domains

Base domains only, one per line, between the markers. A host is allowed if it **equals** a listed
domain or is a **subdomain** of it — so `example.com`, never `www.example.com`. `#` starts a comment.

<!-- ALLOWLIST-START -->
# ARMED 2026-10-27 (self-monitoring 5.5, "safe stack sealed"). Exactly the hosts Marc's three feed fetchers
# (marc-data-fetch, flows_fetch, cftc_cot_fetch) read, listed as full hosts (tighter than a base domain).
# Anything else a safe_fetch.py read asks for is refused before the socket opens. To read another site, add its
# host here on purpose; a one-off research run can seal itself with SAFE_FETCH_ALLOWLIST=<hosts> instead.
query1.finance.yahoo.com
fred.stlouisfed.org
stooq.com
www.ici.org
ticdata.treasury.gov
publicreporting.cftc.gov
<!-- ALLOWLIST-END -->

## Three states, and no quiet fourth one

Check which one you are in at any time:

```
python3 system/tools/safe_fetch.py --l2-status
```

- **OFF** — the shipped state. Reads are allowed and **every run prints one line saying the seal is
  not in force.** You are told the level you are actually at rather than left to assume one.
- **ON** — the list above is enforced. An off-list host is refused by name.
- **AMBIGUOUS** — armed but unusable: the switch says `on` with nothing listed, or domains are listed
  with the switch still `off`, or the switch reads something that is neither word. **Every web read
  is refused until you fix it**, and the refusal names this file and the line.

That last state is the point of the design. Half-configured is the one condition that *looks* like
protection and is not, and a wall you wrongly believe in is worse than one you know you do not have.
So it stops rather than quietly waving reads through. The fix is always one line in this file.

⚠ **A per-run seal beats this file.** If the environment variable `SAFE_FETCH_ALLOWLIST` is set
(comma-separated base domains), it wins for that one run — that is the hook for a skill that wants to
seal a single research session to the domains it just searched. Unset, or empty, and this file
decides. Nothing in this package sets that variable today.

## Honest limits

- It governs `system/tools/safe_fetch.py` and nothing else. A raw `curl` is Level 1's business; a
  compiled program opening its own connection is invisible to both, which is what Level 3 is for.
- It reads a URL's host before connecting. It cannot see where a page redirects you afterwards, and
  it makes no judgement about what a listed domain then serves you.
