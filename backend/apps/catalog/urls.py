from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet

app_name = 'catalog'

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]


# ###############################
# from django.urls import path, include

# urlpatterns = [
#     # ... admin va boshqa yo'llar
#     path('api/v1/catalog/', include('apps.catalog.urls', namespace='catalog')),
# ]