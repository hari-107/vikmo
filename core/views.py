from decimal import Decimal
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Product, Dealer, Order, OrderStatus
from .serializers import ProductSerializer, DealerSerializer, OrderSerializer
from .pagination import StandardResultsSetPagination
from .exceptions import (
    ApiValidationError,
    ApiNotFoundError,
    ApiDuplicateError,
)
from .services import (
    create_draft_order,
    update_draft_order,
    confirm_order,
    dispatch_order,
    deliver_order,
    cancel_order,
)


def health(request):
    """GET /api/health/ — health check endpoint."""
    return JsonResponse({"status": "ok"})


class ProductListCreateView(APIView):
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Product.objects.all().order_by("sku")

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(sku__icontains=search) | Q(name__icontains=search) | Q(brand__icontains=search)
            )

        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        vehicle = request.query_params.get("vehicle")
        if vehicle:
            queryset = queryset.filter(vehicle_fitment__icontains=vehicle)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        sku = request.data.get("sku")
        if not sku:
            raise ApiValidationError("sku is required", details=[{"field": "sku", "error": "Required"}])

        if Product.objects.filter(sku=sku).exists():
            raise ApiDuplicateError(f"Product with SKU '{sku}' already exists")

        serializer = ProductSerializer(data=request.data)
        if not serializer.is_valid():
            errors = []
            for f, err in serializer.errors.items():
                errors.append({"field": f, "error": str(err[0]) if isinstance(err, list) else str(err)})
            raise ApiValidationError("Invalid product data", details=errors)

        product = serializer.save(stock=0)
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    def get_object(self, sku):
        product = Product.objects.filter(sku=sku).first()
        if not product:
            raise ApiNotFoundError(f"Product with SKU '{sku}' not found")
        return product

    def get(self, request, sku):
        product = self.get_object(sku)
        return Response(ProductSerializer(product).data)

    def patch(self, request, sku):
        product = self.get_object(sku)

        if "sku" in request.data and request.data["sku"] != sku:
            raise ApiValidationError("SKU cannot be changed")

        serializer = ProductSerializer(product, data=request.data, partial=True)
        if not serializer.is_valid():
            errors = []
            for f, err in serializer.errors.items():
                errors.append({"field": f, "error": str(err[0]) if isinstance(err, list) else str(err)})
            raise ApiValidationError("Invalid product update data", details=errors)

        product = serializer.save()
        return Response(ProductSerializer(product).data)


class InventoryView(APIView):
    def put(self, request, sku):
        product = Product.objects.filter(sku=sku).first()
        if not product:
            raise ApiNotFoundError(f"Product with SKU '{sku}' not found")

        qty_raw = request.data.get("quantity")
        if qty_raw is None:
            raise ApiValidationError("quantity is required", details=[{"field": "quantity", "error": "Required"}])

        # Validate integer type strictly: reject floats and negative numbers
        if isinstance(qty_raw, bool) or not isinstance(qty_raw, int) or qty_raw < 0:
            raise ApiValidationError(
                "Quantity must be an integer >= 0",
                details=[{"field": "quantity", "error": "Must be integer >= 0"}],
            )

        product.stock = qty_raw
        product.save(update_fields=["stock", "updated_at"])

        return Response({"sku": product.sku, "quantity": product.stock})


class DealerListCreateView(APIView):
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Dealer.objects.all().order_by("id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DealerSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        dealer_code = request.data.get("dealer_code")
        name = request.data.get("name")

        if not dealer_code or not str(dealer_code).strip():
            raise ApiValidationError("dealer_code is required", details=[{"field": "dealer_code", "error": "Required"}])
        if not name or not str(name).strip():
            raise ApiValidationError("name is required", details=[{"field": "name", "error": "Required"}])

        if Dealer.objects.filter(dealer_code=dealer_code).exists():
            raise ApiDuplicateError(f"Dealer with code '{dealer_code}' already exists")

        serializer = DealerSerializer(data=request.data)
        if not serializer.is_valid():
            errors = []
            for f, err in serializer.errors.items():
                errors.append({"field": f, "error": str(err[0]) if isinstance(err, list) else str(err)})
            raise ApiValidationError("Invalid dealer data", details=errors)

        dealer = serializer.save()
        return Response(DealerSerializer(dealer).data, status=status.HTTP_201_CREATED)


class DealerDetailView(APIView):
    def get(self, request, pk):
        dealer = Dealer.objects.filter(id=pk).first()
        if not dealer:
            raise ApiNotFoundError(f"Dealer with ID {pk} not found")
        return Response(DealerSerializer(dealer).data)


class OrderListCreateView(APIView):
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Order.objects.all().prefetch_related("items").order_by("-created_at")

        dealer_id = request.query_params.get("dealer_id")
        if dealer_id:
            queryset = queryset.filter(dealer_id=dealer_id)

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        idempotency_key = request.headers.get("Idempotency-Key")
        dealer_id = request.data.get("dealer_id")
        items_data = request.data.get("items")

        order_data, status_code, _ = create_draft_order(
            dealer_id=dealer_id,
            items_data=items_data,
            idempotency_key=idempotency_key,
            raw_body=request.body,
        )
        return Response(order_data, status=status_code)


class OrderDetailView(APIView):
    def get(self, request, order_number):
        order = Order.objects.filter(order_number=order_number).prefetch_related("items").first()
        if not order:
            raise ApiNotFoundError(f"Order '{order_number}' not found")
        return Response(OrderSerializer(order).data)

    def put(self, request, order_number):
        items_data = request.data.get("items")
        order_data = update_draft_order(order_number, items_data)
        return Response(order_data)


class OrderConfirmView(APIView):
    def post(self, request, order_number):
        order_data = confirm_order(order_number)
        return Response(order_data)


class OrderDispatchView(APIView):
    def post(self, request, order_number):
        order_data = dispatch_order(order_number)
        return Response(order_data)


class OrderDeliverView(APIView):
    def post(self, request, order_number):
        order_data = deliver_order(order_number)
        return Response(order_data)


class OrderCancelView(APIView):
    def post(self, request, order_number):
        order_data = cancel_order(order_number)
        return Response(order_data)


from .assistant.views import AssistantChatView
from .ml_views import ForecastDetailView, ReorderSuggestionsView
from .supplier_views import SupplierSyncView
