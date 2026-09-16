#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible. Same posture as guard_gh_pr_merge.sh, whose shape this
#  hook copies: first attempt denies and TEACHES, a second attempt passes once.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Enver's stated failure mode (design brief, 2026-09-02): "by push time I just
#      approve, because I can't tell what's in it." A `git push` is the moment work
#      leaves the private working tree — for the Lifehack repo it SHIPS to every
#      student the instant it lands on main — and nothing paused to show what is
#      actually going out before that moment.
# GUARDS: DENIES a real `git push` subcommand (never a mere MENTION — tokenized, see
#      MATCHING) on the first attempt of a given push command in a session, printing which repo (private/
#      public) and, for EACH ref the command's own argv actually names — never the
#      checkout's current branch — its remote target and the commit/file manifest
#      that would leave the machine. ALLOWS every other git verb untouched: status,
#      diff, log, fetch, pull, add, commit, branch, checkout, stash, show, blame.
# REFSPEC: FIXED 2026-09-15 — the summary used to be computed from the checkout's
#      current branch (`git rev-parse --abbrev-ref HEAD`) regardless of what the push
#      command named, so `git push origin some-other-branch` while checked out on
#      `main` signposted main's commits/files, not the named branch's. Fixed by
#      parsing the push command's own argv (never a keyword grep) into remote +
#      refspec(s) — `<src>`, `<src>:<dst>`, multiple refspecs, `HEAD`, `--all`,
#      `--tags`, `--mirror`, `-u`, `--force`/`--force-with-lease`, and no refspec at
#      all — and summarising each NAMED ref against its OWN remote-tracking
#      counterpart, or the remote default branch when it is a brand-new ref. A
#      refspec this cannot resolve prints UNRESOLVED rather than guessing.
# REDIRECT: read the printed manifest, confirm it is what you meant to ship, and if
#      genuinely unsure which repo this belongs in — STOP and ask; never guess harness
#      vs personal. Then re-run the exact same push.
# SIGNPOST: system/sops/github-sop.md §0c — the branch/push decision. To change what
#      is gated here, edit that SOP + get sign-off, then update this guard.
# MATCHING: argv STRUCTURE via shlex, never a keyword grep on the command string — a
#      literal "git push" inside a quoted commit message must not trip it. Segments
#      split on ; && || |; only a token that IS literally `git` (or ends in /git),
#      followed by the literal subcommand `push`, counts. On a shlex failure (heredoc,
#      unbalanced quote) we fall back to a raw-text adjacency scan for `git push` as a
#      shape, same fallback guard_gh_pr_merge.sh uses, and deny only if that shape is
#      present.
# IDENTITY: resolved from the COMMAND, never bare `$PWD` — fixed 2026-09-08 after a
#      real incident: a push from a ClaudeOps cwd targeting `git -C
#      ~/lifehack-brain push origin main` was signposted as "ClaudeOps
#      PRIVATE" — the wrong repo, confidently. This hook is a PreToolUse hook, so it
#      runs BEFORE the command — it can never observe a `cd` that hasn't happened
#      yet, so it tracks one explicitly instead: an explicit `-C <path>` on the
#      matched git invocation, or a `cd <path>` earlier in the same chain. A `cd`
#      ITSELF preceded by `|` (pipeline subshell, never affects the parent shell) or
#      `||` (only ran if the left side failed) is not trusted enough to ADOPT as the
#      new cwd — but a cwd already established by an earlier, trusted `cd` is left
#      untouched by what precedes a LATER segment (FIXED 2026-09-16, A1.3: `cd X ||
#      exit 1 ; git push` is the standard cd-or-bail idiom — the `cd` IS the left
#      side of the `||`, so once it is reached it ran and succeeded; the old code
#      instead reset cwd to "" on ANY segment merely preceded by `|`/`||`, discarding
#      a cwd that a genuinely-run `cd` had already set — see the 2026-09-08 INCIDENT
#      this exact idiom caused). An explicit `-C` on the push's own invocation wins
#      over an inherited `cd` — confirmed against real git behaviour (`git -C B`, run
#      from a cwd `cd`'d to A, resolves to B), not assumed. Falls back to `$PWD` only
#      when NEITHER is present (no regression on a plain `git push`). If a `-C`/`cd`
#      path WAS given but does not resolve to a real directory, this hook REFUSES
#      rather than silently falling back to `$PWD` — printing a guess is worse than
#      admitting it cannot tell.
# FAIL_POSTURE: closed — an unreadable hook payload denies. A command shlex cannot
#      tokenize falls back to the raw-text adjacency scan above and denies only if
#      that still reads as `git push`. SILENT (exit 0) when there is no command to
#      judge, or the command is a genuinely different git verb.
# UPDATED: 2026-09-15
# RULE: system/sops/github-sop.md §0c — system/hook-contract.md (mechanics)
# ─────────────────────────────────────────────────────────────────────────────
# guard_git_push_signpost.sh — PreToolUse hook (matcher: Bash)

INPUT=$(cat 2>/dev/null)

VERDICT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, shlex, os, base64

try:
    d = json.load(sys.stdin)
except Exception:
    print("PARSE_ERROR"); raise SystemExit

cmd = ((d.get("tool_input") or {}).get("command") or "")
if not cmd.strip():
    print("NOT_OURS"); raise SystemExit

# Normalized (whitespace-collapsed) command, base64-carried so a stray tab
# or newline inside the real command text can never collide with the
# tab-delimited VERDICT protocol below. Bash folds this into the signpost
# hash so it identifies THIS push, not merely this session.
cmd_key = base64.b64encode(" ".join(cmd.split()).encode("utf-8", "surrogateescape")).decode("ascii")

try:
    toks = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    import re as _re
    _shape = _re.compile(r"(^|[;&|(\s])git\s+(-{1,2}\S+\s+)*push\b")
    if _shape.search(cmd):
        print("DENY\t\t" + cmd_key); raise SystemExit
    print("NOT_OURS"); raise SystemExit

# (segment, operator-that-PRECEDES-it) pairs. A cd before an AND/semicolon
# reliably takes effect on what follows. A cd itself preceded by a PIPE runs
# in a pipeline subshell and never touches the parent shell, and a cd itself
# preceded by OR only ran if the left side failed -- neither is trustworthy
# enough to ADOPT as the new cwd (see the loop below), but a cwd already
# established by an earlier, trusted cd is NOT discarded just because a
# later segment happens to be preceded by `|`/`||` (A1.3, 2026-09-16).
segments, buf, op = [], [], None
for t in toks:
    if t in ("&&", "||", ";", "|"):
        if buf: segments.append((buf, op))
        buf = []
        op = t
    else:
        buf.append(t)
if buf: segments.append((buf, op))

def is_git(tok):
    return os.path.basename(tok) == "git"

cwd = ""
for seg, preceding_op in segments:
    if seg and seg[0] == "cd":
        # A cd reached via `|` runs in a pipeline subshell and never affects the
        # parent shell; a cd reached via `||` only runs if the PRECEDING segment
        # FAILED, so its target is not trustworthy enough to adopt. Neither case
        # invalidates a cwd already established by an EARLIER, trusted segment --
        # fixed 2026-09-16 (A1.3) after the 2026-09-08 incident: the old code reset
        # cwd to "" on ANY segment merely preceded by `|`/`||`, which forgot a cwd
        # that a genuinely-ran `cd` had already set. `cd X || exit 1 ; git push`
        # is the standard cd-or-bail idiom -- the `cd` IS the left side of the
        # `||`; it ran and succeeded. The `exit 1` segment that follows is what is
        # preceded by `||`, not the `cd` -- discarding cwd there was inverted.
        if preceding_op not in ("|", "||"):
            target = ""
            for tok in seg[1:]:
                if not tok.startswith("-"):
                    target = tok
                    break
            if target:
                cwd = target
        continue

    i = 0
    while i < len(seg) and "=" in seg[i] and not seg[i].startswith("-"):
        i += 1
    if i >= len(seg) or not is_git(seg[i]):
        continue
    j = i + 1
    cdir = ""
    while j < len(seg) and seg[j].startswith("-"):
        if seg[j] in ("-C", "-c"):
            if seg[j] == "-C" and j + 1 < len(seg):
                cdir = seg[j + 1]
            j += 2
        else:
            j += 1
    if j < len(seg) and seg[j] == "push":
        # explicit -C wins over an inherited cd — confirmed against real git behaviour
        resolved = cdir if cdir else cwd
        # carry the push subcommand argv (everything after "push" in THIS segment) so
        # the bash side can resolve the NAMED refspec(s), never the currently checked
        # out branch — see the REFSPEC note in the LLM CONTEXT block above.
        push_argv = seg[j + 1:]
        argv_b64 = base64.b64encode(json.dumps(push_argv).encode("utf-8", "surrogateescape")).decode("ascii")
        print("DENY\t" + resolved + "\t" + cmd_key + "\t" + argv_b64); raise SystemExit

print("OK")
' 2>/dev/null)

case "$VERDICT" in
  PARSE_ERROR)
    printf '%s\n' "BLOCKED (push signpost): the hook payload itself was not readable JSON. WHY: failing OPEN would let an unreadable push slip past unseen. REDIRECT: retry the command. RULE: system/sops/github-sop.md section 0c -- FAIL_POSTURE: closed." >&2
    exit 2
    ;;
  "")
    printf '%s\n' "BLOCKED (push signpost): the hook payload itself was not readable JSON. WHY: failing OPEN would let an unreadable push slip past unseen. REDIRECT: retry the command. RULE: system/sops/github-sop.md section 0c -- FAIL_POSTURE: closed." >&2
    exit 2
    ;;
esac

_RAW_VERDICT="$VERDICT"
VERDICT="${_RAW_VERDICT%%$'\t'*}"
_REST1="${_RAW_VERDICT#*$'\t'}"
[ "$_REST1" = "$_RAW_VERDICT" ] && _REST1=""
REQUESTED_DIR="${_REST1%%$'\t'*}"
_REST2="${_REST1#*$'\t'}"
[ "$_REST2" = "$_REST1" ] && _REST2=""
CMD_B64="${_REST2%%$'\t'*}"
_REST3="${_REST2#*$'\t'}"
[ "$_REST3" = "$_REST2" ] && _REST3=""
PUSH_ARGV_B64="$_REST3"

case "$VERDICT" in
  OK|NOT_OURS)
    exit 0
    ;;
  DENY)
    # a -C/cd target was named but does not resolve — refuse rather than guess
    if [ -n "$REQUESTED_DIR" ] && [ ! -d "$REQUESTED_DIR" ]; then
      printf '📍 PUSH · cannot determine the target repo\n' >&2
      printf '   The command names a path (%s) that does not exist here.\n' "$REQUESTED_DIR" >&2
      printf '   WHY: printing a guess about which repo this pushes to is worse than admitting the guard cannot tell.\n' >&2
      printf '   REDIRECT: verify the path, then re-run.\n' >&2
      printf '   -> system/sops/github-sop.md section 0c\n' >&2
      exit 2
    fi

    REPO_DIR="$PWD"
    if [ -n "$REQUESTED_DIR" ] && [ -d "$REQUESTED_DIR" ]; then REPO_DIR="$REQUESTED_DIR"; fi

    # FIXED 2026-09-15 (double-registration race): this hook is registered
    # TWICE for the same PreToolUse Bash event -- hooks/hooks.json loads it via
    # ${CLAUDE_PLUGIN_ROOT} AND .claude/settings.json loads the identical
    # script via ${CLAUDE_PROJECT_DIR} -- so both copies run in PARALLEL on
    # every single push attempt. The marker used to be keyed on session id
    # ALONE and DELETED itself on the allow branch: one copy created it and
    # denied, the other found it, deleted it, and allowed -- so the marker was
    # gone before either copy (or the next real attempt) could see it, and
    # every attempt denied, forever.
    #
    # Fix: key the marker on session id + WHICH push this is (the normalized
    # command + the resolved target dir), and NEVER delete it. A genuine
    # repeat of the exact same push is then recognized as "already
    # signposted" by both racing copies alike; a different push command still
    # gets its own first-sight deny. Creation uses mkdir, which is atomic on
    # POSIX filesystems, so at most one of the two parallel copies can ever
    # win the create -- the loser sees the directory already there and
    # allows, instead of racing on a plain `[ -f ] && rm` check.
    _key="${CLAUDE_CODE_SESSION_ID:-$PWD}|${CMD_B64}|${REPO_DIR}"
    _hash=$(printf '%s' "$_key" | shasum 2>/dev/null | cut -c1-16)
    [ -n "$_hash" ] || _hash="default"
    _bump="$HOME/.claude/.push-signpost.$_hash"
    if mkdir "$_bump" 2>/dev/null; then
      : # first sighting of this exact push in this session -- fall through and signpost
    elif [ -d "$_bump" ]; then
      exit 0   # already signposted (this copy or a racing sibling copy) -- allow
    fi
    # else: mkdir failed for some other reason (e.g. $HOME/.claude unwritable)
    # -- fail closed like the rest of this hook: fall through and signpost
    # rather than silently allow an un-recorded push.

    _branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)
    [ -n "$_branch" ] || _branch="UNKNOWN"
    _repo_name=$(basename "$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
    [ -n "$_repo_name" ] || _repo_name="UNKNOWN"

    # last-resort default remote guess -- used only when the push command names no
    # remote at all AND the current branch has no configured remote either.
    _remote_guess="origin"
    if ! git -C "$REPO_DIR" remote get-url --push origin >/dev/null 2>&1; then
      _first_remote=$(git -C "$REPO_DIR" remote 2>/dev/null | head -1)
      [ -n "$_first_remote" ] && _remote_guess="$_first_remote"
    fi

    # ── manifest: what would actually leave the machine ──────────────────────
    # See the REFSPEC note in the LLM CONTEXT block above: this resolves the push
    # command's OWN argv (PUSH_ARGV_B64, captured by the VERDICT python) into
    # remote + refspec(s) and summarises each NAMED ref against its OWN
    # remote-tracking counterpart -- never the checkout's current branch.
    _py_out=$(python3 -c '
import sys, json, base64, subprocess

repo_dir = sys.argv[1]
current_branch = sys.argv[2]
default_remote_guess = sys.argv[3]
argv_b64 = sys.argv[4] if len(sys.argv) > 4 else ""

def run(args):
    try:
        r = subprocess.run(["git", "-C", repo_dir] + args, capture_output=True, text=True, timeout=10)
        return r.returncode, (r.stdout or "").strip("\n")
    except Exception:
        return 1, ""

def resolves(rev):
    rc, out = run(["rev-parse", "--verify", "--quiet", rev])
    return rc == 0

argv_ok = True
push_argv = []
if argv_b64:
    try:
        push_argv = json.loads(base64.b64decode(argv_b64).decode("utf-8", "surrogateescape"))
        if not isinstance(push_argv, list):
            argv_ok = False
            push_argv = []
    except Exception:
        argv_ok = False
else:
    argv_ok = False

VALUE_FLAGS = ("-o", "--push-option", "--repo", "--receive-pack", "--exec", "--recurse-submodules")

positional = []
do_all = False
do_tags = False
do_mirror = False
force_all = False
set_upstream = False
i = 0
n = len(push_argv)
saw_dashdash = False
while i < n:
    t = push_argv[i]
    if not isinstance(t, str):
        i += 1
        continue
    if not saw_dashdash and t == "--":
        saw_dashdash = True
        i += 1
        continue
    if not saw_dashdash and len(t) > 1 and t[0] == "-":
        base = t.split("=", 1)[0]
        if base in VALUE_FLAGS and "=" not in t:
            i += 2
            continue
        if base == "--all":
            do_all = True
        elif base == "--tags":
            do_tags = True
        elif base == "--mirror":
            do_mirror = True
        elif base in ("--force", "-f", "--force-with-lease", "--force-if-includes"):
            force_all = True
        elif base in ("--set-upstream", "-u"):
            set_upstream = True
        i += 1
        continue
    positional.append(t)
    i += 1

explicit_remote = positional[0] if positional else ""
refspec_tokens = positional[1:] if positional else []
bare_push = (len(positional) == 0) and (not do_all) and (not do_tags) and (not do_mirror)

remote = ""
if explicit_remote:
    remote = explicit_remote
elif bare_push and current_branch not in ("", "UNKNOWN", "HEAD"):
    rc, out = run(["config", "--get", "branch." + current_branch + ".remote"])
    if rc == 0 and out.strip():
        remote = out.strip()
if not remote:
    remote = default_remote_guess if default_remote_guess else "origin"

print(remote)

rows = []
notes = []

def commit_file_summary(range_expr):
    rc1, out1 = run(["rev-list", "--count", range_expr])
    commit_count = out1.strip() if rc1 == 0 and out1.strip().isdigit() else "UNRESOLVED"
    rc2, out2 = run(["diff", "--name-only", range_expr])
    if rc2 == 0:
        files = [f for f in out2.split("\n") if f]
        shown = files[:10]
        extra = len(files) - len(shown)
        file_count = str(len(files))
    else:
        file_count, shown, extra = "UNRESOLVED", [], 0
    return commit_count, file_count, shown, extra

def find_remote_default(rname):
    rc, out = run(["symbolic-ref", "--short", "-q", "refs/remotes/" + rname + "/HEAD"])
    if rc == 0 and out.strip():
        return out.strip()
    for cand in ("main", "master"):
        if resolves("refs/remotes/" + rname + "/" + cand):
            return rname + "/" + cand
    return ""

def render_ref(label, src_token, dst_name, force_marked, delete_only):
    if delete_only:
        rows.append("   [DELETE] " + dst_name + " on " + remote + " (no local ref pushed)")
        return
    if not resolves(src_token + "^{commit}"):
        rows.append("   UNRESOLVED  " + label + " -> " + remote + "/" + dst_name + "  (does not resolve to a known local commit -- verify by hand)")
        return
    remote_ref = remote + "/" + dst_name
    force_flag = " [FORCE]" if force_marked else ""
    if resolves(remote_ref):
        commit_count, file_count, shown, extra = commit_file_summary(remote_ref + ".." + src_token)
        rows.append("   " + label + " -> " + remote_ref + force_flag)
        rows.append("      " + commit_count + " commit(s), " + file_count + " file(s):")
        for f in shown:
            rows.append("        " + f)
        if extra > 0:
            rows.append("        +" + str(extra) + " more")
    else:
        default_ref = find_remote_default(remote)
        if default_ref:
            commit_count, file_count, shown, extra = commit_file_summary(default_ref + ".." + src_token)
            rows.append("   " + label + " -> " + remote_ref + force_flag + "  [NEW BRANCH vs " + default_ref + "]")
            rows.append("      " + commit_count + " commit(s), " + file_count + " file(s):")
            for f in shown:
                rows.append("        " + f)
            if extra > 0:
                rows.append("        +" + str(extra) + " more")
        else:
            rc, out = run(["rev-list", "--count", src_token])
            total = out.strip() if rc == 0 and out.strip().isdigit() else "UNRESOLVED"
            rows.append("   " + label + " -> " + remote_ref + force_flag + "  [NEW BRANCH -- no local " + remote + "/HEAD or main/master remote-tracking ref to diff against]")
            rows.append("      " + total + " commit(s) total (verify manually -- cannot compute the delta this push would add)")

if not argv_ok:
    rows.append("   UNRESOLVED  -- the push command argument structure could not be recovered (heredoc/unbalanced-quote fallback); verify manually with git log/diff before pushing.")
else:
    if do_mirror:
        notes.append("--mirror also deletes any remote ref absent locally -- that cannot be enumerated without contacting the remote.")
        do_all = True
        do_tags = True
    if do_all or do_tags:
        if do_all:
            rc, out = run(["for-each-ref", "--format=%(refname:short)", "refs/heads/"])
            branches = [b for b in out.split("\n") if b]
            if not branches:
                rows.append("   (--all: no local branches found)")
            for b in branches:
                render_ref(b, b, b, force_all, False)
        if do_tags:
            rc, out = run(["for-each-ref", "--format=%(refname:short)", "refs/tags/"])
            tags = [t for t in out.split("\n") if t]
            if not tags:
                rows.append("   (--tags: no local tags to push)")
            else:
                notes.append("--tags requests ALL local tags; git silently skips any already up to date on the remote -- these are the local candidates, not confirmed-new.")
                for t in tags:
                    render_ref(t, t, t, force_all, False)
    elif refspec_tokens:
        for raw in refspec_tokens:
            s = raw
            force_this = force_all
            if s.startswith("+"):
                force_this = True
                s = s[1:]
            if ":" in s:
                src, dst = s.split(":", 1)
            else:
                src, dst = s, s
            if src == "":
                render_ref(raw, "", dst, force_this, True)
                continue
            if src == "HEAD":
                if current_branch in ("", "UNKNOWN", "HEAD"):
                    rows.append("   UNRESOLVED  " + raw + " -> " + remote + "/" + dst + "  (HEAD is detached or unknown -- verify manually)")
                    continue
                if dst == src:
                    dst = current_branch
                render_ref("HEAD (" + current_branch + ")", "HEAD", dst, force_this, False)
                continue
            render_ref(src, src, dst, force_this, False)
    else:
        if current_branch in ("", "UNKNOWN", "HEAD"):
            rows.append("   UNRESOLVED  no refspec given and HEAD is detached or unknown -- git would refuse this push (not on a branch); verify manually.")
        else:
            rc, up_out = run(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
            up_out = up_out.strip()
            if rc == 0 and up_out and "/" in up_out:
                prefix = remote + "/"
                if up_out.startswith(prefix):
                    up_branch = up_out[len(prefix):]
                else:
                    up_branch = up_out.split("/", 1)[1]
                render_ref(current_branch + " (current branch, no refspec)", current_branch, up_branch, force_all, False)
                notes.append("no refspec was given; resolved via the current branch configured upstream (" + remote + "/" + up_branch + ").")
            else:
                render_ref(current_branch + " (current branch, no refspec)", current_branch, current_branch, force_all, False)
                notes.append("no refspec and no upstream configured; assumed push.default of simple/current (same-name branch) -- verify this matches your push.default.")

if set_upstream:
    notes.append("-u/--set-upstream: this push also sets the pushed branch upstream tracking.")

if not rows:
    rows.append("   UNRESOLVED  -- could not determine what this push would send; verify manually with git log/diff before pushing.")

for nline in notes:
    rows.append("   NOTE: " + nline)

for r in rows:
    print(r)
' "$REPO_DIR" "$_branch" "$_remote_guess" "$PUSH_ARGV_B64" 2>/dev/null)

    _remote_name=$(printf '%s\n' "$_py_out" | head -1)
    [ -n "$_remote_name" ] || _remote_name="$_remote_guess"
    _manifest=$(printf '%s\n' "$_py_out" | tail -n +2)
    [ -n "$_manifest" ] || _manifest="   UNRESOLVED  -- the refspec parser produced no output; verify manually with git log/diff before pushing."

    _push_url=$(git -C "$REPO_DIR" remote get-url --push "$_remote_name" 2>/dev/null)
    case "$_push_url" in
      *LifehackMethod/lifehack-brain*) _kind="⚠⚠ PUBLIC -- SHIPS TO STUDENTS ⚠⚠" ;;
      *egjokaj/ClaudeOps*)             _kind="PRIVATE — students never see this" ;;
      "")                              _kind="UNKNOWN — no push remote resolved; STOP and verify by hand" ;;
      *)                               _kind="UNKNOWN — unrecognized remote ($_push_url); STOP and verify by hand" ;;
    esac

    {
      printf '📍 PUSH · %s (%s)\n' "$_repo_name" "$_kind"
      printf '%s\n' "$_manifest"
      printf '   Not sure which repo this belongs in? STOP and ask. Never guess harness vs personal.\n'
      printf '   WHY: "by push time I just approve, because I cant tell whats in it" -- this is the fix. Identity above was read from the real git remote, not guessed.\n'
      printf '   -> system/sops/github-sop.md section 0c\n'
      printf '   (run the same push again to proceed -- this fires once per distinct push in a session)\n'
    } >&2
    exit 2
    ;;
  *)
    printf '%s\n' "BLOCKED (push signpost): the hook payload itself was not readable JSON. WHY: failing OPEN would let an unreadable push slip past unseen. REDIRECT: retry the command. RULE: system/sops/github-sop.md section 0c -- FAIL_POSTURE: closed." >&2
    exit 2
    ;;
esac
