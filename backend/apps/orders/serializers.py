"""
Buyurtmalar uchun Serializer'lar.

Arxitektura qoidalari:
1. Read/Write Separation: O'qish (GET) va yozish (POST) uchun alohida serializer'lar.
2. List/Detail Separation: Ro'yxatni olishda faqat kerakli maydonlar ketadi (tarmoqni og'irlashtirmaslik uchun).
3. Thin Serializers: Bu yerda ma'lumot bazaga yozilmaydi, faqat tekshiriladi (biznes logika services.py da).
"""

from rest_framework import serializers
from apps.orders.models import Order, OrderItem, OrderItemExtra


# =======================================================================
# 1. READ SERIALIZERS (Javob qaytarish uchun - O'qish qatlami)
# =======================================================================

class OrderItemExtraReadSerializer(serializers.ModelSerializer):
    """ Buyurtma taomi qo'shimchalari uchun o'qish serializatori. """
    class Meta:
        model = OrderItemExtra
        fields = ['id', 'extra_name', 'price']
        read_only_fields = fields


class OrderItemReadSerializer(serializers.ModelSerializer):
    """ Buyurtma qilingan taomlar uchun o'qish serializatori. """
    # Nested serializer (N+1 oldi olinishi uchun views.py da prefetch qilish esdan chiqmasin)
    extras = OrderItemExtraReadSerializer(many=True, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'price', 'quantity', 'extras']
        read_only_fields = fields


class OrderListReadSerializer(serializers.ModelSerializer):
    """
    Ro'yxat (List) uchun YENGIL serializer.
    Tarmoq trafigini tejash uchun ichki taomlar (items) ni qaytarmaydi.
    """
    # Frontend'da chiroyli yozuvni ko'rsatish uchun "display" maydonlar
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display', 'order_type', 'order_type_display',
            'total_price', 'payment_status', 'payment_status_display', 'created_at'
        ]
        read_only_fields = fields


class OrderDetailReadSerializer(serializers.ModelSerializer):
    """
    Bitta buyurtma (Detail) uchun TO'LIQ serializer.
    O'z ichiga taomlar va ularning qo'shimchalarini oladi.
    """
    items = OrderItemReadSerializer(many=True, read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display', 'order_type', 'order_type_display',
            'payment_method', 'payment_method_display', 'payment_status', 'payment_status_display',
            'contact_phone', 'address_line', 'latitude', 'longitude', 
            'delivery_distance_km', 'items_total', 'delivery_fee', 'total_price',
            'comment', 'cancellation_reason', 'created_at', 'items'
        ]
        read_only_fields = fields


# =======================================================================
# 2. WRITE SERIALIZERS (So'rovni qabul qilish - Yozish qatlami)
# =======================================================================

class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Buyurtma yaratish (Checkout) uchun kiruvchi ma'lumotlarni tekshiruvchi Qorovul.
    """
    class Meta:
        model = Order
        fields = [
            'order_type', 'payment_method', 'contact_phone', 
            'address_line', 'latitude', 'longitude', 'comment'
        ]

    def validate(self, attrs):
        """ Cross-field (maydonlararo) validatsiya qatlami. """
        order_type = attrs.get('order_type', Order.OrderType.DELIVERY)
        
        # 1. Agar YETKAZIB BERISH tanlansa, manzil va lokatsiya talab qilinadi
        if order_type == Order.OrderType.DELIVERY:
            if not attrs.get('latitude') or not attrs.get('longitude'):
                raise serializers.ValidationError({
                    "location": "Yetkazib berish uchun xaritadan joylashuv (latitude, longitude) tanlanishi shart."
                })
            if not attrs.get('address_line'):
                raise serializers.ValidationError({
                    "address_line": "Yetkazib berish manzili (mo'ljal) kiritilishi shart."
                })
                
        # 2. Agar OLIB KETISH tanlansa, mijoz yuborgan bo'lsa ham ortiqcha datalarni tozalaymiz (Data Sanitization)
        elif order_type == Order.OrderType.TAKEAWAY:
            attrs['latitude'] = None
            attrs['longitude'] = None
            attrs['address_line'] = None
            
        return attrs


class OrderCancelSerializer(serializers.Serializer):
    """
    Buyurtmani bekor qilish sababini qabul qiluvchi oddiy serializer.
    Modelga bog'lanmagan, chunki bu shunchaki bitta maydonli forma.
    """
    reason = serializers.CharField(
        max_length=1000, 
        required=False, 
        allow_blank=True,
        help_text="Ixtiyoriy: Bekor qilish sababi"
    )