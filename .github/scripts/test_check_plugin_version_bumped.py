#!/usr/bin/env python3
"""Unit tests for check_plugin_version_bumped.py -- run with:
    python3 .github/scripts/test_check_plugin_version_bumped.py

No git needed: exercises evaluate()/parse_semver()/is_shipped() directly, the same pure
functions the CI workflow's git-backed path calls into after `changed_files()` and
`read_version_at()` produce their inputs.
"""
from __future__ import annotations

import sys
import unittest

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from check_plugin_version_bumped import (  # noqa: E402
    CANNOT_EVALUATE,
    FLAGGED,
    PASS,
    evaluate,
    is_shipped,
    parse_semver,
)

PLUGIN_JSON = ".claude-plugin/plugin.json"


class IsShipped(unittest.TestCase):
    def test_shipped_paths_count(self) -> None:
        for path in [
            "system/hooks/guard_write_paths.sh",
            "shared/brain_root.py",
            ".claude/skills/save/SKILL.md",
            "agents/sentinel.md",
            "memory/README.md",
            "NEWFILE-NOBODY-EXEMPTED.md",  # denylist is closed, not open -- fail closed
        ]:
            self.assertTrue(is_shipped(path), path)

    def test_non_shipped_paths_excluded(self) -> None:
        for path in [
            ".github/workflows/plugin-version-bump-required.yml",
            ".github/scripts/check_plugin_version_bumped.py",
            "docs/design.md",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            "README.md",
            "INSTALL.md",
            ".gitignore",
        ]:
            self.assertFalse(is_shipped(path), path)


class ParseSemver(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertEqual(parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_semver("0.1.0"), (0, 1, 0))

    def test_invalid(self) -> None:
        for bad in ["1.2", "1.2.3-beta", "v1.2.3", "1.2.3.4", ""]:
            self.assertIsNone(parse_semver(bad), bad)


class Evaluate(unittest.TestCase):
    def test_no_shipped_change_passes_even_with_no_version_info(self) -> None:
        code, msg = evaluate(
            ["README.md", ".github/workflows/x.yml"],
            None, "no base file", None, "no head file", PLUGIN_JSON,
        )
        self.assertEqual(code, PASS)
        self.assertIn("no shipped path changed", msg)

    def test_shipped_change_unbumped_version_is_flagged(self) -> None:
        code, msg = evaluate(
            ["system/hooks/guard_write_paths.sh"],
            "0.1.0", None, "0.1.0", None, PLUGIN_JSON,
        )
        self.assertEqual(code, FLAGGED)
        self.assertIn("did not change", msg)

    def test_shipped_change_bumped_version_passes(self) -> None:
        code, msg = evaluate(
            ["system/hooks/guard_write_paths.sh"],
            "0.1.0", None, "0.1.1", None, PLUGIN_JSON,
        )
        self.assertEqual(code, PASS)
        self.assertIn("increased", msg)

    def test_shipped_change_decreased_version_is_flagged(self) -> None:
        code, msg = evaluate(
            ["system/hooks/guard_write_paths.sh"],
            "0.2.0", None, "0.1.9", None, PLUGIN_JSON,
        )
        self.assertEqual(code, FLAGGED)
        self.assertIn("not an increase", msg)

    def test_shipped_change_same_version_string_reordered_json_is_flagged(self) -> None:
        # base_version_raw == head_version_raw regardless of how the surrounding JSON was
        # formatted -- evaluate() only ever sees the extracted string.
        code, msg = evaluate(["shared/brain_root.py"], "1.0.0", None, "1.0.0", None, PLUGIN_JSON)
        self.assertEqual(code, FLAGGED)

    def test_shipped_change_unreadable_manifest_is_cannot_evaluate(self) -> None:
        code, msg = evaluate(
            ["system/hooks/guard_write_paths.sh"],
            None, "could not read plugin.json at base: not found", None, None, PLUGIN_JSON,
        )
        self.assertEqual(code, CANNOT_EVALUATE)
        self.assertIn("not a pass", msg)

    def test_shipped_change_non_semver_version_is_cannot_evaluate(self) -> None:
        code, msg = evaluate(
            ["system/hooks/guard_write_paths.sh"],
            "0.1.0", None, "next", None, PLUGIN_JSON,
        )
        self.assertEqual(code, CANNOT_EVALUATE)
        self.assertIn("not a plain X.Y.Z semver", msg)

    def test_only_shipped_files_listed_in_message(self) -> None:
        code, msg = evaluate(
            ["README.md", "system/hooks/guard_write_paths.sh"],
            "0.1.0", None, "0.1.0", None, PLUGIN_JSON,
        )
        self.assertEqual(code, FLAGGED)
        self.assertIn("1 shipped file(s) changed", msg)
        self.assertNotIn("README.md", msg)


if __name__ == "__main__":
    unittest.main()
