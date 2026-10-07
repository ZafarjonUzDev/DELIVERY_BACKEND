"""
Accounts Application Routing Module.

Barcha so'rovlarni Controller'larga (Views) yo'naltiradi.
API dizayni kelishilgan REST standartiga to'liq mos keladi.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SendOTPView, VerifyOTPView, LogoutView, UserProfileView, AddressViewSet

app_name = 'accounts'

# DefaultRouter faqat ViewSet'lar (CRUD) uchun qulay.
router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')

urlpatterns = [
    # 1. Autentifikatsiya va OTP yo'nalishlari (POST)
    path('auth/send-code/', SendOTPView.as_view(), name='send-code'),
    path('auth/verify/', VerifyOTPView.as_view(), name='verify'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    
    # 2. Foydalanuvchi profilini boshqarish (GET, PUT, PATCH)
    path('profile/', UserProfileView.as_view(), name='profile'),
    
    # 3. Manzillar (Addresses CRUD yo'nalishlari)
    path('', include(router.urls)),
]