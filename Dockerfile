FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/usr/local/bin:$PATH"

WORKDIR /app

# System deps: libpq for psycopg2, gcc for compilation, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && gunicorn --version \
 && echo "✅ gunicorn installed at $(which gunicorn)"

COPY . .

EXPOSE 8000

CMD ["gunicorn", "hospital_system.wsgi:application", \
     "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "120", \
     "--access-logfile", "-", "--error-logfile", "-"]
