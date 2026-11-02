#!/usr/bin/env python3
# rig-only: imported by rig_live_free.py; never part of the product hooks
"""rig_config_isolation.py - keep the rig runner's OWN Claude config out of rig actor sessions (2026-11-02, record rig-config-isolation).

WHY: the pinned re-run 2 found every session (Enver AND student setup) loading the runner's personal skills and agents, and the student
     setup running the runner's private SessionStart hooks. A dead-network probe settled the mechanism: Claude Code walks UP from the cwd and
     loads every ancestor's .claude/CLAUDE.md, .claude/skills and .claude/agents. The rig's scratch dirs and throwaway HOME lived under the
     real home, so the walk reached the real ~/.claude. A throwaway HOME and CLAUDE_CONFIG_DIR do not stop it; a cwd outside the home does,
     and so does a kernel read-deny (rig_sandbox.personal_config_paths). The private hooks came from the lab settings file itself.
WHAT:
  RIG_ROOT / check_rig_dir()  every rig dir lives under a shared path OUTSIDE the real home (no tmp/scratch/scratchpad segment, not under
                              /tmp, /private or /var), and must be writable.
  personal_names()            the names of the runner's own skills, agents and commands, read from the real home at run time (no name is
                              written in this file).
  findings()                  -> list of problems: a personal skill/agent/command in the init event, a memory path or loaded instructions
                              file outside the run's own dirs, a hook whose output names a personal skill folder or the real home, a
                              settings file that runs hooks from a personal skill folder. Empty = clean.
  probe()                     runs the exact actor command with the network cut (proxy pointed at a dead port the sandbox also refuses) and
                              an InstructionsLoaded logger, so the config a session WOULD load is seen before any money is spent.
"""
import json, os, re, subprocess, time

RIG_ROOT = "/Users/Shared/lifehack-rig"   # the macOS Shared folder: outside every user's home, writable by every user; Claude Code's
                                           # walk-up from here reaches only /Users/Shared and /Users, never a user's own .claude
BAD_SEGMENTS = ("tmp", "scratch", "scratchpad")
BAD_PREFIXES = ("/tmp", "/private", "/var")
DEAD_PORT = 1   # nothing listens on localhost:1 and the actor sandbox only opens the proxy port: no request can leave


def _under(p, root):
    p, root = os.path.realpath(p), os.path.realpath(root)
    return p == root or p.startswith(root.rstrip(os.sep) + os.sep)


def rig_dir_problems(path, real_home):
    """-> list of reasons `path` is not an acceptable rig dir (empty = ok). Pure: does not touch the disk beyond realpath."""
    rp = os.path.realpath(path)
    probs = []
    if _under(rp, real_home):
        probs.append("under the real home %s (Claude Code's cwd walk-up would load its .claude)" % real_home)
    for b in BAD_PREFIXES:
        if _under(rp, b) or _under(os.path.abspath(path), b):
            probs.append("under %s" % b)
    segs = [s.lower() for s in rp.split(os.sep) + os.path.abspath(path).split(os.sep)]
    for s in BAD_SEGMENTS:
        if s in segs:
            probs.append("has a '%s' path segment" % s)
    return probs


def check_rig_dir(path, real_home):
    """Make `path`, prove it is writable and outside the real home; SystemExit (REFUSED) otherwise. -> realpath."""
    probs = rig_dir_problems(path, real_home)
    if probs:
        raise SystemExit("REFUSED: rig dir %s is not allowed: %s" % (path, "; ".join(probs)))
    try:
        os.makedirs(path, exist_ok=True)
        t = os.path.join(path, ".rig-write-check")
        with open(t, "w", encoding="utf-8") as f:
            f.write("ok\n")
        os.unlink(t)
    except OSError as e:
        raise SystemExit("REFUSED: rig dir %s is not writable: %s" % (path, e))
    return os.path.realpath(path)


def _frontmatter_name(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            head = f.read(2000)
    except OSError:
        return None
    m = re.search(r"^name:\s*['\"]?([^'\"\n]+)", head, re.M)
    return m.group(1).strip() if m else None


def personal_names(real_home):
    """-> {"skills": set, "agents": set, "skill_dirs": set}: the runner's own skills/commands/agents (folder/file names AND frontmatter names)."""
    c = os.path.join(real_home, ".claude")
    out = {"skills": set(), "agents": set(), "skill_dirs": set()}
    sk = os.path.join(c, "skills")
    for n in (os.listdir(sk) if os.path.isdir(sk) else []):
        out["skill_dirs"].add(n)
        out["skills"].add(n)
        nm = _frontmatter_name(os.path.join(sk, n, "SKILL.md"))
        if nm:
            out["skills"].add(nm)
    cm = os.path.join(c, "commands")
    for dp, _, fs in (os.walk(cm) if os.path.isdir(cm) else []):
        out["skills"].update(f[:-3] for f in fs if f.endswith(".md"))
    ag = os.path.join(c, "agents")
    for f in (os.listdir(ag) if os.path.isdir(ag) else []):
        if f.endswith(".md"):
            out["agents"].add(f[:-3])
            nm = _frontmatter_name(os.path.join(ag, f))
            if nm:
                out["agents"].add(nm)
    return out


def read_events(stream_path):
    """-> (init event or None, [hook events], ) from a stream-json file."""
    init, hooks = None, []
    try:
        lines = open(stream_path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return None, []
    for ln in lines:
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        if e.get("type") == "system" and e.get("subtype") == "init" and init is None:
            init = e
        elif str(e.get("subtype", "")).startswith("hook_"):
            hooks.append(e)
    return init, hooks


def findings(init, hooks, instructions, settings_text, real_home, allowed_roots, names=None):
    """-> list of problems (empty = no personal config loaded). allowed_roots: the run's own dirs plus the plugin root; an instructions file or
    memory path outside them is a problem, wherever it is. init None is a problem (nothing proves what loaded)."""
    names = names or personal_names(real_home)
    probs = []
    if init is None:
        return ["no init event: the loaded config cannot be checked"]
    ok = lambda p: any(_under(p, r) for r in allowed_roots)
    for s in init.get("skills", []) + init.get("slash_commands", []):
        if ":" not in s and s in names["skills"]:
            probs.append("personal skill/command loaded: %s" % s)
    for a in init.get("agents", []):
        if ":" not in a and a in names["agents"]:
            probs.append("personal agent loaded: %s" % a)
    for k, p in (init.get("memory_paths") or {}).items():
        if p and not ok(p):
            probs.append("memory path outside the run dirs (%s): %s" % (k, p))
    for p in instructions:
        if p and not ok(p):
            probs.append("instructions file outside the run dirs loaded: %s" % p)
    skill_dir_re = re.compile(r"\.claude/skills/(%s)(/|\b)" % "|".join(re.escape(d) for d in sorted(names["skill_dirs"]))) if names["skill_dirs"] else None
    rh = os.path.realpath(real_home)

    def scrub(t):
        for r in sorted(allowed_roots, key=len, reverse=True):
            t = t.replace(os.path.realpath(r), "<run>")
        return t
    seen = set()
    for h in hooks:
        txt = scrub(" ".join(str(h.get(k) or "") for k in ("stdout", "stderr", "output")))
        why = None
        if skill_dir_re and skill_dir_re.search(txt):
            why = "names a personal skill folder"
        elif rh + os.sep in txt:
            why = "names the real home"
        if why and (h.get("hook_name"), why) not in seen:
            seen.add((h.get("hook_name"), why))
            probs.append("hook %s %s: %s" % (h.get("hook_name"), why, txt.strip()[:160]))
    st = scrub(settings_text or "")
    if skill_dir_re and skill_dir_re.search(st):
        probs.append("settings file runs something from a personal skill folder")
    if rh + os.sep in st:
        probs.append("settings file names the real home")
    return probs


def il_settings(base_settings_path, out_path, log_path):
    """A copy of the case settings with an InstructionsLoaded hook that appends each payload to log_path."""
    d = json.load(open(base_settings_path, encoding="utf-8")) if base_settings_path else {}
    d.setdefault("hooks", {}).setdefault("InstructionsLoaded", []).append(
        {"hooks": [{"type": "command", "command": "cat >> '%s'; echo >> '%s'" % (log_path, log_path)}]})
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(d, f)
    return out_path


def dead_net_env(env):
    u = "http://127.0.0.1:%d" % DEAD_PORT
    return dict(env, HTTPS_PROXY=u, HTTP_PROXY=u, https_proxy=u, http_proxy=u)


def probe(cmd, cwd, env, stream_path, il_log, timeout=40):
    """Run `cmd` (already wrapped in the actor sandbox; its env must come from dead_net_env) until the init event and a few seconds of hook
    output are in, then stop it. -> (init, hooks, instruction file paths). No API request can be made: the network is cut."""
    with open(stream_path, "w", encoding="utf-8") as f:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        t0, seen_init = time.time(), None
        while time.time() - t0 < timeout and p.poll() is None:
            time.sleep(1)
            if seen_init is None and '"subtype":"init"' in open(stream_path, encoding="utf-8", errors="replace").read():
                seen_init = time.time()
            if seen_init and time.time() - seen_init > 4:
                break
        if p.poll() is None:
            p.kill()
            p.wait()
    init, hooks = read_events(stream_path)
    paths = []
    if os.path.exists(il_log):
        for ln in open(il_log, encoding="utf-8", errors="replace"):
            try:
                paths.append(json.loads(ln).get("file_path"))
            except ValueError:
                continue
    return init, hooks, [p for p in paths if p]
