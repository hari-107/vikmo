import sys
from pathlib import Path
import pandas as pd

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from forecasting.evaluate import run_temporal_validation
from forecasting.predict import generate_forecast


def main():
    data_dir = base_dir / "data"
    forecast_output = base_dir / "ml" / "forecast.csv"

    print("==================================================")
    print("STEP 1: Chronological Expanding-Window Validation")
    print("==================================================")

    # Keep temporal validation on cutoffs with actual future sales available.
    cutoffs = ["2026-08-24", "2026-07-27", "2026-06-29", "2026-06-01"]
    candidate_wapes = []
    moving_average_wapes = []

    for cutoff in cutoffs:
        result = run_temporal_validation(
            data_dir=data_dir,
            cutoff_date=pd.to_datetime(cutoff),
        )
        print(f"\n[Validation Cutoff: {result['cutoff']}]")
        print(
            f"  Naive (Last Observed) : MAE={result['naive']['mae']:5.2f}, "
            f"WAPE={result['naive']['wape']:.3f}, RMSE={result['naive']['rmse']:5.2f}"
        )
        print(
            f"  Moving Average (4-wk) : MAE={result['moving_average']['mae']:5.2f}, "
            f"WAPE={result['moving_average']['wape']:.3f}, RMSE={result['moving_average']['rmse']:5.2f}"
        )
        print(
            f"  Seasonal Naive (Lag52): MAE={result['seasonal_naive']['mae']:5.2f}, "
            f"WAPE={result['seasonal_naive']['wape']:.3f}, RMSE={result['seasonal_naive']['rmse']:5.2f}"
        )
        print(
            f"  Original Rule-Based   : MAE={result['original_rule']['mae']:5.2f}, "
            f"WAPE={result['original_rule']['wape']:.3f}, RMSE={result['original_rule']['rmse']:5.2f}"
        )
        print(
            f"  HistGradientBoosting  : MAE={result['hgbr_ml']['mae']:5.2f}, "
            f"WAPE={result['hgbr_ml']['wape']:.3f}, RMSE={result['hgbr_ml']['rmse']:5.2f}"
        )
        print(
            f"  Selected Model (Hybrid): MAE={result['candidate']['mae']:5.2f}, "
            f"WAPE={result['candidate']['wape']:.3f}, RMSE={result['candidate']['rmse']:5.2f}"
        )
        candidate_wapes.append(result["candidate"]["wape"])
        moving_average_wapes.append(result["moving_average"]["wape"])

    avg_candidate_wape = sum(candidate_wapes) / len(candidate_wapes)
    avg_ma_wape = sum(moving_average_wapes) / len(moving_average_wapes)
    print(
        f"\nValidation Summary: Hybrid Model average WAPE={avg_candidate_wape:.3f} "
        f"vs Moving Average={avg_ma_wape:.3f}"
    )
    if avg_candidate_wape >= avg_ma_wape:
        print("WARNING: Hybrid model did not outperform the moving-average baseline on average.")

    print("\n==================================================")
    print("STEP 2: Generating rolling next-4-week forecast")
    print("==================================================")
    forecast_df = generate_forecast(data_dir=data_dir, output_file=forecast_output)
    weeks = sorted(forecast_df["week_start"].unique())
    print(
        f"Successfully generated {forecast_output}: {len(forecast_df)} rows for "
        f"{forecast_df['sku'].nunique()} SKUs, weeks {weeks[0]} through {weeks[-1]}."
    )


if __name__ == "__main__":
    main()
