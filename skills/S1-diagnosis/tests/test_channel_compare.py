"""Pure channel comparison metric tests for Batch D5"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from channel_compare import _jaccard, _mode  # noqa: E402


class ChannelMetricTest(unittest.TestCase):
    """Protect null semantics and transparent categorical comparison"""

    def test_jaccard_preserves_no_observation_as_null(self) -> None:
        self.assertIsNone(_jaccard(set(), set()))

    def test_jaccard_is_symmetric(self) -> None:
        left = {"甲", "乙"}
        right = {"乙", "丙"}
        self.assertEqual(_jaccard(left, right), 0.3333)
        self.assertEqual(_jaccard(left, right), _jaccard(right, left))

    def test_mode_reports_value_and_agreement(self) -> None:
        self.assertEqual(_mode(["甲", "甲", "乙"]), {"value": "甲", "agreement": 0.6667})


if __name__ == "__main__":
    unittest.main()
