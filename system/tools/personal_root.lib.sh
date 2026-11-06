#!/usr/bin/env bash
# personal_root.lib.sh -- the shell copy of shared/personal_code_root.py's lookup, sourced by job-run.sh (a python start per job run
# measurably slows the job-sim rig). Parity with the python is held by system/tools/tests/test_personal_root_parity.sh: change a rule in
# one place and that test fails until the other agrees.
# Sets _PCR (no subshell): the personal code folder, or "" when there is none. Rules, as in the python:
#   pointer file ~/.config/lifehack/personal-code present and non-blank on line 1 -> that folder if it is a directory, else "" (a pointer to a
#   missing folder never falls back to the default); no pointer, or a blank/unreadable one -> ~/lifehack-personal-code if it is a directory; else "".
personal_root_lookup() {
  local _pp="$HOME/.config/lifehack/personal-code" _v=""
  _PCR=""
  if [ -f "$_pp" ]; then
    _v="$(head -n 1 "$_pp" 2>/dev/null | tr -d '\r')"
    _v="${_v#"${_v%%[![:space:]]*}"}"; _v="${_v%"${_v##*[![:space:]]}"}"
    case "$_v" in "~") _v="$HOME" ;; "~/"*) _v="$HOME/${_v#\~/}" ;; esac
    if [ -n "$_v" ]; then [ -d "$_v" ] && _PCR="$_v"; return 0; fi
  fi
  [ -d "$HOME/lifehack-personal-code" ] && _PCR="$HOME/lifehack-personal-code"
  return 0
}
