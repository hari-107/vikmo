from django.urls import path
from . import views

urlpatterns = [
    # Health
    path("health/", views.health, name="health"),

    # Products
    path("products/", views.ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<str:sku>/", views.ProductDetailView.as_view(), name="product-detail"),

    # Inventory
    path("inventory/<str:sku>/", views.InventoryView.as_view(), name="inventory-update"),

    # Dealers
    path("dealers/", views.DealerListCreateView.as_view(), name="dealer-list-create"),
    path("dealers/<int:pk>/", views.DealerDetailView.as_view(), name="dealer-detail"),

    # Orders
    path("orders/", views.OrderListCreateView.as_view(), name="order-list-create"),
    path("orders/<str:order_number>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("orders/<str:order_number>/confirm/", views.OrderConfirmView.as_view(), name="order-confirm"),
    path("orders/<str:order_number>/dispatch/", views.OrderDispatchView.as_view(), name="order-dispatch"),
    path("orders/<str:order_number>/deliver/", views.OrderDeliverView.as_view(), name="order-deliver"),
    path("orders/<str:order_number>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),

    # Assistant
    path("assistant/chat/", views.AssistantChatView.as_view(), name="assistant-chat"),

    # Forecasting and Reorder
    path("forecast/<str:sku>/", views.ForecastDetailView.as_view(), name="forecast-detail"),
    path("reorder-suggestions/", views.ReorderSuggestionsView.as_view(), name="reorder-suggestions"),

    # Supplier Sync
    path("sync/supplier/", views.SupplierSyncView.as_view(), name="supplier-sync"),
]
