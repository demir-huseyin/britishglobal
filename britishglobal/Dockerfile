FROM python:3.10-slim

WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment
ENV FLASK_ENV=production

# Expose port
EXPOSE 8080

# Simple start command - keepalive kaldırıldı
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300 main:app