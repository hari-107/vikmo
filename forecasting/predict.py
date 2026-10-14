import os
import sys
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from forecasting.models import (
    DIWALI_MAP,
    get_weeks_to_diwali,
    HybridForecastPipeline,
)

FORECAST_WEEKS: List[str] = ["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19"]


def generate_forecast(
    data_dir: Optional[Path] = None,
    output_file: Optional[Path] = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Generates the official 4-week demand forecasts for all 40 SKUs in lead_times.csv
    using the validated Hybrid (HistGradientBoostingRegressor + Syntetos-Boylan Approximation)
    model.
    
    Guarantees:
    - Exactly 160 rows (40 SKUs x 4 weeks).
    - Preserves required schema: sku, week_start, forecast_units.
    - Zero future sales data leakage (trains up to 2026-09-21 cutoff).
    - Finite, non-negative forecasts.
    - Consistent with validation candidate.
    """
    if data_dir is None:
        data_dir = base_dir / "data"
    if output_file is None:
        output_file = base_dir / "ml" / "forecast.csv"

    sales_file = data_dir / "sales_history.csv"
    lead_file = data_dir / "lead_times.csv"
    promo_file = data_dir / "promo_calendar.csv"

    # 1. Load data
    sales = pd.read_csv(sales_file)
    sales["week_start"] = pd.to_datetime(sales["week_start"])
    sales["diwali_date"] = sales["week_start"].dt.year.map(DIWALI_MAP)
    sales["weeks_to_diwali"] = (sales["diwali_date"] - sales["week_start"]).dt.days // 7

    lead = pd.read_csv(lead_file)
    skus = lead["sku"].tolist()

    promo = pd.read_csv(promo_file)
    promo["week_start"] = pd.to_datetime(promo["week_start"])

    # Build future test metadata for the 4 forecast weeks
    test_weeks = [pd.to_datetime(w) for w in FORECAST_WEEKS]
    promo_lookup = {
        (r["sku"], r["week_start"].strftime("%Y-%m-%d")): int(r["promo_flag"])
        for _, r in promo.iterrows()
    }

    meta_records = []
    for sku in skus:
        for w_dt in test_weeks:
            w_str = w_dt.strftime("%Y-%m-%d")
            p_flag = promo_lookup.get((sku, w_str), 0)
            w_diwali = get_weeks_to_diwali(w_dt)
            meta_records.append({
                "sku": sku,
                "week_start": w_dt,
                "promo_flag": p_flag,
                "weeks_to_diwali": w_diwali,
            })
    test_meta = pd.DataFrame(meta_records)

    # 2. Fit and forecast using the validated Hybrid ML + SBA Pipeline
    pipeline = HybridForecastPipeline(random_state=random_state)
    forecast_df = pipeline.fit_and_predict(
        train_sales=sales,
        skus=skus,
        test_weeks=test_weeks,
        test_meta=test_meta,
    )

    # 3. Format and validate schema
    forecast_df["week_start"] = pd.to_datetime(forecast_df["week_start"]).dt.strftime("%Y-%m-%d")
    forecast_df["forecast_units"] = forecast_df["forecast_units"].astype(float).clip(lower=0.0).round(1)

    # Ensure required columns
    forecast_df = forecast_df[["sku", "week_start", "forecast_units"]]

    # Assert contract constraints
    assert len(forecast_df) == 160, f"Expected exactly 160 rows, got {len(forecast_df)}"
    assert forecast_df["sku"].nunique() == 40, f"Expected 40 SKUs, got {forecast_df['sku'].nunique()}"
    assert sorted(forecast_df["week_start"].unique()) == FORECAST_WEEKS, "Forecast weeks mismatch"
    assert (forecast_df["forecast_units"] >= 0).all(), "Found negative forecast values"

    # 4. Save to output CSV
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    forecast_df.to_csv(output_path, index=False)

    return forecast_df


if __name__ == "__main__":
    out_file = base_dir / "ml" / "forecast.csv"
    print(f"Generating production forecast to {out_file}...")
    df = generate_forecast(output_file=out_file)
    print(f"Successfully generated {len(df)} rows for {df['sku'].nunique()} SKUs.")
