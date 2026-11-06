#!/usr/bin/env bash
# test_personal_root_parity.sh -- the shell lookup job-run.sh uses (system/tools/personal_root.lib.sh) and shared/personal_code_root.py
# must give the same answer. Throwaway HOMEs under mktemp in $TMPDIR; HOME is the one env seam both honour.
# Same answer = the same folder when one is found, and "none" from both when not (python: exit 1, no output with --quiet).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/personal-root-parity.XXXXXX")" || exit 1
trap 'rm -rf "$T"' EXIT
. "$ROOT/system/tools/personal_root.lib.sh"
fails=0
both() {  # both <name> <expected>: compare shell and python under the current $HOME
  local sh_ans py_ans
  personal_root_lookup; sh_ans="$_PCR"
  py_ans="$(python3 "$ROOT/shared/personal_code_root.py" --quiet 2>/dev/null)"
  if [ "$sh_ans" = "$py_ans" ] && [ "$sh_ans" = "$2" ]; then echo "ok   $1 (${sh_ans:-none})"
  else echo "FAIL $1: shell='$sh_ans' python='$py_ans' wanted='$2'"; fails=$((fails+1)); fi
}
newhome() { H="$T/$1"; mkdir -p "$H/.config/lifehack"; export HOME="$H"; }

newhome pointer;          mkdir "$H/elsewhere"; printf '%s\n' "$H/elsewhere" > "$H/.config/lifehack/personal-code"; both "pointer present" "$H/elsewhere"
newhome pointer-default;  mkdir "$H/elsewhere" "$H/lifehack-personal-code"; printf '%s\n' "$H/elsewhere" > "$H/.config/lifehack/personal-code"; both "pointer wins over default" "$H/elsewhere"
newhome pointer-missing;  mkdir "$H/lifehack-personal-code"; printf '%s\n' "$H/gone" > "$H/.config/lifehack/personal-code"; both "pointer to a missing folder (never the default)" ""
newhome default-only;     mkdir "$H/lifehack-personal-code"; both "no pointer, default present" "$H/lifehack-personal-code"
newhome neither;          both "no pointer, no default" ""
newhome tilde;            mkdir "$H/mine"; printf '~/mine\n' > "$H/.config/lifehack/personal-code"; both "pointer written with ~/" "$H/mine"
newhome spaces;           mkdir "$H/mine"; printf '  %s  \r\n' "$H/mine" > "$H/.config/lifehack/personal-code"; both "pointer with spaces and CRLF" "$H/mine"
newhome blank;            mkdir "$H/lifehack-personal-code"; printf '\n' > "$H/.config/lifehack/personal-code"; both "blank pointer falls to the default" "$H/lifehack-personal-code"
newhome blank-none;       printf '   \n' > "$H/.config/lifehack/personal-code"; both "blank pointer, no default" ""
newhome empty-file;       mkdir "$H/lifehack-personal-code"; : > "$H/.config/lifehack/personal-code"; both "empty pointer file falls to the default" "$H/lifehack-personal-code"
newhome pointer-is-file;  : > "$H/afile"; printf '%s\n' "$H/afile" > "$H/.config/lifehack/personal-code"; both "pointer to a file, not a folder" ""

[ "$fails" -eq 0 ] && echo "PASS: shell and python agree in every case" || { echo "FAIL: $fails case(s) differ"; exit 1; }
