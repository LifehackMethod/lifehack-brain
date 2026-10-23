"""
git_target_resolver.py — SHARED repo-target resolver for the git-command signpost
guards (commit, push) and any future outbound-act guard.

WHY THIS EXISTS: guard_git_push_signpost.sh (fixed 2026-09-08, commit 25a01e1) parses
-C and a leading `cd` out of the command text because these guards are PreToolUse —
they run BEFORE the command, so they can never observe a `cd` that hasn't happened
yet and must track one explicitly instead. guard_git_commit_signpost.sh never got
that fix and stayed $PWD-only for anything but an explicit `-C`, so on 2026-09-08 a
live `cd ~/lifehack-brain && git commit ...` was signposted "COMMIT · ClaudeOps
(PRIVATE)" — the wrong repo, confidently. This module is the ONE place that logic
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


def _tokenize(cmd):
    """Tokenize with shell metacharacters as their own tokens even when not
    whitespace-padded (e.g. 'exit;'), while still honoring quotes."""
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


def resolve(cmd, verb):
    """
    cmd: the raw command string from tool_input.
    verb: the git subcommand this guard cares about ("commit", "push", ...).

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
        if shape.search(cmd):
            return ("AMBIGUOUS", "")
        return ("NOT_OURS", "")

    segments = _segment(toks)
    n = len(segments)

    cwd = ""
    tainted = False
    i = 0
    while i < n:
        seg, preceding_op = segments[i]

        if preceding_op == "|":
            # a pipe runs its left side in a subshell; a cd before it never
            # touches what follows -- drop, don't guess.
            cwd = ""
            tainted = False

        if seg and seg[0] == "cd":
            target = _cd_target(seg)
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
            elif target:
                cwd = target
                tainted = False
            i += 1
            continue

        idx = 0
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
