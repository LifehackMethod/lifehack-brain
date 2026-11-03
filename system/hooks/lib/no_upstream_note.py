#!/usr/bin/env python3
"""Worker for guard_no_upstream_commit_signpost.sh when switch no_upstream_note is ON. The payload is on stdin.

It never stops anything: it always exits 0. It prints the PreToolUse additionalContext JSON (the note Claude sees) or nothing.

Silent when: the command has no real commit; the branch has a live upstream; the repo has no remote (nothing to mirror);
the same command, after the commit, pushes that branch. Otherwise one note per session/repo/branch.

The push test only ever decides note-or-silence, so anything unclear counts as NOT pushed: the cost is one extra line.
"""
import hashlib, json, os, shlex, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import git_target_resolver as gtr  # the shared tokenizer: quotes, heredoc bodies, unquoted newlines

KEYWORDS = {"if", "then", "elif", "else", "fi", "do", "done", "while", "until", "{", "}", "!"}
SEP_CHARS = set("();|&")
REDIRECT_CHARS = set("<>&")
PUSH_VALUE_OPTS = {"--repo", "--receive-pack", "--exec", "-o", "--push-option"}
PUSH_NOT_REAL = {"-n", "--dry-run", "-d", "--delete", "--prune", "--tags"}
PUSH_ALL = {"--all", "--branches", "--mirror"}

NOTE = ("The commit is going through. Branch `%s` has %s on `%s`, so its commits stay on this machine until it is pushed. "
        "If it is still unpushed when you finish, say so in one line of your final message, so the person can choose. "
        "Do not push it because of this note.")


def segments(cmd):
    """[(tokens, joiner before them)], with ( ) ; & |, a shell keyword and any redirection taken out of the command words."""
    out, buf, op = [], [], ";"
    toks = gtr._tokenize(cmd)
    i = 0
    while i < len(toks):
        t = toks[i]
        if t and set(t) <= SEP_CHARS:
            if buf:
                out.append((buf, op))
                buf = []
            op = "||" if "||" in t else ("&&" if "&&" in t else ("|" if t in ("|", "|&") else ";"))
            i += 1
        elif t and set(t) <= REDIRECT_CHARS:
            if buf and buf[-1].isdigit():
                buf.pop()  # the 2 of 2>&1
            i += 2
        else:
            buf.append(t)
            i += 1
    if buf:
        out.append((buf, op))
    return out


def strip_keywords(seg):
    """-> (the command words, True when this command sits in an else/elif arm)."""
    other_arm, i = False, 0
    while i < len(seg) and seg[i] in KEYWORDS:
        other_arm = other_arm or seg[i] in ("else", "elif")
        i += 1
    return seg[i:], other_arm


def pushed_sources(seg, j):
    """Branches a `git push` at seg[j] really sends: names, "HEAD" for the current branch, "*" for all; [] for none."""
    k, end_opts, positional, all_refs = j + 1, False, [], False
    while k < len(seg):
        t = seg[k]
        k += 1
        if end_opts or not t.startswith("-"):
            positional.append(t)
        elif t == "--":
            end_opts = True
        elif t in PUSH_NOT_REAL:
            return []
        elif t in PUSH_ALL:
            all_refs = True
        elif t in PUSH_VALUE_OPTS:
            k += 1
    if all_refs:
        return ["*"]
    out = []
    for ref in positional[1:]:
        src = ref.lstrip("+").split(":", 1)[0]
        if src.startswith("refs/heads/"):
            src = src[len("refs/heads/"):]
        out.append("HEAD" if src == "@" else src)
    return [s for s in out if s]


def read_command(cmd):
    """-> (commit dir, branch a chained checkout -b/switch -c created, [branches pushed after the commit]) or None."""
    cwd, chained, chained_dir, found = "", None, "", None
    pushed = []
    for seg, op in segments(cmd):
        if op in ("|", "||"):
            cwd = ""
            if found is None:
                chained = None
            elif op == "||":
                break  # runs only when the commit failed, or cannot be told apart from that
        seg, other_arm = strip_keywords(seg)
        if found is not None and other_arm:
            break
        if not seg:
            continue
        if seg[0] == "cd":
            cwd = gtr._cd_target(seg) or cwd
            continue
        i = gtr.skip_prefix(seg)
        if i >= len(seg) or not gtr._is_git(seg[i]):
            continue
        j, cdir, _ov = gtr._git_sub(seg, i)
        if j >= len(seg):
            continue
        sub, where = seg[j], cdir or cwd
        if sub in ("checkout", "switch"):
            if found is not None:
                break  # HEAD is no longer the committed branch
            flags = ("-b", "-B") if sub == "checkout" else ("-c", "-C")
            for k in range(j + 1, len(seg) - 1):
                if seg[k] in flags:
                    chained, chained_dir = seg[k + 1], where
                    break
        elif sub == "commit" and found is None:
            found = (where, chained if chained is not None and chained_dir == where else None)
        elif sub == "push" and found is not None and where == found[0]:
            pushed.extend(pushed_sources(seg, j))
    return None if found is None else (found[0], found[1], pushed)


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, timeout=10)
    return p.stdout.strip() if p.returncode == 0 else ""


def main():
    d = json.load(sys.stdin)
    cmd = (d.get("tool_input") or {}).get("command") or ""
    if not cmd.strip():
        return
    read = read_command(cmd)
    if read is None:
        return
    where, chained, pushed = read
    repo = where if where and os.path.isdir(where) else os.getcwd()
    top = git(repo, "rev-parse", "--show-toplevel")
    if not top:
        return
    remotes = git(repo, "remote").split()
    if not remotes:
        return
    state = "no upstream"
    branch = chained
    if branch is None:
        branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        line = git(repo, "for-each-ref", "--format=%(upstream:short)|%(upstream:track)", "refs/heads/" + branch) if branch else ""
        if not line:
            return
        up, _, track = line.partition("|")
        if up and "gone" not in track:
            return
        if up:
            state = "lost its upstream"
    if "*" in pushed or "HEAD" in pushed or branch in pushed:
        return
    remote = "origin" if "origin" in remotes else remotes[0]
    key = "%s|%s|%s" % (os.environ.get("CLAUDE_CODE_SESSION_ID") or "nosession", top, branch)
    marker = os.path.join(os.path.expanduser("~"), ".claude", ".no-upstream-commit-signpost." + hashlib.sha1(key.encode()).hexdigest()[:12])
    if os.path.exists(marker):
        return
    try:
        open(marker, "a", encoding="utf-8").close()
    except OSError:
        pass
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": NOTE % (branch, state, remote)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # FAIL_POSTURE: degrade-safe (hook-sop 3.2): exit 0 and say so on stderr
        print("no_upstream_note: skipped, nothing was stopped (%s)" % e, file=sys.stderr)
    sys.exit(0)
