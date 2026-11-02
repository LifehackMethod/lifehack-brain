# person_roots.sh — source it, then call lh_person_roots once. It sets these shell variables:
#   LH_NOTES_ROOT     the notes root (shared/brain_root.py), real path, or empty
#   LH_PERSONAL_ROOT  the personal code folder (shared/personal_code_root.py), real path, or empty
#   LH_CODE_ZONES     array of extra code folders from <personal-code>/code-zones.txt (may be empty)
#   LH_NOTES_STATUS / LH_PERSONAL_STATUS   ok | unset | missing   (anything but ok = the zone is UNKNOWN)
#   LH_OWNER_GH_USER  the person's own GitHub account ($LIFEHACK_OWNER_GH_USER, else the deprecated fallback in person_roots.py)
#   LH_TEAM_ROOT      the team shared-skills folder (shared/team_skills_root.py), real path, or empty
#   LH_TEAM_STATUS    ok | unset | missing (anything but ok = the zone is UNKNOWN, never "absent")
#   LH_STRICT         1 when either status is not ok (or the resolver could not run): a guard then FAILS CLOSED
# One python call answers them all (shared/person_roots.py). Empty means "no such zone" — never a guess.
lh_person_roots() {
  LH_NOTES_ROOT=""; LH_PERSONAL_ROOT=""; LH_CODE_ZONES=(); LH_NOTES_STATUS="unknown"; LH_PERSONAL_STATUS="unknown"; LH_STRICT=1; LH_OWNER_GH_USER="${LIFEHACK_OWNER_GH_USER:-}"; LH_TEAM_ROOT=""; LH_TEAM_STATUS="unknown"
  local _lib_dir _shared _line
  _lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || return 0
  _shared="${_lib_dir%/system/hooks/lib}/shared"
  [ -f "$_shared/person_roots.py" ] || return 0   # resolver absent: statuses stay "unknown", LH_STRICT stays 1
  while IFS= read -r _line; do
    case "$_line" in
      NOTES=*)    LH_NOTES_ROOT="${_line#NOTES=}" ;;
      PERSONAL=*) LH_PERSONAL_ROOT="${_line#PERSONAL=}" ;;
      NOTES_STATUS=*)    LH_NOTES_STATUS="${_line#NOTES_STATUS=}" ;;
      PERSONAL_STATUS=*) LH_PERSONAL_STATUS="${_line#PERSONAL_STATUS=}" ;;
      ZONE=*)     LH_CODE_ZONES+=("${_line#ZONE=}") ;;
      OWNER_GH_USER=*) LH_OWNER_GH_USER="${_line#OWNER_GH_USER=}" ;;
      TEAM=*) LH_TEAM_ROOT="${_line#TEAM=}" ;;
      TEAM_STATUS=*) LH_TEAM_STATUS="${_line#TEAM_STATUS=}" ;;
    esac
  done < <(python3 "$_shared/person_roots.py" --shell 2>/dev/null)
  if [ "$LH_NOTES_STATUS" = ok ] && [ "$LH_PERSONAL_STATUS" = ok ]; then LH_STRICT=0; fi
  return 0
}
