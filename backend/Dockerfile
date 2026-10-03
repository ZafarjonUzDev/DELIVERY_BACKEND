# Xalqaro standart: Yengil va xavfsiz Linux versiyasi
FROM python:3.11-slim-bookworm

# Python xotira va output loglari uchun sozlamalar
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Ishchi papkani belgilash
WORKDIR /app

# Tizim kutubxonalarini yangilash va o'rnatish (PostgreSQL uchun zarur)
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && apt-get clean

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Loyiha fayllarini ko'chirish
COPY . .

# Konteyner ichida qaysi portni ochish (Hozircha test uchun 8000)
EXPOSE 8000