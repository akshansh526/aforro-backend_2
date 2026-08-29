from rest_framework import serializers


class ProductSearchSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField(
        allow_blank=True,
        allow_null=True,
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    category = serializers.CharField()
    inventory_quantity = serializers.IntegerField(
        allow_null=True,
        required=False,
    )
    created_at = serializers.DateTimeField()

class SuggestionSerializer(serializers.Serializer):
    title = serializers.CharField()    