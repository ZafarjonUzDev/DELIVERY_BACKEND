from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cart'  # 'apps/' strukturasi uchun to'liq yo'l ko'rsatiladi
    verbose_name = "Savatcha"