from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from forecasting.predict import _upcoming_week_starts


class UpcomingForecastHorizonTests(TestCase):
    @patch("forecasting.predict.pd.Timestamp.now")
    def test_uses_next_four_full_weeks_when_history_is_stale(self, mock_now):
        mock_now.return_value = pd.Timestamp("2026-10-14 10:00:00", tz="Asia/Kolkata")
        internal_weeks, output_weeks = _upcoming_week_starts(
            pd.Timestamp("2026-09-21"),
            count=4,
        )
        self.assertEqual(
            [w.strftime("%Y-%m-%d") for w in output_weeks],
            ["2026-10-19", "2026-10-26", "2026-11-02", "2026-11-09"],
        )
        self.assertEqual(internal_weeks[0].strftime("%Y-%m-%d"), "2026-09-28")
        self.assertEqual(internal_weeks[-1], output_weeks[-1])

    @patch("forecasting.predict.pd.Timestamp.now")
    def test_does_not_start_before_latest_observed_week(self, mock_now):
        mock_now.return_value = pd.Timestamp("2026-10-14 10:00:00", tz="Asia/Kolkata")
        _, output_weeks = _upcoming_week_starts(
            pd.Timestamp("2026-10-26"),
            count=4,
        )
        self.assertEqual(
            [w.strftime("%Y-%m-%d") for w in output_weeks],
            ["2026-11-02", "2026-11-09", "2026-11-16", "2026-11-23"],
        )
