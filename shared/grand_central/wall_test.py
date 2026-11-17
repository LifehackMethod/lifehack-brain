"""wall_test.py — plan step 1.2, the part that can run from a guarded session.

Proves, against Google itself, using only the rig login and only through the sanctioned doors:
  allowed:   labels list, threads list, an envelope (format=metadata), calendar events, task lists/tasks
  forbidden: full email (format=full), raw email (format=raw), a search (q=...)
The forbidden send / label-change / calendar-create / task-create attempts are blocked by YOLO's guards before
they reach Google from a session, so they live in wall_test_terminal.sh, which the owner runs once in Terminal.

Records field NAMES only, never content. A forbidden call that succeeds is a STOP (exit 2).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_env  # noqa: E402

results = []


def record(name, expect, ok, detail):
    passed = (ok and expect == "allow") or ((not ok) and expect == "forbid")
    results.append({"call": name, "expected": expect, "google_allowed": ok, "pass": passed, "detail": detail})


def main():
    rig_env.apply_to_this_process()
    sys.path.insert(0, rig_env.EMAIL_DOOR_DIR)
    import email_fetch  # noqa: E402  (the sanctioned email door)


    # 0. Which login is actually in force? (same environment the doors will inherit)
    st = subprocess.run(["gws", "auth", "status"], capture_output=True, text=True, env=os.environ.copy())
    raw = st.stdout[st.stdout.find("{"):] if "{" in st.stdout else "{}"
    status = json.loads(raw)
    scopes = set(status.get("scopes", []))
    login_ok = (scopes - rig_env.IDENTITY_SCOPES) == rig_env.EXPECTED_DATA_SCOPES
    login = {"user": status.get("user"), "config_dir": os.environ.get("GOOGLE_WORKSPACE_CLI_CONFIG_DIR"),
             "credential_source": status.get("credential_source"), "data_scopes": sorted(scopes - rig_env.IDENTITY_SCOPES),
             "exactly_expected": login_ok}
    if not login_ok:
        print(json.dumps({"STOP": "rig login is not exactly the five expected data scopes (rig_env.EXPECTED_DATA_SCOPES)", "login": login}, indent=2))
        return 2

    # 1. allowed: labels
    data, err = email_fetch.labels_list()
    record("labels.list", "allow", err is None, {"label_count": len((data or {}).get("labels", []))} if not err else err)

    # 2. allowed: list threads (no query)
    data, err = email_fetch.list_threads({"maxResults": 3})
    tid = ((data or {}).get("threads") or [{}])[0].get("id")
    record("threads.list", "allow", err is None and bool(tid), {"got_a_thread": bool(tid)} if not err else err)

    # 3. allowed: an envelope — record exactly which fields come back
    if tid:
        data, err = email_fetch.get_thread(tid, "metadata")
        fields = {}
        if not err:
            msg = (data.get("messages") or [{}])[0]
            fields = {
                "thread_keys": sorted(data.keys()),
                "message_keys": sorted(msg.keys()),
                "payload_keys": sorted((msg.get("payload") or {}).keys()),
                "header_names": sorted({h.get("name") for h in (msg.get("payload") or {}).get("headers", [])}),
                "has_snippet_text": bool(msg.get("snippet")),
                "has_body_data": bool(((msg.get("payload") or {}).get("body") or {}).get("data")),
                "has_parts": bool((msg.get("payload") or {}).get("parts")),
                "has_sizeEstimate": "sizeEstimate" in msg,
            }
        record("threads.get format=metadata", "allow", err is None, fields if not err else err)

        # 4. forbidden: full and raw
        data, err = email_fetch.get_thread(tid, "full")
        record("threads.get format=full", "forbid", err is None, "GOOGLE RETURNED IT" if not err else err)
        data, err = email_fetch.get_thread(tid, "raw")
        record("threads.get format=raw", "forbid", err is None, "GOOGLE RETURNED IT" if not err else err)

    # 5. forbidden: search
    data, err = email_fetch.list_threads({"q": "from:me", "maxResults": 1})
    record("threads.list with q (search)", "forbid", err is None, "GOOGLE RETURNED IT" if not err else err)

    # 6. allowed: calendar events through safe_calendar (isolate mode: structure only)
    cal_run = subprocess.run([sys.executable, rig_env.SAFE_CALENDAR, json.dumps({"calendarId": "primary", "maxResults": 3})],
                         capture_output=True, text=True, env=os.environ.copy(), timeout=120)
    record("calendar.events.list via safe_calendar", "allow", cal_run.returncode == 0,
           {"rc": cal_run.returncode} if cal_run.returncode == 0 else (cal_run.stderr.strip().splitlines() or ["?"])[-1][:300])

    # 7. allowed: task lists (raw is permitted by the gate), then tasks through safe_tasks
    tl = subprocess.run(["gws", "tasks", "tasklists", "list", "--params", "{}"],
                        capture_output=True, text=True, env=os.environ.copy(), timeout=60)
    tl_id = None
    if tl.returncode == 0:
        try:
            tl_id = (json.loads(tl.stdout[tl.stdout.find("{"):]).get("items") or [{}])[0].get("id")
        except Exception:  # noqa: BLE001
            pass
    record("tasks.tasklists.list", "allow", tl.returncode == 0, {"got_a_list": bool(tl_id)} if tl.returncode == 0
           else (tl.stderr.strip().splitlines() or ["?"])[-1][:300])
    if tl_id:
        tk = subprocess.run([sys.executable, rig_env.SAFE_TASKS, json.dumps({"tasklist": tl_id, "maxResults": 3})],
                            capture_output=True, text=True, env=os.environ.copy(), timeout=120)
        record("tasks.tasks.list via safe_tasks", "allow", tk.returncode == 0,
               {"rc": tk.returncode} if tk.returncode == 0 else (tk.stderr.strip().splitlines() or ["?"])[-1][:300])

    out = {"login": login, "results": results,
           "forbidden_that_worked": [r["call"] for r in results if r["expected"] == "forbid" and r["google_allowed"]],
           "allowed_that_failed": [r["call"] for r in results if r["expected"] == "allow" and not r["google_allowed"]]}
    print(json.dumps(out, indent=2))
    return 2 if out["forbidden_that_worked"] else (1 if out["allowed_that_failed"] else 0)


if __name__ == "__main__":
    sys.exit(main())
