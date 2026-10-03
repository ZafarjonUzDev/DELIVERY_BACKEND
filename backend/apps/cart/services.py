from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from apps.catalog.models import Product


class CartService:
    """
    Savat bilan bog'liq barcha biznes-mantiqni boshqaruvchi Service qatlami.
    """

    @staticmethod
    def get_or_create_cart(request):
        """
        Foydalanuvchi tizimga kirgan bo'lsa uning user ID'si bo'yicha,
        mehmon bo'lsa Header yoki Cookie'dan kelgan session_id (cart_uuid) bo'yicha savatni topadi yoki yaratadi.
        """
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            return cart
        
        # Mehmonlar uchun X-Session-ID header yoki session'dan olinadi
        session_id = request.headers.get('X-Session-ID') or request.session.session_key
        if not session_id:
            # Agar sessiya yo'k bo'lsa, uni yaratamiz (yoki frontend yuborgan cart_uuid ishlatiladi)
            if not request.session.session_key:
                request.session.create()
            session_id = request.session.session_key

        cart, _ = Cart.objects.get_or_create(session_id=session_id, user=None)
        return cart

    @staticmethod
    def add_to_cart(request, validated_data):
        """
        Savatga mahsulot qo'shish yoki mavjud bo'lsa miqdorini oshirish.
        """
        cart = CartService.get_or_create_cart(request)
        product = validated_data['product']
        extras = validated_data.get('extras', [])
        quantity = validated_data.get('quantity', 1)

        # Xuddi shunday mahsulot va bir xil qo'shimchalarga ega item borligini tekshiramiz
        # Best Practice: Qo'shimchalari mos keladigan item'ni topish
        cart_items = CartItem.objects.filter(cart=cart, product=product)
        target_item = None

        for item in cart_items:
            # ManyToMany field larni solishtiramiz
            existing_extras = set(item.extras.all())
            new_extras = set(extras)
            if existing_extras == new_extras:
                target_item = item
                break

        if target_item:
            target_item.quantity += quantity
            target_item.save()
        else:
            target_item = CartItem.objects.create(cart=cart, product=product, quantity=quantity)
            if extras:
                target_item.extras.set(extras)

        return cart

    @staticmethod
    def merge_guest_cart_to_user(session_id, user):
        """
        Mijoz OTP orqali ro'yxatdan o'tganda yoki kirganda mehmon savatini
        uning asosiy user savatiga qo'shib yuborish (Merge Cart).
        """
        if not session_id:
            return

        try:
            guest_cart = Cart.objects.get(session_id=session_id, user=None)
        except Cart.DoesNotExist:
            return

        user_cart, _ = Cart.objects.get_or_create(user=user)

        # Mehmon savatidagi barcha itemlarni user savatiga ko'chiramiz
        for guest_item in guest_cart.items.all():
            # Xuddi shu mahsulot user savatida bormi tekshiramiz
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=guest_item.product,
                defaults={'quantity': guest_item.quantity}
            )
            if not created:
                user_item.quantity += guest_item.quantity
                user_item.save()
            
            # Qo'shimchalarini biriktiramiz
            if guest_item.extras.exists():
                user_item.extras.set(guest_item.extras.all())

        # Mehmon savatini o'chirib tashlaymiz
        guest_cart.delete()