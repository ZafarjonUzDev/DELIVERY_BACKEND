from django.db import models
from django.conf import settings

from common.models import BaseModel
from apps.catalog.models import Product, ProductExtra

# Create your models here.

class Cart(BaseModel):
    """
    Savat modeli.
    Foydalanuvchi tizimga kirgan bo'lsa 'user' orqali, 
    mehmon bo'lsa 'session_id' orqali bog'lanadi.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        related_name='carts',
        verbose_name="Foydalanuvchi"
    )
    session_id = models.CharField(
        max_length=255,
        null=True, 
        blank=True,
        db_index=True, # Mehmonlarni tez topish uchun indeksatsiya
        verbose_name="Sessiya ID (Mehmonlar uchun)"
    )

    class Meta:
        verbose_name = "Savatcha"
        verbose_name_plural = "Savatchalar"
        # Bitta foydalanuvchi yoki sessiyaning faqat bitta aktiv savati bo'lishi qat'iy nazorat qilinadi (API qatlamida)

    def __str__(self):
        if self.user:
            return f"{self.user.phone_number} - Savatchasi"
        return f"Mehmon ({self.session_id}) - Savatchasi"


class CartItem(BaseModel):
    """
    Savat ichidagi mahsulotlar (Item).
    Mijoz '+' yoki '-' tugmasini bosganda 'quantity' (miqdor) o'zgaradi.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items', # API'da cart.items.all() orqali ichidagi mahsulotlarni tez olish uchun
        verbose_name="Savat"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Mahsulot"
    )
    # Xalqaro yetkazib berish standarti: Bitta taomga BIR NECHTA qo'shimcha qo'shish mumkin
    # Masalan: Lavash + "Pishloqli" + "Achchiq". Shuning uchun ManyToManyField tanlandi.
    extras = models.ManyToManyField(
        ProductExtra,
        blank=True,
        verbose_name="Qo'shimchalar"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Miqdori"
    )

    class Meta:
        verbose_name = "Savatdagi mahsulot"
        verbose_name_plural = "Savatdagi mahsulotlar"
        ordering = ['created_at'] # Savatga birinchi solingan mahsulot birinchi ko'rinadi

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"