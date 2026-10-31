#!/usr/bin/env python3
"""make_fixtures.py — (re)writes checks/fixtures/<kind>/{case.env,good/,bad/} from canary/expected.py.
ENTRY POINT, on-demand: a builder runs this by hand when the canary contract changes; listed in README "Run by hand".

The fixtures are SHIPPED as static files; this script only documents how they were made and lets a later
builder regenerate them if the canary contract changes (then re-run checks/selftest.sh). Each kind gets one
step (ai s5, code s7, human s4) at SEED=4242. good/ = the expected record, canonical and re-formatted.
bad/ = one mutation per file; every one must make the real check exit 1.
"""
import json, pathlib, shutil, sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "canary"))
import expected  # noqa: E402

SEED = 4242
CASES = {"ai": 5, "code": 7, "human": 4}


def want(n):
    ks = expected.kinds()
    answers = {k: "yes" for k, v in ks.items() if v == "human" and k <= n}
    return expected.expected_run(SEED, answers)[n - 1]


def j(rec):
    return expected.dumps(rec) + "\n"


def mut(rec, **kw):
    r = dict(rec)
    for k, v in kw.items():
        if v is DEL:
            r.pop(k, None)
        else:
            r[k] = v
    return r


DEL = object()


def bad_cases(kind, n, w):
    c = expected.dumps(w)
    f = w["facts"]
    out = {
        "empty": "",
        "whitespace-only": "  \n\t\n",
        "token-missing": j(mut(w, token=DEL)),
        "token-wrong-step": j(mut(w, token=expected.token(SEED, n - 1))),
        "token-wrong-seed": j(mut(w, token=expected.token(SEED + 1, n))),
        "token-truncated": j(mut(w, token=w["token"][:-1])),
        "value-wrong": j(mut(w, value=(w["value"] + 1) % 1000)),
        "value-as-string": j(mut(w, value=str(w["value"]))),
        "value-prev-step": j(mut(w, value=want(n - 1)["value"])),
        "fact-dropped": j(mut(w, facts=f[:-1])),
        "fact-reordered": j(mut(w, facts=[f[1], f[0]] + f[2:])),
        "fact-edited": j(mut(w, facts=f[:2] + [f[2].split("=")[0] + "=000"] + f[3:])),
        "fact-extra": j(mut(w, facts=f + ["Zed=123"])),
        "extra-key": j(mut(w, note="done")),
        "step-wrong": j(mut(w, step=n + 1)),
        "step-as-string": j(mut(w, step=str(n))),
        "step-missing": j(mut(w, step=DEL)),
        "fenced-json": "```json\n" + c + "\n```\n",
        "prose-wrapped": "Here is the step file:\n" + c + "\n",
        "two-objects": c + "\n" + c + "\n",
        "truncated": c[:-7] + "\n",
        "array-not-object": "[" + c + "]\n",
        "duplicate-key": c.replace('"token":', '"token":"T00-00000000","token":', 1) + "\n",
    }
    if kind == "human":
        out.update({
            "answer-no": j(mut(w, answer="no")),
            "answer-uppercase": j(mut(w, answer="YES")),
            "answer-padded": j(mut(w, answer=" yes")),
            "answer-bool": j(mut(w, answer=True)),
            "answer-missing": j(mut(w, answer=DEL)),
        })
    else:
        out["answer-on-non-human"] = j(mut(w, answer="yes"))
    return out


def main():
    for kind, n in CASES.items():
        d = HERE / kind
        shutil.rmtree(d, ignore_errors=True)
        (d / "good").mkdir(parents=True)
        (d / "bad").mkdir()
        (d / "case.env").write_text("SEED=%d\nSTEP=%d\n" % (SEED, n))
        w = want(n)
        (d / "good" / "canonical.json").write_text(j(w))
        rev = {k: w[k] for k in reversed(list(w))}
        (d / "good" / "reordered-keys-pretty.json").write_text("\n  " + json.dumps(rev, indent=2) + "\n\n")
        for name, text in bad_cases(kind, n, w).items():
            (d / "bad" / (name + ".json")).write_text(text)
        print("%s s%d: good=2 bad=%d" % (kind, n, len(bad_cases(kind, n, w))))


if __name__ == "__main__":
    main()
