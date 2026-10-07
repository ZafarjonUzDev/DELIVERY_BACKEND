"""
Buyurtmalar (Orders) ilovasi uchun ma'lumotlar bazasi modellari.

Arxitektura: Monolith MVP (Minimum Viable Product).
Best Practices qo'llanilgan: 
- DRY (Don't Repeat Yourself): Takrorlanuvchi maydonlar (created_at, updated_at) BaseModel'dan olingan.
- Snapshot Pattern: Moliyaviy va katalog ma'lumotlari xarid vaqtidagi holatida qotirilib saqlanadi.
- Database Indexing (B-Tree): Filter/Qidiruv ko'p bo'ladigan maydonlar bazada indekslangan (db_index=True).
"""

from django.conf import settings
from django.db import models
from apps.catalog.models import Product, ProductExtra
from common.models import BaseModel


class Order(BaseModel):
    """
    Buyurtma yadrosi (Order Core Model).
    Biznes logikasi, logistika va moliyaviy ma'lumotlarni o'zida jamlaydi.
    """
    
    class OrderType(models.TextChoices):
        DELIVERY = 'DELIVERY', "Yetkazib berish"
        TAKEAWAY = 'TAKEAWAY', "Olib ketish"

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', "Naqd pul"
        CARD = 'CARD', "Karta (Click / Payme o'tkazma)"

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', "To'lov kutilmoqda"
        PAID = 'PAID', "To'landi"

    class OrderStatus(models.TextChoices):
        NEW = 'NEW', "Yangi"
        PREPARING = 'PREPARING', "Tayyorlanmoqda"
        ON_THE_WAY = 'ON_THE_WAY', "Yo'lda"
        DELIVERED = 'DELIVERED', "Yetkazib berildi"
        CANCELLED = 'CANCELLED', "Bekor qilindi"

    # --- 1. Mijoz identifikatsiyasi ---
    # PROTECT: Agar foydalanuvchi o'chirilsa, uning moliyaviy tarixi o'chib ketishining oldini oladi.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Foydalanuvchi"
    )
    
    # db_index=True: Admin panelda "Olib ketish" yoki "Yetkazib berish" bo'yicha filterlashni tezlashtiradi.
    order_type = models.CharField(
        max_length=10,
        choices=OrderType.choices,
        default=OrderType.DELIVERY,
        db_index=True,
        verbose_name="Buyurtma turi"
    )

    # --- 2. Manzil, Aloqa va Lokatsiya (MVP Yechimi) ---
    # Tuman/Qishloq sharoiti uchun kvartira, domofon kabi ortiqcha maydonlar olib tashlangan.
    contact_phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="Qo'shimcha aloqa raqami"
    )
    address_line = models.CharField(
        max_length=255, 
        blank=True,
        null=True,
        verbose_name="Mo'ljal / Yetkazib berish manzili"
    )
    # Lokatsiya koordinatalari orqali xaritalarda (Yandex/Google) to'g'ridan-to'g'ri ochish uchun.
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        blank=True,
        null=True,
        verbose_name="Kenglik (Latitude)"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        blank=True,
        null=True,
        verbose_name="Uzunlik (Longitude)"
    )
    # Tizim tomonidan Haversine formulasi bilan hisoblanadigan oraliq masofa (audit uchun).
    delivery_distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Hisoblangan masofa (km)"
    )

    # --- 3. To'lov va Statuslar ---
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="To'lov turi"
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
        verbose_name="To'lov holati"
    )
    status = models.CharField(
        max_length=15,
        choices=OrderStatus.choices,
        default=OrderStatus.NEW,
        db_index=True,
        verbose_name="Buyurtma holati"
    )

    # --- 4. Moliyaviy Summalar (Snapshot Pattern) ---
    items_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Taomlar summasi"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Yetkazib berish narxi"
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Jami umumiy summa"
    )

    # --- 5. Qo'shimcha ma'lumotlar va KPI ---
    comment = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Mijoz izohi"
    )
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Bekor qilinish sababi"
    )

    # Xodimlarning ishlash tezligini (Delivery Speed KPI) o'lchash uchun vaqt tamg'alari.
    accepted_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Qabul qilingan vaqti"
    )
    delivered_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Yetkazib berilgan vaqti"
    )

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ['-created_at']

    def __str__(self):
        # Admin panelda chiroyli ko'rinishi uchun xavfsiz chaqiruv
        phone = getattr(self.user, 'phone_number', self.user.username)
        return f"Buyurtma #{self.id} - {phone} ({self.get_status_display()})"


class OrderItem(BaseModel):
    """
    Buyurtma qilingan taomlar modeli.
    Snapshot Pattern qo'llanilgan: Agar katalogda taom nomi yoki narxi o'zgarsa (yoki o'chirilsa) ham, 
    ushbu buyurtmadagi tarixiy ma'lumot (narx, nom) qotirilgan holatida o'zgarmay qoladi.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Buyurtma"
    )
    # SET_NULL: Katalogdan mahsulot o'chirilsa ham, buyurtma buzilib/o'chib ketmaydi.
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Mahsulot"
    )
    
    # SNAPSHOT MAYDONLAR
    product_name = models.CharField(
        max_length=255,
        verbose_name="Taom nomi (xarid vaqtidagi)"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Narxi (xarid vaqtidagi)"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Miqdori"
    )

    class Meta:
        verbose_name = "Buyurtma taomi"
        verbose_name_plural = "Buyurtma taomlari"

    def __str__(self):
        return f"{self.product_name} (x{self.quantity})"


class OrderItemExtra(BaseModel):
    """
    Buyurtma qilingan taomning qo'shimchalari (masalan: +Pishloq).
    Bu yerda ham moliyaviy barqarorlik uchun Snapshot Pattern ishlatiladi.
    """
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='extras',
        verbose_name="Buyurtma taomi"
    )
    # SET_NULL: Qo'shimcha bazadan o'chirilsa ham, chek buzilmaydi.
    extra = models.ForeignKey(
        ProductExtra,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Qo'shimcha"
    )
    
    # SNAPSHOT MAYDONLAR
    extra_name = models.CharField(
        max_length=100,
        verbose_name="Qo'shimcha nomi (xarid vaqtidagi)"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Qo'shimcha narxi (xarid vaqtidagi)"
    )

    class Meta:
        verbose_name = "Buyurtma taomi qo'shimchasi"
        verbose_name_plural = "Buyurtma taomi qo'shimchalari"

    def __str__(self):
        return f"+ {self.extra_name}"