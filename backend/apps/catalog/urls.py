from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CatalogViewSet

app_name = 'catalog'

# 1. Router ob'ektini yaratamiz
router = DefaultRouter()

# 2. ViewSet'ni routerga ulaymiz. 
# ReadOnlyModelViewSet bo'lgani uchun bu yerda avtomatik 2 ta marshrut yasaladi:
# - GET /menu/ (List - Barcha menyu)
# - GET /menu/{id}/ (Retrieve - Bitta taom)
router.register(r'menu', CatalogViewSet, basename='menu')

# 3. Router yasagan yo'llarni Django'ning urlpatterns'iga qo'shamiz
urlpatterns = [
    path('', include(router.urls)),
]