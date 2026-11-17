#!/usr/bin/env bash
# origin: 92a9739:mover/push.sh
# This script must stay beside the mover code it pushes. The scriptId (.clasp.json) is YOURS and comes from your setup, never from the plugin.
# push.sh: the ONLY way the mover gets created/pushed. Never a bare `clasp push` / `clasp create`.
# Refuses unless the manifest scopes are EXACTLY gmail.modify + drive.file + script.scriptapp, with no webapp and no
# executionApi; runs the static test; pushes; pulls back and re-checks what Google holds. It never runs or authorizes anything:
# the owner runs setup() once in the browser.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
CLASP_USER="${CLASP_USER:-default}"; TITLE="GC-mover"
check() { python3 -I - "$1" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
want = {"https://www.googleapis.com/auth/gmail.modify","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/script.scriptapp"}
got = m.get("oauthScopes")
if not isinstance(got, list) or set(got) != want or len(got) != 3: sys.exit(f"REFUSED: scopes {got!r}")
if "webapp" in m or "executionApi" in m: sys.exit("REFUSED: webapp/executionApi present")
print("manifest OK:", sys.argv[1])
PY
}
cp appsscript.json .manifest.ours.json
check appsscript.json
python3 -m unittest tests.test_static >/dev/null 2>&1 || { echo "REFUSED: static test failed" >&2; exit 2; }
# .clasp.json (your scriptId): $CLASP_JSON, else <personal code folder>/tools/grand-central/mover/.clasp.json (via the one settings loader).
# It is gitignored here; the owner's copy lives in the owner's own setup.
if [ ! -f .clasp.json ]; then
  SRCJ="${CLASP_JSON:-$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import gc_settings, os; r = gc_settings.personal_code_root(); print(os.path.join(r, "tools", "grand-central", "mover", ".clasp.json") if r else "")' "$HERE/..")}"
  if [ -n "$SRCJ" ] && [ -f "$SRCJ" ]; then cp "$SRCJ" .clasp.json; fi
fi
if [ ! -f .clasp.json ]; then
  clasp -u "$CLASP_USER" create --type standalone --title "$TITLE" --rootDir .
  cp .manifest.ours.json appsscript.json   # clasp create overwrites the manifest
  echo "NOTE: a new scriptId was made in .clasp.json (gitignored): keep a copy in your own setup, not in the plugin." >&2
fi
cmp -s .manifest.ours.json appsscript.json || { echo "REFUSED: manifest changed" >&2; exit 2; }
clasp -u "$CLASP_USER" push --force
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cp .clasp.json "$TMP/"; ( cd "$TMP" && clasp -u "$CLASP_USER" pull >/dev/null; for f in *.js; do [ -e "$f" ] && mv "$f" "${f%.js}.gs"; done )
check "$TMP/appsscript.json"
diff <(sed 's/[[:space:]]*$//' Code.gs) <(sed 's/[[:space:]]*$//' "$TMP/Code.gs") >/dev/null && echo "deployed Code.gs identical" || { echo "DEPLOYED CODE DIFFERS — do not run" >&2; exit 3; }
SID="$(python3 -c 'import json;print(json.load(open(".clasp.json"))["scriptId"])')"
echo "Editor link: https://script.google.com/d/$SID/edit"
