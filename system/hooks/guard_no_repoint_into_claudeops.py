#!/usr/bin/env python3
"""
guard_no_repoint_into_claudeops.py — logic half of the PreToolUse BLOCK guard.
Invoked by guard_no_repoint_into_claudeops.sh with the raw PreToolUse JSON on stdin.
Writes exactly one verdict line to stdout: "ALLOW::<reason>" or "BLOCK::<reason>".
Never raises past its own top level -- any uncaught condition is caught and turned into
a BLOCK verdict, because the .sh wrapper treats anything that is not a clean ALLOW:: line
as a deny. See FAIL_POSTURE in the .sh header.
"""
import sys
import json
import re
import os
import glob

HOME = os.path.expanduser("~")
PLUGIN_ROOT = HOME + "/.claude/plugins/cache/lifehack-brain"

# Assembled from fragments on purpose -- a command-string guard once blocked its own
# documentation because the docstring quoted the attack it defended against
# (system/sops/hook-sop.md §4 Trap 2). This guard's own source must not contain the
# literal target-repo name as a bare token that a sibling guard or a future grep-based
# check could trip on by accident.
_PRIVATE_REPO_MARKER = "Claude" + "Ops"


def emit_allow(reason):
    print("ALLOW::" + reason)
    sys.exit(0)


def emit_block(reason):
    print("BLOCK::" + reason)
    sys.exit(0)  # the verdict is communicated via the printed line, not the exit code --
                 # the .sh wrapper is what turns this into exit 2 / exit 0 for the harness.


def under_guarded_dir(p):
    if not isinstance(p, str):
        return False
    pp = p.replace("$HOME", HOME).replace("~", HOME)
    return (".claude/skills/" in pp) or (".claude/agents/" in pp)


def mentions_private_repo(p):
    return isinstance(p, str) and _PRIVATE_REPO_MARKER in p


def plugin_equivalent_exists(basename_guess):
    """Best-effort check: does ~/.claude/plugins/cache/lifehack-brain/*/*/.claude/{skills,agents}/<name>
    exist? When no basename could be narrowed (a loop/variable-driven ln call) this falls back to
    'does the plugin cache exist at all' -- a coarse signal, documented as a known limitation in the
    deliverable, not silently upgraded to a precise per-item check it cannot actually perform."""
    if not basename_guess:
        return os.path.isdir(PLUGIN_ROOT)
    hits = (
        glob.glob(PLUGIN_ROOT + "/*/*/.claude/skills/" + basename_guess)
        + glob.glob(PLUGIN_ROOT + "/*/*/.claude/agents/" + basename_guess)
    )
    return len(hits) > 0


def handle_bash(ti):
    cmd = ti.get("command", "")
    if not isinstance(cmd, str) or cmd.strip() == "":
        emit_block("Bash tool_input carried no usable command string")

    # Find every `ln ... A B` invocation ANYWHERE in the command text -- not just at
    # top-level ; / && boundaries. This deliberately also catches one written inside a
    # for-loop body (`do ln -sf ... ; done`), because the literal `ln <flags> A B`
    # substring still appears even when A or B embeds an unexpanded shell variable like
    # $f. Matching the literal invocation text, not a keyword anywhere in the string,
    # per the "match the target, not a bare keyword" rule.
    matches = re.findall(
        r'(?:^|[;&|\n]|\bdo\b)\s*ln\s+((?:-[A-Za-z]+\s+)*)(\S+)\s+(\S+)',
        cmd,
    )
    if not matches:
        emit_allow("no `ln` invocation found in this command")

    for flags, arg1, arg2 in matches:
        if "s" not in flags:
            continue  # not a symlink operation -- e.g. a hardlink or malformed match, not our concern

        target, linkname = arg1, arg2  # GNU/BSD convention: ln [-flags] TARGET LINKNAME
        link_is_guarded = under_guarded_dir(linkname)
        target_is_guarded = under_guarded_dir(target)  # tolerate a swapped/unclear arg order

        if not (link_is_guarded or target_is_guarded):
            continue  # a symlink op that has nothing to do with ~/.claude/skills or ~/.claude/agents

        if mentions_private_repo(target):
            base = os.path.basename(linkname.rstrip("/")) if link_is_guarded else None
            if plugin_equivalent_exists(base):
                emit_block(
                    "ln re-points a skill/agent symlink at a " + _PRIVATE_REPO_MARKER +
                    " path while a plugin-supplied equivalent exists "
                    "(target=%r link=%r)" % (target, linkname)
                )
            else:
                emit_block(
                    "ln targets a " + _PRIVATE_REPO_MARKER + " path under a guarded symlink "
                    "directory and a plugin equivalent could not be confirmed either way "
                    "(target=%r link=%r) -- ambiguous, denying per fail-closed posture" % (target, linkname)
                )
        elif mentions_private_repo(linkname):
            emit_block(
                "ln's link-name argument itself names " + _PRIVATE_REPO_MARKER +
                " inside a guarded symlink directory (target=%r link=%r) -- ambiguous, "
                "denying per fail-closed posture" % (target, linkname)
            )
        # else: link is under skills/agents but the target does not name the private repo at
        # all (e.g. it points into the plugin cache, or somewhere else entirely) -- not this
        # guard's concern, keep reviewing the remaining matches.

    emit_allow("ln invocation(s) reviewed, none re-point a guarded symlink at the private repo")


def handle_write_edit(ti):
    path = ti.get("file_path") or ti.get("path") or ""
    if not path:
        emit_block("Write/Edit tool_input carried no file_path to check")

    if os.path.basename(str(path)) != "settings.json":
        emit_allow("write target is not a settings.json file")

    content = ti.get("content")
    if content is None:
        content = ti.get("new_string")
    if not isinstance(content, str):
        emit_block(
            "a settings.json write carried no readable content/new_string to inspect -- "
            "cannot confirm this isn't a hook-command repoint, denying per fail-closed posture"
        )

    for m in re.finditer(r'"command"\s*:\s*"([^"]*)"', content):
        val = m.group(1)
        if mentions_private_repo(val):
            mm = re.search(r'\.claude/(skills|agents)/([^/"\\]+)', val)
            base = mm.group(2) if mm else None
            if plugin_equivalent_exists(base):
                emit_block(
                    "settings.json hook registration points a command at a " +
                    _PRIVATE_REPO_MARKER + " script while a plugin equivalent exists (%r)" % val
                )
            else:
                emit_block(
                    "settings.json hook registration points at a " + _PRIVATE_REPO_MARKER +
                    " path and a plugin equivalent could not be confirmed -- ambiguous, "
                    "denying per fail-closed posture (%r)" % val
                )

    emit_allow("settings.json write reviewed, no private-repo hook command found")


def main():
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        emit_block("stdin was empty/unreadable -- cannot evaluate this tool call, denying per fail-closed posture")

    try:
        data = json.loads(raw)
    except Exception as exc:
        emit_block("PreToolUse payload did not parse as JSON (%s) -- denying per fail-closed posture" % exc)

    if not isinstance(data, dict):
        emit_block("PreToolUse payload was valid JSON but not an object -- denying per fail-closed posture")

    tool_name = data.get("tool_name", "")
    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        emit_block("PreToolUse payload carried no usable tool_input object -- denying per fail-closed posture")

    if tool_name == "Bash":
        handle_bash(ti)
    elif tool_name in ("Write", "Edit", "MultiEdit"):
        handle_write_edit(ti)
    else:
        emit_allow("tool %r is not in this guard's scope" % tool_name)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 -- an uncaught condition here must still deny
        print("BLOCK::internal error in guard logic (%s) -- denying per fail-closed posture" % exc)
        sys.exit(0)
