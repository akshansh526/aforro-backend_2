from django.db import transaction
from django.db.models import Count

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from stores.models import Store

from .models import Inventory, Order, OrderItem
from .serializers import (
    OrderCreateSerializer,
    OrderSerializer,
    OrderResponseSerializer,
    OrderRejectedResponseSerializer,
    InventorySerializer,
)
from .tasks import process_order_created


class OrderCreateView(APIView):

    @extend_schema(
    request=OrderCreateSerializer,
    responses={201: OrderResponseSerializer},
                            )
    @transaction.atomic
    def post(self, request):

        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data["store_id"]
        items = serializer.validated_data["items"]

        store = Store.objects.get(id=store_id)

        product_ids = [
            item["product_id"]
            for item in items
        ]

        # Lock inventory rows during this transaction.
        inventory_rows = (
            Inventory.objects
            .select_for_update()
            .select_related("product")
            .filter(
                store_id=store_id,
                product_id__in=product_ids,
            )
        )

        inventory_map = {
            inventory.product_id: inventory
            for inventory in inventory_rows
        }

        insufficient_stock = []

        for item in items:

            product_id = item["product_id"]
            requested_quantity = item["quantity_requested"]

            inventory = inventory_map.get(product_id)

            if (
                inventory is None
                or inventory.quantity < requested_quantity
            ):
                insufficient_stock.append({
                    "product_id": product_id,
                    "requested": requested_quantity,
                    "available": (
                        inventory.quantity
                        if inventory
                        else 0
                    ),
                })

        # --------------------------------------------------
        # REJECTED ORDER
        # --------------------------------------------------

        if insufficient_stock:

            order = Order.objects.create(
                store=store,
                status=Order.Status.REJECTED,
            )

            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product_id=item["product_id"],
                    quantity_requested=item["quantity_requested"],
                )
                for item in items
            ])

            # Run Celery task only after DB transaction commits.
            transaction.on_commit(
                lambda order_id=order.id:
                process_order_created.delay(order_id)
            )

            response_serializer = OrderSerializer(order)

            return Response(
                {
                    "message": "Order rejected due to insufficient stock.",
                    "status": order.status,
                    "insufficient_stock": insufficient_stock,
                    "order": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        # --------------------------------------------------
        # DEDUCT INVENTORY
        # --------------------------------------------------

        for item in items:

            inventory = inventory_map[
                item["product_id"]
            ]

            inventory.quantity -= item[
                "quantity_requested"
            ]

            inventory.save(
                update_fields=["quantity"]
            )

        # --------------------------------------------------
        # CONFIRMED ORDER
        # --------------------------------------------------

        order = Order.objects.create(
            store=store,
            status=Order.Status.CONFIRMED,
        )

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product_id=item["product_id"],
                quantity_requested=item["quantity_requested"],
            )
            for item in items
        ])

        # Run Celery task after transaction commits.
        transaction.on_commit(
            lambda order_id=order.id:
            process_order_created.delay(order_id)
        )

        response_serializer = OrderSerializer(order)

        return Response(
            {
                "message": "Order created successfully.",
                "status": order.status,
                "order": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderListView(APIView):

    @extend_schema(
        responses=OrderSerializer(many=True),
    )
    def get(self, request, store_id):

        orders = (
            Order.objects
            .filter(store_id=store_id)
            .select_related("store")
            .prefetch_related("items__product")
            .annotate(
                total_items=Count("items")
            )
            .order_by("-created_at")
        )

        serializer = OrderSerializer(
            orders,
            many=True,
        )

        return Response(serializer.data)


class InventoryListView(APIView):

    @extend_schema(
        responses=InventorySerializer(many=True),
    )
    def get(self, request, store_id):

        inventory = (
            Inventory.objects
            .filter(store_id=store_id)
            .select_related(
                "product",
                "product__category",
            )
            .order_by("product__title")
        )

        serializer = InventorySerializer(
            inventory,
            many=True,
        )

        return Response(serializer.data)