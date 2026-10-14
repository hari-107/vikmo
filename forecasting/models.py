import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

# Historical and target Diwali dates
DIWALI_MAP: Dict[int, pd.Timestamp] = {
    2024: pd.to_datetime("2024-11-01"),
    2025: pd.to_datetime("2025-10-21"),
    2026: pd.to_datetime("2026-11-08"),
}


def get_weeks_to_diwali(dt: pd.Timestamp) -> int:
    """
    Computes integer weeks until Diwali for a given calendar week start date.
    Negative values indicate post-Diwali weeks.
    """
    diwali_date = DIWALI_MAP.get(dt.year)
    if diwali_date is None:
        # Fallback to nearest typical Diwali in late October / early November
        diwali_date = pd.to_datetime(f"{dt.year}-11-01")
    return int((diwali_date - dt).days // 7)


def croston_sba(
    series: Union[List[float], np.ndarray, pd.Series],
    alpha: float = 0.1,
    method: str = "sba",
) -> float:
    """
    Croston's Method and Syntetos-Boylan Approximation (SBA) for intermittent demand.
    
    Parameters:
    - series: Historical demand observations.
    - alpha: Exponential smoothing parameter (default 0.1).
    - method: 'sba' (with bias-correction 1 - alpha/2) or 'croston'.
    
    Guarantees:
    - Non-negative output.
    - Gracefully handles zero-only series (returns 0.0).
    - Gracefully handles single positive demand observation.
    - Handles empty series (returns 0.0).
    """
    y = np.asarray(series, dtype=float)
    if len(y) == 0:
        return 0.0

    non_zeros = np.where(y > 0)[0]
    if len(non_zeros) == 0:
        return 0.0

    if len(non_zeros) == 1:
        z = float(y[non_zeros[0]])
        p = float(len(y))
        forecast = z / p
        if method.lower() == "sba":
            forecast *= (1.0 - alpha / 2.0)
        return max(0.0, float(forecast))

    # Initialize at first positive demand
    first_idx = non_zeros[0]
    z = float(y[first_idx])
    p = 1.0
    q = 1.0

    for t in range(first_idx + 1, len(y)):
        if y[t] > 0:
            z = alpha * float(y[t]) + (1.0 - alpha) * z
            p = alpha * q + (1.0 - alpha) * p
            q = 1.0
        else:
            q += 1.0

    if p <= 0:
        return 0.0

    forecast = z / p
    if method.lower() == "sba":
        forecast *= (1.0 - alpha / 2.0)

    return max(0.0, float(forecast))


def estimate_promotional_uplift(
    train_sales: pd.DataFrame,
    sku: str,
    global_prior_ratio: float = 1.85,
    k_shrinkage: float = 3.0,
) -> float:
    """
    Estimates SKU-level promotional uplift using empirical Bayesian shrinkage:
    - Isolates non-festive periods to prevent confounding promotion with festival lift.
    - Shrinks sparse observations towards global non-festive promotional prior.
    - Clips extreme ratios to prevent runaway multipliers.
    """
    sku_train = train_sales[train_sales["sku"] == sku]
    if len(sku_train) == 0:
        return global_prior_ratio

    # Isolate non-festive weeks (weeks_to_diwali < 1 or > 6)
    non_festive = sku_train[(sku_train["weeks_to_diwali"] < 1) | (sku_train["weeks_to_diwali"] > 6)]
    if len(non_festive) == 0:
        non_festive = sku_train

    p_rows = non_festive[non_festive["promo_flag"] == 1]
    np_rows = non_festive[non_festive["promo_flag"] == 0]
    n_p = len(p_rows)

    if n_p > 0 and len(np_rows) > 0 and np_rows["units_sold"].mean() > 0:
        empirical_sku_ratio = p_rows["units_sold"].mean() / np_rows["units_sold"].mean()
        # Bayesian shrinkage towards global prior
        shrunk_ratio = (n_p * empirical_sku_ratio + k_shrinkage * global_prior_ratio) / (n_p + k_shrinkage)
    else:
        shrunk_ratio = global_prior_ratio

    return float(np.clip(shrunk_ratio, 1.2, 2.5))


def calculate_diwali_lift(
    train_sales: pd.DataFrame,
    sku: str,
    target_weeks_to_diwali: int,
) -> float:
    """
    Computes festive uplift for a specific relative distance to Diwali.
    - Uses non-promotional history strictly prior to forecast cutoff (no lookahead bias).
    - Uses adjacent week smoothing if exact relative week was unobserved.
    - Bounded between 0.85 and 2.3 to prevent outlier distortion.
    """
    sku_train = train_sales[train_sales["sku"] == sku]
    if len(sku_train) == 0:
        return 1.0

    non_p = sku_train[sku_train["promo_flag"] == 0]
    if len(non_p) == 0 or non_p["units_sold"].mean() <= 0:
        return 1.0

    baseline_mean = non_p["units_sold"].mean()
    exact_hist = non_p[non_p["weeks_to_diwali"] == target_weeks_to_diwali]

    if len(exact_hist) > 0:
        raw_lift = exact_hist["units_sold"].mean() / baseline_mean
        return float(np.clip(raw_lift, 0.85, 2.3))

    # Adjacent week smoothing if exact week is missing
    adj_hist = non_p[non_p["weeks_to_diwali"].isin([target_weeks_to_diwali - 1, target_weeks_to_diwali + 1])]
    if len(adj_hist) > 0:
        raw_lift = adj_hist["units_sold"].mean() / baseline_mean
        return float(np.clip(raw_lift, 0.85, 2.0))

    return 1.0


class HistGradientBoostingForecaster:
    """
    Machine Learning candidate using HistGradientBoostingRegressor.
    Strictly leakage-safe:
    - Lag features and rolling statistics use only past observations.
    - Recursive multi-step forecasting substitutes model predictions into future lag values.
    - Calendar features (promo flag, weeks to Diwali, festive indicator) use known schedule.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model: Optional[HistGradientBoostingRegressor] = None
        self.sku_to_idx: Dict[str, int] = {}
        self.feature_cols = [
            "sku_cat",
            "lag1",
            "lag2",
            "lag4",
            "lag8",
            "roll4",
            "roll8",
            "zero_ratio",
            "cum_mean",
            "promo_flag",
            "weeks_to_diwali",
            "is_festive",
            "week_of_year",
        ]

    def _build_features(self, df: pd.DataFrame, skus: List[str]) -> pd.DataFrame:
        records = []
        for sku in skus:
            s = df[df["sku"] == sku].sort_values("week_start").reset_index(drop=True)
            if len(s) == 0:
                continue

            y_vals = s["units_sold"].values
            w_vals = s["week_start"].values
            p_vals = s["promo_flag"].values
            d_vals = s["weeks_to_diwali"].values

            for i in range(len(s)):
                if i < 4:
                    continue

                target = y_vals[i]
                lag1 = y_vals[i - 1]
                lag2 = y_vals[i - 2]
                lag4 = y_vals[i - 4]
                lag8 = y_vals[i - 8] if i >= 8 else lag4

                roll4 = np.mean(y_vals[max(0, i - 4) : i])
                roll8 = np.mean(y_vals[max(0, i - 8) : i])
                zero_ratio = np.mean(y_vals[:i] == 0)
                cum_mean = np.mean(y_vals[:i])

                promo = p_vals[i]
                w_diwali = d_vals[i]
                is_festive = 1.0 if (1 <= w_diwali <= 6) else 0.0
                dt = pd.to_datetime(w_vals[i])
                week_of_year = dt.isocalendar().week

                records.append({
                    "sku": sku,
                    "sku_cat": self.sku_to_idx.get(sku, 0),
                    "target": target,
                    "lag1": lag1,
                    "lag2": lag2,
                    "lag4": lag4,
                    "lag8": lag8,
                    "roll4": roll4,
                    "roll8": roll8,
                    "zero_ratio": zero_ratio,
                    "cum_mean": cum_mean,
                    "promo_flag": promo,
                    "weeks_to_diwali": w_diwali,
                    "is_festive": is_festive,
                    "week_of_year": week_of_year,
                })

        return pd.DataFrame(records)

    def fit(self, train_sales: pd.DataFrame, skus: List[str]):
        self.sku_to_idx = {sku: idx for idx, sku in enumerate(skus)}
        feat_df = self._build_features(train_sales, skus)
        if len(feat_df) == 0:
            return self

        X_train = feat_df[self.feature_cols].values
        y_train = feat_df["target"].values

        self.model = HistGradientBoostingRegressor(
            max_iter=120,
            learning_rate=0.06,
            min_samples_leaf=8,
            l2_regularization=1.5,
            categorical_features=[0],
            random_state=self.random_state,
        )
        self.model.fit(X_train, y_train)
        return self

    def predict_recursive(
        self,
        train_sales: pd.DataFrame,
        skus: List[str],
        test_weeks: List[pd.Timestamp],
        test_meta: pd.DataFrame,
    ) -> pd.DataFrame:
        preds = []
        for sku in skus:
            sku_hist = train_sales[train_sales["sku"] == sku].sort_values("week_start").copy()
            sku_meta = test_meta[test_meta["sku"] == sku].sort_values("week_start").copy()

            if len(sku_hist) == 0 or self.model is None:
                for w in test_weeks:
                    preds.append({"sku": sku, "week_start": w, "forecast_units": 0.0})
                continue

            history_vals = list(sku_hist["units_sold"].values)

            for _, r in sku_meta.iterrows():
                w = r["week_start"]
                p_flag = r["promo_flag"]
                w_diwali = r["weeks_to_diwali"]
                dt = pd.to_datetime(w)

                lag1 = history_vals[-1]
                lag2 = history_vals[-2] if len(history_vals) >= 2 else lag1
                lag4 = history_vals[-4] if len(history_vals) >= 4 else lag1
                lag8 = history_vals[-8] if len(history_vals) >= 8 else lag4

                roll4 = np.mean(history_vals[-4:])
                roll8 = np.mean(history_vals[-8:])
                zero_ratio = np.mean(np.array(history_vals) == 0)
                cum_mean = np.mean(history_vals)

                is_festive = 1.0 if (1 <= w_diwali <= 6) else 0.0
                woy = dt.isocalendar().week

                feat_vector = np.array([[
                    self.sku_to_idx.get(sku, 0),
                    lag1,
                    lag2,
                    lag4,
                    lag8,
                    roll4,
                    roll8,
                    zero_ratio,
                    cum_mean,
                    p_flag,
                    w_diwali,
                    is_festive,
                    woy,
                ]])

                pred_val = float(self.model.predict(feat_vector)[0])
                pred_val = max(0.0, pred_val)

                history_vals.append(pred_val)
                preds.append({"sku": sku, "week_start": w, "forecast_units": round(pred_val, 2)})

        return pd.DataFrame(preds)


class HybridForecastPipeline:
    """
    Production-quality hybrid demand forecasting pipeline.
    Routes SKUs adaptively:
    - Intermittent demand SKUs (zero_ratio > 0.4 or mean < 2.0): Syntetos-Boylan Approximation (SBA)
    - Short history SKUs (len < 12 weeks): Non-promotional shrinkage baseline
    - Established SKUs (len >= 12 weeks): HistGradientBoostingRegressor (ML)
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.ml_forecaster = HistGradientBoostingForecaster(random_state=random_state)

    def fit_and_predict(
        self,
        train_sales: pd.DataFrame,
        skus: List[str],
        test_weeks: List[pd.Timestamp],
        test_meta: pd.DataFrame,
    ) -> pd.DataFrame:
        # Calculate global non-festive promotional prior
        non_festive = train_sales[(train_sales["weeks_to_diwali"] < 1) | (train_sales["weeks_to_diwali"] > 6)]
        global_p = non_festive[non_festive["promo_flag"] == 1]["units_sold"].mean()
        global_np = non_festive[non_festive["promo_flag"] == 0]["units_sold"].mean()
        global_prior = float(global_p / global_np) if (global_np and global_np > 0) else 1.85
        global_prior = float(np.clip(global_prior, 1.4, 2.2))

        # Train ML candidate on full training sales
        self.ml_forecaster.fit(train_sales, skus)
        ml_preds_df = self.ml_forecaster.predict_recursive(train_sales, skus, test_weeks, test_meta)
        ml_pred_map = {(r["sku"], r["week_start"]): r["forecast_units"] for _, r in ml_preds_df.iterrows()}

        output_rows = []
        for sku in skus:
            sku_train = train_sales[train_sales["sku"] == sku].sort_values("week_start").copy()
            sku_meta = test_meta[test_meta["sku"] == sku].sort_values("week_start").copy()

            if len(sku_train) == 0:
                for w in test_weeks:
                    output_rows.append({"sku": sku, "week_start": w, "forecast_units": 0.0})
                continue

            zero_ratio = (sku_train["units_sold"] == 0).mean()
            mean_demand = sku_train["units_sold"].mean()
            is_short = len(sku_train) < 12
            is_intermittent = (zero_ratio > 0.4) or (mean_demand < 2.0)

            if is_intermittent:
                # 1. Intermittent demand: Syntetos-Boylan Approximation (SBA)
                sba_val = croston_sba(sku_train["units_sold"], alpha=0.1, method="sba")
                for w in test_weeks:
                    output_rows.append({
                        "sku": sku,
                        "week_start": w,
                        "forecast_units": round(float(max(0.0, sba_val)), 1),
                    })

            elif is_short:
                # 2. Short history: Regularized non-promo baseline with prior promo multiplier
                non_p = sku_train[sku_train["promo_flag"] == 0]
                base_units = non_p["units_sold"].mean() if len(non_p) > 0 else mean_demand
                base_units = max(0.0, float(base_units))
                for _, r in sku_meta.iterrows():
                    w = r["week_start"]
                    p_flag = r["promo_flag"]
                    pred = base_units * global_prior if p_flag == 1 else base_units
                    output_rows.append({
                        "sku": sku,
                        "week_start": w,
                        "forecast_units": round(float(max(0.0, pred)), 1),
                    })

            else:
                # 3. Established SKUs: HistGradientBoostingRegressor predictions
                for _, r in sku_meta.iterrows():
                    w = r["week_start"]
                    pred_val = ml_pred_map.get((sku, w), mean_demand)
                    output_rows.append({
                        "sku": sku,
                        "week_start": w,
                        "forecast_units": round(float(max(0.0, pred_val)), 1),
                    })

        return pd.DataFrame(output_rows)
