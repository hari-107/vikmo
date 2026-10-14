from unittest import TestCase

import pandas as pd

from forecasting.predict import _upcoming_week_starts


class UpcomingForecastHorizonTests(TestCase):
    def test_uses_next_four_full_weeks_when_history_is_stale(self):
        internal_weeks, output_weeks = _upcoming_week_starts(
            pd.Timestamp("2026-09-21"),
            count=4,
            today=pd.Timestamp("2026-10-14"),
        )
        self.assertEqual(
            [w.strftime("%Y-%m-%d") for w in output_weeks],
            ["2026-10-19", "2026-10-26", "2026-11-02", "2026-11-09"],
        )
        self.assertEqual(internal_weeks[0].strftime("%Y-%m-%d"), "2026-09-28")
        self.assertEqual(internal_weeks[-1], output_weeks[-1])

    def test_does_not_start_before_latest_observed_week(self):
        _, output_weeks = _upcoming_week_starts(
            pd.Timestamp("2026-10-26"),
            count=4,
            today=pd.Timestamp("2026-10-14"),
        )
        self.assertEqual(
            [w.strftime("%Y-%m-%d") for w in output_weeks],
            ["2026-11-02", "2026-11-09", "2026-11-16", "2026-11-23"],
        )
