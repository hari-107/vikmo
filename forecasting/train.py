import sys
from pathlib import Path
import pandas as pd

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from forecasting.evaluate import run_temporal_validation
from forecasting.predict import generate_forecast


def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    forecast_output = base_dir / "ml" / "forecast.csv"

    print("==================================================")
    print("STEP 1: Chronological Expanding-Window Validation")
    print("==================================================")
    cutoffs = ["2026-08-24", "2026-07-27", "2026-06-29", "2026-06-01"]
    
    cand_wapes = []
    ma_wapes = []
    
    for cutoff in cutoffs:
        res = run_temporal_validation(data_dir=data_dir, cutoff_date=pd.to_datetime(cutoff))
        print(f"\n[Validation Cutoff: {res['cutoff']}]")
        print(f"  Naive (Last Observed) : MAE={res['naive']['mae']:5.2f}, WAPE={res['naive']['wape']:.3f}, RMSE={res['naive']['rmse']:5.2f}")
        print(f"  Moving Average (4-wk) : MAE={res['moving_average']['mae']:5.2f}, WAPE={res['moving_average']['wape']:.3f}, RMSE={res['moving_average']['rmse']:5.2f}")
        print(f"  Seasonal Naive (Lag52): MAE={res['seasonal_naive']['mae']:5.2f}, WAPE={res['seasonal_naive']['wape']:.3f}, RMSE={res['seasonal_naive']['rmse']:5.2f}")
        print(f"  Original Rule-Based   : MAE={res['original_rule']['mae']:5.2f}, WAPE={res['original_rule']['wape']:.3f}, RMSE={res['original_rule']['rmse']:5.2f}")
        print(f"  HistGradientBoosting  : MAE={res['hgbr_ml']['mae']:5.2f}, WAPE={res['hgbr_ml']['wape']:.3f}, RMSE={res['hgbr_ml']['rmse']:5.2f}")
        print(f"  Selected Model (Hybrid): MAE={res['candidate']['mae']:5.2f}, WAPE={res['candidate']['wape']:.3f}, RMSE={res['candidate']['rmse']:5.2f} (WINNER)")
        
        cand_wapes.append(res['candidate']['wape'])
        ma_wapes.append(res['moving_average']['wape'])

    avg_cand_wape = sum(cand_wapes) / len(cand_wapes)
    avg_ma_wape = sum(ma_wapes) / len(ma_wapes)
    print(f"\nValidation Summary: Hybrid Model average WAPE={avg_cand_wape:.3f} vs Moving Average={avg_ma_wape:.3f}")
    assert avg_cand_wape < avg_ma_wape, "Validation failed: Candidate model did not outperform moving average baseline."

    print("\n==================================================")
    print("STEP 2: Generating ml/forecast.csv with Winning Model")
    print("==================================================")
    df = generate_forecast(data_dir=data_dir, output_file=forecast_output)
    print(f"Successfully generated {forecast_output}: {len(df)} rows across {df['sku'].nunique()} SKUs.")


if __name__ == "__main__":
    main()
