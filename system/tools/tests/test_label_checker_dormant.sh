#!/bin/bash
# CR-9 step 6(a) — DORMANT in the label checker's vocabulary.
# Planted cases:
#   1. a manifest entry declaring a part deliberately not in use (`use: dormant`)
#      reads DORMANT — not TARGET, not PARTIAL, and not flagged as a downgrade
#      (failing first on the old code, which ignored `use:` and read PARTIAL);
#   2. an ordinary guard with no `use:` key still reads exactly as before
#      (inert script -> PARTIAL, flagged DOWNGRADE against a LIVE claim).
# Also exercises write-labels: an element backed only by a dormant guard reads
# DORMANT; one backed by an ordinary guard reads as before. DORMANT stands OUTSIDE
# the weakest-wins order (canon/status-health-proof-sop.md).
set -u
cd "$(dirname "$0")/../../.."   # repo root of the worktree
CHECKER="system/tools/organism/label_checker.py"
PY="${PYTHON:-/usr/bin/python3}"
TD="$(mktemp -d)"
trap 'rm -rf "$TD"' EXIT

# a real script on disk (a dormant part is BUILT, just not in use)
cat > "$TD/dormant_guard.sh" <<'G'
#!/bin/bash
exit 0
G
chmod +x "$TD/dormant_guard.sh"

cat > "$TD/manifest.yaml" <<'M'
guards:
  - id: planted-dormant
    label_claim: DORMANT
    use: dormant
    script: DORMANT_SCRIPT
  - id: planted-ordinary
    label_claim: LIVE
    script: DORMANT_SCRIPT
    violations:
      - desc: "inert guard blocks nothing"
        payload: {"tool_name": "WebFetch", "tool_input": {"url": "http://x"}}
M
sed -i '' "s|DORMANT_SCRIPT|$TD/dormant_guard.sh|" "$TD/manifest.yaml"

fail=0
echo "== check (planted manifest) =="
"$PY" "$CHECKER" check --manifest "$TD/manifest.yaml" | tee "$TD/check.out"
grep -q " DORMANT  planted-dormant" "$TD/check.out" || { echo "FAIL: dormant part did not read DORMANT"; fail=1; }
grep -q "PARTIAL  planted-ordinary" "$TD/check.out" || { echo "FAIL: ordinary guard no longer reads PARTIAL"; fail=1; }
grep -q "DOWNGRADE (claimed LIVE)" "$TD/check.out" || { echo "FAIL: ordinary guard lost its downgrade flag"; fail=1; }

echo "== write-labels (planted elements dir) =="
mkdir -p "$TD/elements"
printf -- '---\nelement: dormant-part\nmaturity_label: LIVE\n---\n' > "$TD/elements/dormant-part.md"
printf -- '---\nelement: ordinary-part\nmaturity_label: TARGET\n---\n' > "$TD/elements/ordinary-part.md"
cat > "$TD/manifest2.yaml" <<'M'
guards:
  - id: g-dormant
    label_claim: DORMANT
    use: dormant
    script: DORMANT_SCRIPT
    element: dormant-part
  - id: g-ordinary
    label_claim: LIVE
    script: DORMANT_SCRIPT
    element: ordinary-part
    violations:
      - desc: "inert"
        payload: {"tool_name": "WebFetch", "tool_input": {"url": "http://x"}}
M
sed -i '' "s|DORMANT_SCRIPT|$TD/dormant_guard.sh|" "$TD/manifest2.yaml"
"$PY" "$CHECKER" write-labels --manifest "$TD/manifest2.yaml" --elements "$TD/elements" | tee "$TD/wl.out"
grep -q "maturity_label: DORMANT" "$TD/elements/dormant-part.md" || { echo "FAIL: all-dormant element did not read DORMANT"; fail=1; }
grep -q "maturity_label: PARTIAL" "$TD/elements/ordinary-part.md" || { echo "FAIL: ordinary element no longer reads PARTIAL"; fail=1; }

if [ "$fail" -eq 0 ]; then echo "PASS — dormant part reads DORMANT outside the order; ordinary guards read as before"; exit 0
else echo "FAIL"; exit 1; fi
