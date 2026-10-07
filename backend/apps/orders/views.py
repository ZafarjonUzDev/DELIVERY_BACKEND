# Create your views here.

"""
Buyurtmalar View'lari (Thin Views).

Arxitektura qoidalari:
1. Fat Models & Services, Thin Views: Bu yerda HECH QANDAY narx hisoblash yoki status almashtirish bo'lmaydi.
2. N+1 oldini olish: get_queryset() ichida Detail ko'rinish uchun prefetch_related qo'llanilgan.
3. Data Isolation: Har bir foydalanuvchi faqat o'z buyurtmalarini ko'radi.
"""

from rest_framework import viewsets, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from apps.orders.models import Order
from apps.orders.serializers import (
    OrderListReadSerializer,
    OrderDetailReadSerializer,
    OrderCreateSerializer,
    OrderCancelSerializer
)
from apps.orders import services


class OrderViewSet(
    mixins.ListModelMixin,      # GET /orders/ (list)
    mixins.RetrieveModelMixin,  # GET /orders/{id}/ (detail)
    viewsets.GenericViewSet
):
    """
    Buyurtmalarni boshqarish uchun asosiy ViewSet.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Data Isolation: Faqat tizimga kirgan mijozning o'z buyurtmalari olinadi.
        Query Optimization: Ma'lumotlar bazasini ortiqcha qiynamaslik.
        """
        # Faqat foydalanuvchining o'z buyurtmalarini eng yangisidan boshlab olamiz
        qs = Order.objects.filter(user=self.request.user).order_by('-created_at')

        # Agar bitta order to'liq so'ralayotgan bo'lsa yoki bekor qilinayotgan bo'lsa (N+1 xavfi bor)
        # Unda ovqatlar va ularning qo'shimchalarini JOIN (prefetch) orqali bitta SQL so'rovda olib kelamiz.
        if self.action in ['retrieve', 'cancel']:
            qs = qs.prefetch_related('items__extras')

        return qs

    def get_serializer_class(self):
        """
        Qilinayotgan amalga (action) qarab to'g'ri Serializer'ni (Qorovulni) qaytaradi.
        """
        if self.action == 'list':
            return OrderListReadSerializer
            
        elif self.action in ['retrieve', 'cancel']: 
            # Bekor qilingandan keyin ham to'liq obyekti qaytaramiz
            return OrderDetailReadSerializer
            
        elif self.action == 'create':
            return OrderCreateSerializer
            
        elif self.action == 'cancel_action_serializer': 
            # Swagger hujjatlari va ichki validatsiya uchun
            return OrderCancelSerializer

        return OrderDetailReadSerializer

    def create(self, request, *args, **kwargs):
        """
        POST /orders/
        Yangi buyurtma rasmiylashtirish (Checkout).
        """
        # 1. Qorovulga ko'rsatamiz (Validatsiya)
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Xizmatni chaqiramiz (Service Layer - biznes logika)
        order = services.process_checkout(
            user=request.user,
            validated_data=serializer.validated_data
        )

        # 3. Yaratilgan buyurtmani "To'liq o'qish" formatiga qoliplab, 201 status bilan qaytaramiz
        response_serializer = OrderDetailReadSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        POST /orders/{id}/cancel/
        Mijoz o'z buyurtmasini bekor qilishi.
        """
        # 1. Sababni olamiz va tekshiramiz
        serializer = OrderCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '')

        # 2. Xizmatni chaqiramiz (Service layer tekshiruvlarni va status o'zgartirishni o'zi qiladi)
        order = services.cancel_order(
            user=request.user,
            order_id=pk,
            reason=reason
        )

        # 3. Yangilangan buyurtmani 200 status bilan qaytaramiz
        response_serializer = OrderDetailReadSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_200_OK)