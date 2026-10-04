"""Guard the factor-panel development / sealed-holdout boundary."""
import math
from pathlib import Path
import unittest
import exchange_calendars as xcals
from .build import (DEVELOPMENT_START, HISTORY_END, MAX_DEVELOPMENT_DATE,
                    SEALED_HOLDOUT_START, sessions)


class WindowBoundaryTests(unittest.TestCase):
    def test_development_and_holdout_are_exact_disjoint_windows(self):
        development = sessions(DEVELOPMENT_START, MAX_DEVELOPMENT_DATE)
        calendar = xcals.get_calendar('XNYS', start=DEVELOPMENT_START, end=HISTORY_END)
        history = calendar.sessions_in_range(DEVELOPMENT_START, HISTORY_END)
        holdout = calendar.sessions_in_range(SEALED_HOLDOUT_START, HISTORY_END)

        self.assertEqual(len(history), 2703)
        self.assertEqual(len(development), 2202)
        self.assertEqual(len(holdout), 501)
        self.assertEqual(math.ceil(len(history) * .2), 541)
        self.assertLess(len(holdout), math.ceil(len(history) * .2))
        self.assertEqual(max(development), MAX_DEVELOPMENT_DATE)
        self.assertEqual(min(development), DEVELOPMENT_START)

    def test_session_builder_refuses_to_cross_into_holdout(self):
        with self.assertRaises(ValueError):
            sessions(DEVELOPMENT_START, SEALED_HOLDOUT_START)

    def test_pinned_export_sql_stops_at_development_cutoff(self):
        sql = Path(__file__).with_name('development_export.sql').read_text()
        self.assertEqual(sql.count("BETWEEN '2016-01-04' AND '2024-10-02'"), 2)
        self.assertIn('2024-10-03..2026-10-02 holdout is intentionally excluded', sql)
        self.assertNotIn("BETWEEN '2016-01-04' AND '2026-10-02'", sql)


if __name__ == '__main__':
    unittest.main()
