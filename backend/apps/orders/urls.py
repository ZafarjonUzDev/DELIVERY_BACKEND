"""
Buyurtmalar ilovasi uchun URL marshrutizatsiyasi (Routing Layer).

Arxitektura (Best Practices):
1. DRF DefaultRouter: OrderViewSet ichidagi barcha standart (list, retrieve, create) 
   va custom (@action: cancel) marshrutlarni REST standarti bo'yicha avtomatik shakllantiradi.
2. Namespace Isolation (app_name): Boshqa ilovalardagi URL nomlari bilan toqnashuv 
   (conflict) yuzaga kelmasligi uchun izolyatsiya qilingan.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.orders.views import OrderViewSet

# App name: 'orders:order-list' yoki 'orders:order-detail' deb chaqirish uchun
app_name = 'orders'

# ViewSet lar uchun marshrutizator
router = DefaultRouter()

# ViewSet ni ro'yxatdan o'tkazamiz (prefix bo'sh qoldiriladi, chunki asosiy urls.py da prefix beriladi)
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]