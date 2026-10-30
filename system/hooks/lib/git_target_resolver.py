"""
git_target_resolver.py — SHARED repo-target resolver for the git-command signpost
guards (commit, push) and any future outbound-act guard.

WHY THIS EXISTS: guard_git_push_signpost.sh (fixed 2026-09-08, commit 25a01e1) parses
-C and a leading `cd` out of the command text because these guards are PreToolUse —
they run BEFORE the command, so they can never observe a `cd` that hasn't happened
yet and must track one explicitly instead. guard_git_commit_signpost.sh never got
that fix and stayed $PWD-only for anything but an explicit `-C`, so on 2026-09-08 a
live `cd ~/lifehack-brain && git commit ...` was signposted "COMMIT · (PRIVATE)" — the wrong repo, confidently. This module is the ONE place that logic
now lives, so both guards (and anything built after them) share one proven resolver
instead of drifting apart again.

RESOLUTION PRIORITY (matches `git` itself): an explicit `-C <path>` on the matched
git invocation wins over any inherited `cd`; `cd`/`cd X && ...`/`cd X; ...` wins over
bare $PWD; a bare invocation with neither falls back to $PWD.

TOKENIZING: uses shlex.shlex(..., punctuation_chars=True) rather than plain
shlex.split(). Plain shlex.split only treats `;` `&&` `||` `|` as separators when
they are whitespace-padded — `cd X || exit; git commit` (note: `exit;` has NO space
before the `;`) tokenized as a single `exit;` blob under the old approach, so the
push guard's own `||`-handling silently never fired on exactly this shape. Verified
this session: `shlex.split('cd /tmp || exit; git push origin main')` still glues
`exit;` together; `shlex.shlex(cmd, punctuation_chars=True)` splits it correctly.
Quoted arguments (a commit message, say) are UNCHANGED by this — shlex still keeps
them as one token, which is why a merely-quoted mention of "git push" never matches
the positional `git ... <verb>` shape below; see NOT-A-FALSE-POSITIVE below.

THE `cd X || exit` IDIOM: a common defensive one-liner — "cd there or bail out".
Semantically, if the command AFTER the `cd X || <right-side>` construct ever runs at
all, cwd is GUARANTEED to be X: the only way execution reaches past it with cwd
NOT equal to X is if `cd X` failed AND the right side did not halt — but if the
right side is exit-shaped (`exit`, `exit <n>`, `return`, `return <n>`), it DOES halt,
so that branch never reaches anything after it. This resolver recognizes exactly
that shape and treats it as a confident cd. Any OTHER `cd X || <something>` (the
right side doesn't provably halt) is genuinely ambiguous and is NOT guessed — it is
reported back as REFUSE_AMBIGUOUS so the caller refuses rather than printing a
guess, per this project's standing rule (naming the wrong repo confidently is worse
than admitting the guard cannot tell).

NOT-A-FALSE-POSITIVE (quoted mentions): matching is POSITIONAL — a segment only
counts if its first non-assignment token IS LITERALLY `git` (or ends in `/git`),
found via shlex STRUCTURE, never a keyword scan over raw text. A commit message
like `git commit -m "reminder: git push later"` tokenizes to a single quoted
argument token for the whole message, so the second "git push" mentioned inside it
never appears as its own segment and never matches. Verified this session against
the real guard_git_push_signpost.sh. The ONLY place raw-text scanning happens is the
ValueError fallback below, used only when shlex itself cannot tokenize the command
at all (e.g. a genuinely unbalanced quote) — there, by design, this project's
standing rule is to keep firing rather than risk missing a real outbound act, since
a missed real one is worse than one spurious prompt.
"""

import os
import re
import shlex

_EXIT_SHAPES = {"exit", "return"}
_SEPARATORS = ("&&", "||", ";", "|")


_HEREDOC_OPEN = re.compile(r"<<-?[ \t]*(?:'([^'\n]+)'|\"([^\"\n]+)\"|\\?([A-Za-z_][A-Za-z0-9_]*))")
# A heredoc fed to one of these is EXECUTED, so its body holds real commands.
_EXEC_SINKS = {"bash", "sh", "zsh", "dash", "ksh", "eval", "source", ".", "ssh", "xargs"}


def _strip_heredoc_bodies(cmd):
    """Blank out heredoc BODIES (<<EOF, <<'EOF', <<-EOF) so prose inside a note
    (a stray apostrophe, the words "git push") is never read as a command.
    A heredoc whose line starts with a shell interpreter is left intact: that
    body runs. Local fix (fix-fa); the shared parser is proposed separately."""
    lines = cmd.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        m = _HEREDOC_OPEN.search(line)
        if not m:
            continue
        tag = m.group(1) or m.group(2) or m.group(3)
        first = line.strip().split(None, 1)
        sink = os.path.basename(first[0]) if first else ""
        # find the terminator; if none, leave the rest untouched (fail toward firing)
        k = i
        while k < len(lines) and lines[k].strip() != tag:
            k += 1
        if k >= len(lines) or sink in _EXEC_SINKS:
            continue
        i = k  # drop body lines; the terminator line is dropped too
        i += 1
    return "\n".join(out)


def _newlines_to_semicolons(cmd):
    """An UNQUOTED newline separates commands exactly like `;` (fix-signpost, mirrors
    guard_commit_identity 3b-fa a725747). shlex whitespace-splits it away, so
    `cd X\ngit push` used to read as one segment `cd X git push` and the push was
    labelled with the session cwd. Quoted/escaped newlines are left alone."""
    out, q, i, n = [], None, 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if q:
            if ch == "\\" and q == '"' and i + 1 < n:
                out.append(ch); i += 1; ch = cmd[i]
            elif ch == q:
                q = None
        elif ch == "\\" and i + 1 < n:
            out.append(ch); i += 1; ch = cmd[i]
            if ch == "\n":          # line continuation: drop both
                out.pop(); i += 1; continue
        elif ch in "'\"":
            q = ch
        elif ch == "\n":
            ch = " ; "
        out.append(ch); i += 1
    return "".join(out)


def _tokenize(cmd):
    """Tokenize with shell metacharacters as their own tokens even when not
    whitespace-padded (e.g. 'exit;'), while still honoring quotes."""
    cmd = _newlines_to_semicolons(_strip_heredoc_bodies(cmd))
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def _segment(toks):
    """[(seg_tokens, operator_immediately_before_this_seg_or_None), ...]"""
    segments, buf, op = [], [], None
    for t in toks:
        if t in _SEPARATORS:
            if buf:
                segments.append((buf, op))
            buf = []
            op = t
        else:
            buf.append(t)
    if buf:
        segments.append((buf, op))
    return segments


def _is_git(tok):
    return os.path.basename(tok) == "git"


def _cd_target(seg):
    for tok in seg[1:]:
        if not tok.startswith("-"):
            return tok
    return ""


def resolve(cmd, verb, see_through=False):
    """
    cmd: the raw command string from tool_input.
    verb: the git subcommand this guard cares about ("commit", "push", ...).
    see_through: Round C (fine china). False = exactly the behaviour above. True = also read through a
                 leading `env [opts]`, `command`, `exec`, `nohup`, `time`, a subshell paren or brace (see skip_prefix).

    Returns (status, target):
      NOT_OURS           -- no matching `git <verb>` found; nothing to judge.
      AMBIGUOUS          -- shlex could not tokenize the command at all, but a
                             raw-text scan still finds a `git ... <verb>` shape.
                             Fire (per standing rule: ambiguous means fire), but
                             there is no reliable target -- caller should refuse
                             to name a repo while still treating this as a real hit.
      DENY, target        -- a real `git <verb>` found. target is "" (meaning
                             $PWD applies) or an explicit -C/cd path.
      REFUSE_AMBIGUOUS    -- a real `git <verb>` found, but the only cd info
                             available came from a `cd X || <non-exit-shaped>`
                             construct that cannot be trusted. Refuse rather than
                             silently falling back to $PWD.
    """
    if not cmd.strip():
        return ("NOT_OURS", "")

    try:
        toks = _tokenize(cmd)
    except ValueError:
        shape = re.compile(r"(^|[;&|(\s])git\s+(-{1,2}\S+\s+)*" + re.escape(verb) + r"\b")
        if shape.search(_strip_heredoc_bodies(cmd)):
            return ("AMBIGUOUS", "")
        return ("NOT_OURS", "")

    segments = _segment(toks)
    n = len(segments)

    cwd = ""
    tainted = False
    i = 0
    while i < n:
        seg, preceding_op = segments[i]

        # FIXED 2026-10-30 (fix-signpost): a pipe NEVER resets the working directory
        # for what follows. `cd X && git log | head && git push` runs the push in X;
        # the old code dropped cwd at every `|` and the push was then labelled with the
        # SESSION cwd's repo (a PUBLIC push labelled PRIVATE). A pipeline element
        # inherits the parent cwd; only a `cd` that is itself a pipeline element
        # (left or right of `|`) is a subshell cd and must not be believed.
        next_op = segments[i + 1][1] if (i + 1) < n else None
        in_pipe = preceding_op == "|" or next_op == "|"

        if seg and seg[0] in ("pushd", "popd"):
            cwd, tainted = "", True      # directory changes we do not model
            i += 1
            continue
        if seg and seg[0] == "(" and any(t in ("cd", "pushd", "popd") for t in seg):
            cwd, tainted = "", True      # cd inside a subshell group: not modelled
            i += 1
            continue

        if seg and seg[0] == "cd":
            target = _cd_target(seg)
            if in_pipe:
                cwd, tainted = "", True  # subshell cd: cwd after it is unprovable
                i += 1
                continue
            if not target:
                cwd, tainted = "", True  # bare `cd` (home) / `cd -`: not modelled
                i += 1
                continue
            if target and (i + 1) < n and segments[i + 1][1] == "||":
                guard_seg = segments[i + 1][0]
                if guard_seg and guard_seg[0] in _EXIT_SHAPES:
                    # `cd X || exit` -- if we ever get past this, cwd IS X.
                    cwd = target
                    tainted = False
                else:
                    # `cd X || <something that might not halt>` -- can't prove it.
                    cwd = ""
                    tainted = True
                i += 2
                continue
            cwd = target
            tainted = False
            i += 1
            continue

        idx = 0
        if see_through:
            idx = skip_prefix(seg)
        while idx < len(seg) and "=" in seg[idx] and not seg[idx].startswith("-"):
            idx += 1
        if idx >= len(seg) or not _is_git(seg[idx]):
            i += 1
            continue

        j = idx + 1
        cdir = ""
        while j < len(seg) and seg[j].startswith("-"):
            if seg[j] in ("-C", "-c"):
                if seg[j] == "-C" and j + 1 < len(seg):
                    cdir = seg[j + 1]
                j += 2
            else:
                j += 1

        if j < len(seg) and seg[j] == verb:
            if cdir:
                return ("DENY", cdir)
            if tainted:
                return ("REFUSE_AMBIGUOUS", "")
            return ("DENY", cwd)

        i += 1

    return ("NOT_OURS", "")


# ───────────────────────── Round C (fine china): see through wrappers, aliases, config ─────────────────────────
# Everything below is OPT-IN: resolve() with see_through=False and no caller of these functions behaves exactly as
# before. The push signpost calls them only when fc_force_push or fc_private_push is on.
# Why a token reader and not the Drive guard's regex (lib/gws_guard.py _EXECWRAP): that regex is quote-blind, so a
# commit message that merely MENTIONS `bash -c 'git push -f'` would read as a command. Here a quoted mention is one
# token and never a command word.
_PREFIX_WORDS = {"command", "exec", "nohup", "time", "builtin", "nice"}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
_KNOWN_VERBS = frozenset("""add am annotate apply archive bisect blame branch bundle checkout cherry cherry-pick clean clone
commit config describe diff difftool fetch filter-branch format-patch fsck gc grep help init log maintenance merge
mergetool mv notes pull push range-diff rebase reflog remote repack replace request-pull reset restore revert rm
send-email shortlog show show-branch sparse-checkout stash status submodule subtree switch tag worktree rev-parse
rev-list ls-files ls-remote ls-tree cat-file update-ref update-index write-tree commit-tree read-tree symbolic-ref
for-each-ref name-rev merge-base merge-file diff-tree diff-index diff-files hash-object check-ignore check-attr
credential daemon gui gitk version count-objects pack-objects unpack-objects prune verify-commit verify-tag whatchanged""".split())
_RPUSH = re.compile(r"remote\..+\.push", re.I)


def skip_prefix(seg):
    """Index of the program word in a segment, after NAME=value, `env [opts]`, command/exec/nohup/time and leading
    ( { ! tokens (a subshell or brace group still runs the command)."""
    i, n = 0, len(seg)
    while i < n:
        t = seg[i]
        if t in ("(", "{", "!"):
            i += 1
            continue
        if "=" in t and not t.startswith("-"):
            i += 1
            continue
        b = os.path.basename(t)
        if b == "env":
            i += 1
            while i < n and seg[i].startswith("-") and seg[i] != "--":
                i += 2 if seg[i] in ("-u", "-C", "-S", "--unset", "--chdir", "--split-string") else 1
            continue
        if b in _PREFIX_WORDS:
            i += 1
            while i < n and seg[i].startswith("-"):
                i += 1
            continue
        break
    return i


def _git_sub(seg, i):
    """-> (index of the subcommand or len(seg), -C dir, [-c values]) for a git word at seg[i]."""
    j, cdir, ov = i + 1, "", []
    while j < len(seg) and seg[j].startswith("-"):
        if seg[j] in ("-C", "-c") and j + 1 < len(seg):
            if seg[j] == "-C":
                cdir = seg[j + 1]
            else:
                ov.append(seg[j + 1])
            j += 2
        else:
            j += 1
    return j, cdir, ov


def candidates(cmd, alias_lookup=None, depth=0):
    """Extra command strings the shell would actually run, for the caller to resolve in turn: the body of
    `bash|sh|zsh -c '...'` (also -lc, -ec), `eval ...` (also behind env/command/exec/VAR=x), and, when alias_lookup
    is given, `git <alias>` where the alias is not a built-in verb, expanded to what it stands for.
    alias_lookup(dir, name) -> the alias value or "" (the caller owns the git call; this module runs no process)."""
    if depth > 3:
        return []
    try:
        toks = _tokenize(cmd)
    except ValueError:
        return []
    out, cwd = [], ""
    for seg, _op in _segment(toks):
        if seg and seg[0] == "cd":
            cwd = _cd_target(seg) or cwd
            continue
        i = skip_prefix(seg)
        if i >= len(seg):
            continue
        prog = os.path.basename(seg[i])
        body = None
        if prog in _SHELLS:
            k = i + 1
            while k < len(seg) and seg[k].startswith("-"):
                if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", seg[k]) and k + 1 < len(seg):
                    body = seg[k + 1]
                    break
                k += 1
        elif prog == "eval":
            body = " ".join(seg[i + 1:])
        if body:
            out.append(body)
            out.extend(candidates(body, alias_lookup, depth + 1))
            continue
        if alias_lookup and _is_git(seg[i]):
            j, cdir, _ov = _git_sub(seg, i)
            if j < len(seg) and seg[j] not in _KNOWN_VERBS and re.fullmatch(r"[A-Za-z0-9_][\w.-]*", seg[j]):
                val = (alias_lookup(cdir or cwd, seg[j]) or "").strip()
                if not val:
                    continue
                if val.startswith("!"):
                    exp = val[1:].strip()
                else:
                    try:
                        exp = " ".join(shlex.quote(t) for t in seg[:j] + shlex.split(val) + seg[j + 1:])
                    except ValueError:
                        continue
                    if cwd and not cdir:
                        exp = "cd %s && %s" % (shlex.quote(cwd), exp)
                out.append(exp)
                out.extend(candidates(exp, alias_lookup, depth + 1))
    return out


def config_force(cmd):
    """True when the command SETS a push refspec with a leading + (a forced push the next time anyone pushes):
    `git config [--add|--global|...] remote.<n>.push +refs/...`, or `git -c remote.<n>.push=+... push`."""
    try:
        toks = _tokenize(cmd)
    except ValueError:
        return False
    for seg, _op in _segment(toks):
        i = skip_prefix(seg)
        if i >= len(seg) or not _is_git(seg[i]):
            continue
        j, _cdir, ov = _git_sub(seg, i)
        sub = seg[j] if j < len(seg) else ""
        if sub == "push":
            for o in ov:
                k, _, v = o.partition("=")
                if _RPUSH.fullmatch(k.strip()) and v.startswith("+"):
                    return True
        elif sub == "config":
            a = seg[j + 1:]
            for k, w in enumerate(a):
                if _RPUSH.fullmatch(w) and k + 1 < len(a) and a[k + 1].startswith("+"):
                    return True
    return False
