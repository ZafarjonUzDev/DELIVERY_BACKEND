"""
Catalog Models Module.

Ushbu modul ilovaning "Vitrina" (Menyu) qismini boshqaradi.
Eslatma: Savatcha (Cart), Buyurtma (Order) va Tranzaksiyalar (History) 
SRP (Single Responsibility Principle) qoidasiga ko'ra bu yerda emas, 
kelajakda yaratiladigan 'orders' ilovasida saqlanadi.
"""

from django.db import models
from apps.common.models import BaseModel


class Category(BaseModel):
    """
    Menyu kategoriyalari (masalan: Pitsa, Suyuq taomlar, Ichimliklar).
    Eng ko'p o'qiladigan jadval bo'lgani uchun barcha muhim maydonlar indekslangan (db_index=True).
    """
    name = models.CharField(
        max_length=100, 
        db_index=True, 
        verbose_name="Kategoriya nomi"
    )
    image = models.ImageField(
        upload_to='categories/', 
        null=True, 
        blank=True, 
        verbose_name="Kategoriya rasmi"
    )
    order = models.PositiveIntegerField(
        default=0, 
        db_index=True, 
        verbose_name="Tartib raqami",
        help_text="Kategoriyalarning menyuda chiqish ketma-ketligi (kichik raqamlar yuqorida chiqadi)."
    )
    is_active = models.BooleanField(
        default=True, 
        db_index=True, 
        verbose_name="Aktiv (Menyuda ko'rinishi)",
        help_text="Belgi olib tashlansa, ushbu kategoriya va uning ichidagi barcha mahsulotlar menyudan butunlay yo'qoladi."
    )

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', '-created_at'] # Mijozlarga birinchi tartib, keyin oxirgi qo'shilgani bo'yicha ko'rinadi

    def __str__(self):
        return self.name


class Product(BaseModel):
    """
    Asosiy mahsulotlar (Taomlar).
    Ma'lumotlar bazasiga tushadigan yuklamani kamaytirish uchun db_index'lar to'g'ri sozlangan.
    """
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='products', # Kategoriya orqali uning barcha mahsulotlarini prefetch_related yordamida tez chaqirib olish uchun
        verbose_name="Kategoriya"
    )
    name = models.CharField(
        max_length=255, 
        db_index=True, 
        verbose_name="Mahsulot nomi"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Tavsifi (Description)"
    )
    ingredients = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Tarkibi (Ingredients)"
    )
    weight_or_volume = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Vazni yoki Hajmi",
        help_text="Masalan: 350g, 0.5L, 32sm"
    )
    
    # Moliyaviy operatsiyalar uchun xalqaro standart: FLOAT emas, DECIMAL ishlatiladi
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        db_index=True, 
        verbose_name="Narxi"
    )
    image = models.ImageField(
        upload_to='products/', 
        null=True, 
        blank=True, 
        verbose_name="Mahsulot rasmi"
    )
    order = models.PositiveIntegerField(
        default=0, 
        db_index=True, 
        verbose_name="Tartib raqami",
        help_text="Mahsulotning o'z kategoriyasi ichida chiqish ketma-ketligi (Top taomlarni birinchiga chiqarish uchun)."
    )
    is_active = models.BooleanField(
        default=True, 
        db_index=True, 
        verbose_name="Menyuda ko'rinadimi? (is_active)",
        help_text="Mavsumiy yoki umuman menyudan olib tashlanadigan taomlar uchun o'chiring."
    )
    is_available = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Sotuvda bormi? (is_available)",
        help_text="Mahsulot vaqtinchalik tugagan bo'lsa o'chiring (Menyuda 'Sotuvda yo'q' yozuvi bilan kulrang bo'lib turadi)."
    )

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"
        ordering = ['category', 'order', 'name']

    def __str__(self):
        return f"{self.name} - {self.price}"


class ProductExtra(BaseModel):
    """
    Mahsulot uchun ixtiyoriy qo'shimchalar (masalan: "Pishloqli", "Ketchup", "Katta porsiya").
    Mijoz batafsil oynada taomni o'ziga moslashtirishida (Customization) ishlatiladi.
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='extras', 
        verbose_name="Asosiy mahsulot"
    )
    name = models.CharField(
        max_length=100, 
        verbose_name="Qo'shimcha nomi"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        verbose_name="Qo'shimcha narxi (+ summa)"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Aktiv (Menyuda bormi?)",
        help_text="Ushbu qo'shimchani ro'yxatdan butunlay yashirish uchun o'chiring."
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="Sotuvda bormi?",
        help_text="Qo'shimcha (masalan pishloq) vaqtinchalik tugagan bo'lsa o'chiring."
    )

    class Meta:
        verbose_name = "Mahsulot qo'shimchasi"
        verbose_name_plural = "Mahsulot qo'shimchalari"
        ordering = ['price', 'name']

    def __str__(self):
        return f"{self.product.name} + {self.name} (+{self.price})"