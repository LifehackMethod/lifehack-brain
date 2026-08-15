#!/usr/bin/env python3
"""test_egress_level2.py — the Level 2 domain seal on ordinary web reads.

Run:  python3 system/tools/test_egress_level2.py

WHY THIS IS ITS OWN FILE. It belongs beside the other reader tests, and it cannot live there: the
aggregate gate (system/tools/run-all-tests.sh) SKIPS test_safe_readers.py by name, because two cases
in it make a real outbound call nothing in the runner can neutralize. A wall whose tests never run in
the gate is a softer version of the exact failure this wall exists to prevent — something that looks
covered and is not. Nothing below opens a socket, so this file runs in the gate every time.

WHAT IS BEING PROVEN. Not just that an off-list host is refused and a listed one passes. The three
states are the point:

  OFF        the shipped state — allowed, and it SAYS it is unsealed rather than staying quiet
  ON         enforced, and the refusal names the host it stopped
  AMBIGUOUS  half-configured — refused, loudly, instead of passing traffic while looking armed

The switch itself is system/safe-fetch-allowlist.md; the person-facing account of all three levels
is docs/OUTSIDE-SERVICES.md.
"""

import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


class EgressLevelTwoCase(unittest.TestCase):
    """The Level 2 domain seal — armed 2026-08-15, OFF until a person turns it on.

    ⭐ THE CASE THAT MATTERS IS THE HALF-CONFIGURED ONE. A wall that is present but not in force,
    and does not say so, is worse than no wall: it buys confidence nothing is backing. So the states
    proven here are not just allow/refuse — they are that OFF announces itself, and that every
    ambiguous configuration REFUSES rather than quietly passing traffic through while looking armed.

    None of these opens a socket: the seal is checked before the connection, so a refusal is provable
    without the network and an allow is provable as 'the wall did not stop it'."""

    def setUp(self):
        sys.path.insert(0, HERE)
        import safe_fetch
        self.sf = safe_fetch
        self.tmp = tempfile.mkdtemp(prefix="l2-switch-")
        self.switch = os.path.join(self.tmp, "switch.md")
        for k in ("SAFE_FETCH_ALLOWLIST", "SAFE_FETCH_ALLOWLIST_FILE"):
            os.environ.pop(k, None)
        os.environ["SAFE_FETCH_ALLOWLIST_FILE"] = self.switch
        safe_fetch._L2_ANNOUNCED = False

    def tearDown(self):
        for k in ("SAFE_FETCH_ALLOWLIST", "SAFE_FETCH_ALLOWLIST_FILE"):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, mode, domains=()):
        with open(self.switch, "w") as f:
            f.write("<!-- L2-MODE-START -->\n%s\n<!-- L2-MODE-END -->\n"
                    "<!-- ALLOWLIST-START -->\n%s\n<!-- ALLOWLIST-END -->\n"
                    % (mode, "\n".join(domains)))

    def test_it_ships_off_and_the_shipped_file_says_so(self):
        """The file in the repo, not a fixture — the state a person actually receives."""
        os.environ.pop("SAFE_FETCH_ALLOWLIST_FILE", None)
        state, domains, why = self.sf.l2_state()
        self.assertEqual(state, "off", f"the shipped switch must be off, said {state} ({why})")
        self.assertEqual(domains, [])

    def test_off_is_announced_rather_than_silent(self):
        self.write("off")
        err = io.StringIO()
        old, sys.stderr = sys.stderr, err
        try:
            self.sf._enforce_egress_allowlist("https://anywhere.example.org/x")
        finally:
            sys.stderr = old
        self.assertIn("L2-ALLOWLIST OFF", err.getvalue(),
                      "an unsealed read must say it is unsealed — silence reads as protection")

    def test_a_host_outside_the_list_is_refused(self):
        self.write("on", ["example.com"])
        with self.assertRaises(RuntimeError) as cm:
            self.sf._enforce_egress_allowlist("https://attacker.example.org/collect")
        self.assertIn("REFUSED", str(cm.exception))
        self.assertIn("attacker.example.org", str(cm.exception), "the refusal must name the host")

    def test_a_host_inside_the_list_passes(self):
        self.write("on", ["example.com"])
        self.sf._enforce_egress_allowlist("https://example.com/page")          # exact
        self.sf._enforce_egress_allowlist("https://docs.example.com/page")     # subdomain

    def test_the_env_var_seals_one_run_and_outranks_the_file(self):
        self.write("on", ["example.com"])
        os.environ["SAFE_FETCH_ALLOWLIST"] = "example.org"
        self.sf._enforce_egress_allowlist("https://example.org/page")
        with self.assertRaises(RuntimeError):
            self.sf._enforce_egress_allowlist("https://example.com/page")

    def test_armed_with_nothing_listed_refuses(self):
        """Switch on, list empty. Sealed to nothing is not the same as unsealed, and guessing which
        one was meant is exactly how a wall ends up looking armed while passing everything."""
        self.write("on", [])
        with self.assertRaises(RuntimeError) as cm:
            self.sf._enforce_egress_allowlist("https://example.com/page")
        self.assertIn("AMBIGUOUS", str(cm.exception))

    def test_domains_listed_with_the_switch_still_off_refuses(self):
        """The believable human error: add the domains, forget the switch, assume you are protected."""
        self.write("off", ["example.com"])
        with self.assertRaises(RuntimeError) as cm:
            self.sf._enforce_egress_allowlist("https://example.com/page")
        self.assertIn("AMBIGUOUS", str(cm.exception))

    def test_an_unreadable_switch_value_refuses(self):
        self.write("true", ["example.com"])
        with self.assertRaises(RuntimeError):
            self.sf._enforce_egress_allowlist("https://example.com/page")

    def test_a_mangled_file_refuses_rather_than_defaulting_to_off(self):
        with open(self.switch, "w") as f:
            f.write("# the markers are gone\n")
        with self.assertRaises(RuntimeError):
            self.sf._enforce_egress_allowlist("https://example.com/page")

    def test_an_env_var_naming_no_usable_domain_refuses(self):
        os.environ["SAFE_FETCH_ALLOWLIST"] = ", ,"
        with self.assertRaises(RuntimeError):
            self.sf._enforce_egress_allowlist("https://example.com/page")

    def test_no_switch_file_at_all_is_off_not_broken(self):
        state, _, _ = self.sf.l2_state()                # setUp pointed at a path that does not exist
        self.assertEqual(state, "off")

    def test_a_non_web_scheme_is_blocked_whatever_the_switch_says(self):
        """SSRF hygiene, unconditional — it is not part of the allowlist and must not depend on it."""
        self.write("off")
        for bad in ("file:///etc/passwd", "gopher://x/1", "data:text/html,x"):
            with self.assertRaises(RuntimeError, msg=f"{bad} was not blocked"):
                self.sf._enforce_egress_allowlist(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
