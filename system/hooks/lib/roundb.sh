# Round B switch reader. Source it, then: roundb_on back_door && ...
# Env ROUNDB_<NAME> (upper case) overrides roundB.conf; anything but "on" is off.
roundb_on() {
  local name="$1" var val conf
  var="ROUNDB_$(printf '%s' "$name" | tr '[:lower:]' '[:upper:]')"
  val="${!var:-}"
  if [ -z "$val" ]; then
    conf="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/roundB.conf"
    val="$(sed -n "s/^${name}=//p" "$conf" 2>/dev/null | tail -1 | tr -d '[:space:]')"
  fi
  [ "$val" = "on" ]
}
