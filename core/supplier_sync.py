import time
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
import requests
from django.conf import settings
from django.db import transaction
from core.models import Product
from core.exceptions import ApiSupplierUnavailableError

logger = logging.getLogger(__name__)


def is_valid_price(price_val):
    if price_val is None:
        return False
    try:
        d = Decimal(str(price_val))
        if d <= 0:
            return False
        parts = str(d).split(".")
        if len(parts) > 1 and len(parts[1]) > 2:
            return False
        return True
    except (InvalidOperation, TypeError, ValueError):
        return False


def run_supplier_sync():
    api_url = getattr(settings, "SUPPLIER_API_URL", "http://127.0.0.1:8099").rstrip("/")
    api_key = getattr(settings, "SUPPLIER_API_KEY", "")

    headers = {"X-Api-Key": api_key}
    cursor = None
    all_raw_items = []
    pages_fetched = 0
    requests_made = 0

    # Step 1: Fetch all pages with retry logic
    while True:
        url = f"{api_url}/v1/products"
        params = {"limit": 20}
        if cursor:
            params["cursor"] = cursor

        page_success = False
        page_items = []
        next_cursor = None

        for attempt in range(1, 6):
            requests_made += 1
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    page_items = data.get("items", [])
                    next_cursor = data.get("next_cursor")
                    page_success = True
                    pages_fetched += 1
                    break
                elif resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "1")
                    try:
                        wait_sec = max(1, int(retry_after))
                    except ValueError:
                        wait_sec = 1
                    time.sleep(wait_sec)
                    continue
                elif resp.status_code == 401:
                    # Invalid API key fails sync immediately
                    raise ApiSupplierUnavailableError("Supplier API key invalid (401)")
                elif resp.status_code in (500, 502, 503):
                    time.sleep(0.5 * attempt)
                    continue
                else:
                    # Other client error
                    time.sleep(0.5 * attempt)
                    continue
            except requests.RequestException as e:
                time.sleep(0.5 * attempt)
                continue

        if not page_success:
            raise ApiSupplierUnavailableError("Supplier API failed to respond after 5 attempts")

        all_raw_items.extend(page_items)
        if not next_cursor:
            break
        cursor = next_cursor

    # Step 2: Validate and filter items
    valid_items = []
    rejected = []

    for it in all_raw_items:
        supplier_sku = it.get("supplier_sku", "")
        sku = it.get("sku")
        price = it.get("price")

        if not sku or not str(sku).strip():
            rejected.append({"supplier_sku": supplier_sku, "reason": "missing or empty sku"})
            continue

        if not is_valid_price(price):
            rejected.append({"supplier_sku": supplier_sku, "reason": "invalid price"})
            continue

        valid_items.append(it)

    # Step 3: Resolve duplicate SKUs using latest updated_at
    latest_by_sku = {}
    for it in valid_items:
        sku = str(it["sku"]).strip()
        updated_at_str = it.get("updated_at", "")
        try:
            # Parse ISO datetime
            dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            dt = datetime.min

        if sku not in latest_by_sku or dt > latest_by_sku[sku][0]:
            latest_by_sku[sku] = (dt, it)

    unique_items = [v[1] for v in latest_by_sku.values()]

    # Step 4: Apply to database atomically (all or nothing)
    created_count = 0
    updated_count = 0
    unchanged_count = 0

    with transaction.atomic():
        skus_to_check = [it["sku"].strip() for it in unique_items]
        existing_products = {p.sku: p for p in Product.objects.filter(sku__in=skus_to_check)}

        for it in unique_items:
            sku = it["sku"].strip()
            name = it.get("name", "").strip()
            category = it.get("category", "").strip()
            brand = it.get("brand", "").strip()
            vehicle_fitment = it.get("vehicle_fitment", "").strip()
            description = it.get("description", "").strip()
            price = Decimal(str(it["price"]))

            if sku not in existing_products:
                # Create with stock 0
                Product.objects.create(
                    sku=sku,
                    name=name,
                    category=category,
                    brand=brand,
                    vehicle_fitment=vehicle_fitment,
                    description=description,
                    price=price,
                    stock=0,
                )
                created_count += 1
            else:
                p = existing_products[sku]
                # Compare fields
                diff = (
                    p.name != name
                    or p.category != category
                    or p.brand != brand
                    or p.vehicle_fitment != vehicle_fitment
                    or p.description != description
                    or p.price != price
                )
                if diff:
                    p.name = name
                    p.category = category
                    p.brand = brand
                    p.vehicle_fitment = vehicle_fitment
                    p.description = description
                    p.price = price
                    p.save(update_fields=["name", "category", "brand", "vehicle_fitment", "description", "price", "updated_at"])
                    updated_count += 1
                else:
                    unchanged_count += 1

    return {
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "rejected": rejected,
        "pages_fetched": pages_fetched,
        "requests_made": requests_made,
    }
