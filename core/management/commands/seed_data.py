import csv
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Product, Dealer, Order


class Command(BaseCommand):
    help = "Seed database with catalogue and dealer CSV data idempotently."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Path to data directory containing CSV files.",
        )

    def handle(self, *args, **options):
        data_dir_opt = options.get("data_dir")
        if data_dir_opt:
            data_dir = Path(data_dir_opt)
        elif hasattr(settings, "DATA_DIR"):
            data_dir = Path(settings.DATA_DIR)
        else:
            data_dir = Path(settings.BASE_DIR) / "data"

        catalogue_path = data_dir / "catalogue.csv"
        dealers_path = data_dir / "dealers.csv"

        if not catalogue_path.exists():
            self.stderr.write(self.style.ERROR(f"Catalogue file not found at {catalogue_path}"))
            return

        if not dealers_path.exists():
            self.stderr.write(self.style.ERROR(f"Dealers file not found at {dealers_path}"))
            return

        self.stdout.write("Seeding products from catalogue.csv...")
        products_created = 0
        products_updated = 0
        valid_skus = set()

        with open(catalogue_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for row in reader:
                    sku = row["sku"].strip()
                    valid_skus.add(sku)
                    name = row["name"].strip()
                    category = row["category"].strip()
                    brand = row["brand"].strip()
                    vehicle_fitment = row["vehicle_fitment"].strip()
                    price = Decimal(row["price"].strip())
                    stock = int(row["stock"].strip())
                    description = row.get("description", "").strip()

                    obj, created = Product.objects.update_or_create(
                        sku=sku,
                        defaults={
                            "name": name,
                            "category": category,
                            "brand": brand,
                            "vehicle_fitment": vehicle_fitment,
                            "price": price,
                            "stock": stock,
                            "description": description,
                        },
                    )
                    if created:
                        products_created += 1
                    else:
                        products_updated += 1

                # Clean up any non-catalogue products
                non_seed_products = Product.objects.exclude(sku__in=valid_skus)
                if non_seed_products.exists():
                    non_seed_products.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogue seeded. Created: {products_created}, Updated: {products_updated}, Total: {Product.objects.count()}"
            )
        )

        self.stdout.write("Seeding dealers from dealers.csv...")
        dealers_created = 0
        dealers_updated = 0
        valid_dealer_codes = set()

        with open(dealers_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for row in reader:
                    dealer_code = row["dealer_code"].strip()
                    valid_dealer_codes.add(dealer_code)
                    name = row["name"].strip()
                    city = row.get("city", "").strip()
                    phone = row.get("phone", "").strip()
                    email = row.get("email", "").strip()
                    gstin = row.get("gstin", "").strip()
                    credit_limit_raw = row.get("credit_limit", "0.00").strip()
                    credit_limit = Decimal(credit_limit_raw) if credit_limit_raw else Decimal("0.00")

                    obj, created = Dealer.objects.update_or_create(
                        dealer_code=dealer_code,
                        defaults={
                            "name": name,
                            "city": city,
                            "phone": phone,
                            "email": email,
                            "gstin": gstin,
                            "credit_limit": credit_limit,
                        },
                    )
                    if created:
                        dealers_created += 1
                    else:
                        dealers_updated += 1

                # Clean up any non-seed test dealers and their test orders
                non_seed_dealers = Dealer.objects.exclude(dealer_code__in=valid_dealer_codes)
                if non_seed_dealers.exists():
                    Order.objects.filter(dealer__in=non_seed_dealers).delete()
                    non_seed_dealers.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Dealers seeded. Created: {dealers_created}, Updated: {dealers_updated}, Total: {Dealer.objects.count()}"
            )
        )
