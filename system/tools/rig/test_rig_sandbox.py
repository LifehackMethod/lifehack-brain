#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; checks rig_sandbox.py (the kernel layer around live rig actors) without any model call
"""Known-answer + FAIL-FIRST checks for the rig actor sandbox (2026-11-02, record rig-actor-sandbox).
A preflight you have never watched fail proves nothing (hook-sop §4, F4). So beside the good profile passing, every deliberately broken COPY
of the profile, proxy or wrapper must make the preflight FAIL, naming the check that caught it. Broken copies only ever aim at fake dirs under
a temp root, never the real home or Drive. Tests that run unsandboxed on purpose turn the escape probes off (no Terminal pops, no launchd job).
--real-drive  also proves condition 1 on the REAL Drive mount: a write inside a fresh "Lifehack test area/<run-id>/" works, one folder up
              (the test area itself, and My Drive) is refused by the kernel. The run folder is MOVED to _archive afterwards, never deleted.
Prints N of N; exit 1 on any miss."""
import os, secrets, stat, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import rig_sandbox as sb  # noqa: E402
import rig_isolation as iso  # noqa: E402

_T = tempfile.TemporaryDirectory(prefix="rigsbx-")   # removed when the process exits (leaked rigsbx-* per run, 2026-11-01)
T = os.path.realpath(_T.name)
ok = n = 0


def check(name, cond, detail=""):
    global ok, n
    n += 1
    ok += bool(cond)
    print("%s %s%s" % ("ok  " if cond else "MISS", name, "" if cond else "   <- " + str(detail)[:400]))


def exe(path, body):
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    return path


def mk(*p):
    d = os.path.join(T, *p)
    os.makedirs(d, exist_ok=True)
    return d


# one fake world: allowed run dirs, fake "real" places that must stay unwritable, a fake notes root, a protected (plugin-like) dir
HOME, CASE = mk("allowed", "rig-iso-home"), mk("allowed", "case")
DENIED = [mk("fake-real-home"), mk("fake-notes-root")]
PROTECT = mk("allowed", "case", "protected-plugin")  # INSIDE the allowed case dir on purpose: only the re-deny AFTER the allow keeps it safe
NOTES = [DENIED[1]]
path, _linked, _missing = iso.make_private_path(mk("work", "actor-bin"))
ENV, _dropped = iso.build_actor_env(os.environ, {"TMPDIR": mk("allowed", "rig-iso-home", "tmp")}, home=HOME, path=path)


def run_case(tag, mutate=lambda s: s, write_denied=None, notes=None, proxy_allow=(sb.API_HOST,), sandbox_exec=sb.SANDBOX_EXEC, escapes=True,
             allow=None, env_over=None, home_read=None, blind=None):
    """Generate the real profile, apply `mutate` to a COPY, run the real preflight. -> problems list.
    home_read: the student real-home read-deny (rig-validity-fix bug 2), aimed at a FAKE home under the temp root."""
    work = mk("work", tag)
    proxy, port = sb.start_proxy(os.path.join(work, "proxy.jsonl"), allow=proxy_allow)
    try:
        run = os.path.join(work, "canary")
        kw = {"home_read": home_read} if home_read is not None else {}
        kw.update({"blind": blind} if blind is not None else {})
        text = sb.profile(allow if allow is not None else [HOME, CASE], CASE, port, protect=[PROTECT], decoy=os.path.join(run, "decoy"), **kw)
        prof = sb.write_profile(mutate(text), os.path.join(work, "actor.sb"))
        env = dict(ENV, **sb.actor_net_env(port))
        env.update(env_over or {})
        probs, _lines = sb.preflight(env, prof, port, DENIED + [PROTECT] if write_denied is None else write_denied,
                                     [HOME, CASE], NOTES if notes is None else notes, CASE, run, sandbox_exec, escapes=escapes, **kw)
        return probs
    finally:
        sb.stop_proxy(proxy)


def caught(probs, *ids):
    return bool(probs) and all(any(p.startswith(i) for p in probs) for i in ids)


def drop_line(prefix):
    return lambda s: "\n".join(l for l in s.splitlines() if not l.startswith(prefix))


def drop_block(start):
    """remove a multi-line form that starts at a line beginning with `start` and ends at the line ending its parens."""
    def f(s):
        out, skip = [], False
        for l in s.splitlines():
            if l.startswith(start):
                skip = True
            if not skip:
                out.append(l)
            elif l.rstrip().endswith("))"):
                skip = False
        return "\n".join(out)
    return f


def _move_redeny_up(s):
    lines = s.splitlines()
    red = [l for l in lines if l.startswith("(deny file-write* (subpath")]
    rest = [l for l in lines if l not in red]
    i = rest.index("(allow file-write*")
    return "\n".join(rest[:i] + red + rest[i:])


# ---- condition 2: fail closed when sandbox-exec is missing, errors, refuses, or does not enforce
good, det = sb.available()
check("available(): the real sandbox-exec enforces", good, det)
check("available(): missing binary -> NOT ok", not sb.available(os.path.join(T, "no-such-sandbox-exec"))[0])
passthru = exe(os.path.join(T, "fake-sbx-passthru"), '#!/bin/sh\nshift 2\nexec "$@"\n')        # runs the command with NO sandbox
check("available(): pass-through stub (write lands) -> NOT ok", not sb.available(passthru)[0], sb.available(passthru)[1])
refuse = exe(os.path.join(T, "fake-sbx-refuse"), "#!/bin/sh\necho 'sandbox-exec: sandbox_apply: Operation not permitted' >&2\nexit 71\n")
check("available(): refusing stub (rc 71) -> NOT ok", not sb.available(refuse)[0])
broken = exe(os.path.join(T, "fake-sbx-broken"), "#!/bin/sh\nexit 1\n")
check("available(): erroring stub -> NOT ok", not sb.available(broken)[0])
try:
    with sb.Sandbox(mk("work", "missing"), sandbox_exec=os.path.join(T, "no-such-sandbox-exec")):
        refused = False
except SystemExit as e:
    refused = "REFUSED" in str(e)
check("Sandbox(): a run with no working sandbox-exec is REFUSED before anything starts", refused)

# ---- the good profile passes (control: without it, every FAIL below could be noise)
p = run_case("good")
check("good profile: preflight passes every check", not p, p)

# ---- fail-first: each broken COPY must fail, and the right check must name it
check("broken 1: no (deny file-write*) -> C1 catches it", caught(run_case("b1", drop_line("(deny file-write* (with")), "C1"),)
check("broken 2: allow widened to the whole temp root -> C1 catches it",
      caught(run_case("b2", lambda s: s.replace("(allow file-write*", "(allow file-write* (subpath \"%s\")" % T, 1)), "C1"))
check("broken 3: plugin re-deny moved ABOVE the allow (order bug) -> C1 catches it",
      caught(run_case("b3", lambda s: _move_redeny_up(s)), "C1"))
check("broken 4: no (deny network-outbound) -> C5 catches it", caught(run_case("b4", drop_line("(deny network-outbound")), "C5"))
check("broken 5: proxy also allows www.googleapis.com -> C6 catches it",
      caught(run_case("b5", proxy_allow=(sb.API_HOST, "www.googleapis.com:443")), "C6"))
check("broken 6: no credential (deny file-read*) block -> C8 catches it (the decoy proves it on any machine)",
      caught(run_case("b6", drop_block("(deny file-read*")), "C8"))
# measured 2026-11-02: an UNFILTERED trailing (allow file-read*) does NOT re-open the filtered denies (a filtered rule outranks a bare one),
# so the realistic regression is a FILTERED allow appended after the denies:
check("broken 7: (allow file-read* (subpath \"/\")) appended at the end -> C8 catches it",
      caught(run_case("b7", lambda s: s + '\n(allow file-read* (subpath "/"))\n'), "C8"))
check("broken 8: no mach-lookup / appleevent denies -> C9 catches it",
      caught(run_case("b8", lambda s: drop_line("(deny appleevent-send")(drop_line("(deny mach-lookup")(s))), "C9"))
check("broken 9: wrap() runs the actor UNsandboxed (pass-through stub) -> C0 catches it",
      caught(run_case("b9", sandbox_exec=passthru, escapes=False), "C0"))
check("broken 10: no real notes root resolved -> C3 refuses a vacuous pass", caught(run_case("b10", notes=[]), "C3"))
check("broken 11: profile denies even the run dirs -> C4 catches it (broken-closed is not 'safe')",
      caught(run_case("b11", allow=[mk("work", "b11", "elsewhere")]), "C4"))

# ---- each layer alone (layer independence): a fake gws that tries the network and a fake Drive outside the run is stopped by the sandbox
#      even with the fence gone (the fence is a hook; this layer is not), and the same fake gws SUCCEEDS unsandboxed (the test can see a breach)
fake_drive = mk("fake-real-drive")
fake_gws = exe(os.path.join(T, "fake-gws.py"), "import os,socket,sys\nr=[]\ntry:\n os.mkdir(os.path.join(sys.argv[1],'trashed'))\n r.append('drive-write')\n"
               "except OSError: pass\ntry:\n socket.create_connection(('142.250.0.1',443),5).close()\n r.append('net')\nexcept OSError: pass\nprint(' '.join(r) or 'BLOCKED')\n")
proxy, port = sb.start_proxy(os.path.join(mk("work", "layer"), "proxy.jsonl"))
try:
    prof = sb.write_profile(sb.profile([HOME, CASE], CASE, port), os.path.join(T, "work", "layer", "a.sb"))
    sand = subprocess.run(sb.wrap([sys.executable, "-I", fake_gws, fake_drive], prof), capture_output=True, text=True, timeout=60).stdout.strip()
    bare = subprocess.run([sys.executable, "-I", fake_gws, fake_drive], capture_output=True, text=True, timeout=60).stdout.strip()
finally:
    sb.stop_proxy(proxy)
check("layer alone: sandbox ON, no fence -> fake gws can neither write the fake Drive nor reach Google directly", sand == "BLOCKED", sand)
check("layer alone: sandbox OFF -> the same fake gws writes the fake Drive (the test can see a breach)", "drive-write" in bare, bare)

# ---- the shared per-user claude temp dir: only THIS case's task dir is writable, never another session's scratchpad
tmpd = "/private/tmp/claude-%d" % os.getuid()
txt = sb.profile([HOME, CASE], CASE, 1)
check("profile: claude temp dir writable only under this case's own slug",
      ('(regex #"^%s/%s(/|$)")' % (tmpd, sb._rx(sb.case_slug(CASE)))) in txt and ('(subpath "%s")' % tmpd) not in txt)
check("standard_write_denied(): includes the shared claude temp dir and the real Drive mount root",
      tmpd in sb.standard_write_denied(sb.real_home(), [], V2) and os.path.join(sb.real_home(), "Library", "CloudStorage")
      in sb.standard_write_denied(sb.real_home(), [], V2) or not os.path.isdir(tmpd))

# ---- 2026-11-02 rig-validity-fix, BUG 1: a hook's bare `mktemp` must work inside the sandbox (C11). macOS /usr/bin/mktemp ignores $TMPDIR
#      (it asks confstr for the shared /var/folders/../T dir, which the profile never allows), so the Enver setup's copied guard hook failed
#      closed on EVERY Bash call. The canary runs a stand-in hook script the way claude runs hooks (bash <script>, the actor env) and needs
#      mktemp / mktemp -d to land inside an allowed dir.
p = run_case("c11-good")
check("C11: the good setup passes, and the canary now REQUIRES the stand-in hook mktemp check", not p and "C11.mktemp" in sb.REQUIRED_EXTRA_IDS, p)
check("FAIL-FIRST C11: actor PATH without the rig's mktemp wrapper (stock /usr/bin/mktemp) -> C11 catches it",
      caught(run_case("c11-nowrap", env_over={"PATH": ":".join(iso.SYSTEM_DIRS)}), "C11"))
check("FAIL-FIRST C11: TMPDIR outside every allowed dir -> C11 catches it",
      caught(run_case("c11-badtmp", env_over={"TMPDIR": DENIED[0]}), "C11"))

# ---- BUG 2: STUDENT profile only - the real home is read-denied (a student `find /` listed the runner's own files), with exact re-allows
#      for what the actor really needs inside it (claude's own binary + symlink chain, the plugin dir when it lives there). Proven on a FAKE
#      home: the decoy read must be EPERM (judged by errno), the home listing EPERM, every re-allow readable (control).
FH = mk("fake-user-home")
os.makedirs(os.path.join(FH, ".local", "bin"), exist_ok=True)
os.makedirs(os.path.join(FH, ".local", "share", "claude", "versions"), exist_ok=True)
exe(os.path.join(FH, ".local", "share", "claude", "versions", "9.9.9"), "#!/bin/sh\necho fake-claude\n")
if not os.path.lexists(os.path.join(FH, ".local", "bin", "claude")):
    os.symlink("../share/claude/versions/9.9.9", os.path.join(FH, ".local", "bin", "claude"))
PLUG = mk("fake-user-home", "lifehack-v2")
with open(os.path.join(PLUG, "plugin.txt"), "w", encoding="utf-8") as f:
    f.write("plugin\n")
with open(os.path.join(FH, "private.txt"), "w", encoding="utf-8") as f:
    f.write("the runner's own file\n")
HR = sb.student_home_read(FH, {"claude": os.path.join(FH, ".local", "bin", "claude"), "python3": sys.executable}, [PLUG, "/opt/nowhere-else"])
check("student_home_read: the real home is resolved at run time and denied; claude's symlink chain re-allowed as literals; the plugin dir as a subpath; nothing outside the home",
      HR["home"] == FH and set(HR["literal"]) == {os.path.join(FH, ".local", "bin", "claude"), os.path.join(FH, ".local", "share", "claude", "versions", "9.9.9")}
      and HR["subpath"] == [PLUG], HR)
check("student_home_read: real home comes from the machine when not given (never hard-coded)", sb.student_home_read(None, {}, [])["home"] == sb.real_home())
txt = sb.profile([HOME, CASE], CASE, 1, home_read=HR)
lines = txt.splitlines()
dh = [i for i, l in enumerate(lines) if l.startswith('(deny file-read* (subpath %s)' % sb._q(FH))]
check("profile: the home read-deny comes AFTER (allow default) and the write allows, the re-allows after it, the credential denies last",
      dh and dh[0] > lines.index("(allow default)") and dh[0] > lines.index("(allow file-write*") and lines[dh[0] + 1].startswith("(allow file-read*")
      and lines.index("(deny file-read*") > dh[0] + 1, txt)
check("profile: no home read-deny unless asked (the Enver setup is unchanged)", "fake-user-home" not in sb.profile([HOME, CASE], CASE, 1))
p = run_case("home-good", home_read=HR)
check("home read-deny: decoy under the home EPERM, home listing EPERM, every re-allow readable -> preflight passes", not p, p)
check("FAIL-FIRST home: no home read-deny line -> C10 catches the readable decoy",
      caught(run_case("home-nodeny", drop_line('(deny file-read* (subpath %s)' % sb._q(FH)), home_read=HR), "C10"))
check("FAIL-FIRST home: the whole home re-allowed after the deny -> C10 catches it",
      caught(run_case("home-reopen", lambda s: s.replace("(allow file-read*", "(allow file-read* (subpath %s)" % sb._q(FH), 1), home_read=HR), "C10"))
check("FAIL-FIRST home: re-allows dropped (claude's binary would be unreadable) -> the C10 control catches it",
      caught(run_case("home-noallow", drop_line("(allow file-read*"), home_read=HR), "C10"))

# ---- this machine (zero spend): under the real-home read-deny, the REAL claude binary still starts through the actor shim, and without the
#      re-allows it would not (so the re-allows are needed, not decoration)
_rp, _rl, _rm = iso.make_private_path(mk("work", "real-shim"))
_rhr = sb.student_home_read(None, _rl, [V2])
if _rl.get("claude") and _rhr["literal"]:
    def _ver(hr):
        prof = sb.write_profile(sb.profile([HOME, CASE], CASE, 1, home_read=hr), os.path.join(T, "work", "real-shim.sb"))
        q = subprocess.run(sb.wrap(["claude", "--version"], prof), env=dict(ENV, PATH=_rp, HOME=HOME), capture_output=True, text=True, timeout=60)
        return q.returncode, (q.stdout + q.stderr).strip()[:200]
    rc_ok, out_ok = _ver(_rhr)
    check("real machine: `claude --version` runs under the real-home read-deny with the re-allows", rc_ok == 0 and "Claude Code" in out_ok, (rc_ok, out_ok))
    rc_no, out_no = _ver(dict(_rhr, literal=[], subpath=[]))
    check("FAIL-FIRST real machine: the same deny WITHOUT the re-allows stops claude (the re-allows are load-bearing)", rc_no != 0, (rc_no, out_no))
else:
    print("skip real-machine claude check (claude not under the real home here)")

# ---- 2026-11-02 rig-honest-exit: claude's Bash tool ends every command with `pwd -P >| /tmp/claude-XXXX-cwd`. Denied, every Bash result said
#      "Exit code 1" even when the command worked (real machine: exit 0), so exit codes in the exam were not honest. The allowance is ONE file
#      shape, regular files only, three operations only; the per-run temp dir is TMPDIR inside the throwaway HOME and needs no rule of its own.
CWD_RX = '(regex #"^/private/tmp/claude-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-cwd$")'
HEXNAME = "/tmp/claude-%s-cwd" % secrets.token_hex(2)  # allow-silence: the exact name shape claude's Bash tool writes; the probes below remove what lands


def in_profile(tag, code, *args, mutate=lambda s: s, protect=(PROTECT,), cwd=None):
    """Run python `code` under the real profile text (mutated copy if asked). -> stdout. Exit status is printed by the code itself."""
    work = mk("work", tag)
    prof = sb.write_profile(mutate(sb.profile([HOME, CASE], CASE, 1, protect=list(protect))), os.path.join(work, "p.sb"))
    q = subprocess.run(sb.wrap([sys.executable, "-I", "-c", code] + list(args), prof), cwd=cwd or CASE, env=ENV, capture_output=True, text=True, timeout=60)
    return q.stdout.strip() + q.stderr.strip()[-200:]


ERRNO = ("import errno,os,sys\ndef t(fn):\n try:\n  fn()\n  print('ALLOWED')\n except OSError as e:\n  print(errno.errorcode.get(e.errno))\n")
CREATE = ERRNO + ("def c():\n open(sys.argv[1],'w').close()\n os.unlink(sys.argv[1])\nt(c)\n")
CLOBBER = ("import subprocess,sys,os\nr=subprocess.run(['/bin/bash','--noprofile','--norc','-c','pwd -P >| \"%s\"' % sys.argv[1]],capture_output=True,text=True)\n"
           "print('rc=%d' % r.returncode, r.stderr.strip()[:120])\nif r.returncode==0:\n print('read=' + open(sys.argv[1]).read().strip())\n os.unlink(sys.argv[1])\n print('gone=%s' % (not os.path.lexists(sys.argv[1])))\n")
out = in_profile("cwd-clobber", CLOBBER, HEXNAME)
check("cwd file: claude's own `pwd -P >| /tmp/claude-XXXX-cwd`, the read back and the unlink all work under the real profile",
      "rc=0" in out and ("read=" + CASE) in out and "gone=True" in out, out)
out = in_profile("cwd-tmpdir", "import tempfile,os\nfd,p=tempfile.mkstemp()\nos.write(fd,b'x')\nos.close(fd)\nprint(p)\nos.unlink(p)\n")
check("per-run temp dir: python tempfile follows TMPDIR into the throwaway HOME and writes there", out.startswith(ENV["TMPDIR"] + os.sep), out)
for name in ("/tmp/rig-plain-" + secrets.token_hex(3), "/private/tmp/rig-plain-" + secrets.token_hex(3), "/tmp/claude-other-cwd", "/tmp/claude-abc-cwd", "/tmp/claude-abcde-cwd",
             "/tmp/claude-zzzz-cwd", "/tmp/claude-ab12-cwd.x", "/tmp/xclaude-ab12-cwd", "/var/tmp/claude-ab12-cwd", "/private/tmp/claude-%d/claude-ab12-cwd" % os.getuid()):  # allow-silence: names the sandbox must REFUSE; nothing lands
    out = in_profile("cwd-wide", CREATE, name)
    check("still denied: %s -> EPERM" % name, out == "EPERM", out)
for label, code in (("a directory", "os.mkdir(sys.argv[1]); os.rmdir(sys.argv[1])"), ("a symlink", "os.symlink('/private/etc/hosts', sys.argv[1]); os.unlink(sys.argv[1])"),
                    ("a fifo", "os.mkfifo(sys.argv[1]); os.unlink(sys.argv[1])")):
    out = in_profile("cwd-kind", ERRNO + "def f():\n " + code.replace("; ", "\n ") + "\nt(f)\n", "/tmp/claude-%s-cwd" % secrets.token_hex(2))  # allow-silence: must be REFUSED, and the probe unlinks it if a broken profile lets it land
    check("cwd name, regular files only: %s at that name -> EPERM" % label, out == "EPERM", out)
own = "/tmp/claude-%s-cwd" % secrets.token_hex(2)  # allow-silence: the probe's own file, unlinked in the same breath
out = in_profile("cwd-ops", ERRNO + "open(sys.argv[1],'w').close()\nt(lambda: os.chmod(sys.argv[1],0o666))\nos.unlink(sys.argv[1])\n", own)
check("cwd file, three operations only: chmod on it -> EPERM", out == "EPERM", out)
victim = os.path.join(mk("cwd-victim"), "write-denied-file")
with open(victim, "w", encoding="utf-8") as f:
    f.write("original\n")
out = in_profile("cwd-link", ERRNO + "t(lambda: os.link(sys.argv[1],sys.argv[2]))\n", victim, "/tmp/claude-%s-cwd" % secrets.token_hex(2))  # allow-silence: must be REFUSED
check("cwd name: a hard link from a write-denied file onto it -> EPERM (no write door by inode)", out == "EPERM" and open(victim, encoding="utf-8").read() == "original\n", out)
target = os.path.join(mk("cwd-victim"), "must-stay-absent")
planted = "/private/tmp/claude-%s-cwd" % secrets.token_hex(2)  # allow-silence: symlink made and removed by this test, proves writes resolve to the target
os.symlink(target, planted)
try:
    out = in_profile("cwd-through", ERRNO + "t(lambda: open(sys.argv[1],'w').close())\n", planted)
finally:
    os.unlink(planted)
check("cwd name: a symlink already planted there -> writing through it is EPERM, the kernel judges the target", out == "EPERM" and not os.path.lexists(target), out)
# ORDER, the marked trap, measured: the rule names its operations, and that outranks ANY (deny file-write* ...), even one written after it. So no re-deny can
# narrow these names, and profile() refuses a protect path they could fall under rather than let a re-deny look as if it worked.
PNAME = "/private/tmp/claude-%s-cwd" % secrets.token_hex(2)  # allow-silence: a name this test tries to re-deny; the probe unlinks what lands
_later_deny = lambda s: s + '\n(deny file-write* (subpath "%s"))\n' % PNAME
out = in_profile("cwd-order", CREATE, PNAME, mutate=_later_deny)
check("order, measured: a later (deny file-write* (subpath NAME)) does NOT beat the cwd rule (why profile() refuses it)", out == "ALLOWED" and CWD_RX in sb.profile([HOME], CASE, 1), out)
out = in_profile("cwd-order2", CREATE, PNAME, mutate=lambda s: s + '\n(deny file-write-create (subpath "%s"))\n' % PNAME)
check("order, control: the same deny naming file-write-create does beat it (the probe can see a deny)", out == "EPERM", out)


def _refuses(protect):
    try:
        sb.profile([HOME], CASE, 1, protect=protect)
        return False
    except ValueError as e:
        return "REFUSED" in str(e)


check("profile() refuses a protect path that IS a cwd name", _refuses([PNAME]))
check("profile() refuses a protect path a cwd name lives under (/private/tmp)", _refuses([PROTECT, "/private/tmp"]))
check("profile() takes an ordinary protect path, one that only looks close", not _refuses([PROTECT, "/private/tmp/claude-other-cwd", "/private/tmp/claude-%d" % os.getuid()]))  # allow-silence: text compared only
out = in_profile("cwd-protect", CREATE, os.path.join(PROTECT, "x"))
check("protect still holds under the new rule: a file in the re-denied plugin dir -> EPERM", out == "EPERM", out)

# the planted symlink lives only for one canary run: a leftover in the shared /private/tmp could catch a real session's own cwd write (found live: a direct
# canary_spec caller left one behind). So building a spec plants nothing, and a full preflight leaves none of its names behind.
_spec = sb.canary_spec(mk("work", "cwd-spec"), 1, [], [CASE], ["/x"], "aabbccdd", escapes=False)
_planted = _spec.get("cwd_file", {}).get("planted")
check("canary_spec only names the planted symlink, it does not make it", _planted and not os.path.lexists(_planted), _planted)
if _planted and os.path.islink(_planted):
    os.unlink(_planted)   # a spec that really planted it must not leave it behind


def _cwd_names():
    return {n for n in os.listdir("/private/tmp") if n.startswith("claude-") and n.endswith("-cwd")}  # allow-silence: lists the shared temp dir to prove the preflight leaves nothing


_before_names = _cwd_names()
p = run_case("cwd-litter")
_left = [n for n in _cwd_names() - _before_names if os.path.islink(os.path.join("/private/tmp", n))]  # allow-silence: reads the listing above
check("preflight leaves no symlink at a cwd name behind", not p and not _left, (p, _left))

# the preflight itself must now carry these checks, and each widened COPY of the profile must make it FAIL by name
p = run_case("cwd-good")
check("preflight: the good profile passes with the C12 and C13 checks required", not p and "C12.write" in sb.REQUIRED_EXTRA_IDS and "C13.tmpdir" in sb.REQUIRED_EXTRA_IDS, p)
_widen = lambda new: (lambda s: s.replace(CWD_RX, new) if CWD_RX in s else s)
check("FAIL-FIRST C12: the cwd rule dropped -> C12.write catches it", caught(run_case("cwd-b1", lambda s: "\n".join(l for l in s.splitlines() if CWD_RX not in l)), "C12.write"))
check("FAIL-FIRST C12: all of /private/tmp opened -> C12.wider catches it",
      caught(run_case("cwd-b2", _widen('(subpath "/private/tmp")')), "C12.wider"))
check("FAIL-FIRST C12: the name's tail left open (claude-XXXX-cwd*) -> C12.wider catches it",
      caught(run_case("cwd-b3", _widen('(regex #"^/private/tmp/claude-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-cwd")')), "C12.wider"))
check("FAIL-FIRST C12: any name between claude- and -cwd -> C12.wider catches it",
      caught(run_case("cwd-b4", _widen('(regex #"^/private/tmp/claude-.*-cwd$")')), "C12.wider"))
check("FAIL-FIRST C12: the regular-file filter removed -> C12.symlink catches it",
      caught(run_case("cwd-b5", lambda s: s.replace("(require-all %s (vnode-type REGULAR-FILE))" % CWD_RX, CWD_RX)), "C12.symlink", "C12.mkdir", "C12.fifo"))
check("FAIL-FIRST C12: every write operation instead of the three -> C12.chmod catches it",
      caught(run_case("cwd-b6", lambda s: s.replace("(allow file-write-create file-write-data file-write-unlink ", "(allow file-write* ")), "C12.chmod"))
check("FAIL-FIRST C13: TMPDIR outside every allowed dir -> C13 catches it", caught(run_case("cwd-b7", env_over={"TMPDIR": DENIED[0]}), "C13"))
check("FAIL-FIRST C13: TMPDIR under an allowed dir but missing on disk -> C13 catches it",
      caught(run_case("cwd-b8", env_over={"TMPDIR": os.path.join(HOME, "tmp-never-made")}), "C13"))


# ---- rig-blind-runs (2026-11-03): a session reads its own run dirs and no other run or test artifact, through the real Sandbox.case entry
import shutil  # noqa: E402
import rig_config_isolation as ci  # noqa: E402
FS = mk("fake-shared")
FR = mk("fake-shared", "lifehack-rig")
BNEIGH = mk("fake-shared", "rep-b07-tmp")
BH, BC, BSIB = mk("fake-shared", "lifehack-rig", "this-run", "rig-iso-home"), mk("fake-shared", "lifehack-rig", "this-run", "work", "case"), mk("fake-shared", "lifehack-rig", "other-run", "u1")
BWORK = mk("work")
os.makedirs(os.path.join(BH, "tmp"), exist_ok=True)
for q in (os.path.join(BSIB, "stream.jsonl"), os.path.join(BC, "own.txt")):
    open(q, "w", encoding="utf-8").close()
BTASKS = "/private/tmp/claude-%d" % os.getuid()  # allow-silence: claude's per-uid task dir; the other-session folder below is made and removed by this test
BTSIB = os.path.join(BTASKS, "-Users-someone-else-rigsbx-test-" + secrets.token_hex(3))
os.makedirs(BTSIB, exist_ok=True)
BUT = os.path.realpath(subprocess.check_output(["/usr/bin/getconf", "DARWIN_USER_TEMP_DIR"], text=True).strip())
_keep_root, ci.RIG_ROOT = ci.RIG_ROOT, FR
try:
    with sb.Sandbox(BWORK, protect=[]) as _s:
        _w, _e = _s.case("blind", [BH, BC], BC, os.path.join(T, "no-settings.json"), DENIED, NOTES, dict(ENV, TMPDIR=os.path.join(BH, "tmp")))
        _rc = lambda *c: subprocess.run(_w(list(c)), cwd=BC, env=_e, capture_output=True, text=True, timeout=30)
        for _name, _cmd in (("a sibling run's file", ("/bin/cat", os.path.join(BSIB, "stream.jsonl"))), ("a sibling run's folder", ("/bin/ls", BSIB)), ("the rig root listing", ("/bin/ls", FR)),
                            ("the rig root's parent listing", ("/bin/ls", FS)), ("a neighbour of the rig root", ("/bin/ls", BNEIGH)), ("another session's task dir", ("/bin/ls", BTSIB)),
                            ("the per-uid task dir listing", ("/bin/ls", BTASKS)), ("the shared temp dir listing", ("/bin/ls", "/private/tmp")), ("the per-user temp dir listing", ("/bin/ls", BUT))):  # allow-silence: read probes only
            check("blind: %s is refused" % _name, "not permitted" in _rc(*_cmd).stderr)
        _f = _rc("/usr/bin/find", FS, BTASKS, "/private/tmp", BUT)  # allow-silence: read probe only
        _ft = _f.stdout + _f.stderr
        check("blind: find names no other run", not any(x in _ft for x in ("other-run", "rep-b07-tmp", "lifehack-rig/this-run", os.path.basename(BTSIB))), _ft[:400])
        check("blind: this run's own folder still reads (control)", _rc("/bin/cat", os.path.join(BC, "own.txt")).returncode == 0)
        check("blind: the rig root still stats, so mkdir -p and realpath work from the run folder (control)", _rc("/usr/bin/stat", FR).returncode == 0)
        check("blind: mkdir -p inside the run folder works (control)", _rc("/bin/mkdir", "-p", os.path.join(BC, "x", "y")).returncode == 0)
        _g = _rc("/usr/bin/git", "--version")
        check("blind: /usr/bin/git prints no xcrun cache error (control)", _g.returncode == 0 and "cache file" not in _g.stderr, _g.stderr[:200])
        check("blind: claude gets its own temp dir, or it dies at startup on the refused per-uid dir", _e.get("CLAUDE_CODE_TMPDIR") == os.path.join(BH, "tmp"), _e.get("CLAUDE_CODE_TMPDIR"))
        check("blind: a here-doc through bash still works (control)", _rc("/bin/bash", "--noprofile", "--norc", "-c", "cat <<E\nhi\nE\n").stdout.strip() == "hi")
except SystemExit as x:
    check("blind: the real Sandbox.case preflight passes with the rule on", False, x)
finally:
    ci.RIG_ROOT = _keep_root
    shutil.rmtree(BTSIB, ignore_errors=True)
BL = sb.blind_read([BH, BC, HOME, CASE, BWORK], FR) if hasattr(sb, "blind_read") else None
check("blind_read: a dir under the rig root counts as its top folder there, once; a dir outside the root stays itself",
      bool(BL) and os.path.join(FR, "this-run") in BL["own"] and BH not in BL["own"] and BC not in BL["own"] and CASE in BL["own"], BL)
_bk = {"blind": BL}
_good = run_case("blind-good", **_bk) if BL else ["no blind_read"]
check("blind: the canary passes on the good profile", not _good, _good)
_unsub = lambda p: (lambda s: s.replace("(subpath %s)" % sb._q(p), '(subpath "/nonexistent-rig")'))
if BL:
    # the fake parent sits inside the real per-user temp dir, so that deny must go too or it still covers the fake tree; the text check pins the parent's own deny
    check("blind: the deny line names the rig root's parent, the shared temp dir and the per-user temp dir", all("(subpath %s)" % sb._q(q) in next(l for l in sb.profile([HOME], CASE, 1, blind=BL).splitlines() if l.startswith("(deny file-read* (subpath")) for q in (FS, "/private/tmp", BUT)))  # allow-silence: text check, nothing is written
    for _tag, _mut, _name in (("noshared", lambda s: _unsub(FS)(_unsub(BUT)(s)), "no deny on the rig root's parent or the temp dir around the fake tree"), ("noown", _unsub(os.path.join(FR, "this-run")), "own folder not re-allowed"),
                              ("notmp", _unsub("/private/tmp"), "the shared temp dir left readable"), ("noutmp", _unsub(BUT), "the per-user temp dir left readable")):  # allow-silence: a profile mutation, nothing is written
        check("FAIL-FIRST blind: %s -> C14 catches it" % _name, caught(run_case("blind-" + _tag, _mut, **_bk), "C14"))
_lf = open(os.path.join(HERE, "rig_live_free.py"), encoding="utf-8").read()
check("rig_live_free: the real home is read-denied in every setup, not only the student's", "student_home_read(None, linked" in _lf and 'else [])} if student_home else {}' not in _lf)
_pr = sb.student_home_read(None, {}, [])["probe_denied"]
check("student_home_read: ~/worktrees, ~/rig-exam-scratch and CloudStorage go to the canary when present", all(p.startswith(sb.real_home() + os.sep) for p in _pr) and len(_pr) >= 1, _pr)


# ---- condition 1 on a fake Drive tree (always) and on the REAL mount (--real-drive)
area = mk("fake-mydrive", "Lifehack test area")
runf = mk("fake-mydrive", "Lifehack test area", "run-x")
p = run_case("drive-fake", allow=[HOME, CASE, runf], write_denied=DENIED + [area, os.path.dirname(area)])
check("drive (fake tree): write inside the run folder ok; the test area itself and My Drive above it are refused", not p, p)


if "--real-drive" in sys.argv[1:]:
    import rig_drive
    real_area = rig_drive.area()
    if not real_area or not os.path.isdir(real_area):
        check("real drive: the Lifehack test area exists on this machine", False, real_area)
    else:
        rid = "sbx-cond1-%s" % time.strftime("%Y%m%d-%H%M%S")
        real_run = os.path.join(real_area, rid)
        os.mkdir(real_run)
        try:
            p = run_case("drive-real", allow=[HOME, CASE, real_run], write_denied=DENIED + [real_area, os.path.dirname(real_area)], escapes=False)
            check("REAL drive: write inside 'Lifehack test area/%s/' ok; the test area and My Drive are refused by the kernel" % rid, not p, p)
        finally:
            arch = os.path.join(real_area, "_archive")
            os.makedirs(arch, exist_ok=True)
            os.rename(real_run, os.path.join(arch, rid))   # moved, never deleted

print("\n%d of %d" % (ok, n))
sys.exit(0 if ok == n else 1)
