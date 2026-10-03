from django.shortcuts import render

# Create your views here.

"""
Accounts API Views Module.

Autentifikatsiya va foydalanuvchi manzillarini boshqaruvchi API Endpoint'lar:
1. SendOTPView: SMS OTP kod yuborish endpoint'i.
2. VerifyOTPView: Kodni tekshirish va JWT Token (Access & Refresh) berish.
3. LogoutView: Refresh tokenni qora ro'yxatga (Blacklist) kiritib, tizimdan chiqish.
4. AddressViewSet: Manzillar bo'yicha to'liq CRUD xizmati.
"""

from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import (SendOTPSerializer, VerifyOTPSerializer, UserProfileSerializer, AddressSerializer)
from .services import OTPService
from .models import Address

User = get_user_model()


class SendOTPView(APIView):
    """
    POST /api/v1/accounts/send-otp/
    Mijozga 4 xonali tasdiqlash SMS kodini yuboradi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        success, message = OTPService.send_otp(phone_number)

        if not success:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': message}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    POST /api/v1/accounts/verify-otp/
    OTP kodni tekshiradi. Agar foydalanuvchi yangi bo'lsa, avtomatik yaratadi (get_or_create)
    va JWT Access/Refresh tokenlarni qaytaradi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        # OTP tekshiruvi
        success, message = OTPService.verify_otp(phone_number, code)
        if not success:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)

        # Passwordless Auth: Foydalanuvchini olish yoki avtomatik ro'yxatdan o'tkazish
        user, created = User.objects.get_or_create(phone_number=phone_number)
        
        # SimpleJWT orqali token generatsiyasi
        refresh = RefreshToken.for_user(user)

        return Response({
            'detail': message,
            'is_new_user': created,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/accounts/logout/
    Foydalanuvchining Refresh tokenini qora ro'yxatga (Blacklist) kiritadi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"detail": "Refresh token taqdim etilmadi."}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist() # Tokenni yaroqsiz qilish
            return Response({"detail": "Tizimdan muvaffaqiyatli chiqildi."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"detail": "Yaroqsiz yoki muddati o'tgan token."}, status=status.HTTP_400_BAD_REQUEST)


class AddressViewSet(viewsets.ModelViewSet):
    """
    GET, POST, PUT, PATCH, DELETE /api/v1/accounts/addresses/
    Foydalanuvchining shaxsiy yetkazib berish manzillarini boshqarish.
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Faqat joriy tizimga kirgan foydalanuvchining manzillarini qaytarish (Xavfsizlik)
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Yangi manzil 'is_default=True' bo'lsa, qolgan barcha manzillarni odatiy (False) holatga o'tkazish
        is_default = serializer.validated_data.get('is_default', False)
        if is_default:
            Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Manzil tahrirlanganda 'is_default=True' bo'lsa, qolganlarini odatiy holatga o'tkazish
        is_default = serializer.validated_data.get('is_default', False)
        if is_default:
            Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save()