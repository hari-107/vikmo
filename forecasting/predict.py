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


def _upcoming_week_starts(
    latest_observed_week: pd.Timestamp,
    count: int = 4,
) -> tuple[List[pd.Timestamp], List[pd.Timestamp]]:
    """
    Return (internal_weeks, output_weeks).

    The output horizon starts next Monday, so a partially completed/current week is
    not presented as a future prediction. If historical data is stale, the model
    recursively forecasts the missing weekly buckets internally before emitting the
    four genuinely upcoming weeks.
    """
    latest = pd.Timestamp(latest_observed_week).normalize()
    today = pd.Timestamp.now(tz="Asia/Kolkata").normalize().tz_localize(None)
    current_monday = today - pd.Timedelta(days=today.weekday())
    next_monday = current_monday + pd.Timedelta(days=7)

    output_start = max(latest + pd.Timedelta(days=7), next_monday)
    output_weeks = [output_start + pd.Timedelta(weeks=i) for i in range(count)]

    internal_start = latest + pd.Timedelta(days=7)
    internal_weeks = list(pd.date_range(start=internal_start, end=output_weeks[-1], freq="7D"))
    return internal_weeks, output_weeks


def generate_forecast(
    data_dir: Optional[Path] = None,
    output_file: Optional[Path] = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Generate a rolling 4-week-ahead demand forecast for every SKU in lead_times.csv.

    The horizon is anchored to the latest week present in sales_history.csv, not to
    fixed historical calendar dates. All sales observations up to and including that
    latest observed week are used for training; predictions begin on the next week.

    Output schema remains sku, week_start, forecast_units for API compatibility.
    """
    if data_dir is None:
        data_dir = base_dir / "data"
    if output_file is None:
        output_file = base_dir / "ml" / "forecast.csv"

    sales_file = Path(data_dir) / "sales_history.csv"
    lead_file = Path(data_dir) / "lead_times.csv"
    promo_file = Path(data_dir) / "promo_calendar.csv"

    # 1. Load historical sales. The model must never train on forecast targets.
    sales = pd.read_csv(sales_file)
    sales["week_start"] = pd.to_datetime(sales["week_start"])
    sales["diwali_date"] = sales["week_start"].dt.year.map(DIWALI_MAP)
    sales["weeks_to_diwali"] = (
        (sales["diwali_date"] - sales["week_start"]).dt.days // 7
    )

    lead = pd.read_csv(lead_file)
    skus = lead["sku"].astype(str).tolist()
    latest_sales_week = sales["week_start"].max()
    if pd.isna(latest_sales_week):
        raise ValueError("sales_history.csv contains no usable historical weeks")

    # Forecast missing intervening buckets internally if the sales history is stale,
    # but expose only four weekly periods starting next Monday (or after the latest
    # actual week if that falls later).
    internal_weeks, output_weeks = _upcoming_week_starts(latest_sales_week, count=4)
    output_week_strings = {w.strftime("%Y-%m-%d") for w in output_weeks}
    # Sales data after the latest known weekly observation is not used for training.
    train_sales = sales[sales["week_start"] <= latest_sales_week].copy()

    # 2. Load the promotion calendar if available. Missing future rows mean no known
    # promotion, which is safer than accidentally applying an old promotion flag.
    if Path(promo_file).exists():
        promo = pd.read_csv(promo_file)
        promo["week_start"] = pd.to_datetime(promo["week_start"])
    else:
        promo = pd.DataFrame(columns=["week_start", "sku", "promo_flag"])

    promo_lookup = {
        (str(row["sku"]), pd.Timestamp(row["week_start"]).strftime("%Y-%m-%d")): int(row["promo_flag"])
        for _, row in promo.iterrows()
    }

    meta_records = []
    for sku in skus:
        for week_dt in internal_weeks:
            week_str = week_dt.strftime("%Y-%m-%d")
            meta_records.append({
                "sku": sku,
                "week_start": week_dt,
                "promo_flag": promo_lookup.get((sku, week_str), 0),
                "weeks_to_diwali": get_weeks_to_diwali(week_dt),
            })
    test_meta = pd.DataFrame(meta_records)

    # 3. Forecast recursively from the latest known sales week through the target
    # horizon, then expose only the four upcoming weeks to the API and reorder logic.
    pipeline = HybridForecastPipeline(random_state=random_state)
    forecast_df = pipeline.fit_and_predict(
        train_sales=train_sales,
        skus=skus,
        test_weeks=internal_weeks,
        test_meta=test_meta,
    )
    forecast_df["week_start"] = pd.to_datetime(forecast_df["week_start"]).dt.strftime("%Y-%m-%d")
    forecast_df = forecast_df[forecast_df["week_start"].isin(output_week_strings)].copy()

    # 4. Keep the contract schema, with exactly 4 future weeks per SKU.
    forecast_df["forecast_units"] = (
        forecast_df["forecast_units"].astype(float).clip(lower=0.0).round(1)
    )
    forecast_df = forecast_df[["sku", "week_start", "forecast_units"]]
    forecast_df = forecast_df.sort_values(["sku", "week_start"]).reset_index(drop=True)

    expected_weeks = [w.strftime("%Y-%m-%d") for w in output_weeks]
    assert len(forecast_df) == len(skus) * 4, (
        f"Expected {len(skus) * 4} rows ({len(skus)} SKUs x 4 weeks), got {len(forecast_df)}"
    )
    assert forecast_df["sku"].nunique() == len(skus), "Forecast SKU count mismatch"
    assert sorted(forecast_df["week_start"].unique().tolist()) == expected_weeks, "Forecast weeks mismatch"
    assert (forecast_df["forecast_units"] >= 0).all(), "Found negative forecast values"
    assert np.isfinite(forecast_df["forecast_units"]).all(), "Found non-finite forecast values"
    assert pd.to_datetime(forecast_df["week_start"]).min() > latest_sales_week, (
        "Forecast includes a week that is not strictly after the latest sales observation"
    )

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    forecast_df.to_csv(output_path, index=False)
    return forecast_df


if __name__ == "__main__":
    out_file = base_dir / "ml" / "forecast.csv"
    print(f"Generating rolling four-week forecast to {out_file}...")
    df = generate_forecast(output_file=out_file)
    weeks = sorted(df["week_start"].unique())
    print(
        f"Generated {len(df)} rows for {df['sku'].nunique()} SKUs. "
        f"Forecast horizon: {weeks[0]} through {weeks[-1]}."
    )
