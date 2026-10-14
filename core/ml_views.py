import csv
import math
import statistics
from pathlib import Path
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import Product
from core.exceptions import ApiNotFoundError


def get_paths():
    base_dir = Path(settings.BASE_DIR)
    forecast_path = base_dir / "ml" / "forecast.csv"
    data_dir = getattr(settings, "DATA_DIR", base_dir / "data")
    lead_path = Path(data_dir) / "lead_times.csv"
    sales_path = Path(data_dir) / "sales_history.csv"
    return forecast_path, lead_path, sales_path


class ForecastDetailView(APIView):
    def get(self, request, sku):
        clean_sku = sku.strip().upper()
        forecast_path, _, _ = get_paths()

        if not forecast_path.exists():
            raise ApiNotFoundError(f"Forecast file not found at {forecast_path}")

        weeks_data = []
        with open(forecast_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["sku"].strip().upper() == clean_sku:
                    weeks_data.append({
                        "week_start": row["week_start"].strip(),
                        "forecast_units": float(row["forecast_units"].strip()),
                    })

        if not weeks_data:
            raise ApiNotFoundError(f"Forecast for SKU '{clean_sku}' not found")

        # Sort by week_start ascending
        weeks_data.sort(key=lambda x: x["week_start"])

        return Response({
            "sku": clean_sku,
            "forecast": weeks_data,
        })


class ReorderSuggestionsView(APIView):
    def get(self, request):
        forecast_path, lead_path, sales_path = get_paths()

        if not forecast_path.exists() or not lead_path.exists() or not sales_path.exists():
            raise ApiNotFoundError("Required forecast or data files missing")

        # 1. Read lead_times.csv
        lead_times = {}
        ordered_skus = []
        with open(lead_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row["sku"].strip()
                lead_times[sku] = int(row["lead_time_weeks"].strip())
                ordered_skus.append(sku)

        # 2. Read forecast.csv
        forecast_map = {}
        with open(forecast_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row["sku"].strip()
                if sku not in forecast_map:
                    forecast_map[sku] = []
                forecast_map[sku].append({
                    "week_start": row["week_start"].strip(),
                    "forecast_units": float(row["forecast_units"].strip()),
                })

        for sku in forecast_map:
            forecast_map[sku].sort(key=lambda x: x["week_start"])

        # 3. Read sales_history.csv to compute sigma over most recent 12 weeks
        sales_map = {}
        with open(sales_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row["sku"].strip()
                if sku not in sales_map:
                    sales_map[sku] = []
                sales_map[sku].append({
                    "week_start": row["week_start"].strip(),
                    "units_sold": float(row["units_sold"].strip()),
                })

        for sku in sales_map:
            sales_map[sku].sort(key=lambda x: x["week_start"])

        # 4. Fetch live stock from Product table
        live_products = {p.sku.strip().upper(): p.stock for p in Product.objects.filter(sku__in=ordered_skus)}

        # 5. Compute reorder metrics for all 40 SKUs
        results = []
        for sku in ordered_skus:
            L = lead_times.get(sku, 1)
            fc_list = forecast_map.get(sku, [])

            # lead_time_demand = sum of forecast_units for the first L forecast weeks
            lead_time_demand = sum(item["forecast_units"] for item in fc_list[:L])
            lead_time_demand = round(lead_time_demand, 1)

            # sigma = sample standard deviation (ddof=1, n-1) over last 12 weeks
            sku_sales = sales_map.get(sku, [])
            recent_sales = [x["units_sold"] for x in sku_sales[-12:]]

            if len(recent_sales) > 1:
                sigma = statistics.stdev(recent_sales)
            elif len(recent_sales) == 1:
                sigma = 0.0
            else:
                sigma = 0.0

            # safety_stock = ceil(1.65 * sigma * sqrt(L))
            safety_stock = math.ceil(1.65 * sigma * math.sqrt(L))

            # reorder_point = lead_time_demand + safety_stock
            reorder_point = round(lead_time_demand + safety_stock, 1)

            # current_stock: LIVE available stock
            current_stock = live_products.get(sku.strip().upper(), 0)

            # reorder_qty = max(0, ceil(reorder_point - current_stock))
            reorder_qty = max(0, math.ceil(reorder_point - current_stock))

            results.append({
                "sku": sku,
                "current_stock": current_stock,
                "lead_time_weeks": L,
                "lead_time_demand": lead_time_demand,
                "safety_stock": safety_stock,
                "reorder_point": reorder_point,
                "reorder_qty": reorder_qty,
            })

        return Response({"results": results})
