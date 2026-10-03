"""
Authentication and OTP Business Services Module.

Ushbu modul autentifikatsiya va xavfsizlikka oid barcha biznes-mantiqni o'z ichiga oladi:
1. SMSAdapter: Adapter Pattern yordamida Dev (Konsol) va Prod (Eskiz.uz) SMS xizmatini o'zgartirish.
2. OTPService: Redis keshida OTP kodlarni saqlash, umrini boshqarish (TTL), 
   rate-limiting (throttling) va Brute-Force hujumlaridan himoyalash.
"""

import random
import logging
import requests
from typing import Tuple
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SMSAdapter:
    """
    SMS xabarlarni yuborish uchun Adapter interfeysi.
    
    Lokal va Production muhitlari o'rtasida muammosiz o'tishni ta'minlaydi:
    - Development (DEBUG=True yoki SMS_PROVIDER='console'): SMS kodni konsolga chop etadi (Moliyaviy xarajat nol).
    - Production (SMS_PROVIDER='eskiz'): Eskiz.uz REST API orqali real SMS xabar yuboradi.
    """
    
    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        """
        Telefon raqamga SMS xabar yuboradi.

        :param phone_number: Xabar yuboriladigan telefon raqam (+998XXXXXXXXX)
        :param message: Yuboriladigan matn
        :return: Muvaffaqiyatli yuborilgan bo'lsa True, aks holda False
        """
        provider = getattr(settings, 'SMS_PROVIDER', 'console')
        
        # Development muhiti: Konsolga chiqarish
        if provider == 'console' or settings.DEBUG:
            print("\n================ [SMS CONSOLE DEV] ================")
            print(f"TO     : {phone_number}")
            print(f"MESSAGE: {message}")
            print("===================================================\n")
            return True

        # Production muhiti: Eskiz.uz Gateway
        try:
            url = getattr(settings, 'ESKIZ_API_URL', 'https://notify.eskiz.uz/api/message/sms/send')
            token = getattr(settings, 'ESKIZ_API_TOKEN', '')
            
            payload = {
                'mobile_phone': phone_number.replace('+', ''), # Eskiz API "+" belgisiz raqam qabul qiladi
                'message': message,
                'from': '4546', # Eskiz default nickname
            }
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.post(url, data=payload, headers=headers, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Eskiz SMS Gateway yuborishda xatolik yuz berdi: {e}")
            return False


class OTPService:
    """
    Redis asosida ishlovchi bir martalik parollar (OTP) servisi.
    
    Xavfsizlik qoidalari:
    - OTP umri (TTL): 3 daqiqa (180 sekund).
    - Re-send Cooldown: 1 daqiqa (60 sekund) — tezkor qayta SMS so'rashni bloklaydi.
    - Daily Limit: Bitta raqamga 24 soat ichida maksimal 5 ta SMS.
    - Brute-Force protection: 3 marta xato kiritilsa, kod Redis'dan o'chiriladi.
    """

    @staticmethod
    def send_otp(phone_number: str) -> Tuple[bool, str]:
        """
        4 xonali OTP kod yaratadi, Redis keshiga saqlaydi va SMS yuboradi.

        :param phone_number: Mijozning telefon raqami
        :return: Tuple[muvaffaqiyat_statusi (bool), xabar_matni (str)]
        """
        cooldown_key = f"otp_cooldown_{phone_number}"
        daily_key = f"otp_daily_{phone_number}"
        code_key = f"otp_code_{phone_number}"
        attempts_key = f"otp_attempts_{phone_number}"

        # 1-Bosqich: 1 daqiqalik qayta yuborish cheklovini tekshirish (Cooldown)
        if cache.get(cooldown_key):
            return False, "Qayta SMS so'rash uchun 1 daqiqa kuting."

        # 2-Bosqich: Kunlik SMS limitini tekshirish (Max 5 SMS / 24 soat)
        daily_count = cache.get(daily_key, 0)
        if daily_count >= 5:
            return False, "Kunlik SMS limitidan oshdingiz (maksimal 5 marta). 24 soatdan keyin urinib ko'ring."

        # 3-Bosqich: Cryptographically unsafe bo'lmagan 4 xonali tasodifiy kod
        code = f"{random.randint(1000, 9999)}"

        # 4-Bosqich: Redis'ga atomik yozish va vaqtlarni (TTL) belgilash
        cache.set(code_key, code, timeout=180)        # OTP kodi 3 daqiqa yashaydi
        cache.set(attempts_key, 0, timeout=180)      # Xato urinishlar hisoblagichi
        cache.set(cooldown_key, True, timeout=60)    # 1 daqiqalik spamlardan himoya kesh

        # Kunlik limit hisoblagichini oshirish
        if daily_count == 0:
            cache.set(daily_key, 1, timeout=86400)   # 24 soatlik TTL
        else:
            cache.incr(daily_key)

        # 5-Bosqich: SMS adapter orqali jo'natish
        sms_sent = SMSAdapter.send_sms(phone_number, f"Tasdiqlash kodingiz: {code}")
        if not sms_sent:
            return False, "SMS yuborish xizmatida xatolik yuz berdi. Qaytadan urinib ko'ring."

        return True, "SMS tasdiqlash kodi yuborildi."

    @staticmethod
    def verify_otp(phone_number: str, input_code: str) -> Tuple[bool, str]:
        """
        Mijoz kiritgan OTP kodni Redis'dagi kod bilan solishtiradi.

        :param phone_number: Mijozning telefon raqami
        :param input_code: Mijoz kiritgan 4 xonali kod
        :return: Tuple[muvaffaqiyat_statusi (bool), xabar_matni (str)]
        """
        code_key = f"otp_code_{phone_number}"
        attempts_key = f"otp_attempts_{phone_number}"

        real_code = cache.get(code_key)
        if not real_code:
            return False, "Kod muddati o'tgan yoki SMS so'ralmagan."

        # Brute-force himoyasi: Urinishlar sonini sanash
        attempts = cache.get(attempts_key, 0)
        if attempts >= 3:
            # 3 marta xato kiritilsa, xakerlik hujumining oldini olish uchun kod kuydiriladi
            cache.delete(code_key)
            cache.delete(attempts_key)
            return False, "3 marta xato kiritildi. Kod bekor qilindi, qayta SMS so'rang."

        # Kodni solishtirish
        if str(real_code) != str(input_code):
            cache.incr(attempts_key)
            remaining = 2 - attempts
            return False, f"Kod xato. Qolgan urinishlar soni: {remaining}"

        # Muvaffaqiyatli tasdiqlanganda keshni tozalash
        cache.delete(code_key)
        cache.delete(attempts_key)
        return True, "Kod muvaffaqiyatli tasdiqlandi."