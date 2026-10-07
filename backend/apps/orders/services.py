"""
Buyurtmalar xizmati (Order Services).

Arxitektura: Clean Architecture (Fat Services, Thin Views).
Biznes logika (narx hisoblash, savatdagi taomlar va ularning QO'SHIMCHALARINI (extras) 
buyurtmaga ko'chirish, tranzaksiyalar) faqat shu yerda izolyatsiya qilingan.
"""

from decimal import Decimal
from typing import Dict, Any

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

# Model va umumiy funksiyalarni import qilamiz
from apps.cart.models import Cart
from apps.orders.models import Order, OrderItem, OrderItemExtra
from common.distance import calculate_haversine_distance


def get_delivery_info(customer_lat: float, customer_lon: float) -> Dict[str, Any]:
    """
    Yetkazib berish (DELIVERY) uchun masofa va narxni hisoblash.
    """
    distance = calculate_haversine_distance(
        settings.CAFE_LATITUDE, 
        settings.CAFE_LONGITUDE, 
        customer_lat, 
        customer_lon
    )

    if distance > settings.MAX_DELIVERY_DISTANCE_KM:
        return {
            "is_deliverable": False,
            "distance_km": Decimal(str(distance)),
            "delivery_price": Decimal("0.00"),
            "error_message": (
                f"Sizning manzilingiz ({distance} km) xizmat doiramizdan tashqarida. "
                f"Maksimal masofa: {settings.MAX_DELIVERY_DISTANCE_KM} km."
            )
        }

    base_price = Decimal(str(settings.DELIVERY_BASE_PRICE))
    price_per_km = Decimal(str(settings.DELIVERY_PRICE_PER_KM))
    exact_distance = Decimal(str(distance))

    calculated_price = base_price + (exact_distance * price_per_km)
    final_price = round(calculated_price, -2) # O'zbek so'mi uchun yuzliklarga yaxlitlash

    return {
        "is_deliverable": True,
        "distance_km": exact_distance,
        "delivery_price": final_price,
        "error_message": None
    }


@transaction.atomic
def process_checkout(user, validated_data: Dict[str, Any]) -> Order:
    """
    Mijoz savatini (Cart) rasmiylashtirib, Buyurtma (Order) va uning Snapshot'larini yaratadi.
    
    HIGH PERFORMANCE:
    Savatdagi taomlar (items) va ularning qo'shimchalari (extras) bazadan 
    `prefetch_related` orqali N+1 muammosisiz bitta so'rovda olinadi.
    """
    # 1. Savatni topish. (DIQQAT: cart ilovangizdagi extras related_name 'extras' deb faraz qildim)
    cart = Cart.objects.prefetch_related(
        'items__product', 
        'items__extras__extra' 
    ).filter(user=user).first()

    if not cart or not cart.items.exists():
        raise ValidationError({"cart": "Savat bo'sh. Buyurtma berish uchun avval mahsulot qo'shing."})

    order_type = validated_data['order_type']
    delivery_price = Decimal("0.00")
    distance_km = Decimal("0.00")

    # 2. Logistika tekshiruvi (Faqat Yetkazib berish bo'lsa hisoblaymiz, Olib ketishda nol qoladi)
    if order_type == Order.OrderType.DELIVERY:
        lat = validated_data.get('latitude')
        lon = validated_data.get('longitude')
        
        if not lat or not lon:
            raise ValidationError({"location": "Yetkazib berish xizmati uchun lokatsiya koordinatalari majburiy."})

        info = get_delivery_info(float(lat), float(lon))
        
        if not info['is_deliverable']:
            raise ValidationError({"location": info['error_message']})
            
        delivery_price = info['delivery_price']
        distance_km = info['distance_km']

    # 3. Order (Yadro) yaratish
    order = Order.objects.create(
        user=user,
        order_type=order_type,
        payment_method=validated_data['payment_method'],
        contact_phone=validated_data.get('contact_phone', ''),
        address_line=validated_data.get('address_line', ''),
        latitude=validated_data.get('latitude'),
        longitude=validated_data.get('longitude'),
        delivery_distance_km=distance_km,
        delivery_fee=delivery_price,
        comment=validated_data.get('comment', ''),
        items_total=Decimal("0.00"), 
        total_price=Decimal("0.00")  
    )

    total_items_price = Decimal("0.00")

    # 4. Taomlar (OrderItem) va Qo'shimchalarni (OrderItemExtra) Snapshot qilish
    for cart_item in cart.items.all():
        product_price = cart_item.product.price
        item_total = product_price * cart_item.quantity
        
        # 4.1. Asosiy taomni qotirish
        order_item = OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            price=product_price,
            quantity=cart_item.quantity
        )
        
        # 4.2. Agar ushbu taomga qo'shimchalar (masalan +Pishloq, +Sous) qo'shilgan bo'lsa
        if hasattr(cart_item, 'extras') and cart_item.extras.exists():
            extras_to_create = []
            
            for cart_extra in cart_item.extras.all():
                extra_price = cart_extra.extra.price
                extras_to_create.append(
                    OrderItemExtra(
                        order_item=order_item,
                        extra=cart_extra.extra,
                        extra_name=cart_extra.extra.name,
                        price=extra_price
                    )
                )
                # Qo'shimchaning narxi ham taom miqdoriga ko'paytirilib, summasiga qo'shiladi
                item_total += (extra_price * cart_item.quantity)
                
            # Qo'shimchalarni bitta zapros bilan bazaga uramiz (Bulk Create)
            OrderItemExtra.objects.bulk_create(extras_to_create)

        total_items_price += item_total

    # 5. Yakuniy moliya: Barcha taomlar (va ularning qo'shimchalari) + Yetkazib berish xizmati
    order.items_total = total_items_price
    order.total_price = total_items_price + delivery_price
    order.save(update_fields=['items_total', 'total_price'])

    # 6. Savatni tozalash
    cart.items.all().delete()

    return order


def cancel_order(user, order_id: int, reason: str = "") -> Order:
    """
    Buyurtmani bekor qilish.
    Faqat 'Yangi' (NEW) statusidagi buyurtmalarni bekor qilish mumkin.
    Data Isolation: Foydalanuvchi faqat o'z buyurtmasini bekor qila oladi.
    """
    order = get_object_or_404(Order, id=order_id, user=user)

    if order.status != Order.OrderStatus.NEW:
        raise ValidationError({
            "status": f"Buyurtmani bekor qilib bo'lmaydi. Uning hozirgi holati: {order.get_status_display()}."
        })

    order.status = Order.OrderStatus.CANCELLED
    order.cancellation_reason = reason
    order.save(update_fields=['status', 'cancellation_reason'])

    return order