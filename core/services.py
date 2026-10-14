import hashlib
import json
import zoneinfo
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
from .models import Product, Dealer, Order, OrderItem, OrderStatus, IdempotencyRecord
from .exceptions import (
    ApiValidationError,
    ApiNotFoundError,
    ApiInsufficientStockError,
    ApiInvalidTransitionError,
    ApiOrderLockedError,
    ApiIdempotencyConflictError,
)

KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")


def generate_order_number() -> str:
    """Generates unique ORD-YYYYMMDD-NNNN in Asia/Kolkata timezone."""
    now_kolkata = timezone.localtime(timezone.now(), KOLKATA_TZ)
    date_str = now_kolkata.strftime("%Y%m%d")
    prefix = f"ORD-{date_str}-"

    # Query latest order today with lock to avoid race conditions
    last_order = (
        Order.objects.filter(order_number__startswith=prefix)
        .order_by("-order_number")
        .select_for_update()
        .first()
    )

    if last_order:
        last_seq = int(last_order.order_number.split("-")[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:04d}"


def calculate_order_totals(items_data):
    """
    Validates items and computes line items and order totals.
    Uses ROUND_HALF_UP for GST 18% per line item.
    """
    if not items_data or not isinstance(items_data, list):
        raise ApiValidationError("Order must have at least one item", details=[{"field": "items", "error": "Must not be empty"}])

    skus_seen = set()
    sku_list = []
    quantities = {}

    for idx, item in enumerate(items_data):
        if not isinstance(item, dict):
            raise ApiValidationError(f"Invalid item format at index {idx}")
        sku = item.get("sku")
        qty = item.get("quantity")

        if not sku or not isinstance(sku, str):
            raise ApiValidationError(f"Missing or invalid SKU at item index {idx}")

        if sku in skus_seen:
            raise ApiValidationError(
                f"Duplicate SKU '{sku}' in order items",
                details=[{"field": "items", "error": f"Duplicate SKU {sku}"}],
            )
        skus_seen.add(sku)
        sku_list.append(sku)

        if qty is None or not isinstance(qty, int) or qty < 1:
            raise ApiValidationError(
                f"Quantity for SKU '{sku}' must be an integer >= 1",
                details=[{"field": f"items[{idx}].quantity", "error": "Must be integer >= 1"}],
            )
        quantities[sku] = qty

    # Fetch products
    products = {p.sku: p for p in Product.objects.filter(sku__in=sku_list)}
    missing_skus = [s for s in sku_list if s not in products]
    if missing_skus:
        raise ApiValidationError(
            f"Unknown SKU(s): {', '.join(missing_skus)}",
            details=[{"field": "items", "error": f"SKU {s} does not exist"} for s in missing_skus],
        )

    computed_lines = []
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")

    for sku in sku_list:
        product = products[sku]
        qty = quantities[sku]
        unit_price = product.price
        line_sub = (unit_price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line_tax = (line_sub * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line_tot = line_sub + line_tax

        computed_lines.append({
            "product": product,
            "sku": sku,
            "name": product.name,
            "quantity": qty,
            "unit_price": unit_price,
            "line_subtotal": line_sub,
            "line_tax": line_tax,
            "line_total": line_tot,
        })
        subtotal += line_sub
        tax_total += line_tax

    grand_total = subtotal + tax_total

    return computed_lines, subtotal, tax_total, grand_total


def create_draft_order(dealer_id, items_data, idempotency_key=None, raw_body=None):
    """Creates a DRAFT order with full validation and idempotency handling."""
    if idempotency_key:
        payload_hash = hashlib.sha256(raw_body or b"").hexdigest()
        existing = IdempotencyRecord.objects.filter(key=idempotency_key).first()
        if existing:
            if existing.request_hash == payload_hash:
                return existing.response_data, existing.status_code, False
            else:
                raise ApiIdempotencyConflictError("Idempotency key reused with different request payload")

    if not dealer_id:
        raise ApiValidationError("dealer_id is required", details=[{"field": "dealer_id", "error": "Required"}])

    dealer = Dealer.objects.filter(id=dealer_id).first()
    if not dealer:
        raise ApiValidationError(f"Dealer with id {dealer_id} does not exist", details=[{"field": "dealer_id", "error": "Not found"}])

    with transaction.atomic():
        computed_lines, subtotal, tax_total, grand_total = calculate_order_totals(items_data)
        order_number = generate_order_number()

        order = Order.objects.create(
            order_number=order_number,
            dealer=dealer,
            status=OrderStatus.DRAFT,
            subtotal=subtotal,
            tax_total=tax_total,
            grand_total=grand_total,
        )

        for line in computed_lines:
            OrderItem.objects.create(
                order=order,
                product=line["product"],
                sku=line["sku"],
                name=line["name"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                line_subtotal=line["line_subtotal"],
                line_tax=line["line_tax"],
                line_total=line["line_total"],
            )

        from .serializers import OrderSerializer
        serializer_data = OrderSerializer(order).data

        if idempotency_key:
            IdempotencyRecord.objects.create(
                key=idempotency_key,
                request_hash=payload_hash,
                status_code=201,
                response_data=serializer_data,
            )

        return serializer_data, 201, True


def update_draft_order(order_number, items_data):
    """Replaces all items in a DRAFT order."""
    order = Order.objects.filter(order_number=order_number).first()
    if not order:
        raise ApiNotFoundError(f"Order {order_number} not found")

    if order.status != OrderStatus.DRAFT:
        raise ApiOrderLockedError(f"Order {order_number} is in status '{order.status}' and cannot be edited")

    with transaction.atomic():
        computed_lines, subtotal, tax_total, grand_total = calculate_order_totals(items_data)

        order.items.all().delete()
        for line in computed_lines:
            OrderItem.objects.create(
                order=order,
                product=line["product"],
                sku=line["sku"],
                name=line["name"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                line_subtotal=line["line_subtotal"],
                line_tax=line["line_tax"],
                line_total=line["line_total"],
            )

        order.subtotal = subtotal
        order.tax_total = tax_total
        order.grand_total = grand_total
        order.save()

    from .serializers import OrderSerializer
    return OrderSerializer(order).data


def confirm_order(order_number):
    """DRAFT -> CONFIRMED. Atomically checks and deducts stock."""
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(order_number=order_number).first()
        if not order:
            raise ApiNotFoundError(f"Order {order_number} not found")

        if order.status != OrderStatus.DRAFT:
            raise ApiInvalidTransitionError(
                f"Cannot confirm order in status '{order.status}'",
                details=[{"field": "status", "error": f"Invalid transition from {order.status} to CONFIRMED"}],
            )

        items = list(order.items.select_related("product").all())
        product_ids = [item.product_id for item in items]
        locked_products = {p.id: p for p in Product.objects.filter(id__in=product_ids).select_for_update()}

        short_lines = []
        messages = []
        for item in items:
            p = locked_products[item.product_id]
            if item.quantity > p.stock:
                short_lines.append({
                    "sku": item.sku,
                    "requested": item.quantity,
                    "available": p.stock,
                })
                messages.append(
                    f"Insufficient stock for {item.name}. Available: {p.stock}, Requested: {item.quantity}"
                )

        if short_lines:
            raise ApiInsufficientStockError(
                message=". ".join(messages),
                details=short_lines,
            )

        # Deduct stock and lock prices
        for item in items:
            p = locked_products[item.product_id]
            p.stock -= item.quantity
            p.save(update_fields=["stock"])

        order.status = OrderStatus.CONFIRMED
        order.save(update_fields=["status", "updated_at"])

    from .serializers import OrderSerializer
    return OrderSerializer(order).data


def dispatch_order(order_number):
    """CONFIRMED -> DISPATCHED."""
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(order_number=order_number).first()
        if not order:
            raise ApiNotFoundError(f"Order {order_number} not found")

        if order.status != OrderStatus.CONFIRMED:
            raise ApiInvalidTransitionError(
                f"Cannot dispatch order in status '{order.status}'",
                details=[{"field": "status", "error": f"Invalid transition from {order.status} to DISPATCHED"}],
            )

        order.status = OrderStatus.DISPATCHED
        order.save(update_fields=["status", "updated_at"])

    from .serializers import OrderSerializer
    return OrderSerializer(order).data


def deliver_order(order_number):
    """DISPATCHED -> DELIVERED."""
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(order_number=order_number).first()
        if not order:
            raise ApiNotFoundError(f"Order {order_number} not found")

        if order.status != OrderStatus.DISPATCHED:
            raise ApiInvalidTransitionError(
                f"Cannot deliver order in status '{order.status}'",
                details=[{"field": "status", "error": f"Invalid transition from {order.status} to DELIVERED"}],
            )

        order.status = OrderStatus.DELIVERED
        order.save(update_fields=["status", "updated_at"])

    from .serializers import OrderSerializer
    return OrderSerializer(order).data


def cancel_order(order_number):
    """
    DRAFT -> CANCELLED (no stock change)
    CONFIRMED -> CANCELLED (restores stock exactly once)
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(order_number=order_number).first()
        if not order:
            raise ApiNotFoundError(f"Order {order_number} not found")

        if order.status not in (OrderStatus.DRAFT, OrderStatus.CONFIRMED):
            raise ApiInvalidTransitionError(
                f"Cannot cancel order in status '{order.status}'",
                details=[{"field": "status", "error": f"Invalid transition from {order.status} to CANCELLED"}],
            )

        if order.status == OrderStatus.CONFIRMED:
            # Restore stock
            items = list(order.items.select_related("product").all())
            product_ids = [item.product_id for item in items]
            locked_products = {p.id: p for p in Product.objects.filter(id__in=product_ids).select_for_update()}

            for item in items:
                p = locked_products[item.product_id]
                p.stock += item.quantity
                p.save(update_fields=["stock"])

        order.status = OrderStatus.CANCELLED
        order.save(update_fields=["status", "updated_at"])

    from .serializers import OrderSerializer
    return OrderSerializer(order).data
