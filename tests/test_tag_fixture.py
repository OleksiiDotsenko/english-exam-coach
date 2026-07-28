"""The tagging fixture must stay consistent with the closed taxonomy.

The fixture in references/tagging-examples.md is what the assistant consults
when tagging an error, so a tag that has drifted out of the enum would teach
it to emit an invalid tag — which log_error.py then rejects, mid-session, in
front of the learner. This keeps the two in lockstep.

Whether the model actually chooses these tags is a behavioural question that
unit tests cannot answer; DOGFOOD.md covers it with a human checklist.
"""

import re
import sys
import unittest
from pathlib import Path

from helpers import SCRIPTS

FIXTURE = (SCRIPTS.parent / "references" / "tagging-examples.md")

sys.path.insert(0, str(SCRIPTS))
import log_error  # noqa: E402


def fixture_rows():
    """Parse the markdown table into (error, category, subtype, point)."""
    rows = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 4:
            continue
        if cells[1] == "category":  # header
            continue
        rows.append(tuple(cells))
    return rows


class TagFixtureTests(unittest.TestCase):
    def setUp(self):
        self.rows = fixture_rows()

    def test_the_fixture_is_big_enough_to_be_a_calibration_set(self):
        self.assertGreaterEqual(len(self.rows), 20,
                                "a smaller fixture cannot show tagging patterns")

    def test_every_tag_exists_in_the_closed_taxonomy(self):
        for error, category, subtype, _point in self.rows:
            with self.subTest(error=error):
                self.assertIn(category, log_error.TAXONOMY,
                              "category %r is not in the enum" % category)
                self.assertIn(subtype, log_error.TAXONOMY[category],
                              "subtype %r is not valid for %r"
                              % (subtype, category))

    def test_every_point_would_pass_validation(self):
        # The point is what a fresh item must test; log_error rejects stubs.
        for error, _c, _s, point in self.rows:
            with self.subTest(error=error):
                self.assertGreaterEqual(len(point), 4)
                self.assertNotEqual(point.lower(), _s.lower(),
                                    "the point must be more specific than the "
                                    "subtype it sits under")

    def test_points_are_distinct(self):
        points = [p.lower() for _e, _c, _s, p in self.rows]
        self.assertEqual(len(points), len(set(points)),
                         "duplicate points teach duplicate queue entries")

    def test_the_fixture_covers_most_of_the_taxonomy(self):
        covered = {category for _e, category, _s, _p in self.rows}
        missing = set(log_error.TAXONOMY) - covered
        # `vocabulary` is exercised by the vocabulary skill's own examples.
        self.assertLessEqual(missing, {"vocabulary"},
                             "these categories have no worked example: %s"
                             % sorted(missing))

    def test_every_taxonomy_entry_has_a_description(self):
        for category, subtypes in log_error.TAXONOMY.items():
            for subtype, description in subtypes.items():
                with self.subTest(tag="%s/%s" % (category, subtype)):
                    self.assertTrue(description.strip())
                    self.assertGreater(len(description), 15,
                                       "a one-word gloss will not disambiguate "
                                       "the tag at logging time")


if __name__ == "__main__":
    unittest.main()
