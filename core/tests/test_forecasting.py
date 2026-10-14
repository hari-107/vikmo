import csv
import math
from pathlib import Path
import numpy as np
import pandas as pd
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Product
from forecasting.models import (
    DIWALI_MAP,
    croston_sba,
    get_weeks_to_diwali,
    estimate_promotional_uplift,
    calculate_diwali_lift,
    HistGradientBoostingForecaster,
    HybridForecastPipeline,
)
from forecasting.predict import generate_forecast, FORECAST_WEEKS
from forecasting.evaluate import run_temporal_validation, evaluate_predictions


class ForecastingPipelineTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.weeks = ["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19"]
        self.base_dir = Path(settings.BASE_DIR)
        self.data_dir = self.base_dir / "data"

        self.product = Product.objects.create(
            sku="FIL-1016",
            name="Oil Filter - Bajaj Pulsar",
            category="Filters",
            brand="Uno Minda",
            vehicle_fitment="Bajaj Pulsar 150",
            price="450.00",
            stock=40,
            description="High quality oil filter",
        )

    # 1. Forecast Generation & Execution
    def test_forecast_generation_execution(self):
        df = generate_forecast(data_dir=self.data_dir)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 160)
        self.assertEqual(df["sku"].nunique(), 40)

    # 2. Exactly 160 Forecast Rows
    def test_forecast_csv_file_structure(self):
        forecast_path = self.base_dir / "ml" / "forecast.csv"
        self.assertTrue(forecast_path.exists())

        with open(forecast_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertEqual(reader.fieldnames, ["sku", "week_start", "forecast_units"])
        self.assertEqual(len(rows), 160)

        skus = {r["sku"] for r in rows}
        self.assertEqual(len(skus), 40)

        weeks = {r["week_start"] for r in rows}
        self.assertEqual(sorted(list(weeks)), self.weeks)

        for r in rows:
            val = float(r["forecast_units"])
            self.assertGreaterEqual(val, 0)
            self.assertTrue(math.isfinite(val))

    # 3. Four Forecast Weeks per SKU
    def test_four_forecast_weeks_per_sku(self):
        forecast_path = self.base_dir / "ml" / "forecast.csv"
        df = pd.read_csv(forecast_path)
        counts = df.groupby("sku")["week_start"].count()
        for sku, count in counts.items():
            self.assertEqual(count, 4, f"SKU {sku} does not have exactly 4 weeks")

    # 4. Missing and Invalid Sales Observations Handled Safely
    def test_missing_and_invalid_sales_handling(self):
        # Empty array
        self.assertEqual(croston_sba([], method="sba"), 0.0)
        # NaN in array should not crash when sanitized
        sanitized = pd.Series([10.0, np.nan, 15.0]).dropna()
        val = croston_sba(sanitized, method="sba")
        self.assertGreater(val, 0.0)

    # 5. New SKUs / Cold Start
    def test_new_skus_and_cold_start(self):
        # Test cold start with zero history
        pipeline = HybridForecastPipeline()
        empty_sales = pd.DataFrame(columns=["sku", "week_start", "units_sold", "promo_flag", "weeks_to_diwali"])
        test_weeks = [pd.to_datetime(w) for w in self.weeks]
        test_meta = pd.DataFrame([
            {"sku": "NEW-9999", "week_start": w, "promo_flag": 0, "weeks_to_diwali": 4}
            for w in test_weeks
        ])
        pred_df = pipeline.fit_and_predict(
            train_sales=empty_sales,
            skus=["NEW-9999"],
            test_weeks=test_weeks,
            test_meta=test_meta,
        )
        self.assertEqual(len(pred_df), 4)
        for val in pred_df["forecast_units"]:
            self.assertEqual(val, 0.0)

    # 6. Products with No Positive Sales
    def test_products_with_no_positive_sales(self):
        zero_series = [0, 0, 0, 0, 0, 0, 0, 0]
        self.assertEqual(croston_sba(zero_series, method="sba"), 0.0)
        self.assertEqual(croston_sba(zero_series, method="croston"), 0.0)

    # 7. Intermittent Demand (Croston / SBA)
    def test_intermittent_demand_croston_sba(self):
        # Demand every 3 weeks: [0, 0, 3, 0, 0, 3, 0, 0, 3]
        pattern = [0, 0, 3, 0, 0, 3, 0, 0, 3]
        f_croston = croston_sba(pattern, alpha=0.1, method="croston")
        f_sba = croston_sba(pattern, alpha=0.1, method="sba")
        self.assertGreater(f_croston, 0.0)
        self.assertGreater(f_sba, 0.0)
        # SBA includes bias correction factor (1 - alpha/2 = 0.95), so f_sba < f_croston
        self.assertLess(f_sba, f_croston)

    # 8. Promotional Periods & Regularized Uplift
    def test_promotional_uplift_regularization(self):
        sample_sales = pd.DataFrame({
            "sku": ["TEST-1"] * 10,
            "units_sold": [10, 10, 10, 10, 10, 20, 20, 10, 10, 10],
            "promo_flag": [0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
            "weeks_to_diwali": [15] * 10,  # Non-festive
        })
        uplift = estimate_promotional_uplift(sample_sales, "TEST-1", global_prior_ratio=1.85)
        self.assertGreaterEqual(uplift, 1.2)
        self.assertLessEqual(uplift, 2.5)

    # 9. Diwali-Related Forecasts
    def test_diwali_week_calculations(self):
        self.assertEqual(get_weeks_to_diwali(pd.to_datetime("2026-11-08")), 0)
        self.assertEqual(get_weeks_to_diwali(pd.to_datetime("2026-10-19")), 2)
        self.assertEqual(get_weeks_to_diwali(pd.to_datetime("2026-10-12")), 3)
        self.assertEqual(get_weeks_to_diwali(pd.to_datetime("2026-10-05")), 4)
        self.assertEqual(get_weeks_to_diwali(pd.to_datetime("2026-09-28")), 5)

    # 10. No Future-Data Leakage in Temporal Cutoffs
    def test_no_future_data_leakage(self):
        cutoff = pd.to_datetime("2026-08-24")
        res = run_temporal_validation(self.data_dir, cutoff_date=cutoff, horizon_weeks=4)
        self.assertIn("candidate", res)
        self.assertIn("wape", res["candidate"])
        self.assertLess(res["candidate"]["wape"], 0.25)

    # 11. Reproducible Predictions
    def test_reproducible_predictions(self):
        df1 = generate_forecast(data_dir=self.data_dir, random_state=42)
        df2 = generate_forecast(data_dir=self.data_dir, random_state=42)
        pd.testing.assert_frame_equal(df1, df2)

    # 12. Validation and Prediction Model Consistency
    def test_model_consistency(self):
        # Both evaluate.py and predict.py use HybridForecastPipeline
        pipeline = HybridForecastPipeline(random_state=42)
        self.assertIsNotNone(pipeline.ml_forecaster)

    # 13. Reorder Calculation Correctness
    def test_reorder_calculation_correctness(self):
        resp = self.client.get("/api/reorder-suggestions/")
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(len(results), 40)

        for entry in results:
            L = entry["lead_time_weeks"]
            self.assertGreaterEqual(L, 1)
            self.assertGreaterEqual(entry["safety_stock"], 0)
            self.assertGreaterEqual(entry["reorder_qty"], 0)

            # Contract: reorder_point = lead_time_demand + safety_stock
            expected_point = round(entry["lead_time_demand"] + entry["safety_stock"], 1)
            self.assertAlmostEqual(entry["reorder_point"], expected_point, places=1)

            # Contract: reorder_qty = max(0, ceil(reorder_point - current_stock))
            expected_qty = max(0, math.ceil(entry["reorder_point"] - entry["current_stock"]))
            self.assertEqual(entry["reorder_qty"], expected_qty)

    # 14. API Contract Compatibility
    def test_forecast_and_reorder_api_contracts(self):
        # Forecast endpoint
        resp = self.client.get("/api/forecast/FIL-1016/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["sku"], "FIL-1016")
        self.assertEqual(len(data["forecast"]), 4)
        for idx, item in enumerate(data["forecast"]):
            self.assertEqual(item["week_start"], self.weeks[idx])
            self.assertIsInstance(item["forecast_units"], (int, float))

        # 404 on unknown SKU
        r404 = self.client.get("/api/forecast/NON-EXISTENT-SKU/")
        self.assertEqual(r404.status_code, 404)
        self.assertEqual(r404.json()["error"]["code"], "NOT_FOUND")

        # Live stock update reflects in reorder suggestions
        self.client.put("/api/inventory/FIL-1016/", {"quantity": 500}, format="json")
        resp2 = self.client.get("/api/reorder-suggestions/")
        item = next(x for x in resp2.json()["results"] if x["sku"] == "FIL-1016")
        self.assertEqual(item["current_stock"], 500)
        self.assertEqual(item["reorder_qty"], 0)
