from rest_framework import viewsets
from django.db.models import Prefetch
from .models import Category, Product, ProductExtra
from .serializers import CategoryMenuSerializer, ProductDetailSerializer


class CatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Katalog va Taomlar uchun yagona va optimallashtirilgan ViewSet.
    """
    pagination_class = None

    def get_serializer_class(self):
        # Agar bitta taom batafsil so'ralsa (Detail), to'liq serializer ishlaydi
        if self.action == 'retrieve':
            return ProductDetailSerializer
        # Agar umumiy menyu so'ralsa (List), yengil serializer ishlaydi
        return CategoryMenuSerializer

    def get_queryset(self):
        # Action'ga qarab faqat kerakli bazaviy so'rovni (QuerySet) yig'amiz
        if self.action == 'retrieve':
            active_extras = ProductExtra.objects.filter(is_active=True)
            return Product.objects.filter(is_active=True).select_related('category').prefetch_related(
                Prefetch('extras', queryset=active_extras)
            )
        
        # Ro'yxat (List) uchun N+1 ning oldini oluvchi so'rov
        active_products = Product.objects.filter(is_active=True)
        return Category.objects.filter(is_active=True).prefetch_related(
            Prefetch('products', queryset=active_products)
        )