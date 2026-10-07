from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from common.models import BaseModel


class UserManager(BaseUserManager):
    """
    Standart username o'rniga faqat telefon raqam orqali 
    foydalanuvchilarni boshqaruvchi xalqaro standartdagi Manager.
    """
    use_in_migrations = True

    def _create_user(self, phone_number: str, password: str | None, **extra_fields):
        """
        Foydalanuvchi yaratish uchun bazaviy va xavfsiz yordamchi metod.
        """
        if not phone_number:
            raise ValueError(_("Telefon raqam kiritilishi qat'iyan shart!"))
        
        # Telefon raqamni ortiqcha bo'sh joylardan tozalash (Data Normalization)
        phone_number = phone_number.strip()
        
        user = self.model(phone_number=phone_number, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            # OTP orqali kiruvchilar uchun parol o'rnatilmaydi (Xavfsizlik standarti)
            user.set_unusable_password() 
            
        user.save(using=self._db)
        return user

    def create_user(self, phone_number: str, password: str | None = None, **extra_fields):
        """
        Oddiy foydalanuvchi (mijoz, kuryer) yaratish.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number: str, password: str | None = None, **extra_fields):
        """
        Tizim administratori (Superuser) yaratish.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_("Superuser uchun is_staff=True bo'lishi qat'iyan shart."))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_("Superuser uchun is_superuser=True bo'lishi qat'iyan shart."))

        return self._create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser, BaseModel):
    """
    Mijozlar, kuryerlar va adminlar uchun yagona User modeli.
    OTP (Redis) logikasi va "Soft Delete" (is_active) xususiyatlarini qo'llab-quvvatlaydi.
    """
    # Django'ning standart username maydonini to'liq olib tashlaymiz
    username = None  
    
    phone_number = models.CharField(
        max_length=15, 
        unique=True, 
        db_index=True, # Qidiruv tezligini oshirish uchun indeks (Best Practice)
        verbose_name=_("Telefon raqam"),
        help_text=_("Format: +998901234567")
    )
    full_name = models.CharField(
        max_length=150, 
        blank=True, 
        null=True, 
        verbose_name=_("F.I.O.")
    )
    
    # AbstractUser dan kelayotgan standart auth ruxsatlari bilan to'qnashuvni oldini olish
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('Guruhlar'),
        blank=True,
        related_name='custom_users',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('Foydalanuvchi huquqlari'),
        blank=True,
        related_name='custom_users',
        related_query_name='custom_user',
    )

    # Identifikatsiya qilish uchun asosiy maydon
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")
        db_table = "users" # Ma'lumotlar bazasida jadval nomini aniq ko'rsatish (Clean Architecture)

    def __str__(self) -> str:
        return f"{self.full_name or 'Mijoz'} ({self.phone_number})"


class Address(BaseModel):
    """
    Mijozning yetkazib berish manzillari. 
    GPS koordinatalar hamda kuryer uchun tushunarli matnli manzil saqlanadi.
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='addresses', 
        verbose_name=_("Foydalanuvchi")
    )
    address_line = models.CharField(
        max_length=255, 
        verbose_name=_("Manzil matni (Dom, qavat, xonadon)")
    )
    
    # Xalqaro GPS standarti: aniqlik 11 sm gacha bo'lishi uchun Decimal(9, 6) ishlatiladi
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        verbose_name=_("Kenglik (Latitude)")
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        verbose_name=_("Uzunlik (Longitude)")
    )
    
    is_default = models.BooleanField(
        default=False, 
        verbose_name=_("Asosiy manzilmi?")
    )

    class Meta:
        verbose_name = _("Manzil")
        verbose_name_plural = _("Manzillar")
        ordering = ['-is_default', '-created_at'] # Asosiy manzil doim birinchi chiqadi
        db_table = "user_addresses"

    def __str__(self) -> str:
        return f"{self.user.phone_number} - {self.address_line}"

    def save(self, *args, **kwargs):
        """
        Custom saqlash logikasi. Agar mijoz ushbu manzilni 'Asosiy' (is_default=True) qilsa,
        uning boshqa 'Asosiy' manzillari statusi xavfsiz tarzda olib tashlanadi.
        """
        # Tranzaksiya orqali Data Integrity ni ta'minlaymiz
        with transaction.atomic():
            if self.is_default:
                # Faqatgina rostdan ham is_default=True bo'lgan qatorlarni o'zgartiramiz (Query Optimization)
                Address.objects.filter(
                    user=self.user, 
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
            
            super().save(*args, **kwargs)