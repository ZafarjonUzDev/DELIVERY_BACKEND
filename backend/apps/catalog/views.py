from rest_framework import viewsets
from django.db.models import Prefetch
from .models import Category, Product, ProductExtra
from .serializers import (
    CategoryMenuSerializer, 
    ProductListSerializer, 
    ProductDetailSerializer
)

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/catalog/categories/
    GET /api/catalog/categories/{id}/
    """
    pagination_class = None
    serializer_class = CategoryMenuSerializer

    def get_queryset(self):
        active_products = Product.objects.filter(is_active=True)
        return Category.objects.filter(is_active=True).prefetch_related(
            Prefetch('products', queryset=active_products)
        )

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/catalog/products/
    GET /api/catalog/products/{id}/
    """
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category')
        
        if self.action == 'retrieve':
            active_extras = ProductExtra.objects.filter(is_active=True)
            queryset = queryset.prefetch_related(
                Prefetch('extras', queryset=active_extras)
            )
        return queryset