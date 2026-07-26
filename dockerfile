# Dockerfile برای استقرار روی Railway
FROM python:3.11-slim

# تنظیمات محیطی
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# ایجاد دایرکتوری کاری
WORKDIR /app

# نصب وابستگی‌های سیستم
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل‌های وابستگی
COPY requirements.txt .

# نصب وابستگی‌های پایتون
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد برنامه
COPY app.py .
COPY runtime.txt .

# ایجاد دایرکتوری برای دیتابیس
RUN mkdir -p /data

# پورت
EXPOSE 8080

# اجرا با gunicorn (برای Railway)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
