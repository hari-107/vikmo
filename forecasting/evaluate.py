import os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from forecasting.models import (
    DIWALI_MAP,
    croston_sba,
    estimate_promotional_uplift,
    calculate_diwali_lift,
    get_weeks_to_diwali,
    HistGradientBoostingForecaster,
    HybridForecastPipeline,
)


def load_data(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Loads sales history and lead times, enriching with Diwali distance."""
    sales = pd.read_csv(data_dir / "sales_history.csv")
    sales["week_start"] = pd.to_datetime(sales["week_start"])
    sales["diwali_date"] = sales["week_start"].dt.year.map(DIWALI_MAP)
    sales["weeks_to_diwali"] = (sales["diwali_date"] - sales["week_start"]).dt.days // 7
    lead = pd.read_csv(data_dir / "lead_times.csv")
    return sales, lead


def evaluate_predictions(actual_df: pd.DataFrame, pred_df: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Calculates MAE, WAPE, and RMSE between actual and predicted weekly units.
    WAPE is safely handled when total actual demand is 0.
    """
    merged = pd.merge(actual_df, pred_df, on=["sku", "week_start"], suffixes=("_actual", "_pred"))
    y_true = merged["units_sold"].values.astype(float)
    y_pred = np.maximum(0.0, merged["forecast_units"].values.astype(float))

    mae = float(np.mean(np.abs(y_true - y_pred)))
    sum_y = float(np.sum(y_true))
    wape = float(np.sum(np.abs(y_true - y_pred)) / sum_y) if sum_y > 0 else 0.0
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return mae, wape, rmse


def predict_naive_baseline(train_sales: pd.DataFrame, skus: List[str], test_weeks: List[pd.Timestamp]) -> pd.DataFrame:
    preds = []
    for sku in skus:
        s = train_sales[train_sales["sku"] == sku].sort_values("week_start")
        val = float(s["units_sold"].iloc[-1]) if len(s) > 0 else 0.0
        for w in test_weeks:
            preds.append({"sku": sku, "week_start": w, "forecast_units": val})
    return pd.DataFrame(preds)


def predict_moving_average_baseline(
    train_sales: pd.DataFrame, skus: List[str], test_weeks: List[pd.Timestamp], window: int = 4
) -> pd.DataFrame:
    preds = []
    for sku in skus:
        s = train_sales[train_sales["sku"] == sku].sort_values("week_start")
        val = float(s["units_sold"].tail(window).mean()) if len(s) > 0 else 0.0
        for w in test_weeks:
            preds.append({"sku": sku, "week_start": w, "forecast_units": val})
    return pd.DataFrame(preds)


def predict_seasonal_naive_baseline(
    train_sales: pd.DataFrame, skus: List[str], test_weeks: List[pd.Timestamp]
) -> pd.DataFrame:
    preds = []
    for sku in skus:
        s = train_sales[train_sales["sku"] == sku].set_index("week_start")
        for w in test_weeks:
            last_year = w - pd.DateOffset(weeks=52)
            if last_year in s.index:
                val = float(s.loc[last_year, "units_sold"])
            else:
                val = float(s["units_sold"].tail(4).mean()) if len(s) > 0 else 0.0
            preds.append({"sku": sku, "week_start": w, "forecast_units": val})
    return pd.DataFrame(preds)


def predict_original_rule_based(
    train_sales: pd.DataFrame, skus: List[str], test_weeks: List[pd.Timestamp], test_meta: pd.DataFrame
) -> pd.DataFrame:
    preds = []
    for sku in skus:
        sku_train = train_sales[train_sales["sku"] == sku].sort_values("week_start").copy()
        sku_meta = test_meta[test_meta["sku"] == sku].sort_values("week_start").copy()
        zero_ratio = (sku_train["units_sold"] == 0).mean() if len(sku_train) > 0 else 1.0
        is_short = len(sku_train) < 12
        is_intermittent = zero_ratio > 0.4 or sku_train["units_sold"].mean() < 2.0

        if is_intermittent:
            val = sku_train["units_sold"].tail(12).mean() if len(sku_train) > 0 else 0.5
            for w in test_weeks:
                preds.append({"sku": sku, "week_start": w, "forecast_units": float(val)})
        elif is_short:
            non_promo = sku_train[sku_train["promo_flag"] == 0]
            base_val = non_promo["units_sold"].mean() if len(non_promo) > 0 else (sku_train["units_sold"].mean() if len(sku_train) > 0 else 0.0)
            for _, r in sku_meta.iterrows():
                val = base_val * 2.0 if r["promo_flag"] == 1 else base_val
                preds.append({"sku": sku, "week_start": r["week_start"], "forecast_units": float(val)})
        else:
            non_promo = sku_train[sku_train["promo_flag"] == 0]
            recent_base = non_promo["units_sold"].tail(8).mean() if len(non_promo) >= 4 else (sku_train["units_sold"].tail(4).mean() if len(sku_train) > 0 else 0.0)
            promo_rows = sku_train[sku_train["promo_flag"] == 1]
            if len(promo_rows) >= 2 and len(non_promo) > 0 and non_promo["units_sold"].mean() > 0:
                p_ratio = promo_rows["units_sold"].mean() / non_promo["units_sold"].mean()
                promo_ratio = float(np.clip(p_ratio, 1.2, 3.0))
            else:
                promo_ratio = 2.0

            for _, r in sku_meta.iterrows():
                w = r["week_start"]
                p_flag = r["promo_flag"]
                w_diwali = r["weeks_to_diwali"]
                diwali_hist = non_promo[non_promo["weeks_to_diwali"] == w_diwali]
                diwali_lift = 1.0
                if len(diwali_hist) > 0 and non_promo["units_sold"].mean() > 0:
                    lift_val = diwali_hist["units_sold"].mean() / non_promo["units_sold"].mean()
                    diwali_lift = float(np.clip(lift_val, 0.85, 2.5))
                pred = recent_base * diwali_lift
                if p_flag == 1:
                    pred *= promo_ratio
                preds.append({"sku": sku, "week_start": w, "forecast_units": float(pred)})
    return pd.DataFrame(preds)


def run_temporal_validation(data_dir: Path, cutoff_date: pd.Timestamp, horizon_weeks: int = 4) -> Dict:
    """
    Evaluates candidate and baseline models using expanding-window temporal validation.
    Guarantees no future lookahead data leakage.
    """
    sales, lead = load_data(data_dir)
    train_sales = sales[sales["week_start"] < cutoff_date].copy()
    test_sales = sales[
        (sales["week_start"] >= cutoff_date)
        & (sales["week_start"] < cutoff_date + pd.Timedelta(weeks=horizon_weeks))
    ].copy()

    skus = lead["sku"].unique().tolist()
    test_weeks = sorted(test_sales["week_start"].unique())
    test_meta = test_sales[["sku", "week_start", "promo_flag", "weeks_to_diwali"]].copy()

    # 1. Baseline 1: Naive (last observed value)
    b1_df = predict_naive_baseline(train_sales, skus, test_weeks)
    b1_mae, b1_wape, b1_rmse = evaluate_predictions(test_sales, b1_df)

    # 2. Baseline 2: 4-week Moving Average
    b2_df = predict_moving_average_baseline(train_sales, skus, test_weeks, window=4)
    b2_mae, b2_wape, b2_rmse = evaluate_predictions(test_sales, b2_df)

    # 3. Baseline 3: Seasonal Naive (Lag 52)
    b3_df = predict_seasonal_naive_baseline(train_sales, skus, test_weeks)
    b3_mae, b3_wape, b3_rmse = evaluate_predictions(test_sales, b3_df)

    # 4. Original Rule-Based
    orig_df = predict_original_rule_based(train_sales, skus, test_weeks, test_meta)
    orig_mae, orig_wape, orig_rmse = evaluate_predictions(test_sales, orig_df)

    # 5. Machine Learning (HistGradientBoostingRegressor)
    ml_model = HistGradientBoostingForecaster(random_state=42)
    ml_model.fit(train_sales, skus)
    ml_df = ml_model.predict_recursive(train_sales, skus, test_weeks, test_meta)
    ml_mae, ml_wape, ml_rmse = evaluate_predictions(test_sales, ml_df)

    # 6. Selected Production Model (Hybrid ML + SBA)
    hybrid_pipeline = HybridForecastPipeline(random_state=42)
    cand_df = hybrid_pipeline.fit_and_predict(train_sales, skus, test_weeks, test_meta)
    c_mae, c_wape, c_rmse = evaluate_predictions(test_sales, cand_df)

    # Segment performance breakdown
    intermittent_skus = ["ELE-1031", "GRP-1043", "BRK-1088", "ELE-1006"]
    short_skus = ["BRK-1105", "CHN-1006"]
    established_skus = [s for s in skus if s not in intermittent_skus and s not in short_skus]

    est_test = test_sales[test_sales["sku"].isin(established_skus)]
    int_test = test_sales[test_sales["sku"].isin(intermittent_skus)]
    sh_test = test_sales[test_sales["sku"].isin(short_skus)]

    c_est_mae, c_est_wape, c_est_rmse = evaluate_predictions(est_test, cand_df) if len(est_test) > 0 else (0.0, 0.0, 0.0)
    c_int_mae, c_int_wape, c_int_rmse = evaluate_predictions(int_test, cand_df) if len(int_test) > 0 else (0.0, 0.0, 0.0)
    c_sh_mae, c_sh_wape, c_sh_rmse = evaluate_predictions(sh_test, cand_df) if len(sh_test) > 0 else (0.0, 0.0, 0.0)

    return {
        "cutoff": cutoff_date.strftime("%Y-%m-%d"),
        "naive": {"mae": b1_mae, "wape": b1_wape, "rmse": b1_rmse},
        "moving_average": {"mae": b2_mae, "wape": b2_wape, "rmse": b2_rmse},
        "seasonal_naive": {"mae": b3_mae, "wape": b3_wape, "rmse": b3_rmse},
        "original_rule": {"mae": orig_mae, "wape": orig_wape, "rmse": orig_rmse},
        "hgbr_ml": {"mae": ml_mae, "wape": ml_wape, "rmse": ml_rmse},
        "candidate": {"mae": c_mae, "wape": c_wape, "rmse": c_rmse},
        "segments": {
            "established": {"mae": c_est_mae, "wape": c_est_wape, "rmse": c_est_rmse},
            "intermittent": {"mae": c_int_mae, "wape": c_int_wape, "rmse": c_int_rmse},
            "short_history": {"mae": c_sh_mae, "wape": c_sh_wape, "rmse": c_sh_rmse},
        },
    }


def run_full_evaluation(data_dir: Path) -> pd.DataFrame:
    """Runs temporal validation across 4 chronological historical cutoffs."""
    cutoffs = ["2026-08-24", "2026-07-27", "2026-06-29", "2026-06-01"]
    records = []
    for c_str in cutoffs:
        res = run_temporal_validation(data_dir, pd.to_datetime(c_str))
        records.append({
            "cutoff": res["cutoff"],
            "naive_wape": res["naive"]["wape"],
            "ma_wape": res["moving_average"]["wape"],
            "s_naive_wape": res["seasonal_naive"]["wape"],
            "orig_wape": res["original_rule"]["wape"],
            "hgbr_wape": res["hgbr_ml"]["wape"],
            "candidate_wape": res["candidate"]["wape"],
            "candidate_mae": res["candidate"]["mae"],
            "candidate_rmse": res["candidate"]["rmse"],
        })
    return pd.DataFrame(records)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    print("Running Temporal Validation across 4 Historical Cutoffs...")
    eval_df = run_full_evaluation(data_dir)
    print("\nSummary Table (WAPE by Cutoff):")
    print(eval_df.to_string(index=False))
