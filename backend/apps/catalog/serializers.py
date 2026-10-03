from rest_framework import serializers
from .models import Category, Product, ProductExtra


class ProductExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductExtra
        fields = ['id', 'name', 'price', 'is_available']


class ProductListSerializer(serializers.ModelSerializer):
    """Menyu ro'yxati uchun yengillashtirilgan serializer (ortiqcha matnlarsiz)."""
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'image', 'is_available', 'order']


class ProductDetailSerializer(serializers.ModelSerializer):
    """Bitta taomning batafsil oynasi uchun (tarkibi va qo'shimchalari bilan)."""
    extras = ProductExtraSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'name', 'description', 'ingredients', 
            'weight_or_volume', 'price', 'image', 'is_available', 'extras'
        ]


class CategoryMenuSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'order', 'products']