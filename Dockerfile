FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (Pillow needs libjpeg, qrcode needs zlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer-cached unless requirements change)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Gunicorn is the entrypoint; docker-compose command overrides for migrations
CMD ["gunicorn", "hospital_system.wsgi:application", \
     "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "120"]
