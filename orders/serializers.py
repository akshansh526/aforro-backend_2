from rest_framework import serializers

from products.models import Product
from stores.models import Store

from .models import Inventory, Order, OrderItem


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity_requested = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    items = OrderItemInputSerializer(many=True)

    def validate_store_id(self, value):
        if not Store.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Store does not exist."
            )

        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one product is required."
            )

        product_ids = [
            item["product_id"]
            for item in value
        ]

        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Duplicate products are not allowed."
            )

        existing_ids = set(
            Product.objects.filter(
                id__in=product_ids
            ).values_list("id", flat=True)
        )

        missing_ids = set(product_ids) - existing_ids

        if missing_ids:
            raise serializers.ValidationError(
                f"Products not found: {sorted(missing_ids)}"
            )

        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(
        source="product.title",
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_title",
            "quantity_requested",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    total_items = serializers.IntegerField(
        read_only=True,
        required=False,
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "store",
            "status",
            "created_at",
            "items",
            "total_items",
        ]

class InventorySerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(
        source="product.title",
        read_only=True,
    )

    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    category_name = serializers.CharField(
        source="product.category.name",
        read_only=True,
    )

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product",
            "product_title",
            "product_price",
            "category_name",
            "quantity",
        ]

class OrderResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    insufficient_stock = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )
    order = OrderSerializer()


class OrderRejectedResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    insufficient_stock = serializers.ListField(
        child=serializers.DictField()
    )
    order = OrderSerializer()