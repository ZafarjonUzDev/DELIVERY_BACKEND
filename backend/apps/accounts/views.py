"""
Accounts API Views Module.

Thin Views prinsipi: View faqat so'rovlarni qabul qilib, uni tegishli Service yoki Serializer'ga uzatadi.
DRY qoidasiga to'liq amal qilingan.
"""

from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import SendOTPSerializer, VerifyOTPSerializer, UserProfileSerializer, AddressSerializer
from .services import OTPService
from .models import Address

User = get_user_model()


class SendOTPView(APIView):
    """
    POST /api/accounts/auth/send-code/
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
    POST /api/accounts/auth/verify/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        success, message = OTPService.verify_otp(phone_number, code)
        if not success:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(phone_number=phone_number)
        refresh = RefreshToken.for_user(user)

        return Response({
            'detail': message,
            'is_new_user': created,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)


class UserProfileView(RetrieveUpdateAPIView):
    """
    GET, PUT, PATCH /api/accounts/profile/
    Mijozning shaxsiy ma'lumotlarini o'qish va tahrirlash (faqat tizimga kirgan foydalanuvchi uchun).
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # URL parametr orqali ID izlamaydi, to'g'ridan to'g'ri JWT tokendagi userni qaytaradi.
        return self.request.user


class LogoutView(APIView):
    """
    POST /api/accounts/auth/logout/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"detail": "Refresh token taqdim etilmadi."}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist() 
            return Response({"detail": "Tizimdan muvaffaqiyatli chiqildi."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"detail": "Yaroqsiz yoki muddati o'tgan token."}, status=status.HTTP_400_BAD_REQUEST)


class AddressViewSet(viewsets.ModelViewSet):
    """
    Manzillarni boshqarish uchun CRUD ViewSet.
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Qo'shimcha logikalarsiz faqat user'ni biriktiramiz.
        # Asosiy manzilga (is_default) oid mantiq modelning save() funksiyasida bajariladi.
        serializer.save(user=self.request.user)