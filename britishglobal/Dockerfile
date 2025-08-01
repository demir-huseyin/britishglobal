# Python 3.10 slim image kullan
FROM python:3.10-slim

# Working directory oluştur
WORKDIR /app

# System dependencies (gerekirse)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies önce kopyala (cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Non-root user oluştur (security)
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check ekle
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Port expose et
EXPOSE 8080

# Production server ile çalıştır
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "30", "main:app"]