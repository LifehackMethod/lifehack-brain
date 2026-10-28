#!/bin/bash
# deterministic stub builder. env: STUB_LOG, STUB_PLANT, STUB_PLANT_ON, STUB_SLEEP_ON, STUB_PIDFILE
[ "$1" = "-p" ] || exit 2
P="$2"
case "$P" in
  *"SCOPE=<card"*) echo "SCOPE=normal-skill REASON=toy"; exit 0 ;;
esac
id="$(printf '%s' "$P" | sed -nE 's/.*plan card ([A-Za-z0-9.]+):.*/\1/p')"
wh="$(printf '%s' "$P" | sed -nE 's/.* Where: ([^ ]+)\. Do:.*/\1/p')"
[ -n "$id" ] && [ -n "$wh" ] || { echo "stub: cannot parse" >&2; exit 3; }
echo "$id" >> "$STUB_LOG"
if [ "${STUB_SLEEP_ON:-}" = "$id" ]; then echo $$ > "${STUB_PIDFILE:-/dev/null}"; sleep 30; fi
mkdir -p "$(dirname "$wh")"
{
  echo '#!/bin/bash'
  if [ -n "${STUB_PLANT:-}" ] && [ "${STUB_PLANT_ON:-$id}" = "$id" ]; then
    # planted violation, assembled at run time so this file never contains the pattern
    printf '%s\n' "curl -s https://example.invalid ""|""| true"
  fi
  echo "echo hello-$id"
} > "$wh"
echo "Built it."
echo "BUILT $id"
