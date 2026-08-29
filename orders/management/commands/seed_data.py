import random

from django.core.management.base import BaseCommand
from faker import Faker

from products.models import Category, Product
from stores.models import Store
from orders.models import Inventory


class Command(BaseCommand):
    help = "Generate dummy categories, products, stores and inventory"

    def handle(self, *args, **options):
        fake = Faker()

        self.stdout.write(
            self.style.WARNING("Starting seed data...")
        )

        # -------------------------------------------------
        # 1. Categories
        # -------------------------------------------------

        category_names = [
            "Electronics",
            "Clothing",
            "Shoes",
            "Home & Kitchen",
            "Books",
            "Beauty",
            "Sports",
            "Toys",
            "Groceries",
            "Furniture",
            "Accessories",
            "Automotive",
        ]

        categories = []

        for name in category_names:
            category, created = Category.objects.get_or_create(
                name=name
            )
            categories.append(category)

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories ready: {len(categories)}"
            )
        )

        # -------------------------------------------------
        # 2. Products
        # -------------------------------------------------

        existing_products = Product.objects.count()

        products_to_create = 1000 - existing_products

        if products_to_create > 0:
            products = []

            for _ in range(products_to_create):
                products.append(
                    Product(
                        title=fake.unique.catch_phrase(),
                        description=fake.text(max_nb_chars=200),
                        price=round(
                            random.uniform(10, 5000),
                            2,
                        ),
                        category=random.choice(categories),
                    )
                )

            Product.objects.bulk_create(
                products,
                batch_size=500,
            )

        products = list(Product.objects.all())

        self.stdout.write(
            self.style.SUCCESS(
                f"Products ready: {len(products)}"
            )
        )

        # -------------------------------------------------
        # 3. Stores
        # -------------------------------------------------

        existing_stores = Store.objects.count()

        stores_to_create = 20 - existing_stores

        if stores_to_create > 0:
            stores = []

            for _ in range(stores_to_create):
                stores.append(
                    Store(
                        name=fake.unique.company(),
                        location=fake.city(),
                    )
                )

            Store.objects.bulk_create(
                stores,
                batch_size=100,
            )

        stores = list(Store.objects.all())

        self.stdout.write(
            self.style.SUCCESS(
                f"Stores ready: {len(stores)}"
            )
        )

        # -------------------------------------------------
        # 4. Inventory
        # -------------------------------------------------

        inventory_to_create = []

        for store in stores:

            # Select at least 300 products per store
            selected_products = random.sample(
                products,
                min(300, len(products)),
            )

            existing_product_ids = set(
                Inventory.objects.filter(
                    store=store,
                    product__in=selected_products,
                ).values_list(
                    "product_id",
                    flat=True,
                )
            )

            for product in selected_products:

                if product.id in existing_product_ids:
                    continue

                inventory_to_create.append(
                    Inventory(
                        store=store,
                        product=product,
                        quantity=random.randint(0, 100),
                    )
                )

        Inventory.objects.bulk_create(
            inventory_to_create,
            batch_size=1000,
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Inventory created: {len(inventory_to_create)}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seed data completed successfully!"
            )
        )