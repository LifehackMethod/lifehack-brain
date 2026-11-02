#!/bin/bash
# temporary: forwards for windows opened before 2026-11-01; remove once all pre-11-01 windows are restarted
# not-wired-yet: temporary: forwards for windows opened before 2026-11-01; remove once all pre-11-01 windows are restarted (old windows call it by path from their cached hook config, so it is deliberately absent from hooks/hooks.json)
exec "$(dirname "$0")/guard_no_repoint_into_personal_code.sh" "$@"
