#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: its sibling `enforce_egress_allowlist.sh` asks WHERE a call is going. This one asks WHAT is
#      in it. They catch different mistakes: the allowlist would happily pass an API key posted to
#      github.com, and this one would happily pass an empty request to a stranger. Together they are
#      "not to a stranger, and not with a secret in it."
#      The realistic shape this stops is not espionage — it is a session pasting a key straight into
#      a command line to make something work, where it then lives in shell history, in a log, and in
#      whatever the far end records.
# GUARDS: a Bash command containing BOTH something that looks like a credential AND an outbound
#      mechanism (curl · wget · nc · ncat · netcat · telnet, or inline Python HTTP). Either one on
#      its own is fine — printing a key is not blocked, and fetching a page is not blocked. It is
#      the pair.
# REDIRECT: never inline a raw secret. Reference it from a file or a keychain the far end already
#      trusts, or use the sanctioned fetch path. If this is a false positive, run the two halves as
#      separate commands — which is also just better practice.
# SIGNPOST: the outbound story as a whole is in system/egress-allowlist.md.
# FAIL_POSTURE: open — unreadable input allows, mirroring its sibling. Neither of these may brick a
#      shell; the operating system's firewall is the layer that fails closed.
# UPDATED: 2026-08-11 (ported unchanged in substance; wording generalised)
# ─────────────────────────────────────────────────────────────────────────────
# guard_egress.sh — PreToolUse hook (matcher: Bash). Blocks a secret and a network call in one breath.

INPUT=$(cat 2>/dev/null)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception:
    print('')
" 2>/dev/null)

[ -z "$COMMAND" ] && exit 0

# Condition 1 — is anything going out? Shell tools OR inline Python HTTP. The Python patterns match
# actual CALL sites (requests.get, urllib.request), never the bare word "python" and never
# urllib.parse, so a legitimate fetcher invoked as a script does not trip this.
printf '%s' "$COMMAND" | grep -qE '(^|[^[:alnum:]_/])(curl|wget|nc|ncat|netcat|telnet)([^[:alnum:]_]|$)|urllib\.request|urllib\.urlopen|\brequests\.(get|post|put|patch|delete|request)|\bhttpx\.|http\.client|socket\.(socket|create_connection)' 2>/dev/null || exit 0

# Condition 2 — is a credential in the same breath? Only then does it block.
if printf '%s' "$COMMAND" | grep -qE 'sk-ant-|sk_live_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|xox[bporsa]-|ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN|OPENAI_API_KEY|SERPER_API_KEY|AWS_SECRET_ACCESS_KEY|GOOGLE_APPLICATION_CREDENTIALS' 2>/dev/null; then
  echo "BLOCKED: this command puts a credential and a network call in the same breath. WHY: an inlined key does not stay in the command — it lands in shell history, in any log of this session, and in whatever the far end writes down. REDIRECT: do not inline the secret. Reference it from a file or a keychain the far end already trusts, or use the sanctioned fetch path (python3 <repo>/system/tools/safe_fetch.py). If this is a false positive, run the two halves as separate commands." >&2
  exit 2
fi

exit 0
