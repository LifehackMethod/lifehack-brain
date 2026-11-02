#!/usr/bin/env python3
# not-wired-yet: imported by the rig launchers (rig_live_free.py, rig_meal.py, rig_student.py, rig_canary_live.py); never part of the product hooks
"""rig_isolation.py - what a rig ACTOR process (a headless `claude -p` exam session) may inherit from the machine it runs on.

WHY (2026-11-02, record rig-real-drive-write-audit): a sandbox exam actor trashed 899 real Drive files with `gws`. The launchers built the child
     environment as dict(os.environ, ...), so the child inherited the real gws config dir and credentials file (absolute real-home paths a throwaway
     HOME cannot hide) and a PATH that still found the gws binary. The fence only judged file writes.
WHAT this module gives every launcher:
  build_actor_env()   an ALLOWLIST env: only the names below pass from the parent; credentials and cloud-CLI config never do. Returns the names
                      it dropped (never the values) so the run log can list them.
  make_private_path() a per-run shim folder of symlinks to the few non-system binaries the actors need, then the SIP-protected system folders.
                      No gws, gcloud, gsutil, gh, aws, az, rclone or gdrive is ever linked.
  preflight()         refuses the run (with evidence) if any forbidden binary resolves on the actor PATH or any forbidden env name is present.
  real_notes_roots()  the REAL notes root(s), resolved from the parent's pointer through shared/person_roots.py BEFORE the env is scrubbed, so the
                      fence can hard-deny them wherever they live (Drive, Dropbox, a plain folder).
  fence_env()         the RIG_FENCE_* variables, including RIG_FENCE_DENY (hard-deny roots: real ~/Library/CloudStorage + the real notes roots).
"""
import json, os, re, shlex, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
V2_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# ---- binaries ---------------------------------------------------------------------------------------------------------------------
FORBIDDEN_BINS = ("gws", "gcloud", "gsutil", "gh", "aws", "az", "rclone", "gdrive")
# Linked into the shim, each resolved from the PARENT's PATH. Derived from a census of every Bash call in the 828 saved exam streams plus every
# command the plugin hooks and githooks run (rig-cred-isolation record): the only NON-system binaries actors ran were python3, claude and the
# forbidden gws/gh; the hooks additionally probe jq, gitleaks (pre-commit, fail-closed) and timeout/gtimeout (coreutils). git is linked so
# the parent's git (not whichever /usr/bin shim) runs. Everything else the actors use (ls, cat, sed, find, sqlite3, zip, curl, shasum, ...) is in
# /usr/bin or /bin, which stay on PATH after the shim.
ACTOR_BINS = ("claude", "python3", "git", "jq", "gitleaks", "timeout", "gtimeout")
REQUIRED_BINS = ("claude", "python3", "git")
SYSTEM_DIRS = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")   # SIP-protected on macOS: nothing can be installed into them, so no cloud CLI lives there

# ---- environment ------------------------------------------------------------------------------------------------------------------
# Narrowed 2026-11-02 (record rig-actor-sandbox; per-name reasons in drafts/rig-actor-sandbox-layer-design.md §4):
#  kept     TERM LANG LC_ALL LC_CTYPE TZ USER LOGNAME - harmless, and python/git behave the same as in a real session
#  dropped  COLORTERM (cosmetic); TMPDIR (the shared /var/folders temp: the rig sets a per-run one); SHELL (the rig fixes /bin/bash: without it
#           the Bash tool used zsh, whose temp files land outside the sandbox's allowed set); every parent proxy and CA variable (the rig points
#           the proxy at its own allowlist proxy; NO_PROXY=* would silently bypass it; CA paths can point into the real home);
#           ANTHROPIC_BASE_URL (it redirects claude's API traffic - WITH the token - to any host).
PARENT_KEEP = ("TERM", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "USER", "LOGNAME")
NET_KEEP = ()
AUTH_TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
AUTH_KEY = "ANTHROPIC_API_KEY"   # passed only when no OAuth token is set, so the token is the one credential (same rule as the skill-tester rig)
RIG_PREFIXES = ("ROUNDB_", "LH_", "LHB_", "LIFEHACK_", "RIG_FENCE_", "RIG_DRIVE_")   # the rig's own switches (ROUNDB_FC_ASK_NOT_TOKEN is a switch, not a token)
FORBIDDEN_PREFIXES = ("GOOGLE_", "GWS_", "GOOGLE_WORKSPACE_", "CLOUDSDK_", "GCLOUD_", "GSUTIL_", "BOTO_", "GH_", "GITHUB_", "AWS_", "AZURE_", "AZ_",
                      "ARM_", "RCLONE_", "GDRIVE_", "DROPBOX_", "ONEDRIVE_")
FORBIDDEN_NAMES = ("SSH_AUTH_SOCK", "GPG_AGENT_INFO", "KUBECONFIG", "DOCKER_CONFIG", "NETRC", "GIT_ASKPASS", "SSH_ASKPASS", "CLAUDE_CONFIG_DIR",
                   "CLAUDE_PLUGIN_ROOT", "BOTO_CONFIG")
SECRETY = re.compile(r"TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|API_?KEY|PRIVATE_KEY|ACCESS_KEY|_AUTH$|^AUTH_|COOKIE|SESSION_KEY", re.I)
# Fixed values every actor gets: no system git config (macOS ships credential.helper=osxkeychain there, which would hand a real GitHub token to
# any https push), no git password prompt, and ssh that offers no key and asks nothing.
ACTOR_FIXED = {"LIFEHACK_SANDBOX": "V2", "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "DISABLE_AUTOUPDATER": "1", "SHELL": "/bin/bash",
               "GIT_SSH_COMMAND": "ssh -F /dev/null -o IdentitiesOnly=yes -o IdentityFile=/dev/null -o IdentityAgent=none -o BatchMode=yes"}


def forbidden_name(k):
    """True for a name that must never reach an actor: a cloud-CLI/GitHub/SSH config name, or anything that looks like a secret except the
    Anthropic auth the actor needs to run."""
    if k in (AUTH_TOKEN, AUTH_KEY):
        return False
    if k.startswith(FORBIDDEN_PREFIXES) or k in FORBIDDEN_NAMES:
        return True
    return not k.startswith(RIG_PREFIXES) and bool(SECRETY.search(k))


def _real_home():
    return os.path.realpath(os.path.expanduser("~"))


def build_actor_env(parent, extra, home=None, path=None, real_home=None):
    """-> (env, dropped_names). parent: the launcher's own environment (os.environ). extra: what the RIG chose for this actor (HOME, LIFEHACK_ROOT,
    RIG_FENCE_*, ROUNDB_*, the OAuth token, --env K=V). From the parent only PARENT_KEEP / NET_KEEP / the Anthropic auth pass; a parent value that
    holds the real home path is dropped too (TMPDIR or SHELL pointing into the real home would hand the actor a real path). From `extra`, every
    name passes EXCEPT a forbidden one. dropped_names: sorted names (never values)."""
    rh = real_home or _real_home()
    extra = dict(extra or {})
    env, dropped = {}, set()
    for k, v in parent.items():
        if k in (AUTH_TOKEN, AUTH_KEY):
            continue
        if k in NET_KEEP or (k in PARENT_KEEP and rh not in v):
            env[k] = v
        else:
            dropped.add(k)
    for k, v in extra.items():
        if forbidden_name(k):
            dropped.add(k)
        else:
            env[k] = v
    tok = extra.get(AUTH_TOKEN) or parent.get(AUTH_TOKEN)
    if tok:
        env[AUTH_TOKEN] = tok
        if AUTH_KEY in parent or AUTH_KEY in extra:
            dropped.add(AUTH_KEY)
            env.pop(AUTH_KEY, None)
    elif extra.get(AUTH_KEY) or parent.get(AUTH_KEY):
        env[AUTH_KEY] = extra.get(AUTH_KEY) or parent.get(AUTH_KEY)
    env.update(ACTOR_FIXED)
    if home:
        env["HOME"] = home
    if path:
        env["PATH"] = path
    elif "PATH" not in extra:
        env["PATH"] = ":".join(SYSTEM_DIRS)
    dropped -= set(env)   # a name the rig set itself (HOME, PATH, the token) is not "dropped"
    return env, sorted(dropped)


def make_private_path(bindir, parent_path=None):
    """Create (idempotent) `bindir` holding symlinks to ACTOR_BINS resolved on the parent's PATH; -> (PATH string, {name: target}, [missing]).
    A name that resolves to a forbidden binary (a symlink called python3 that is really gws, say) is refused. The PATH is bindir + SYSTEM_DIRS."""
    parent_path = parent_path if parent_path is not None else os.environ.get("PATH", "")
    search = ":".join(d for d in parent_path.split(":") if d and os.path.realpath(d) != os.path.realpath(bindir))
    os.makedirs(bindir, exist_ok=True)
    linked, missing = {}, []
    for name in ACTOR_BINS:
        tgt = shutil.which(name, path=search)
        if not tgt or os.path.basename(os.path.realpath(tgt)) in FORBIDDEN_BINS:
            missing.append(name)
            continue
        ln = os.path.join(bindir, name)
        if os.path.islink(ln) and os.readlink(ln) == tgt:
            linked[name] = tgt
            continue
        if os.path.lexists(ln):
            os.unlink(ln)
        os.symlink(tgt, ln)
        linked[name] = tgt
    for name in os.listdir(bindir):   # anything else in the shim (planted, or left from an older list) is a defect
        if name not in linked:
            raise SystemExit("REFUSED: unexpected entry in the actor shim %s: %s" % (bindir, name))
    return ":".join([bindir] + list(SYSTEM_DIRS)), linked, missing


def find_forbidden_bins(env):
    """-> [(name, path)] for every forbidden binary resolvable on env['PATH'] (python scan of each PATH entry) plus what a POSIX `command -v`
    run UNDER that env reports (the same check a shell in the actor would make)."""
    hits = set()
    for d in (env.get("PATH") or "").split(":"):
        for name in FORBIDDEN_BINS:
            p = os.path.join(d or ".", name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                hits.add((name, p))
    try:
        r = subprocess.run(["/bin/sh", "-c", "command -v " + " ".join(FORBIDDEN_BINS)], env=env, capture_output=True, text=True, timeout=20)
        for ln in r.stdout.split():
            if os.path.basename(ln) in FORBIDDEN_BINS:
                hits.add((os.path.basename(ln), ln))
    except (OSError, subprocess.SubprocessError) as e:
        hits.add(("command -v", "could not run: %s" % e))
    return sorted(hits)


def preflight(env, linked=None, missing=None):
    """-> list of problems (empty = clean). Checks: no forbidden binary on the actor PATH, no forbidden env name, required shim binaries present."""
    probs = ["forbidden binary on actor PATH: %s -> %s" % h for h in find_forbidden_bins(env)]
    probs += ["forbidden env name present: %s" % k for k in sorted(env) if forbidden_name(k)]
    if missing is not None:
        probs += ["required binary missing from the actor shim: %s" % n for n in REQUIRED_BINS if n in missing]
    if linked is not None:
        probs += ["shim links a forbidden binary: %s -> %s" % (n, t) for n, t in linked.items() if os.path.basename(os.path.realpath(t)) in FORBIDDEN_BINS]
    return probs


def require_clean(env, linked=None, missing=None, where="preflight"):
    """sys.exit with the evidence when preflight finds anything; prints a one-line ok otherwise."""
    probs = preflight(env, linked, missing)
    if probs:
        sys.exit("REFUSED (%s): the actor environment is not isolated; no session was started.\n  " % where + "\n  ".join(probs))
    return True


def real_notes_roots(parent=None):
    """The REAL notes root(s) of whoever runs the rig, resolved through shared/person_roots.py from the PARENT environment (before any scrub):
    once as the parent sees it, and once with LIFEHACK_ROOT removed so the pointer's answer counts even when the launcher itself runs under a
    throwaway LIFEHACK_ROOT. -> sorted list of real paths (may be empty for a person with no pointer)."""
    parent = dict(os.environ if parent is None else parent)
    roots = set()
    pr = os.path.join(V2_ROOT, "shared", "person_roots.py")
    for env in (parent, {k: v for k, v in parent.items() if k != "LIFEHACK_ROOT"}):
        try:
            r = subprocess.run([sys.executable, "-I", pr, "--shell"], env=env, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        for ln in r.stdout.splitlines():
            if ln.startswith("NOTES=") and ln[6:].strip():
                roots.add(os.path.realpath(ln[6:].strip()))
    return sorted(roots)


def deny_roots(real_home=None, notes_roots=()):
    """Hard-deny roots for the fence: the real ~/Library/CloudStorage (every synced drive mount) and every real notes root. These beat the
    fence's allow list; only the one rig_drive run folder (RIG_FENCE_RUN_DRIVE) is honoured inside them."""
    rh = real_home or _real_home()
    return [os.path.realpath(os.path.join(rh, "Library", "CloudStorage"))] + [os.path.realpath(n) for n in notes_roots if n]


def fence_env(real_home, real_notes, allow, log=None, notes_roots=()):
    """The RIG_FENCE_* variables for an actor. real_notes: list of real notes roots (also hard-denied). allow: throwaway dirs."""
    notes = sorted({os.path.realpath(n) for n in list(real_notes) + list(notes_roots) if n})
    e = {"RIG_FENCE_REAL_HOME": os.path.realpath(real_home), "RIG_FENCE_REAL_NOTES": ":".join(notes),
         "RIG_FENCE_ALLOW": ":".join(os.path.realpath(a) for a in allow if a), "RIG_FENCE_DENY": ":".join(deny_roots(real_home, notes))}
    if log:
        e["RIG_FENCE_LOG"] = log
    return e


def fence_settings(base_path, out_path):
    """A copy of the base --settings file (or {} when base_path is None) with ONE extra PreToolUse hook, rig_fence.py. The base file is not touched."""
    d = {}
    if base_path:
        with open(base_path, encoding="utf-8") as f:
            d = json.load(f)
    hk = d.setdefault("hooks", {}).setdefault("PreToolUse", [])
    hk.append({"matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash|Read|Glob|Grep",
               "hooks": [{"type": "command", "command": "python3 -I " + shlex.quote(os.path.join(HERE, "rig_fence.py"))}]})
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(d, f)
    return out_path


def oauth_token(real_home=None):
    """The Claude login token the rig hands an actor whose HOME is throwaway (the launcher's own env first, then the saved token file)."""
    if os.environ.get(AUTH_TOKEN):
        return os.environ[AUTH_TOKEN]
    tok = os.path.join(real_home or _real_home(), ".config", "lifehack", "claude-oauth-token")
    return re.sub(r"\s+", "", open(tok, encoding="utf-8").read()) if os.path.exists(tok) else None


def write_log(path, dropped, linked, missing, problems):
    """The per-session isolation log (names only, never values)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"dropped_env_names": dropped, "shim": linked, "shim_missing": missing, "preflight_problems": problems}, f, indent=1)
