# Source me from a hook test: pins every Round B switch to OFF (the pre-go-live default these tests were written against)
# and pins mode to enforce-semantics (LIFEHACK_WATCH=0) so neither the live roundB.conf values nor watch mode leak in.
# A test case that needs a switch ON sets ROUNDB_<NAME>=on itself; env always wins over the conf (lib/roundb.sh, lib/roundb.py).
_PIN_CONF="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/roundB.conf"
for _pin_n in $(sed -nE 's/^([a-z][a-z0-9_]*)=(on|off)[[:space:]]*$/\1/p' "$_PIN_CONF"); do
  export "ROUNDB_$(printf '%s' "$_pin_n" | tr '[:lower:]' '[:upper:]')=off"
done
export LIFEHACK_WATCH=0
export ROUNDB_FC_PRIVATE_PUSH_MODE=block   # the valued line (2026-11-02): pinned to the old behaviour too; warn mode has its own test
unset _pin_n _PIN_CONF
