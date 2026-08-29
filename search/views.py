from django.db.models import (
    Q,
    Case,
    When,
    Value,
    IntegerField,
    F,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from orders.models import Inventory

from .serializers import (ProductSearchSerializer,   SuggestionSerializer,)
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)


from django.core.cache import cache

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)


class ProductSearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="q",
            description="Search keyword",
            required=False,
            type=OpenApiTypes.STR,
        ),
        OpenApiParameter(
            name="category",
            description="Category ID",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="min_price",
            description="Minimum price",
            required=False,
            type=OpenApiTypes.DECIMAL,
        ),
        OpenApiParameter(
            name="max_price",
            description="Maximum price",
            required=False,
            type=OpenApiTypes.DECIMAL,
        ),
        OpenApiParameter(
            name="store_id",
            description="Store ID",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="in_stock",
            description="Filter by stock availability",
            required=False,
            type=OpenApiTypes.BOOL,
        ),
        OpenApiParameter(
            name="sort",
            description="Sorting",
            required=False,
            type=OpenApiTypes.STR,
            enum=[
                "price",
                "newest",
                "relevance",
            ],
        ),
        OpenApiParameter(
            name="page",
            description="Page number",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="page_size",
            description="Number of results per page",
            required=False,
            type=OpenApiTypes.INT,
        ),
    ],
)

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="q",
            description="Search keyword",
            required=False,
            type=OpenApiTypes.STR,
        ),
        OpenApiParameter(
            name="category",
            description="Category ID",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="min_price",
            description="Minimum price",
            required=False,
            type=OpenApiTypes.DECIMAL,
        ),
        OpenApiParameter(
            name="max_price",
            description="Maximum price",
            required=False,
            type=OpenApiTypes.DECIMAL,
        ),
        OpenApiParameter(
            name="store_id",
            description="Store ID",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="in_stock",
            description="Filter by stock availability",
            required=False,
            type=OpenApiTypes.BOOL,
        ),
        OpenApiParameter(
            name="sort",
            description="Sorting",
            required=False,
            type=OpenApiTypes.STR,
            enum=[
                "price",
                "newest",
                "relevance",
            ],
        ),
        OpenApiParameter(
            name="page",
            description="Page number",
            required=False,
            type=OpenApiTypes.INT,
        ),
        OpenApiParameter(
            name="page_size",
            description="Number of results per page",
            required=False,
            type=OpenApiTypes.INT,
        ),
    ],
    responses=ProductSearchSerializer(many=True),
)

class ProductSearchView(APIView):

    def get(self, request):

        queryset = Product.objects.select_related(
            "category"
        )

        # -----------------------------------------
        # Query parameters
        # -----------------------------------------

        q = request.query_params.get("q")
        category = request.query_params.get("category")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        store_id = request.query_params.get("store_id")
        in_stock = request.query_params.get("in_stock")
        sort = request.query_params.get("sort", "relevance")

        # -----------------------------------------
        # Keyword search
        # -----------------------------------------

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(category__name__icontains=q)
            )

        # -----------------------------------------
        # Category filter
        # -----------------------------------------

        if category:
            queryset = queryset.filter(
                category_id=category
            )

        # -----------------------------------------
        # Price filters
        # -----------------------------------------

        if min_price:
            queryset = queryset.filter(
                price__gte=min_price
            )

        if max_price:
            queryset = queryset.filter(
                price__lte=max_price
            )

        # -----------------------------------------
        # Store filter
        # -----------------------------------------

        if store_id:
            queryset = queryset.filter(
                inventory__store_id=store_id
            )

        # -----------------------------------------
        # Stock filter
        # -----------------------------------------

        if in_stock is not None and store_id:

            if in_stock.lower() == "true":
                queryset = queryset.filter(
                    inventory__store_id=store_id,
                    inventory__quantity__gt=0,
                )

            elif in_stock.lower() == "false":
                queryset = queryset.filter(
                    inventory__store_id=store_id,
                    inventory__quantity=0,
                )

        # -----------------------------------------
        # Relevance
        # -----------------------------------------

        if q and sort == "relevance":

            queryset = queryset.annotate(
                relevance=Case(
                    When(
                        title__istartswith=q,
                        then=Value(3),
                    ),
                    When(
                        title__icontains=q,
                        then=Value(2),
                    ),
                    When(
                        description__icontains=q,
                        then=Value(1),
                    ),
                    When(
                        category__name__icontains=q,
                        then=Value(1),
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ).order_by(
                "-relevance",
                "title",
            )

        elif sort == "price":
            queryset = queryset.order_by(
                "price"
            )

        elif sort == "newest":
            queryset = queryset.order_by(
                "-created_at"
            )

        else:
            queryset = queryset.order_by(
                "title"
            )

        # -----------------------------------------
        # Pagination
        # -----------------------------------------

        paginator = ProductSearchPagination()

        page = paginator.paginate_queryset(
            queryset,
            request,
        )

        # -----------------------------------------
        # Inventory quantity
        # -----------------------------------------

        data = []

        inventory_map = {}

        if store_id and page:

            inventory_map = {
                inventory.product_id: inventory.quantity
                for inventory in Inventory.objects.filter(
                    store_id=store_id,
                    product_id__in=[
                        product.id
                        for product in page
                    ],
                )
            }

        for product in page:

            data.append({
                "id": product.id,
                "title": product.title,
                "description": product.description,
                "price": product.price,
                "category": product.category.name,
                "inventory_quantity": (
                    inventory_map.get(product.id)
                    if store_id
                    else None
                ),
                "created_at": product.created_at,
            })

        serializer = ProductSearchSerializer(
            data,
            many=True,
        )

        return paginator.get_paginated_response(
            serializer.data
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="q",
            description="Search term. Minimum 3 characters.",
            required=True,
            type=OpenApiTypes.STR,
        ),
    ],
    responses=SuggestionSerializer(many=True),
)

class ProductSuggestView(APIView):

    def get(self, request):

        q = request.query_params.get(
            "q",
            ""
        ).strip()

        # -----------------------------------------
        # Minimum 3 characters
        # -----------------------------------------

        if len(q) < 3:
            return Response(
                {
                    "error": "Query must contain at least 3 characters."
                },
                status=400,
            )

        # -----------------------------------------
        # Normalize query
        # -----------------------------------------

        normalized_q = q.lower()

        # -----------------------------------------
        # Redis cache
        # -----------------------------------------

        cache_key = f"product_suggestions:{normalized_q}"

        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return Response(cached_result)

        # -----------------------------------------
        # Prefix matches first
        # -----------------------------------------

        prefix_matches = list(
            Product.objects
            .filter(
                title__istartswith=normalized_q
            )
            .order_by("title")
            .values("title")[:10]
        )

        prefix_titles = [
            item["title"]
            for item in prefix_matches
        ]

        # -----------------------------------------
        # General matches
        # -----------------------------------------

        remaining_limit = 10 - len(prefix_titles)

        general_titles = []

        if remaining_limit > 0:
            general_matches = (
                Product.objects
                .filter(title__icontains=normalized_q)
                .exclude(
                    title__in=prefix_titles
                )
                .order_by("title")
                .values("title")[:remaining_limit]
            )

            general_titles = [
                item["title"]
                for item in general_matches
            ]

        # -----------------------------------------
        # Combine
        # -----------------------------------------

        results = [
            {
                "title": title
            }
            for title in (
                prefix_titles + general_titles
            )
        ]

        # -----------------------------------------
        # Store in Redis
        # -----------------------------------------

        cache.set(
            cache_key,
            results,
            timeout=300,
        )

        return Response(results)        