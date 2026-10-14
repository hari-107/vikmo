import json
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from core.models import Product, Dealer, Order, OrderItem, OrderStatus


class BackendCoreTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dealer = Dealer.objects.create(
            dealer_code="DLR-TEST-01",
            name="Test Dealer One",
            city="Bengaluru",
            credit_limit=Decimal("100000.00"),
        )
        self.product1 = Product.objects.create(
            sku="TEST-BRK-01",
            name="Test Brake Pad",
            category="Brakes",
            brand="Endurance",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("1500.00"),
            stock=50,
            description="High performance brake pad",
        )
        self.product2 = Product.objects.create(
            sku="TEST-OIL-02",
            name="Test Engine Oil",
            category="Engine & Oils",
            brand="Motul",
            vehicle_fitment="Universal",
            price=Decimal("500.50"),
            stock=10,
            description="Synthetic engine oil",
        )

    def test_health_endpoint(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_products_list_and_pagination(self):
        resp = self.client.get("/api/products/?page_size=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("count", data)
        self.assertIn("next", data)
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["sku"], "TEST-BRK-01")
        self.assertEqual(data["results"][0]["price"], "1500.00")
        self.assertEqual(data["results"][0]["stock"], 50)

    def test_products_filtering(self):
        # Search match
        resp = self.client.get("/api/products/?search=brake")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)
        self.assertEqual(resp.json()["results"][0]["sku"], "TEST-BRK-01")

        # Category match
        resp = self.client.get("/api/products/?category=Brakes")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)
        self.assertEqual(resp.json()["results"][0]["sku"], "TEST-BRK-01")

        # Vehicle fitment match
        resp = self.client.get("/api/products/?vehicle=pulsar")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["results"]), 1)
        self.assertEqual(resp.json()["results"][0]["sku"], "TEST-BRK-01")

    def test_product_create_and_duplicate(self):
        payload = {
            "sku": "TEST-NEW-01",
            "name": "New Part",
            "category": "Accessories",
            "brand": "Bosch",
            "vehicle_fitment": "Universal",
            "price": "99.99",
            "description": "A new part",
        }
        resp = self.client.post("/api/products/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["stock"], 0)
        self.assertEqual(resp.json()["price"], "99.99")

        # Duplicate SKU -> 409
        dup_resp = self.client.post("/api/products/", payload, format="json")
        self.assertEqual(dup_resp.status_code, 409)
        err = dup_resp.json()["error"]
        self.assertEqual(err["code"], "DUPLICATE")

    def test_product_detail_and_404(self):
        resp = self.client.get("/api/products/TEST-BRK-01/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "Test Brake Pad")

        not_found = self.client.get("/api/products/NON-EXISTENT/")
        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(not_found.json()["error"]["code"], "NOT_FOUND")

    def test_inventory_update(self):
        resp = self.client.put("/api/inventory/TEST-BRK-01/", {"quantity": 80, "reason": "Restocked"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"sku": "TEST-BRK-01", "quantity": 80})

        # Verify product reflects updated stock
        prod_resp = self.client.get("/api/products/TEST-BRK-01/")
        self.assertEqual(prod_resp.json()["stock"], 80)

        # Reject negative stock
        neg_resp = self.client.put("/api/inventory/TEST-BRK-01/", {"quantity": -5}, format="json")
        self.assertEqual(neg_resp.status_code, 400)
        self.assertEqual(neg_resp.json()["error"]["code"], "VALIDATION_ERROR")

    def test_dealer_crud_and_duplicate(self):
        resp = self.client.get("/api/dealers/")
        self.assertEqual(resp.status_code, 200)

        # Create dealer
        new_dealer = {"dealer_code": "DLR-NEW-99", "name": "Super Bikes"}
        post_resp = self.client.post("/api/dealers/", new_dealer, format="json")
        self.assertEqual(post_resp.status_code, 201)

        # Duplicate dealer_code -> 409
        dup_resp = self.client.post("/api/dealers/", new_dealer, format="json")
        self.assertEqual(dup_resp.status_code, 409)
        self.assertEqual(dup_resp.json()["error"]["code"], "DUPLICATE")

    def test_draft_order_creation_and_stock_preservation(self):
        initial_stock = self.product1.stock
        order_payload = {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "TEST-BRK-01", "quantity": 3}],
        }
        resp = self.client.post("/api/orders/", order_payload, format="json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["status"], "DRAFT")
        self.assertTrue(data["order_number"].startswith("ORD-"))
        self.assertEqual(data["subtotal"], "4500.00")
        self.assertEqual(data["tax_total"], "810.00")
        self.assertEqual(data["grand_total"], "5310.00")

        # Draft order must NOT reduce stock
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, initial_stock)

    def test_draft_order_validation_errors(self):
        # Empty items
        r1 = self.client.post("/api/orders/", {"dealer_id": self.dealer.id, "items": []}, format="json")
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()["error"]["code"], "VALIDATION_ERROR")

        # Unknown dealer
        r2 = self.client.post("/api/orders/", {"dealer_id": 999999, "items": [{"sku": "TEST-BRK-01", "quantity": 1}]}, format="json")
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.json()["error"]["code"], "VALIDATION_ERROR")

        # Unknown SKU
        r3 = self.client.post("/api/orders/", {"dealer_id": self.dealer.id, "items": [{"sku": "NO-SUCH-SKU", "quantity": 1}]}, format="json")
        self.assertEqual(r3.status_code, 400)
        self.assertEqual(r3.json()["error"]["code"], "VALIDATION_ERROR")

        # Duplicate SKU in same order
        r4 = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "TEST-BRK-01", "quantity": 1}, {"sku": "TEST-BRK-01", "quantity": 2}],
        }, format="json")
        self.assertEqual(r4.status_code, 400)
        self.assertEqual(r4.json()["error"]["code"], "VALIDATION_ERROR")

        # Invalid quantity (0 or negative)
        r5 = self.client.post("/api/orders/", {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "TEST-BRK-01", "quantity": 0}],
        }, format="json")
        self.assertEqual(r5.status_code, 400)
        self.assertEqual(r5.json()["error"]["code"], "VALIDATION_ERROR")

    def test_order_lifecycle_confirm_cancel_concurrency(self):
        # Create draft order for 5 units of product1 (stock 50)
        order_payload = {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "TEST-BRK-01", "quantity": 5}],
        }
        resp = self.client.post("/api/orders/", order_payload, format="json")
        order_num = resp.json()["order_number"]

        # Confirm order -> stock decreases from 50 to 45
        conf_resp = self.client.post(f"/api/orders/{order_num}/confirm/")
        self.assertEqual(conf_resp.status_code, 200)
        self.assertEqual(conf_resp.json()["status"], "CONFIRMED")
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 45)

        # Cancel confirmed order -> stock restored to 50
        cancel_resp = self.client.post(f"/api/orders/{order_num}/cancel/")
        self.assertEqual(cancel_resp.status_code, 200)
        self.assertEqual(cancel_resp.json()["status"], "CANCELLED")
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 50)

        # Cannot confirm cancelled order -> 409 INVALID_TRANSITION
        invalid_resp = self.client.post(f"/api/orders/{order_num}/confirm/")
        self.assertEqual(invalid_resp.status_code, 409)
        self.assertEqual(invalid_resp.json()["error"]["code"], "INVALID_TRANSITION")

    def test_insufficient_stock_on_confirm(self):
        # Try to order 100 units when stock is 50
        order_payload = {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "TEST-BRK-01", "quantity": 100}],
        }
        resp = self.client.post("/api/orders/", order_payload, format="json")
        order_num = resp.json()["order_number"]

        conf_resp = self.client.post(f"/api/orders/{order_num}/confirm/")
        self.assertEqual(conf_resp.status_code, 409)
        err = conf_resp.json()["error"]
        self.assertEqual(err["code"], "INSUFFICIENT_STOCK")
        self.assertIn("Insufficient stock", err["message"])
        self.assertEqual(len(err["details"]), 1)
        self.assertEqual(err["details"][0]["available"], 50)
        self.assertEqual(err["details"][0]["requested"], 100)

    def test_idempotency_key(self):
        order_payload = {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "TEST-BRK-01", "quantity": 2}],
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": "test-key-123"}
        r1 = self.client.post("/api/orders/", order_payload, format="json", **headers)
        self.assertEqual(r1.status_code, 201)
        order_num = r1.json()["order_number"]

        # Reusing same key with same payload returns original order
        r2 = self.client.post("/api/orders/", order_payload, format="json", **headers)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r2.json()["order_number"], order_num)

        # Reusing same key with different payload returns 409 IDEMPOTENCY_CONFLICT
        different_payload = {
            "dealer_id": self.dealer.id,
            "items": [{"sku": "TEST-BRK-01", "quantity": 4}],
        }
        r3 = self.client.post("/api/orders/", different_payload, format="json", **headers)
        self.assertEqual(r3.status_code, 409)
        self.assertEqual(r3.json()["error"]["code"], "IDEMPOTENCY_CONFLICT")
