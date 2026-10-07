"""
Authentication and OTP Business Services Module.

Ushbu modul autentifikatsiya va xavfsizlikka oid barcha biznes-mantiqni o'z ichiga oladi:
1. SMSAdapter: Adapter Pattern yordamida Dev (Konsol) va Prod (Eskiz.uz) SMS xizmatini muammosiz almashtirish.
2. OTPService: Kriptografik xavfsiz OTP (One-Time Password) yaratish, Redis keshida umrini boshqarish (TTL), 
   rate-limiting (throttling) va Brute-Force hujumlaridan himoyalash.
"""

import logging
import secrets
import requests
from typing import Tuple
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SMSAdapter:
    """
    SMS xabarlarni yuborish uchun Adapter interfeysi.
    Lokal va Production muhitlari o'rtasida mustaqil ishlashni ta'minlaydi.
    """
    
    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        provider = getattr(settings, 'SMS_PROVIDER', 'console')
        
        # Dasturchilar uchun lokal (Dev) muhitda konsolga chiqarish
        if provider == 'console' or settings.DEBUG:
            print("\n================ [SMS CONSOLE DEV] ================")
            print(f"TO     : {phone_number}")
            print(f"MESSAGE: {message}")
            print("===================================================\n")
            return True

        # Production muhitida haqiqiy SMS shlyuziga so'rov yuborish
        try:
            url = getattr(settings, 'ESKIZ_API_URL', 'https://notify.eskiz.uz/api/message/sms/send')
            token = getattr(settings, 'ESKIZ_API_TOKEN', '')
            
            payload = {
                'mobile_phone': phone_number.replace('+', ''), 
                'message': message,
                'from': '4546', 
            }
            headers = {'Authorization': f'Bearer {token}'}
            
            # Timeout orqali server qotib qolishining (Thread blocking) oldi olinadi
            response = requests.post(url, data=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return True
                
            logger.warning(f"SMS yuborilmadi. Status: {response.status_code}, Javob: {response.text}")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Eskiz SMS Gateway tarmog'ida xatolik: {e}")
            return False


class OTPService:
    """
    Redis kesh xotirasiga asoslangan, yuqori yuklanishga (High-load) chidamli OTP servisi.
    """

    @staticmethod
    def send_otp(phone_number: str) -> Tuple[bool, str]:
        """
        Foydalanuvchiga xavfsiz OTP kod yaratadi va SMS orqali yuboradi.
        Spam va iqtisodiy zararlarning oldini olish uchun Rate-limiting qo'llaniladi.
        """
        cooldown_key = f"otp_cooldown_{phone_number}"
        daily_key = f"otp_daily_{phone_number}"
        code_key = f"otp_code_{phone_number}"
        attempts_key = f"otp_attempts_{phone_number}"

        # 1. Cooldown tekshiruvi: 1 daqiqa ichida qayta so'rashni taqiqlash (Spam himoyasi)
        if cache.get(cooldown_key):
            return False, "Qayta SMS so'rash uchun 1 daqiqa kuting."

        # 2. Kunlik limit tekshiruvi: Kuniga maksimal 5 ta SMS (Byudjet himoyasi)
        daily_count = cache.get(daily_key, 0)
        if daily_count >= 5:
            return False, "Kunlik SMS limitidan oshdingiz. 24 soatdan keyin urinib ko'ring."

        # 3. Kriptografik xavfsiz OTP yaratish (OWASP Best Practice)
        # random.randint o'rniga secrets.randbelow ishlatiladi, chunki u bashorat qilib bo'lmaydigan generator
        code = f"{secrets.randbelow(9000) + 1000}"

        # 4. Redis keshga saqlash (TTL - Time to live)
        cache.set(code_key, code, timeout=180)       # Kodning amal qilish muddati: 3 daqiqa
        cache.set(attempts_key, 0, timeout=180)      # Urinishlar soni reset qilinadi
        cache.set(cooldown_key, True, timeout=60)    # Keyingi SMS uchun 1 daqiqa blok

        if daily_count == 0:
            cache.set(daily_key, 1, timeout=86400)   # Kunlik hisoblagich (24 soat)
        else:
            cache.incr(daily_key)

        # 5. SMS Gateway'ga uzatish
        sms_sent = SMSAdapter.send_sms(phone_number, f"Tasdiqlash kodingiz: {code}")
        
        if not sms_sent:
            # Agar provayder ishlamasa, cooldown va limitni bekor qilishimiz (rollback) kerak
            cache.delete(cooldown_key)
            if daily_count == 0:
                cache.delete(daily_key)
            else:
                cache.decr(daily_key)
            return False, "SMS yuborishda tarmoq xatoligi yuz berdi. Qaytadan urinib ko'ring."

        return True, "SMS tasdiqlash kodi yuborildi."

    @staticmethod
    def verify_otp(phone_number: str, input_code: str) -> Tuple[bool, str]:
        """
        Kiritilgan OTP kodni tekshiradi va Brute-Force (kuch ishlatib topish) hujumlaridan himoyalaydi.
        """
        code_key = f"otp_code_{phone_number}"
        attempts_key = f"otp_attempts_{phone_number}"

        # 1. Kodning mavjudligi va muddati tekshiruvi
        real_code = cache.get(code_key)
        if not real_code:
            return False, "Kod muddati o'tgan yoki so'ralmagan."

        # 2. Brute-Force tekshiruvi: 3 marta xato qilsa, kodni kuydirish (Security Measure)
        attempts = cache.get(attempts_key, 0)
        if attempts >= 3:
            cache.delete(code_key)
            cache.delete(attempts_key)
            return False, "3 marta xato kiritildi. Xavfsizlik yuzasidan kod bekor qilindi, qayta SMS so'rang."

        # 3. Kiritilgan kodni solishtirish
        if str(real_code) != str(input_code):
            cache.incr(attempts_key)
            remaining = 2 - attempts
            return False, f"Tasdiqlash kodi xato. Qolgan urinishlar soni: {remaining}"

        # 4. Muvaffaqiyatli tasdiqlash: Bir marta ishlagan kodni qayta ishlatmaslik uchun o'chirish (Idempotency)
        cache.delete(code_key)
        cache.delete(attempts_key)
        
        return True, "Kod muvaffaqiyatli tasdiqlandi."