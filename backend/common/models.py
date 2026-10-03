import uuid
from django.db import models

class BaseModel(models.Model):
    """Barcha modellar uchun umumiy meros (Shared Kernel)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    class Meta:
        abstract = True