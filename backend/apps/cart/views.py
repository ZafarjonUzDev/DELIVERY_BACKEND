from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from .services import CartService
from .serializers import CartSerializer, CartItemSerializer
from .models import CartItem


class CartDetailView(APIView):
    """
    GET /api/v1/cart/
    Savat ichidagi barcha mahsulotlar, tanlangan qo'shimchalar va umumiy summani ko'rsatish.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cart = CartService.get_or_create_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartAddView(APIView):
    """
    POST /api/v1/cart/add/
    Savatga mahsulot (va uning qo'shimchalarini) qo'shish yoki miqdorini oshirish (+ tugmasi).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CartItemSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        cart = CartService.add_to_cart(request, serializer.validated_data)
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartDecrementView(APIView):
    """
    POST /api/v1/cart/decrement/
    Savatdagi mahsulot miqdorini 1 taga kamaytirish (- tugmasi).
    Agar miqdor 1 bo'lsa va yana kamaytirilsa, mahsulot savatdan avtomatik o'chiriladi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({"detail": "Mahsulot item_id ko'rsatilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        cart = CartService.get_or_create_cart(request)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)

        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartRemoveItemView(APIView):
    """
    POST /api/v1/cart/remove-item/
    Savatdan muayyan bir mahsulotni miqdoridan qat'i nazar bittada o'chirib tashlash (Axlat qutisi tugmasi).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        item_id = request.data.get('item_id')
        if not item_id:
            return Response({"detail": "Mahsulot item_id ko'rsatilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        cart = CartService.get_or_create_cart(request)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        item.delete()

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartClearView(APIView):
    """
    DELETE /api/v1/cart/clear/
    Savatni to'liq tozalash.
    """
    permission_classes = [AllowAny]

    def delete(self, request):
        cart = CartService.get_or_create_cart(request)
        cart.items.all().delete()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)