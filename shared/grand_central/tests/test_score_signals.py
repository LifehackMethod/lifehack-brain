"""score.py: the signals it discovers in signals/ are exactly the five it imports by name (EXPLICIT)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import score  # noqa: E402


class DiscoveredEqualsExplicit(unittest.TestCase):
    def test_same_set(self):
        found = {m.__name__ for m in score.discover()}
        named = {m.__name__ for m in score.EXPLICIT}
        self.assertEqual(found, named)
        self.assertEqual(len(named), 5)


if __name__ == "__main__":
    unittest.main()
