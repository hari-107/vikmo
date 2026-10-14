from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from core.models import Product
from core.exceptions import ApiSupplierUnavailableError
from core.supplier_sync import run_supplier_sync


class SupplierSyncTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.existing_p = Product.objects.create(
            sku="SYNC-BRK-01",
            name="Original Brake Pad",
            category="Brakes",
            brand="Endurance",
            vehicle_fitment="Bajaj Pulsar 150",
            price=Decimal("1000.00"),
            stock=15,
            description="Original description",
        )

    @patch("requests.get")
    def test_sync_creates_and_updates_products(self, mock_get):
        # Mock 2-page response with 1 new item, 1 updated item, 1 unchanged item, 1 invalid item
        def side_effect(url, params=None, headers=None, timeout=None):
            cursor = params.get("cursor") if params else None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if not cursor:
                mock_resp.json.return_value = {
                    "items": [
                        {
                            "supplier_sku": "SUP-101",
                            "sku": "SYNC-BRK-01",
                            "name": "Updated Brake Pad (2026)",
                            "category": "Brakes",
                            "brand": "Endurance",
                            "vehicle_fitment": "Bajaj Pulsar 150",
                            "description": "Original description",
                            "price": "1200.00",
                            "supplier_stock": 500,
                            "updated_at": "2026-10-08T09:15:00Z",
                        },
                        {
                            "supplier_sku": "SUP-102",
                            "sku": "SYNC-NEW-02",
                            "name": "Brand New Horn",
                            "category": "Lighting & Electrical",
                            "brand": "Bosch",
                            "vehicle_fitment": "Universal",
                            "description": "Loud horn",
                            "price": "750.00",
                            "supplier_stock": 300,
                            "updated_at": "2026-10-08T09:15:00Z",
                        },
                    ],
                    "next_cursor": "page2",
                }
            else:
                mock_resp.json.return_value = {
                    "items": [
                        {
                            "supplier_sku": "SUP-103",
                            "sku": "",  # invalid: missing sku
                            "price": "500.00",
                        },
                        {
                            "supplier_sku": "SUP-104",
                            "sku": "SYNC-INV-04",
                            "price": "not-a-number",  # invalid price
                        },
                    ],
                    "next_cursor": None,
                }
            return mock_resp

        mock_get.side_effect = side_effect

        resp = self.client.post("/api/sync/supplier/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["created"], 1)
        self.assertEqual(data["updated"], 1)
        self.assertEqual(data["unchanged"], 0)
        self.assertEqual(len(data["rejected"]), 2)
        self.assertEqual(data["pages_fetched"], 2)

        # Check existing product was updated and stock was NOT overwritten
        self.existing_p.refresh_from_db()
        self.assertEqual(self.existing_p.name, "Updated Brake Pad (2026)")
        self.assertEqual(self.existing_p.price, Decimal("1200.00"))
        self.assertEqual(self.existing_p.stock, 15)  # stock preserved!

        # Check new product was created with stock 0
        new_p = Product.objects.get(sku="SYNC-NEW-02")
        self.assertEqual(new_p.stock, 0)
        self.assertEqual(new_p.price, Decimal("750.00"))

    @patch("requests.get")
    def test_sync_outage_fails_all_or_nothing(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_get.return_value = mock_resp

        resp = self.client.post("/api/sync/supplier/")
        self.assertEqual(resp.status_code, 502)
        err = resp.json()["error"]
        self.assertEqual(err["code"], "SUPPLIER_UNAVAILABLE")
