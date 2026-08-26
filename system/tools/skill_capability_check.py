#!/usr/bin/env python3
"""skill_capability_check.py — surface skills that declare a capability this system forbids.

PLAN TASK T3.7(b)+(c). Read `T3.7` in the migration plan before changing this.

WHY THIS EXISTS
  A skill's frontmatter can declare `allowed-tools:` — the harness capabilities it needs. Nothing
  read those declarations, so a skill could announce a dependency the system DENIES and no one found
  out until the skill silently did nothing mid-run.
  MEASURED 2026-08-23: `.claude/skills/first-principles/SKILL.md` declares `AskUserQuestion`, which is
  in this system's `permissions.deny`. A skill announcing a forbidden dependency, and nothing caught it.

WHY IT IS SHAPED THIS WAY — read `build-rules-index.md`'s code-spiral rule before "improving" it.
  * ⛔ IT IS ONE PART WITH ONE CALL SITE. It is invoked from `system/hooks/session_context_loader.sh`,
    the SessionStart hook that already fires every session — i.e. the place the session ALREADY LOOKS.
    It is deliberately NOT a new detector that something else must remember to run, and there is
    deliberately NO third component watching this one. "If your fix has three parts and one of them
    checks the other two, delete that one."
  * ⛔ IT NEVER BLOCKS. Always exits 0. This is a FACT the session should see, not a gate. A session
    that cannot start because a skill's metadata is wrong is a worse failure than the one being fixed.

⭐ THE PRECISION THAT MAKES IT WORTH HAVING — a bare deny and a scoped deny are NOT the same claim.
  `permissions.deny` holds two different shapes:
     "AskUserQuestion"          -> BARE. The tool is unusable, full stop. A skill declaring it is broken.
     "Edit(~/.ssh/**)"          -> SCOPED. The tool is fine; one path is off-limits. A skill declaring
                                   `Edit` is perfectly healthy.
  Treating those the same is not a small inaccuracy — MEASURED on this machine, the naive version
  flagged 7 skills when only 1 was real. A check that cries wolf 6 times out of 7 gets ignored, and an
  ignored check is worse than no check because the map still reports it green.

THE NEGATIVE CONTROL IS PART OF THE DESIGN, not an afterthought: when every declared capability is
available, this prints NOTHING. A check never seen to stay quiet is noise. `--self-test` proves both
directions — that it fires on a real violation AND stays silent on a scoped one.
"""
import glob
import json
import os
import re
import sys

# THREE levels up: .../<repo>/system/tools/this_file.py -> <repo>. Two was wrong and cost a live
# green illusion during this tool's own build: it globbed <repo>/system/.claude/skills/*, matched
# ZERO skills, and printed nothing -- which in this tool's design MEANS HEALTHY. The checker failed
# exactly the way it exists to catch. Hence the resolve-time assertion below: a scan that finds no
# skills at all is a BROKEN LOCATOR, never a clean result.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETTINGS = os.path.expanduser("~/.claude/settings.json")


def load_denies(settings_path):
    """Return (bare_denied, scoped_denied) from a settings file.

    Absent or unreadable settings is NOT 'nothing is denied' — the caller must be able to tell
    'I checked and it is clean' from 'I could not check'. Returns None on failure.
    """
    try:
        with open(settings_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    deny = data.get("permissions", {}).get("deny", [])
    bare, scoped = set(), {}
    for entry in deny:
        entry = str(entry).strip()
        if "(" in entry:
            scoped.setdefault(entry.split("(", 1)[0].strip(), []).append(entry)
        elif entry:
            bare.add(entry)
    return bare, scoped


def declared_tools(skill_md):
    """Extract `allowed-tools:` from a SKILL.md's YAML frontmatter. Handles list and inline forms."""
    try:
        with open(skill_md, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return []
    fm = m.group(1)
    block = re.search(r"^allowed-tools:\s*\n((?:[ \t]*-[ \t]*\S+[ \t]*\n?)+)", fm, re.M)
    if block:
        return [ln.strip().lstrip("-").strip() for ln in block.group(1).splitlines() if ln.strip()]
    inline = re.search(r"^allowed-tools:[ \t]*(.+)$", fm, re.M)
    if inline:
        raw = inline.group(1).strip().strip("[]")
        return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]
    return []


def scan(skills_glob, settings_path):
    """Return (violations, checked_count, error). violations = [(skill_name, tool)]."""
    denies = load_denies(settings_path)
    if denies is None:
        return [], 0, f"could not read {settings_path}"
    bare, _scoped = denies

    violations = []
    checked = 0
    for path in sorted(glob.glob(skills_glob)):
        tools = declared_tools(path)
        if not tools:
            continue
        checked += 1
        name = os.path.basename(os.path.dirname(path))
        for tool in tools:
            if tool in bare:
                violations.append((name, tool))
    return violations, checked, None


def main():
    if "--self-test" in sys.argv:
        return self_test()

    skills_glob = os.path.join(REPO, ".claude", "skills", "*", "SKILL.md")

    # ⛔ BROKEN LOCATOR IS NOT A CLEAN RESULT (ABSENT-SUBJECT-RULE-v1). If the glob matches no
    # SKILL.md at all, this tool has been pointed somewhere wrong -- it has NOT proven the skills are
    # healthy. Measured during this tool's own build: a two-level REPO resolve globbed a directory
    # that does not exist, matched zero skills, and printed nothing, which this design reads as
    # "all clear." Say so out loud instead.
    if not glob.glob(skills_glob):
        print(f"⚠ skill-capability check found NO skills at {skills_glob} — "
              f"this is a broken locator, not a clean result (T3.7)")
        return 0

    violations, checked, error = scan(skills_glob, SETTINGS)

    if error:
        # ABSENT-SUBJECT-RULE-v1: could-not-check must never be spelled the way clean is spelled.
        print(f"⚠ skill-capability check could not run — {error}")
        return 0

    # THE NEGATIVE CONTROL. Silence here is the healthy state and is deliberate.
    if not violations:
        return 0

    for name, tool in violations:
        print(f"⚠ skill `{name}` declares `{tool}`, which this system DENIES outright — "
              f"it will not work as written (T3.7)")
    return 0


def self_test():
    """Prove BOTH directions: it fires on a bare deny and stays silent on a scoped one."""
    import tempfile
    failures = []

    with tempfile.TemporaryDirectory() as tmp:
        sk = os.path.join(tmp, "skills")
        os.makedirs(os.path.join(sk, "fires"))
        os.makedirs(os.path.join(sk, "quiet"))
        with open(os.path.join(sk, "fires", "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nskill: fires\nallowed-tools:\n  - AskUserQuestion\n---\nbody\n")
        with open(os.path.join(sk, "quiet", "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nskill: quiet\nallowed-tools:\n  - Edit\n  - Bash\n---\nbody\n")

        settings = os.path.join(tmp, "settings.json")
        with open(settings, "w", encoding="utf-8") as fh:
            json.dump({"permissions": {"deny": [
                "AskUserQuestion",            # bare  -> must fire
                "Edit(~/.ssh/**)",            # scoped -> must stay quiet
                "Bash(gws auth logout:*)",    # scoped -> must stay quiet
            ]}}, fh)

        v, checked, err = scan(os.path.join(sk, "*", "SKILL.md"), settings)
        names = {n for n, _ in v}
        if err:
            failures.append(f"unexpected error: {err}")
        if checked != 2:
            failures.append(f"expected to check 2 skills, checked {checked}")
        if "fires" not in names:
            failures.append("POSITIVE CONTROL FAILED: a bare-denied tool did not fire")
        if "quiet" in names:
            failures.append("NEGATIVE CONTROL FAILED: a scope-restricted tool fired — this is the "
                            "cry-wolf bug the docstring warns about")

        # could-not-check must not be spelled like clean
        _v, _c, err2 = scan(os.path.join(sk, "*", "SKILL.md"), os.path.join(tmp, "nope.json"))
        if not err2:
            failures.append("ABSENT-SUBJECT FAILED: a missing settings file returned clean")

    if failures:
        for f in failures:
            print(f"  [FAIL] {f}")
        print("\nFAIL — self-test did not pass.")
        return 1
    print("  [PASS] fires on a bare-denied tool")
    print("  [PASS] stays SILENT on a scope-restricted tool (the negative control)")
    print("  [PASS] a missing settings file reports could-not-check, not clean")
    print("\nPASS — both directions proven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
