"""
Master URL Routing Configuration for the project.

Ushbu fayl butun loyihaning markaziy routing (yo'naltirish) tuguni hisoblanadi.
Barcha ilovalarning (apps) API versiyalangani (v1) holda shu yerga ulanadi.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django Admin Paneli
    path('admin/', admin.site.urls),
    
    # REST API v1 Endpoints (Accounts app)
    path('api/v1/accounts/', include('apps.accounts.urls')),
]

# Development (DEBUG) rejimida local media fayllarni (rasm, hujjatlar) brauzerda ko'rish uchun:
# Production muhitida media fayllarga Nginx yoki S3 (Object Storage) xizmat qiladi.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)