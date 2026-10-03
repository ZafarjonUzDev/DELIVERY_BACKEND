"""
Orders Models Module.

Ushbu modul Buyurtmalar, Savatcha buyumlari va ularning qo'shimchalarini boshqaradi.
Snapshot Pattern va Strict Role Access tamoyillariga to'liq moslashtirilgan.
"""

from django.conf import settings
from django.db import models
from apps.catalog.models import Product, ProductExtra
from apps.common.models import BaseModel


class Order(BaseModel):
    """
    Buyurtma yadrosi (Order).
    Mijoz, manzil, to'lov turi, buyurtma turi va holatlarini boshqaruvchi asosiy model.
    """
    class OrderType(models.TextChoices):
        DELIVERY = 'DELIVERY', "Yetkazib berish"
        TAKEAWAY = 'TAKEAWAY', "Olib ketish"

    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', "Naqd pul"
        CARD = 'CARD', "Karta (Click / Payme)"

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', "Kutilmoqda"
        PAID = 'PAID', "To'landi"
        FAILED = 'FAILED', "Xatolik yuz berdi"

    class OrderStatus(models.TextChoices):
        NEW = 'NEW', "Yangi"
        PREPARING = 'PREPARING', "Tayyorlanmoqda"
        ON_THE_WAY = 'ON_THE_WAY', "Yo'lda"
        DELIVERED = 'DELIVERED', "Yetkazib berildi"
        CANCELLED = 'CANCELLED', "Bekor qilindi"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name="Foydalanuvchi"
    )
    
    order_type = models.CharField(
        max_length=10,
        choices=OrderType.choices,
        default=OrderType.DELIVERY,
        db_index=True,
        verbose_name="Buyurtma turi"
    )

    # --- Manzil va Aloqa Snapshot'i ---
    # Takeaway (Olib ketish) bo'lganda manzil talab qilinmaydi (null=True).
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
        verbose_name="Yetkazib berish manzili matni"
    )
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

    # --- To'lov va Statuslar ---
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

    # --- Moliyaviy Summalar (Buxgalteriya va Analitika uchun bo'lingan) ---
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

    # --- KPI va Analitika uchun vaqtlar ---
    accepted_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Qabul qilingan (PREPARING) vaqti"
    )
    delivered_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Yetkazib berilgan (DELIVERED) vaqti"
    )

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.user.phone_number} ({self.get_status_display()})"


class OrderItem(BaseModel):
    """
    Buyurtma qilingan taomlar (Item).
    Snapshot Pattern: Katalogda narx yoki nom o'zgarsa ham, bu yerdagi ma'lumot qotib qoladi.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Buyurtma"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Mahsulot (Havola)"
    )
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
        return f"{self.product_name} (x{self.quantity}) - {self.price} so'm"


class OrderItemExtra(BaseModel):
    """
    Buyurtma qilingan taomning qo'shimchalari (Masalan: +Pishloq, +Sirka).
    Bunda ham Snapshot Pattern qat'iy saqlanadi.
    """
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='extras',
        verbose_name="Buyurtma taomi"
    )
    extra = models.ForeignKey(
        ProductExtra,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Qo'shimcha (Havola)"
    )
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
        return f"+ {self.extra_name} ({self.price} so'm)"