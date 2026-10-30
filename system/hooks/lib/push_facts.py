#!/usr/bin/env python3
"""push_facts.py -- what a `git push` is, for guard_git_push_signpost.sh (Round C, fine china).

One verdict line on stdout, tab separated:
  NORMAL                        nothing special: the signpost behaves exactly as before
  QUIET                         fc_plain_push_quiet: a plain push the branch tracks normally -> no signpost
  HARD_FORCE <detail>           fc_force_push: a force push of any spelling
  HARD_PRIVATE <detail>         fc_private_push: outgoing commits carry private material (existing leakage scan)
  HARD_PRIVATE_CANNOT <detail>  the leakage scan exists but could not run -> fail closed on a remote that is not local

Switches arrive as flags (the bash caller reads roundB.conf); a switch that is OFF skips its whole check, so
OFF is exactly the old behaviour. Nothing here runs the push, writes anything, or touches the network.

The leakage rules are NOT copied: the scanner at .github/scripts/check_no_internal_leakage.py is imported and its
own parse_unified_diff / scan_files are called, the way system/githooks/checks/safe_to_ship.py does it.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys

PUBLIC_REPO = "LifehackMethod/lifehack-brain"
VALUE_FLAGS = ("-o", "--push-option", "--repo", "--receive-pack", "--exec", "--recurse-submodules")
MAX_COMMITS = 400


def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True,
                           errors="replace", timeout=20)
        return r.returncode, (r.stdout or "").strip("\n")
    except Exception:
        return 1, ""


def parse_argv(argv):
    """-> dict. Walks push's own argv: flags, then remote, then refspecs."""
    p = {"force": False, "mirror": False, "all": False, "tags": False, "delete": False,
         "positional": [], "plus": False}
    i, n, dashdash = 0, len(argv), False
    while i < n:
        t = argv[i]
        if not isinstance(t, str):
            i += 1
            continue
        if not dashdash and t == "--":
            dashdash = True
            i += 1
            continue
        if not dashdash and len(t) > 1 and t[0] == "-":
            base = t.split("=", 1)[0]
            if base in VALUE_FLAGS and "=" not in t:
                i += 2
                continue
            if base in ("--force", "--force-with-lease", "--force-if-includes"):
                p["force"] = True
            elif base == "--mirror":
                p["mirror"] = True
            elif base == "--all":
                p["all"] = True
            elif base == "--tags":
                p["tags"] = True
            elif base == "--delete":
                p["delete"] = True
            elif not t.startswith("--"):
                # a cluster of short flags such as -fu or -uf: f is force, d is delete
                letters = t[1:]
                if "f" in letters:
                    p["force"] = True
                if "d" in letters:
                    p["delete"] = True
            i += 1
            continue
        p["positional"].append(t)
        i += 1
    p["remote"] = p["positional"][0] if p["positional"] else ""
    p["refspecs"] = p["positional"][1:]
    p["plus"] = any(r.startswith("+") for r in p["refspecs"])
    return p


def push_url(repo, remote):
    rc, out = git(repo, "remote", "get-url", "--push", remote)
    return out.strip() if rc == 0 else ""


def is_networked(url):
    """A remote someone else can read: a host-bearing URL. A local path or file:// is not."""
    if not url:
        return False
    if url.startswith("file://") or url.startswith("/") or url.startswith("./") or url.startswith("../"):
        return False
    return bool(re.match(r"^(https?|ssh|git)://", url) or re.match(r"^[\w.-]+@[\w.-]+:", url))


def is_personal_repo(repo, shared):
    rc, top = git(repo, "rev-parse", "--show-toplevel")
    if rc != 0 or not top:
        return False
    try:
        sys.path.insert(0, shared)
        import personal_code_root
        source, path = personal_code_root.resolve_personal_code_root()
        return source in ("pointer", "default") and bool(path) and os.path.realpath(path) == os.path.realpath(top)
    except Exception:
        return False


def current_branch(repo):
    rc, out = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if rc == 0 else ""


def resolve_remote(repo, p, branch):
    if p["remote"]:
        return p["remote"]
    if p["all"] or p["tags"] or p["mirror"]:
        return ""
    if branch and branch != "HEAD":
        rc, out = git(repo, "config", "--get", "branch.%s.remote" % branch)
        if rc == 0 and out.strip():
            return out.strip()
    rc, out = git(repo, "remote")
    first = out.split("\n")[0] if rc == 0 and out else ""
    return "origin" if git(repo, "remote", "get-url", "origin")[0] == 0 else first


def named_remote(repo, remote):
    rc, out = git(repo, "remote")
    return rc == 0 and remote in out.split("\n")


def refs_pushed(p, branch):
    """[(src, dst)] the push names; a bare push is current-branch -> its upstream/same name."""
    if p["all"] or p["mirror"]:
        return None  # cannot enumerate cheaply -> caller treats as "everything local"
    out = []
    for raw in p["refspecs"]:
        s = raw[1:] if raw.startswith("+") else raw
        src, dst = (s.split(":", 1) + [""])[:2] if ":" in s else (s, s)
        if src == "HEAD":
            src = branch
            if dst == "HEAD":
                dst = branch
        out.append((src, dst))
    if not out and branch and branch != "HEAD":
        out.append((branch, branch))
    return out


# ───────────────────────── force ─────────────────────────
def force_detail(p):
    if p["force"] or p["plus"] or p["mirror"]:
        why = []
        if p["force"]:
            why.append("a force flag (--force / -f / --force-with-lease)")
        if p["plus"]:
            why.append("a +refspec")
        if p["mirror"]:
            why.append("--mirror (overwrites every remote ref)")
        return " and ".join(why)
    return ""


# ───────────────────────── quiet ─────────────────────────
def plain_and_tracked(repo, p, branch, remote):
    """True only for the ordinary case: a fast-forward push of the checked-out branch to the branch it tracks,
    on a configured remote that is not the public Lifehack repo."""
    if p["force"] or p["plus"] or p["mirror"] or p["all"] or p["tags"] or p["delete"]:
        return False
    if not branch or branch == "HEAD" or not remote or not named_remote(repo, remote):
        return False
    url = push_url(repo, remote)
    if not url or PUBLIC_REPO in url:
        return False
    rc, trk = git(repo, "config", "--get", "branch.%s.remote" % branch)
    if rc != 0 or trk.strip() != remote:
        return False
    rc, merge = git(repo, "config", "--get", "branch.%s.merge" % branch)
    if rc != 0 or not merge.startswith("refs/heads/"):
        return False
    upstream_branch = merge[len("refs/heads/"):]
    pairs = refs_pushed(p, branch)
    if not pairs or len(pairs) != 1:
        return False
    src, dst = pairs[0]
    if src != branch or dst != upstream_branch:
        return False
    tracking = "refs/remotes/%s/%s" % (remote, upstream_branch)
    if git(repo, "rev-parse", "--verify", "--quiet", tracking)[0] != 0:
        return False
    return git(repo, "merge-base", "--is-ancestor", tracking, branch)[0] == 0


# ───────────────────────── private material ─────────────────────────
def outgoing_commits(repo, src, remote, url):
    if git(repo, "rev-parse", "--verify", "--quiet", src + "^{commit}")[0] != 0:
        return []
    args = ["rev-list", "--topo-order", src]
    if named_remote(repo, remote):
        args += ["--not", "--remotes=" + remote]
    rc, out = git(repo, *args)
    return [c for c in out.split("\n") if c] if rc == 0 else []


def leak_scan(repo, p, branch, remote, url, hooks_lib):
    """-> ("clean"|"flagged"|"cannot"|"skip", [lines])."""
    scanner_dir = os.path.normpath(os.path.join(hooks_lib, "..", "..", "..", ".github", "scripts"))
    if not os.path.isfile(os.path.join(scanner_dir, "check_no_internal_leakage.py")):
        return "skip", []  # not shipped here (a plugin install): nothing to run, stay quiet
    pairs = refs_pushed(p, branch)
    if pairs is None:
        rc, out = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
        pairs = [(b, b) for b in out.split("\n") if b]
    commits = []
    for src, _dst in pairs:
        for c in outgoing_commits(repo, src, remote, url):
            if c not in commits:
                commits.append(c)
    if not commits:
        return "clean", []
    sys.path.insert(0, scanner_dir)
    try:
        import check_no_internal_leakage as leak
    except Exception as e:
        return "cannot", ["scanner import failed: %s" % str(e)[:120]]
    try:
        leak.install_identity_patterns(os.environ.get("SHIP_IDENTITY") or None)
    except Exception as e:
        return "cannot", ["operator-identity tier not compilable: %s" % str(e)[:160]]
    findings = []
    texts = []
    if len(commits) > MAX_COMMITS:
        rc, diff = git(repo, "diff", "--unified=0", "--no-color", "--no-renames",
                       "4b825dc642cb6eb9a060e54bf8d69288fbee4904", pairs[0][0])
        texts.append(("(net of %d commits)" % len(commits), diff))
    else:
        for c in commits:
            rc, diff = git(repo, "show", "--format=", "-m", "--first-parent", "--unified=0", "--no-color", "--no-renames", c)
            if diff:
                texts.append((c[:8], diff))
    for label, diff in texts:
        try:
            file_diffs = leak.parse_unified_diff(diff)
            whole = {path: "\n".join(t for _, t in lines) for path, lines in file_diffs}
            vs = leak.scan_files(file_diffs, whole, frozenset(leak.DESK_PERSONA_CANDIDATES))
        except Exception as e:
            return "cannot", ["scan raised: %s" % str(e)[:120]]
        for v in vs:
            findings.append("commit %s: %s" % (label, re.sub(r"\s+", " ", str(v))[:200]))
    return ("flagged", findings[:6]) if findings else ("clean", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--argv-b64", default="")
    ap.add_argument("--shared", default="")
    ap.add_argument("--force-on", action="store_true")
    ap.add_argument("--private-on", action="store_true")
    ap.add_argument("--quiet-on", action="store_true")
    ap.add_argument("--local-on", action="store_true")
    a = ap.parse_args()
    try:
        argv = json.loads(base64.b64decode(a.argv_b64).decode("utf-8", "surrogateescape")) if a.argv_b64 else []
        if not isinstance(argv, list):
            argv = []
    except Exception:
        print("NORMAL")
        return 0
    p = parse_argv(argv)
    repo = a.repo
    if a.force_on:
        d = force_detail(p)
        if d:
            print("HARD_FORCE\t" + d)
            return 0
    branch = current_branch(repo)
    remote = resolve_remote(repo, p, branch)
    if a.force_on and remote and not p["refspecs"]:
        # a push that names no refspec uses remote.<n>.push; a leading + there makes it a force push
        rc, out = git(repo, "config", "--get-all", "remote.%s.push" % remote)
        if rc == 0 and any(ln.strip().startswith("+") for ln in out.split("\n")):
            print("HARD_FORCE\ta + refspec in remote.%s.push config" % remote)
            return 0
    if a.private_on and remote:
        url = push_url(repo, remote) if named_remote(repo, remote) else remote
        # silent and cheap when there is nothing to leak to: no remote, a local path, or the person's own private repo
        if is_networked(url) and not is_personal_repo(repo, a.shared):
            status, lines = leak_scan(repo, p, branch, remote, url, os.path.dirname(os.path.abspath(__file__)))
            if status == "flagged":
                print("HARD_PRIVATE\t" + " | ".join(lines))
                return 0
            if status == "cannot":
                print("HARD_PRIVATE_CANNOT\t" + " | ".join(lines))
                return 0
    if a.local_on and remote and not (p["force"] or p["plus"] or p["mirror"] or p["delete"]):
        # fc_local_push_quiet: a push to a folder on this same machine (a bare repo, a backup copy) cannot reach anyone: no signpost
        url = push_url(repo, remote) if named_remote(repo, remote) else remote
        if url and not is_networked(url) and PUBLIC_REPO not in url and (url.startswith(("/", "./", "../", "~", "file://")) or os.path.isdir(os.path.join(repo, url))):
            print("QUIET")
            return 0
    if a.quiet_on and plain_and_tracked(repo, p, branch, remote):
        print("QUIET")
        return 0
    print("NORMAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
