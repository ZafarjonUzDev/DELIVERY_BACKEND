"""
Accounts Serializers Module.

API so'rovlaridagi ma'lumotlarni validatsiya qilish va
JSON formatiga o'girish uchun mas'ul serializer'lar.
"""

from rest_framework import serializers
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from .models import Address

User = get_user_model()

# O'zbekiston telefon raqamlari formati uchun qat'iy validator (+998XXXXXXXXX)
phone_validator = RegexValidator(
    regex=r'^\+998\d{9}$',
    message="Telefon raqam '+998XXXXXXXXX' formatida bo'lishi kerak."
)


class SendOTPSerializer(serializers.Serializer):
    """SMS OTP so'rash uchun input serializer."""
    phone_number = serializers.CharField(
        validators=[phone_validator], 
        max_length=13,
        help_text="Foydalanuvchining telefon raqami (+998901234567)"
    )


class VerifyOTPSerializer(serializers.Serializer):
    """SMS OTP kodini tasdiqlash uchun input serializer."""
    phone_number = serializers.CharField(
        validators=[phone_validator], 
        max_length=13,
        help_text="Telefon raqami"
    )
    code = serializers.CharField(
        max_length=4, 
        min_length=4,
        help_text="SMS orqali kelgan 4 xonali tasdiqlash kodi"
    )


class UserProfileSerializer(serializers.ModelSerializer):
    """Foydalanuvchi profili ma'lumotlarini qaytaruvchi serializer."""
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'phone_number', 'is_active', 'created_at']


class AddressSerializer(serializers.ModelSerializer):
    """Foydalanuvchining yetkazib berish manzillari uchun ModelSerializer."""
    class Meta:
        model = Address
        fields = ['id', 'address_line', 'latitude', 'longitude', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']