#!/usr/bin/env python3
"""job-sim-gws-stub.py -- TEST-ONLY stand-in for `gws`, used by the rig's danger-email scenario via LIFEHACK_GWS_BIN
(5.4). Answers only `gmail users ...` from fixture files under $JOB_SIM_DIR/gmail/ and records every call to
$JOB_SIM_DIR/gmail/calls.log. It never touches the network or any real mailbox.
  getProfile                  -> {"emailAddress":"sim@example.com"}
  labels list                 -> labels.json
  threads list                -> threads.json  ({"label_ids": {"<labelId>": [thread ids]}, "all": [thread ids]})
  threads get (any format)    -> thread-<id>.json
"""
import json, os, sys
d = os.path.join(os.environ.get("JOB_SIM_DIR", "/nonexistent"), "gmail")
args = sys.argv[1:]
if len(args) < 3 or args[:2] != ["gmail", "users"] or not os.path.isdir(d):
    sys.stderr.write("stub gws: unsupported call\n"); sys.exit(1)
params = {}
if "--params" in args:
    params = json.loads(args[args.index("--params") + 1])
with open(os.path.join(d, "calls.log"), "a") as fh:
    fh.write(" ".join(args[2:5]) + " " + json.dumps(params, sort_keys=True) + "\n")
op = args[2:4] if args[2] != "getProfile" else ["getProfile"]
if op == ["getProfile"]:
    print(json.dumps({"emailAddress": "sim@example.com"}))
elif op == ["labels", "list"]:
    print(open(os.path.join(d, "labels.json")).read())
elif op == ["threads", "list"]:
    idx = json.load(open(os.path.join(d, "threads.json")))
    ids = idx["label_ids"].get(params.get("labelIds", ""), []) if "labelIds" in params else idx.get("all", [])
    print(json.dumps({"threads": [{"id": i} for i in ids[: int(params.get("maxResults", 100))]]}))
elif op == ["threads", "get"]:
    print(open(os.path.join(d, "thread-%s.json" % params["id"])).read())
else:
    sys.stderr.write("stub gws: unsupported op\n"); sys.exit(1)
