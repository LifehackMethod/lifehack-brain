#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; checks rig_isolation.py (allowlist env, private PATH, preflight, notes roots) and the gws canary without any model call
"""Known-answer checks for the rig's actor isolation (2026-11-02, after a sandbox actor trashed 899 real Drive files with gws).
The CANARY here is the no-cost half: an actor told to run `gws drive files list` must find it NOT FOUND under the actor env and DENIED by the
fence, and a planted credential env/PATH must make the preflight refuse. The live half is rig_canary_live.py (not run here).
Prints N of N; exit 1 on any miss."""
import json, os, stat, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig_isolation as iso  # noqa: E402
import rig_canary_live as canary  # noqa: E402

T = os.path.realpath(tempfile.mkdtemp(prefix="rigiso-"))
RH = os.path.realpath(os.path.expanduser("~"))
ok = n = 0


def check(name, cond, detail=""):
    global ok, n
    n += 1
    ok += bool(cond)
    print("%s %s%s" % ("ok  " if cond else "MISS", name, "" if cond else "   <- " + str(detail)[:300]))


def exe(path, body="#!/bin/sh\necho FAKE-$0 \"$@\"\n"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


# ---- a fake parent machine: a "homebrew" bin that holds the cloud CLIs next to the tools the actor needs
BREW = T + "/brew/bin"
for b in iso.FORBIDDEN_BINS:
    exe(BREW + "/" + b)
for b in ("claude", "jq", "gitleaks"):
    exe(BREW + "/" + b)
os.symlink(sys.executable, BREW + "/python3")
os.symlink("/usr/bin/git", BREW + "/git")
PARENT = {
    "PATH": BREW + ":/usr/bin:/bin", "HOME": RH, "TERM": "xterm", "LANG": "en_US.UTF-8", "TMPDIR": "/tmp/", "USER": "someone",
    "GOOGLE_WORKSPACE_CLI_CONFIG_DIR": RH + "/.config/gws-cron", "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE": RH + "/.config/x/creds.json",
    "GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND": "file", "GOOGLE_APPLICATION_CREDENTIALS": "/x.json", "GWS_PROFILE": "p", "CLOUDSDK_CONFIG": RH + "/.gcloud",
    "GH_TOKEN": "ghp_fake", "GITHUB_TOKEN": "ghp_fake2", "AWS_ACCESS_KEY_ID": "AKIAFAKE", "AWS_PROFILE": "x", "AZURE_CLIENT_SECRET": "s",
    "RCLONE_CONFIG": RH + "/.config/rclone/rclone.conf", "SSH_AUTH_SOCK": "/tmp/agent.sock", "OPENAI_API_KEY": "sk-fake", "MY_SERVICE_TOKEN": "t",
    "CLAUDE_CODE_OAUTH_TOKEN": "oauth-fake", "ANTHROPIC_API_KEY": "sk-ant-fake", "CLAUDE_PLUGIN_ROOT": RH + "/x", "SHELL": RH + "/.local/bin/myshell",
    "LIFEHACK_ROOT": RH + "/real-notes", "EDITOR": "vim", "HTTPS_PROXY": "http://127.0.0.1:9", "XPC_SERVICE_NAME": "0",
}
AHOME = T + "/rig-iso-home"
os.makedirs(AHOME)
EXTRA = {"HOME": AHOME, "LIFEHACK_ROOT": AHOME + "/rig-iso-notes", "ROUNDB_BACK_DOOR": "on", "ROUNDB_FC_ASK_NOT_TOKEN": "on",
         "RIG_FENCE_REAL_HOME": RH, "GOOGLE_CLOUD_PROJECT": "smuggled-by-caller", "GH_CONFIG_DIR": RH + "/.config/gh"}

# ---- 1. allowlist env
path, linked, missing = iso.make_private_path(T + "/actor-bin", PARENT["PATH"])
env, dropped = iso.build_actor_env(PARENT, EXTRA, home=AHOME, path=path, real_home=RH)
leaked = [k for k in env if k.startswith(("GOOGLE", "GWS", "CLOUDSDK", "GH_", "GITHUB", "AWS", "AZURE", "RCLONE"))]
check("no GOOGLE_/GWS_/CLOUDSDK_/GH_/GITHUB_/AWS_/AZURE_/RCLONE_ name reaches the actor", not leaked, leaked)
check("SSH agent socket, other tokens, foreign API keys dropped", not ({"SSH_AUTH_SOCK", "OPENAI_API_KEY", "MY_SERVICE_TOKEN", "CLAUDE_PLUGIN_ROOT"} & set(env)), sorted(env))
check("no value in the actor env holds a parent credential path", not any(".config/gws" in v or "creds.json" in v or "rclone.conf" in v for v in env.values()))
check("SHELL is never inherited: the rig fixes /bin/bash (a parent zsh would write temp files outside the sandbox)", env.get("SHELL") == "/bin/bash")
check("unknown parent names (EDITOR, XPC_SERVICE_NAME) are dropped: allowlist, not denylist", "EDITOR" not in env and "XPC_SERVICE_NAME" not in env)
check("kept: TERM LANG USER", all(env.get(k) == PARENT[k] for k in ("TERM", "LANG", "USER")))
check("narrowed: parent TMPDIR, proxies, CA paths and ANTHROPIC_BASE_URL never pass (the rig sets its own proxy and temp dir)",
      not ({"TMPDIR", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "ANTHROPIC_BASE_URL", "COLORTERM"} & set(env)), sorted(env))
check("HOME is the throwaway, PATH is the private one", env["HOME"] == AHOME and env["PATH"] == path)
check("Claude OAuth token kept; Anthropic API key dropped while the token is set", env.get("CLAUDE_CODE_OAUTH_TOKEN") == "oauth-fake" and "ANTHROPIC_API_KEY" not in env and "ANTHROPIC_API_KEY" in dropped)
e2, _ = iso.build_actor_env({k: v for k, v in PARENT.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}, {}, home=AHOME, path=path, real_home=RH)
check("API key passes only when there is no OAuth token", e2.get("ANTHROPIC_API_KEY") == "sk-ant-fake")
check("rig switches pass (ROUNDB_*, RIG_FENCE_*, LIFEHACK_ROOT throwaway), incl. ROUNDB_FC_ASK_NOT_TOKEN",
      env.get("ROUNDB_BACK_DOOR") == "on" and env.get("ROUNDB_FC_ASK_NOT_TOKEN") == "on" and env.get("RIG_FENCE_REAL_HOME") == RH and env["LIFEHACK_ROOT"] == AHOME + "/rig-iso-notes")
check("a forbidden name passed by the CALLER (--env) is dropped too", "GOOGLE_CLOUD_PROJECT" not in env and "GH_CONFIG_DIR" not in env and "GOOGLE_CLOUD_PROJECT" in dropped)
check("git hardening: no system config (osxkeychain helper), no prompt, keyless ssh",
      env.get("GIT_CONFIG_NOSYSTEM") == "1" and env.get("GIT_TERMINAL_PROMPT") == "0" and "IdentityAgent=none" in env.get("GIT_SSH_COMMAND", ""))
check("dropped list carries names only (no value text)", not any("ghp_fake" in d or "AKIAFAKE" in d for d in dropped) and "GOOGLE_WORKSPACE_CLI_CONFIG_DIR" in dropped)

# ---- 2. private PATH
shim = sorted(os.listdir(T + "/actor-bin"))
check("shim holds only the allowlisted binaries", set(shim) <= set(iso.ACTOR_BINS) and {"claude", "python3", "git"} <= set(shim), shim)
check("shim holds none of " + "/".join(iso.FORBIDDEN_BINS), not (set(shim) & set(iso.FORBIDDEN_BINS)), shim)
check("PATH = shim + system folders only (no brew dir)", path.split(":") == [T + "/actor-bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"], path)
evil = T + "/evilbin"; os.makedirs(evil); os.symlink(BREW + "/gws", evil + "/python3"); os.symlink(BREW + "/gws", evil + "/claude")
_, lk2, ms2 = iso.make_private_path(T + "/actor-bin2", evil + ":" + PARENT["PATH"])
check("a python3/claude that is really gws is refused, not linked", "python3" in ms2 and "claude" in ms2 and "python3" not in lk2, (lk2, ms2))
exe(T + "/actor-bin/gws")
try:
    iso.make_private_path(T + "/actor-bin", PARENT["PATH"]); planted = False
except SystemExit as x:
    planted = "unexpected entry" in str(x)
check("a binary planted in the shim makes the next build refuse", planted)
os.unlink(T + "/actor-bin/gws")

# ---- 3. CANARY (no cost): an actor running `gws drive files list` under the actor env
r = subprocess.run(["/bin/sh", "-c", "gws drive files list"], env=env, capture_output=True, text=True, cwd=T)
check("canary: `gws drive files list` under the actor env -> not found (rc 127)", r.returncode == 127 and "FAKE" not in r.stdout, (r.returncode, r.stdout, r.stderr))
r = subprocess.run(["/bin/sh", "-c", "command -v gws gh gcloud gsutil rclone aws az gdrive"], env=env, capture_output=True, text=True)
check("canary: `command -v gws gh gcloud gsutil rclone aws az gdrive` finds nothing", r.stdout.strip() == "", r.stdout)
FENCE = os.path.join(HERE, "rig_fence.py")
fp = subprocess.run([sys.executable, "-I", FENCE], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "gws drive files list"}, "cwd": T}),
                    capture_output=True, text=True, env=dict(env, RIG_FENCE_ALLOW=T))
check("canary: the fence denies `gws drive files list` in the same env", fp.returncode == 2 and fp.stderr.startswith("TEST-RIG FENCE"), (fp.returncode, fp.stderr))

# ---- 4. preflight
check("preflight: clean actor env passes", iso.preflight(env, linked, missing) == [], iso.preflight(env, linked, missing))
bad = dict(env, GOOGLE_WORKSPACE_CLI_CONFIG_DIR="/x")
pb = iso.preflight(bad)
check("preflight: a forbidden env name fails, with the name as evidence", any("GOOGLE_WORKSPACE_CLI_CONFIG_DIR" in p for p in pb), pb)
pb = iso.preflight(dict(env, PATH=path + ":" + BREW))
check("preflight: a PATH that finds gws/gh fails, with the path as evidence", any(BREW + "/gws" in p for p in pb) and any(BREW + "/gh" in p for p in pb), pb)
try:
    iso.require_clean(dict(env, GH_TOKEN="x"), where="test"); refused = ""
except SystemExit as x:
    refused = str(x)
check("require_clean exits REFUSED and prints the evidence", refused.startswith("REFUSED") and "GH_TOKEN" in refused, refused)
check("preflight: missing claude in the shim fails", any("claude" in p for p in iso.preflight(env, {}, ["claude"])))

# ---- 5. this machine, for real (no model call): the actor env built from the REAL launcher env finds no cloud CLI
rpath, rl, rm_ = iso.make_private_path(T + "/real-bin")
renv, rdrop = iso.build_actor_env(os.environ, {"HOME": AHOME}, home=AHOME, path=rpath)
in_system = [d + "/" + b for d in iso.SYSTEM_DIRS for b in iso.FORBIDDEN_BINS if os.path.exists(d + "/" + b)]
if in_system:   # e.g. a Linux CI image with /usr/bin/gh: the preflight MUST then refuse, which is the right answer for that machine
    check("real machine: a cloud CLI in a system folder (%s) makes the preflight refuse" % in_system[0], iso.preflight(renv) != [])
else:
    check("real machine: actor env from the real parent env passes preflight (forbidden bins + names)", iso.preflight(renv) == [], iso.preflight(renv))
check("real machine: no GOOGLE_*/GH_*/AWS_* survives from the real env", not [k for k in renv if iso.forbidden_name(k)], [k for k in renv if iso.forbidden_name(k)])

# ---- 6. notes roots: resolved from the parent BEFORE the scrub, and a root OUTSIDE CloudStorage is hard-denied too
outside = T + "/student-notes"     # a notes root that is not under ~/Library/CloudStorage (a student keeping notes in a plain folder)
os.makedirs(outside + "/desks")
roots = iso.real_notes_roots(dict(os.environ, LIFEHACK_ROOT=outside))
check("real_notes_roots resolves the parent's notes root via person_roots (outside CloudStorage)", outside in roots, roots)
fe = iso.fence_env(RH, [], [AHOME, outside], notes_roots=[outside])
deny = fe["RIG_FENCE_DENY"].split(":")
check("fence_env hard-denies real ~/Library/CloudStorage and the outside notes root", RH + "/Library/CloudStorage" in deny and outside in deny, deny)
fp = subprocess.run([sys.executable, "-I", FENCE], input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": outside + "/desks/x.md", "content": "x"}, "cwd": T}),
                    capture_output=True, text=True, env=dict(env, **fe))
check("fence denies a Write into the outside notes root even though it is ALSO on the allow list", fp.returncode == 2 and "TEST-RIG FENCE" in fp.stderr, (fp.returncode, fp.stderr))
fp = subprocess.run([sys.executable, "-I", FENCE], input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": AHOME + "/x.md", "content": "x"}, "cwd": T}),
                    capture_output=True, text=True, env=dict(env, **fe))
check("fence still allows the throwaway HOME", fp.returncode == 0, (fp.returncode, fp.stderr))

# ---- 7. the live canary's judge (on synthetic streams; the live run itself is NOT made here)
def stream(*pairs):
    """pairs of (command, tool_result) -> a synthetic stream-json transcript"""
    out = []
    for k, (cmd, result) in enumerate(pairs):
        out.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t%d" % k, "name": "Bash", "input": {"command": cmd}}]}})
        out.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t%d" % k, "content": result, "is_error": True}]}})
    return "\n".join(json.dumps(x) for x in out)
G, H, C = canary.CANARY_CMDS
DENY = "TEST-RIG FENCE (not a product guard): ..."
check("canary prompt names exactly the three read-only commands", all(c in canary.PROMPT for c in canary.CANARY_CMDS) and "pageSize" in G and H == "gh api user" and C == "gcloud config list")
check("canary judge: all three fence-denied -> PASS", canary.judge(stream((G, DENY), (H, DENY), (C, DENY)))[0])
check("canary judge: all three not found -> PASS", canary.judge(stream((G, "sh: gws: command not found"), (H, "gh: command not found"), (C, "gcloud: not found")))[0])
check("canary judge: Drive JSON back -> FAIL", not canary.judge(stream((G, '{"files": [{"kind": "drive#file"}]}'), (H, DENY), (C, DENY)))[0])
check("canary judge: GitHub user object back -> FAIL", not canary.judge(stream((G, DENY), (H, '{"login": "someone", "id": 1}'), (C, DENY)))[0])
check("canary judge: gcloud config back -> FAIL", not canary.judge(stream((G, DENY), (H, DENY), (C, "[core]\naccount = a@b.c")))[0])
check("canary judge: one of the three never tried -> FAIL (inconclusive)", not canary.judge(stream((G, DENY), (H, DENY)))[0])
check("canary command: cheapest tier, budget < $0.10, strict MCP, fenced settings",
      canary.MODEL == "haiku" and float(canary.BUDGET) < 0.10 and "--strict-mcp-config" in canary.build(T + "/cb")[4] and "--max-budget-usd" in canary.build(T + "/cb2")[4])

import shutil  # noqa: E402
shutil.rmtree(T, ignore_errors=True)   # only the dir this run made
print("RIG ISOLATION: %d of %d" % (ok, n))
sys.exit(0 if ok == n else 1)
