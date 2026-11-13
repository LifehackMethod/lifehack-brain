#!/bin/bash
# hook_alert_ack.sh -- acknowledge the hook alert (hooks-alert.json) so hook_health_check.sh stops printing it.
# The alert is MOVED to hooks-alert.acked.<UTC time> (history kept), never deleted. Exit 0 always.
# Usage: bash system/tools/hook_alert_ack.sh
st="${LIFEHACK_STATE_DIR:-$HOME/.local/state/lifehack}"
if [ -s "$st/hooks-alert.json" ]; then
  mv -f "$st/hooks-alert.json" "$st/hooks-alert.acked.$(date -u +%Y%m%dT%H%M%SZ)" && echo "hook_alert_ack: acknowledged" || echo "hook_alert_ack: could not move $st/hooks-alert.json" >&2
else
  echo "hook_alert_ack: no unacknowledged hook alert"
fi
exit 0
