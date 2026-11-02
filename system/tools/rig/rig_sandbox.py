#!/usr/bin/env python3
# rig-only: imported by the live rig launchers (rig_live_free.py, rig_canary_live.py); never part of the product hooks
"""rig_sandbox.py - the second, NON-HOOK layer around every live rig actor (2026-11-02, record rig-actor-sandbox).

WHY: on 2026-11-01 a sandbox exam actor (D-F11) trashed 899 real Drive files through gws. The first fix (rig_isolation + rig_fence, 25dd6cf)
     still rests on a PreToolUse hook that parses command strings - the exact shape that failed. This layer does not parse anything:
     the WHOLE actor process (claude, its plugin hooks, Write/Edit, Bash, every subprocess) runs under macOS sandbox-exec, so the kernel
     refuses what the profile does not allow, however the command was spelled.
WHAT the profile allows (everything else of its kind is refused):
     writes   - only the run's own dirs (throwaway HOME, the case scratch dir, the per-run Drive folder when the case has one), the claude
                Bash-tool task dir keyed to THIS case's cwd, and the few /dev and bash here-doc files a0's write guard proved necessary.
                The plugin root, the actor settings file and the profile itself are re-denied AFTER the allow (last matching rule wins).
     reads    - default allow, EXCEPT cloud/GitHub/ssh credentials, the saved Claude token file and the keychain (paths + daemons).
                STUDENT setup only (2026-11-02, record rig-validity-fix): the whole real home is read-denied too (a student `find /`
                listed the runner's own files), with exact re-allows for what the actor needs there (student_home_read).
     network  - only 127.0.0.1:<proxy port>. rig_proxy.py (outside the sandbox) tunnels only to api.anthropic.com:443. SBPL cannot filter
                by host name; that is why the allowlist lives in the proxy. Proxy dead = no network (fails closed).
     escapes  - Apple Events, LaunchServices (open/Terminal) and the keychain daemons are refused.
FAILS CLOSED: available() must prove sandbox-exec exists AND enforces (a deny-all-writes probe really gets EPERM) before any run; otherwise
     the launcher refuses to start. Apple has deprecated sandbox-exec; the day it stops working, live runs stop, they never run unsandboxed.
PROVEN, NOT ASSUMED: preflight() runs rig_sandbox_canary.py through the SAME wrap() and the SAME env as the actor (hook-sop §4 trap 1) and
     refuses the run unless every check passes; scheduler registrations (crontab/at/launchctl) and escape sentinels are judged OUTSIDE.
KNOWN, ACCEPTED LIMIT (coordinator 2026-11-02): the actor can read its own CLAUDE_CODE_OAUTH_TOKEN from its environment. The worst case is
     spend on the owner's account through api.anthropic.com - the only host the proxy opens - not data loss.
"""
import json, os, re, secrets, shutil, socket, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
API_HOST = "api.anthropic.com:443"
TAG = "LH-RIG-SBX"
EPERM_RC = 71   # sandbox_apply refused (sandbox-exec's own exit code when a profile cannot be applied)

# credential locations under the REAL home the actor must never read (subpaths, plus a regex for every ~/.config/gws* variant)
CRED_SUBPATHS = (".config/gh", ".config/gcloud", ".aws", ".azure", ".ssh", ".config/rclone", ".config/lifehack/claude-oauth-token",
                 ".netrc", ".git-credentials", "Library/Keychains")
CRED_REGEX = (r"\.config/gws",)
MACH_DENY = ("com.apple.coreservices.appleevents", "com.apple.coreservices.launchservicesd", "com.apple.coreservices.quarantine-resolver",
             "com.apple.SecurityServer", "com.apple.securityd.xpc", "com.apple.security.agent", "com.apple.security.syspolicy")


def _q(p):
    """SBPL string literal."""
    return '"' + p.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _rx(s):
    """A POSIX-ERE-safe escape for an SBPL #"..." regex (re.escape over-escapes some chars SBPL rejects, e.g. '-' and ' ')."""
    return re.sub(r"([.^$*+?()\[\]{}|\\])", r"\\\1", s)


def case_slug(cwd):
    """claude's per-cwd task dir name under /private/tmp/claude-<uid>/: the real path with every non-alphanumeric turned into '-'."""  # allow-silence: names claude's own fixed per-uid task dir (a path the profile must match), nothing is written there by this code
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd))


def real_home():
    return os.path.realpath(os.path.expanduser("~"))


def student_home_read(real_home_dir, linked, dirs):
    """STUDENT setup (record rig-validity-fix, bug 2) -> {"home", "literal", "subpath"}: deny reading the real home (resolved here, at run
    time), re-allow EXACTLY what the actor needs inside it. Found by probing: claude runs from ~/.local/bin/claude -> ~/.local/share/claude/
    versions/<v> (one Mach-O), so each link of every shim binary's symlink chain under the home is re-allowed as a LITERAL path; `dirs`
    (the plugin dir, the rig's own source, a Drive run folder) are re-allowed as subpaths when they live under the home. A claude installed
    some other way (e.g. a node package under ~/.nvm) would fail to start -> the config preflight / canary control refuses the run (closed)."""
    rh = os.path.realpath(real_home_dir) if real_home_dir else real_home()
    under = lambda p: p == rh or p.startswith(rh + os.sep)
    lit, sub = [], []
    for t in (linked or {}).values():
        p, seen = os.path.abspath(t), 0
        while seen < 40:
            seen += 1
            parent = os.path.realpath(os.path.dirname(p))
            p = os.path.join(parent, os.path.basename(p))   # the link itself, with its directory resolved (the kernel matches real paths)
            if under(p) and p not in lit:
                lit.append(p)
            if not os.path.islink(p):
                break
            p = os.path.join(os.path.dirname(p), os.readlink(p))
    for d in dirs or ():
        if d and under(os.path.realpath(d)) and os.path.realpath(d) not in sub:
            sub.append(os.path.realpath(d))
    return {"home": rh, "literal": lit, "subpath": sub}


def profile(allow_write, cwd, proxy_port, protect=(), real_home_dir=None, decoy=None, uid=None, read_deny=(), home_read=None):
    """-> SBPL text. allow_write: the run's own dirs (realpaths). protect: re-denied after the allow (plugin root, settings, profile).
    decoy: a scratch-path fake credential tree the canary reads to prove the read rules on any machine.
    read_deny: extra paths the actor must not read (student setup: the real home's own Claude config, see personal_config_paths).
    home_read: student_home_read() -> the whole home read-denied AFTER (allow default) and the write allows, the exact re-allows after that,
    and the credential denies after both (last matching rule wins: a re-allow can never re-open a credential)."""
    rh = real_home_dir or real_home()
    uid = os.getuid() if uid is None else uid
    w = ["(version 1)", ";; rig actor sandbox (rig_sandbox.py). LAST MATCHING RULE WINS: a deny that must beat an allow comes AFTER it.",
         "(allow default)", "", '(deny file-write* (with message "%s"))' % TAG, "(allow file-write*"]
    for d in allow_write:
        w.append("  (subpath %s)" % _q(os.path.realpath(d)))
    w += ['  (literal "/dev/null") (literal "/dev/tty") (literal "/dev/dtracehelper") (subpath "/dev/fd")',
          '  (literal "/private/tmp") (regex #"^/private/tmp/sh-thd-[0-9]+$")',
          '  (literal "/private/tmp/claude-%d")' % uid,  # allow-silence: SBPL rule text for claude's fixed per-uid task dir, not a temp file this code creates
          '  (regex #"^/private/tmp/claude-%d/%s(/|$)"))' % (uid, _rx(case_slug(cwd)))]
    if protect:
        w.append("(deny file-write* %s (with message \"%s\"))" % (" ".join("(subpath %s)" % _q(os.path.realpath(p)) for p in protect), TAG))
    if home_read:
        w += ["", "(deny file-read* (subpath %s) (with message \"%s\"))" % (_q(home_read["home"]), TAG)]
        allows = ["(literal %s)" % _q(p) for p in home_read.get("literal", ())] + ["(subpath %s)" % _q(p) for p in home_read.get("subpath", ())]
        if allows:
            w.append("(allow file-read* %s)" % " ".join(allows))
    w += ["", "(deny file-read*"]
    for s in CRED_SUBPATHS:
        w.append("  (subpath %s)" % _q(os.path.join(rh, s)))
    for r in CRED_REGEX:
        w.append('  (regex #"^%s/%s")' % (_rx(rh), r))
    if decoy:
        w.append("  (subpath %s)" % _q(os.path.realpath(decoy)))
    for p in read_deny:
        w.append("  (subpath %s)" % _q(os.path.realpath(p)))
    w.append('  (with message "%s"))' % TAG)
    w.append("(deny mach-lookup %s (with message \"%s\"))" % (" ".join("(global-name %s)" % _q(n) for n in MACH_DENY), TAG))
    w.append('(deny appleevent-send (with message "%s"))' % TAG)
    w += ["", '(deny network-outbound (with message "%s"))' % TAG,
          '(allow network-outbound (remote tcp "localhost:%d"))' % int(proxy_port),
          '(allow network-outbound (remote unix-socket (path-literal "/private/var/run/mDNSResponder")))', ""]
    return "\n".join(w)


def personal_config_paths(real_home_dir=None):
    """The real home's OWN Claude config a student actor must never load (2026-11-02, record rig-config-isolation): Claude Code walks UP from
    the cwd and loads every ancestor's .claude/CLAUDE.md, skills and agents (proven by a dead-network probe), so a run dir anywhere under the
    real home handed students the owner's brief and skills. The rig dirs now live outside the home; these kernel read-denies are the second
    layer. Existing paths only (a subpath rule on a missing path proves nothing in the canary)."""
    rh = real_home_dir or real_home()
    c = os.path.join(rh, ".claude")
    import rig_config_isolation as ci   # errno-based: a DENIED path raises here (refuse), only ENOENT counts as absent
    names = ["CLAUDE.md", "skills", "agents", "hooks"] + sorted(n for n in ci.listdir_or_empty(c) if re.match(r"settings.*\.json$", n))
    return [p for p in [os.path.join(c, n) for n in names] + [os.path.join(rh, ".claude.json")] if ci.present(p)]


def write_profile(text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def wrap(cmd, profile_path, sandbox_exec=SANDBOX_EXEC):
    """THE launch function. Used for the actor AND for the canary, so the canary proves the very wrapper the actor runs under."""
    return [sandbox_exec, "-f", profile_path] + list(cmd)


def available(sandbox_exec=SANDBOX_EXEC, workdir=None):
    """-> (ok, detail). ok only if sandbox-exec exists, runs, AND enforces: under a deny-all-writes profile a write really gets EPERM.
    Missing binary, a refusal, an error, or a pass-through stub that lets the write land are all NOT ok (fail closed)."""
    if not (os.path.isfile(sandbox_exec) and os.access(sandbox_exec, os.X_OK)):
        return False, "sandbox-exec missing or not executable: %s" % sandbox_exec
    d = tempfile.mkdtemp(prefix="rig-sbx-avail-", dir=workdir)
    target = os.path.join(d, "must-not-exist")
    prof = '(version 1)(allow default)(deny file-write* (subpath %s))' % _q(os.path.realpath(d))
    try:
        p = subprocess.run([sandbox_exec, "-p", prof, sys.executable, "-I", "-c",
                            "import sys,errno\ntry:\n open(sys.argv[1],'w').close()\nexcept OSError as e:\n sys.exit(0 if e.errno==errno.EPERM else 3)\nsys.exit(4)",
                            target], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, "sandbox-exec could not run: %r" % e
    landed = os.path.exists(target)
    if landed:
        os.unlink(target)
    os.rmdir(d)
    if p.returncode == 0 and not landed:
        return True, "sandbox-exec enforces (deny-write probe got EPERM)"
    return False, "sandbox-exec does not enforce (rc=%s, write landed=%s, stderr=%s)" % (p.returncode, landed, (p.stderr or "").strip()[:200])


def start_proxy(log_path, allow=(API_HOST,)):
    """-> (Popen, port). rig_proxy.py runs OUTSIDE the sandbox; it prints 'PORT <n>' once listening."""
    cmd = [sys.executable, "-I", os.path.join(HERE, "rig_proxy.py"), "--log", log_path]
    for a in allow:
        cmd += ["--allow", a]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL)
    line = p.stdout.readline().strip()
    if not line.startswith("PORT "):
        p.kill()
        raise RuntimeError("rig_proxy did not start: %r %s" % (line, (p.stderr.read() or "")[:200]))
    return p, int(line.split()[1])


def stop_proxy(p):
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()


def actor_net_env(port):
    """Env the sandboxed actor needs: every proxy spelling pointed at the allowlist proxy, a fixed shell (no SHELL made the Bash tool use zsh,
    whose temp files land outside the allowed set), no non-essential claude traffic, no bytecode writes into the read-only plugin dir."""
    u = "http://127.0.0.1:%d" % port
    return {"HTTPS_PROXY": u, "HTTP_PROXY": u, "https_proxy": u, "http_proxy": u, "SHELL": "/bin/bash",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "PYTHONDONTWRITEBYTECODE": "1"}


# ---------------------------------------------------------------- preflight (outside half; the inside half is rig_sandbox_canary.py)

def _state(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return p.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        return "ERR %r" % e


def scheduler_state():
    """crontab, at queue, launchd jobs: compared before/after the canary. Anything new = something escaped the sandbox."""
    return {"crontab": _state(["/usr/bin/crontab", "-l"]), "atq": _state(["/usr/bin/atq"]), "launchctl": _state(["/bin/launchctl", "list"])}


HOOK_STANDIN = """#!/bin/bash
# rig canary stand-in hook (rig_sandbox.canary_spec): does what the Enver setup's guard_gh_pr_merge.sh does first - a bare mktemp
f=$(mktemp) || exit 3
d=$(mktemp -d) || exit 4
echo "$f"
echo "$d"
rm -f "$f"
rmdir "$d"
"""
REQUIRED_EXTRA_IDS = ("C11.mktemp",)   # always required (rig-validity-fix); C10.* added when the spec carries a home read-deny


def canary_spec(run, port, write_denied, write_allowed, notes_roots, nonce, real_home_dir=None, escapes=True, read_denied_extra=(), home_read=None):
    """The checks the in-sandbox canary runs. run: a scratch dir OUTSIDE every allowed dir (decoy, probe plist, sentinel live there)."""
    rh = real_home_dir or real_home()
    decoy = os.path.join(run, "decoy")
    os.makedirs(os.path.join(decoy, ".config", "gws"), exist_ok=True)
    with open(os.path.join(decoy, ".config", "gws", "credentials.json"), "w", encoding="utf-8") as f:
        f.write('{"decoy": true}\n')
    reads = [os.path.join(decoy, ".config", "gws", "credentials.json")]
    for s in CRED_SUBPATHS:
        if os.path.exists(os.path.join(rh, s)):
            reads.append(os.path.join(rh, s))
    reads += [p for p in read_denied_extra if os.path.exists(p)]
    cfg = os.path.join(rh, ".config")
    if os.path.isdir(cfg):
        reads += [os.path.join(cfg, n) for n in sorted(os.listdir(cfg)) if n.startswith("gws")]
    label = "lh.rig.canary.%s" % nonce
    plist = os.path.join(run, label + ".plist")
    with open(plist, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict><key>Label</key><string>%s</string>'
                '<key>ProgramArguments</key><array><string>/usr/bin/true</string></array></dict></plist>\n' % label)
    standin = os.path.join(run, "hook-standin.sh")
    with open(standin, "w", encoding="utf-8") as f:
        f.write(HOOK_STANDIN)
    hr = None
    if home_read:   # the decoy lives UNDER the denied home (made outside the sandbox, removed by preflight); controls = every re-allow
        hdecoy = os.path.join(home_read["home"], ".lh-rig-canary-decoy-%s" % nonce)
        with open(hdecoy, "w", encoding="utf-8") as f:
            f.write("rig canary decoy: must be unreadable inside the student sandbox\n")
        hr = {"home": home_read["home"], "decoy": hdecoy, "controls": list(home_read.get("literal", ())) + list(home_read.get("subpath", ()))}
    return {"nonce": nonce, "write_denied": list(write_denied), "write_allowed": list(write_allowed), "hook_standin": standin, "home_read": hr,
            "direct_hosts": [["1.1.1.1", 443], ["www.googleapis.com", 443], ["github.com", 443]],
            "proxy": {"port": port, "denied": ["www.googleapis.com:443", "github.com:443", "example.com:443"], "allowed": [API_HOST]},
            "read_denied": reads, "notes_roots": list(notes_roots),
            "escapes": {"security": "/usr/bin/security", "osascript": "/usr/bin/osascript", "lsappinfo": "/usr/bin/lsappinfo", "crontab": "/usr/bin/crontab",
                        "at": "/usr/bin/at", "launchctl": "/bin/launchctl", "label": label, "plist": plist} if escapes else {},
            "_outside": {"label": label, "decoy": decoy}}


def judge(lines, spec, before, after):
    """-> list of problems (empty = sandbox proven for this run). lines: the canary's JSON lines."""
    probs = []
    got = {}
    for ln in lines:
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        got[d["id"]] = d
        if not d.get("ok"):
            probs.append("%s FAIL: %s (%s)" % (d["id"], d.get("name"), d.get("detail")))
    need = ["C0"] + ["C1.%d" % i for i in range(len(spec["write_denied"]))] + ["C4.%d" % i for i in range(len(spec["write_allowed"]))] \
        + ["C5.%d" % i for i in range(len(spec["direct_hosts"]))] + ["C6.%d" % i for i in range(len(spec["proxy"]["denied"]))] \
        + ["C7.%d" % i for i in range(len(spec["proxy"]["allowed"]))] + ["C8.%d" % i for i in range(len(spec["read_denied"]))] \
        + (["C9.keychain", "C9.appleevent", "C9.launchservices", "C9.crontab", "C9.at", "C9.lc-submit", "C9.lc-load", "C9.lc-bootstrap"] if spec["escapes"] else []) \
        + list(REQUIRED_EXTRA_IDS)
    hr = spec.get("home_read")
    if hr:
        need += ["C10.decoy", "C10.home-list"] + ["C10.control.%d" % i for i in range(len(hr["controls"]))]
        if not hr["controls"]:
            probs.append("C10 MISSING: no re-allowed control path (a deny of the whole home with nothing re-allowed is unproven)")
    for i in need:
        if i not in got:
            probs.append("%s MISSING: the canary never reported it (crashed or not sandboxed as expected)" % i)
    if not spec["write_allowed"]:
        probs.append("C4 MISSING: no write-allowed control dir (a profile that denies everything would pass as safe)")
    if not spec.get("notes_roots"):
        probs.append("C3 FAIL: no real notes root resolved - the notes-root deny would be a vacuous pass")
    o = spec["_outside"]
    for k in ("crontab", "atq", "launchctl"):
        if after[k] != before[k]:
            added = sorted(set(after[k].splitlines()) - set(before[k].splitlines()))
            if k != "launchctl" or any(o["label"] in a for a in added):
                probs.append("C9.%s ESCAPE: scheduler state changed: %s" % (k, added[:5]))
    for d in spec["write_denied"]:
        p = os.path.join(d, ".rig-canary-" + spec["nonce"])
        if os.path.isdir(p):   # it landed: the sandbox is broken. Remove only what the canary made (an empty dir), then fail.
            os.rmdir(p)
            probs.append("C1 ESCAPE: canary dir landed in a denied place: %s (removed)" % p)
    return probs


def preflight(cmd_prefix_env, profile_path, port, write_denied, write_allowed, notes_roots, cwd, run, sandbox_exec=SANDBOX_EXEC, escapes=True, read_denied_extra=(),
              home_read=None):
    """Run the canary through wrap() with the actor's exact env; -> (problems, lines). run: the canary dir, OUTSIDE every allowed dir;
    its decoy/ subdir must be the profile's decoy (read-denied), the spec beside it stays readable."""
    nonce = secrets.token_hex(4)
    os.makedirs(run, exist_ok=True)
    spec = canary_spec(run, port, write_denied, write_allowed, notes_roots, nonce, escapes=escapes, read_denied_extra=read_denied_extra,
                       home_read=home_read)   # escapes=False only in tests that run UNsandboxed on purpose
    sp = os.path.join(run, "spec.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(spec, f)
    before = scheduler_state()
    py = shutil.which("python3", path=cmd_prefix_env.get("PATH")) or sys.executable
    try:
        p = subprocess.run(wrap([py, "-I", os.path.join(HERE, "rig_sandbox_canary.py"), sp], profile_path, sandbox_exec),
                           cwd=cwd, env=cmd_prefix_env, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
        lines, err = p.stdout.splitlines(), p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        lines, err = [], repr(e)
    time.sleep(1)
    after = scheduler_state()
    probs = judge(lines, spec, before, after)
    if spec.get("home_read") and os.path.lexists(spec["home_read"]["decoy"]):   # outside the sandbox: remove exactly the decoy we made
        os.unlink(spec["home_read"]["decoy"])
    if not lines:
        probs.insert(0, "canary produced no output (stderr: %s)" % (err or "")[:300])
    _cleanup_launchd(spec["_outside"]["label"], after)
    return probs, lines


def _cleanup_launchd(label, after):
    """If a canary job DID get registered (sandbox broken), remove exactly that job, nothing else."""
    for suffix in ("", ".submit"):
        if (label + suffix) in after.get("launchctl", ""):
            subprocess.run(["/bin/launchctl", "remove", label + suffix], capture_output=True, timeout=20)


def require(problems, lines, log_path=None, where="sandbox preflight"):
    if log_path:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"where": where, "problems": problems, "canary": lines}, f, indent=1)
    if problems:
        sys.exit("REFUSED (%s): the actor sandbox is not proven:\n  - %s" % (where, "\n  - ".join(problems)))
    print("sandbox: %s ok (%d canary checks passed)" % (where, len(lines)), flush=True)


class Sandbox:
    """One per live run: proves sandbox-exec, starts the proxy. Per case: profile() + preflight() + wrap().
    with Sandbox(workdir, protect=[V2]) as sb: ...  The proxy is stopped on exit."""

    def __init__(self, workdir, protect=(), sandbox_exec=SANDBOX_EXEC):
        self.workdir, self.protect, self.sandbox_exec = workdir, list(protect), sandbox_exec
        self.proxy = self.port = None

    def __enter__(self):
        ok, det = available(self.sandbox_exec, self.workdir)
        if not ok:
            sys.exit("REFUSED: %s. Live rig runs never run unsandboxed (Apple deprecated sandbox-exec; fix or replace the layer first)." % det)
        print("sandbox: %s" % det, flush=True)
        self.proxy, self.port = start_proxy(os.path.join(self.workdir, "proxy.jsonl"))
        print("sandbox: proxy on 127.0.0.1:%d allows only %s" % (self.port, API_HOST), flush=True)
        return self

    def __exit__(self, *a):
        stop_proxy(self.proxy)

    def case(self, name, allow_write, cwd, settings_path, write_denied, notes_roots, env, read_deny=(), home_read=None):
        """-> (wrapped-command builder, env). Writes the profile, runs the preflight, refuses the case if anything fails.
        read_deny: extra read-denied paths (student setup); the canary proves each one is refused (C8).
        home_read: student_home_read() (student setup): the real home read-denied with exact re-allows; the canary proves it (C10)."""
        prof = os.path.join(self.workdir, name + ".sb")
        protect = self.protect + [settings_path, prof]
        run = os.path.join(self.workdir, "canary-" + name)
        write_profile(profile(allow_write, cwd, self.port, protect=protect, decoy=os.path.join(run, "decoy"), read_deny=read_deny, home_read=home_read), prof)
        env = dict(env, **actor_net_env(self.port))
        probs, lines = preflight(env, prof, self.port, write_denied, allow_write, notes_roots, cwd, run, self.sandbox_exec, read_denied_extra=read_deny,
                                 home_read=home_read)
        require(probs, lines, os.path.join(self.workdir, name + ".sandbox.json"), where="case " + name)
        return (lambda cmd: wrap(cmd, prof, self.sandbox_exec)), env


def standard_write_denied(real_home_dir, notes_roots, v2_root, drive_area=None):
    """The places a canary mkdir must be refused in: the real home, the Drive mount root, the plugin's rig dir, every real notes root,
    the shared per-user claude temp dir (other sessions' scratchpads), and - for Drive cases - the test area itself and My Drive above it."""
    d = [real_home_dir, os.path.join(real_home_dir, "Library", "CloudStorage"), os.path.join(v2_root, "system", "tools", "rig"),
         "/private/tmp/claude-%d" % os.getuid()]  # allow-silence: a place the canary must be REFUSED to write in (other sessions' scratchpads), not a temp file
    d += list(notes_roots)
    if drive_area:
        d += [drive_area, os.path.dirname(drive_area)]
    return [x for x in d if os.path.isdir(x)]
