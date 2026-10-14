from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from .models import Product, Dealer, Order, OrderItem


class MoneyField(serializers.Field):
    """Formats decimal values as string with exactly 2 decimal places."""

    def to_representation(self, value):
        if value is None:
            return "0.00"
        d = Decimal(str(value))
        return f"{d:.2f}"

    def to_internal_value(self, data):
        if data is None or data == "":
            raise serializers.ValidationError("Price is required.")
        try:
            d = Decimal(str(data))
        except Exception:
            raise serializers.ValidationError("Invalid decimal value.")
        return d


class ProductSerializer(serializers.ModelSerializer):
    price = MoneyField()
    stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "category",
            "brand",
            "vehicle_fitment",
            "price",
            "stock",
            "description",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        # Check decimal places
        str_val = str(value)
        if "." in str_val and len(str_val.split(".")[1]) > 2:
            raise serializers.ValidationError("Price must have at most 2 decimal places.")
        return value


class DealerSerializer(serializers.ModelSerializer):
    credit_limit = MoneyField(required=False, default=Decimal("0.00"))

    class Meta:
        model = Dealer
        fields = [
            "id",
            "dealer_code",
            "name",
            "city",
            "phone",
            "email",
            "gstin",
            "credit_limit",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    unit_price = MoneyField(read_only=True)
    line_subtotal = MoneyField(read_only=True)
    line_tax = MoneyField(read_only=True)
    line_total = MoneyField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "sku",
            "name",
            "quantity",
            "unit_price",
            "line_subtotal",
            "line_tax",
            "line_total",
        ]


class OrderSerializer(serializers.ModelSerializer):
    dealer_id = serializers.IntegerField(source="dealer.id", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    subtotal = MoneyField(read_only=True)
    tax_total = MoneyField(read_only=True)
    grand_total = MoneyField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z", read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_number",
            "dealer_id",
            "status",
            "items",
            "subtotal",
            "tax_total",
            "grand_total",
            "created_at",
            "updated_at",
        ]
