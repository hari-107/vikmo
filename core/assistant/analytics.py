import csv
import math
from pathlib import Path
from django.conf import settings
from core.models import Product


def get_sku_forecast(sku: str) -> dict | None:
    """Reads ml/forecast.csv and returns weekly predictions for the given SKU."""
    clean_sku = sku.strip().upper() if sku else ""
    if not clean_sku:
        return None

    forecast_path = Path(settings.BASE_DIR) / "ml" / "forecast.csv"
    if not forecast_path.exists():
        return None

    weeks_data = []
    with open(forecast_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["sku"].strip().upper() == clean_sku:
                try:
                    units = float(row["forecast_units"].strip())
                except (ValueError, TypeError):
                    units = 0.0
                weeks_data.append({
                    "week_start": row["week_start"].strip(),
                    "forecast_units": units,
                })

    if not weeks_data:
        return None

    weeks_data.sort(key=lambda x: x["week_start"])
    total_demand = sum(w["forecast_units"] for w in weeks_data)
    return {
        "sku": clean_sku,
        "weeks": weeks_data,
        "total_units": round(total_demand, 1),
    }


def get_reorder_recommendations(limit: int = 5) -> list[dict]:
    """Computes real reorder recommendations using forecast, lead times, and current stock."""
    base_dir = Path(settings.BASE_DIR)
    forecast_path = base_dir / "ml" / "forecast.csv"
    lead_path = base_dir / "data" / "lead_times.csv"
    sales_path = base_dir / "data" / "sales_history.csv"

    if not (forecast_path.exists() and lead_path.exists() and sales_path.exists()):
        return []

    # 1. Lead times
    lead_times = {}
    with open(lead_path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                lead_times[row["sku"].strip()] = max(1, int(row["lead_time_weeks"].strip()))
            except (ValueError, KeyError):
                pass

    # 2. Weekly forecast
    forecast_map = {}
    with open(forecast_path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sku = row["sku"].strip()
            if sku not in forecast_map:
                forecast_map[sku] = []
            try:
                val = float(row["forecast_units"].strip())
            except ValueError:
                val = 0.0
            forecast_map[sku].append({"week_start": row["week_start"].strip(), "forecast_units": val})

    for sku in forecast_map:
        forecast_map[sku].sort(key=lambda x: x["week_start"])

    # 3. Weekly sales std dev
    sales_map = {}
    with open(sales_path, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sku = row["sku"].strip()
            if sku not in sales_map:
                sales_map[sku] = []
            try:
                sales_map[sku].append(float(row["units_sold"].strip()))
            except ValueError:
                pass

    sigma_map = {}
    for sku, vals in sales_map.items():
        if len(vals) < 2:
            sigma_map[sku] = 0.0
        else:
            mean = sum(vals) / len(vals)
            var = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
            sigma_map[sku] = math.sqrt(var)

    # 4. Products in DB
    all_skus = set(lead_times.keys()) & set(forecast_map.keys())
    products = {p.sku: p for p in Product.objects.filter(sku__in=all_skus)}

    recommendations = []
    for sku in sorted(all_skus):
        prod = products.get(sku)
        if not prod:
            continue

        L = lead_times.get(sku, 2)
        fc_list = forecast_map.get(sku, [])
        lead_time_demand = sum(item["forecast_units"] for item in fc_list[:L])
        sigma = sigma_map.get(sku, 0.0)
        safety_stock = 1.65 * math.sqrt(L) * sigma
        reorder_point = math.ceil(lead_time_demand + safety_stock)
        current_stock = prod.stock

        if current_stock <= reorder_point:
            needed = max(0, reorder_point - current_stock)
            recommendations.append({
                "sku": sku,
                "name": prod.name,
                "current_stock": current_stock,
                "reorder_point": reorder_point,
                "recommended_quantity": needed,
                "lead_time_weeks": L,
                "unit_price": f"{prod.price:.2f}",
            })

    # Sort by urgency (ratio of stock to reorder point)
    recommendations.sort(key=lambda x: (x["current_stock"] / max(1, x["reorder_point"]), -x["recommended_quantity"]))
    return recommendations[:limit]
