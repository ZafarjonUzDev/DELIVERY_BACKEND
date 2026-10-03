from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from common.models import BaseModel

# Create your models here.


class UserManager(BaseUserManager):
    """
    Standart username o'rniga faqat telefon raqam orqali 
    foydalanuvchilarni yaratuvchi xalqaro standartdagi Manager.
    """
    use_in_migrations = True

    def _create_user(self, phone_number, password, **extra_fields):
        if not phone_number:
            raise ValueError("Telefon raqam kiritilishi qat'iyan shart!")
        # Telefon raqamni yagona formatga keltirish (normalization) ham qo'shilishi mumkin
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password() # OTP orqali kiruvchilar uchun parol shart emas
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser uchun is_staff=True bo'lishi kerak.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser uchun is_superuser=True bo'lishi kerak.")

        return self._create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser, BaseModel):
    """
    Mijozlar, kuryerlar va adminlar uchun yagona User modeli.
    OTP (Redis) logikasi va "Soft Delete" (is_active) xususiyatlarini qo'llab-quvvatlaydi.
    """
    username = None  # Django'ning standart username maydonini o'chirib tashlaymiz
    
    phone_number = models.CharField(
        max_length=15, 
        unique=True, 
        db_index=True, # Qidiruv va tizimga kirish tez ishlashi uchun indeksatsiya
        verbose_name="Telefon raqam"
    )
    full_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="F.I.O.")
    
    # is_active, is_staff, is_superuser maydonlari AbstractUser'dan keladi (Soft Delete uchun is_active yetarli)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self):
        return f"{self.full_name or 'Mijoz'} ({self.phone_number})"


class Address(BaseModel):
    """
    Mijozning yetkazib berish manzillari. Bir mijozda bir nechta manzil bo'lishi mumkin.
    GPS koordinatalar hamda kuryer uchun tushunarli matnli manzil saqlanadi.
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='addresses', 
        verbose_name="Foydalanuvchi"
    )
    address_line = models.CharField(max_length=255, verbose_name="Manzil matni (Dom, qavat, xonadon)")
    
    # Xalqaro GPS standarti: lat/lon uchun Float o'rniga Decimal ishlatiladi (aniqlik 11 sm gacha bo'lishi uchun)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Kenglik (Latitude)")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Uzunlik (Longitude)")
    
    is_default = models.BooleanField(default=False, verbose_name="Asosiy manzilmi?")

    class Meta:
        verbose_name = "Manzil"
        verbose_name_plural = "Manzillar"
        ordering = ['-is_default', '-created_at'] # Asosiy manzil doim birinchi chiqadi

    def __str__(self):
        return f"{self.user.phone_number} - {self.address_line}"

    def save(self, *args, **kwargs):
        """
        Agar mijoz ushbu manzilni 'Asosiy' (is_default=True) qilsa, uning boshqa 
        barcha manzillaridan 'Asosiy' maqomini avtomatik olib tashlaymiz.
        """
        if self.is_default:
            Address.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)