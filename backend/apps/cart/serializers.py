from rest_framework import serializers
from .models import Cart, CartItem
from apps.catalog.serializers import ProductListSerializer, ProductExtraSerializer
from apps.catalog.models import Product, ProductExtra


class CartItemSerializer(serializers.ModelSerializer):
    """
    Savat ichidagi har bir mahsulot va uning tanlangan qo'shimchalarini ko'rsatish uchun.
    """
    product = ProductListSerializer(read_only=True)
    extras = ProductExtraSerializer(many=True, read_only=True)
    
    # Frontend'dan qo'shish yoki o'zgartirish paytida kerak bo'ladigan ID'lar
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True, is_available=True),
        write_only=True,
        source='product'
    )
    extra_ids = serializers.PrimaryKeyRelatedField(
        queryset=ProductExtra.objects.filter(is_active=True, is_available=True),
        many=True,
        write_only=True,
        required=False,
        source='extras'
    )
    
    total_item_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'extras', 'extra_ids', 'quantity', 'total_item_price']

    def get_total_item_price(self, obj):
        """Mahsulotning o'z narxi + qo'shimchalar narxi * miqdori"""
        product_price = obj.product.price
        extras_price = sum(extra.price for extra in obj.extras.all())
        return (product_price + extras_price) * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    """
    To'liq savatcha va uning umumiy summasini hisoblovchi serializer.
    """
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)
    total_items_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'session_id', 'items', 'total_price', 'total_items_count', 'created_at']
        read_only_fields = ['id', 'user', 'session_id', 'created_at']

    def get_total_price(self, obj):
        """Savatdagi barcha mahsulotlarning umumiy summasi"""
        total = 0
        for item in obj.items.all():
            p_price = item.product.price
            e_price = sum(e.price for e in item.extras.all())
            total += (p_price + e_price) * item.quantity
        return total

    def get_total_items_count(self, obj):
        """Savatdagi mahsulotlarning umumiy soni (quantity yig'indisi)"""
        return sum(item.quantity for item in obj.items.all())