# Where this system is allowed to reach on the network

This is the list of hostnames a raw network call from a session may go to. It is short on purpose.

**Why a list at all.** Everything else in the security wall is about what comes IN. This one is
about what goes OUT — because the failure that actually costs you something is not a session
reading a poisoned page, it is a session that read one and then sent something of yours somewhere.
An instruction buried in a web page cannot do much on its own; an instruction buried in a web page
plus an unrestricted `curl` can do quite a lot. This closes the second half.

**What it governs, and what it does not.** It applies to RAW outbound calls — `curl`, `wget`, `nc`,
and inline Python HTTP. It does NOT apply to `safe_fetch.py`, which is how ordinary web reading
happens and which has an allowlist of its own — a separate list, and one that ships OFF until you
arm it (`system/safe-fetch-allowlist.md`). So researching a topic does not touch this list; only a
hand-rolled network call does. Package managers, `git` and `gws` do not match the
pattern either, so normal work is untouched.

**Name-based, not IP-based** — cloud addresses rotate, names do not.

**The match rule:** a host is allowed if it EQUALS a listed domain or is a subdomain of it
(`host == d or host.endswith("." + d)`). So list **base domains only** — `googleapis.com`, not
`www.googleapis.com`.

**To allow something new:** add its base domain inside the markers below. Keep it tight. Every entry
widens the wall, and the wall is only worth having while it is narrow.

## Approved base domains

<!-- ALLOWLIST-START -->
# Anthropic — the model API itself
anthropic.com
# GitHub — cloning this repository and pulling updates
github.com
githubusercontent.com
# Google Workspace — the gws CLI, if you have wired your own account (see INSTALL.md)
googleapis.com
google.com
gstatic.com
googleusercontent.com
# Serper — the search API behind safe_search_api.sh
serper.dev
# ntfy — push notifications, if you turn them on
ntfy.sh
# YouTube — transcript fetch for the lecture-builder skill (MZ approved 2026-08-30);
# watch pages + the timedtext caption endpoint both live under youtube.com
youtube.com
<!-- ALLOWLIST-END -->

## Two things worth knowing

- **This fails OPEN when it cannot do its job.** If no hostname can be extracted from the command,
  or this file cannot be read, the call is allowed and the reason is printed. That is deliberate:
  the tool layer is a speed bump, and a speed bump that bricks your shell on a parsing edge case
  gets removed. **The fail-closed layer is your operating system's own firewall** — Little Snitch,
  LuLu, `ufw`, whatever you use. If you want a hard outbound wall, point one of those at this same
  list. Nothing here can substitute for that, and nothing here pretends to.
- **It is blind to a compiled program opening its own connection.** It reads the text of a shell
  command. A binary you installed that phones home is invisible to it, by construction. Again: that
  is what the OS-layer firewall is for.
