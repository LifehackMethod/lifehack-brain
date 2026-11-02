#!/usr/bin/env python3
# not-wired-yet: run by hand and by run-all-tests.sh; checks rig_sandbox.py (the kernel layer around live rig actors) without any model call
"""Known-answer + FAIL-FIRST checks for the rig actor sandbox (2026-11-02, record rig-actor-sandbox).
A preflight you have never watched fail proves nothing (hook-sop §4, F4). So beside the good profile passing, every deliberately broken COPY
of the profile, proxy or wrapper must make the preflight FAIL, naming the check that caught it. Broken copies only ever aim at fake dirs under
a temp root, never the real home or Drive. Tests that run unsandboxed on purpose turn the escape probes off (no Terminal pops, no launchd job).
--real-drive  also proves condition 1 on the REAL Drive mount: a write inside a fresh "Lifehack test area/<run-id>/" works, one folder up
              (the test area itself, and My Drive) is refused by the kernel. The run folder is MOVED to _archive afterwards, never deleted.
Prints N of N; exit 1 on any miss."""
import os, stat, subprocess, sys, tempfile, time

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
             allow=None, env_over=None, home_read=None):
    """Generate the real profile, apply `mutate` to a COPY, run the real preflight. -> problems list.
    home_read: the student real-home read-deny (rig-validity-fix bug 2), aimed at a FAKE home under the temp root."""
    work = mk("work", tag)
    proxy, port = sb.start_proxy(os.path.join(work, "proxy.jsonl"), allow=proxy_allow)
    try:
        run = os.path.join(work, "canary")
        kw = {"home_read": home_read} if home_read is not None else {}
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
