"""
Accounts Application Routing Module.

'accounts' modlining barcha REST API yo'nalishlarini belgilaydi.
`config/urls.py` faylida `path('api/v1/accounts/', include('apps.accounts.urls'))` orqali ulanadi.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SendOTPView, VerifyOTPView, LogoutView, AddressViewSet

app_name = 'accounts'

# AddressViewSet uchun DRF DefaultRouter orqali avtomatik CRUD URL'larni generatsiya qilish
router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')

urlpatterns = [
    # Autentifikatsiya va OTP yo'nalishlari
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Address CRUD yo'nalishlari (router orqali)
    path('', include(router.urls)),
]