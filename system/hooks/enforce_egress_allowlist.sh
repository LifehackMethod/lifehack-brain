#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: everything else in this wall is about what comes IN. This is the only piece about what goes
#      OUT — and that is the half that actually costs something. An instruction hidden in a web page
#      cannot do much on its own. The same instruction plus an unrestricted `curl` can send your
#      material anywhere. The reader-actor split stops a hijacked READER from acting; this stops a
#      fooled ACTOR from reaching a stranger's server.
# GUARDS: a Bash command that BOTH uses a raw outbound mechanism (curl · wget · nc · ncat · netcat ·
#      telnet, or inline Python urllib/requests/httpx/http.client/socket) AND names a host that is
#      not in system/egress-allowlist.md. Package managers, git, gws and safe_fetch.py do not match
#      the mechanism pattern, so ordinary work never touches this.
# REDIRECT: to read a web page use `python3 <repo>/system/tools/safe_fetch.py '<url>'` — it sanitizes
#      on the way in and allowlists per run. If a host genuinely belongs, add its base domain to
#      system/egress-allowlist.md between the ALLOWLIST markers.
# SIGNPOST: the list, the match rule and the honest limits are all in system/egress-allowlist.md.
# FAIL_POSTURE: OPEN, deliberately, and it says so out loud when it happens. No readable host, or an
#      unreadable list, means the call goes through with a printed reason. The tool layer is a speed
#      bump; a speed bump that bricks a shell on a parsing edge case is one people remove. The
#      fail-CLOSED layer is your operating system's own firewall, pointed at the same list.
# UPDATED: 2026-08-11 (ported; the allowlist and the logic both resolved from this script's repo)
# ─────────────────────────────────────────────────────────────────────────────
# enforce_egress_allowlist.sh — PreToolUse hook (matcher: Bash). Hands off to its .py sibling; the
# PreToolUse JSON flows straight through on stdin via exec.

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
exec python3 "$_HOOKDIR/enforce_egress_allowlist.py"
