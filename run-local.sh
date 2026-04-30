#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

REQ_FILE="requirements.txt"
REQ_STAMP=".venv/.requirements.sha256"
CURRENT_REQ_HASH="$(sha256sum "$REQ_FILE" | awk '{print $1}')"
STORED_REQ_HASH=""
if [ -f "$REQ_STAMP" ]; then
  STORED_REQ_HASH="$(cat "$REQ_STAMP")"
fi

if [ "$CURRENT_REQ_HASH" != "$STORED_REQ_HASH" ]; then
  echo "Installing Python dependencies..."
  if python -m pip install -r "$REQ_FILE"; then
    printf '%s' "$CURRENT_REQ_HASH" > "$REQ_STAMP"
  else
    echo "Dependency installation failed. Verifying existing environment..."
    if ! python -c "import django" >/dev/null 2>&1; then
      echo "Django is not available in .venv. Please ensure network/package index access and rerun."
      exit 1
    fi
    echo "Existing environment appears usable; continuing with current packages."
  fi
fi


if [ ! -f ".env" ]; then
  cp .env.example .env
fi

# Enforce local-safe defaults unless explicitly opted out.
# This avoids local startup hanging on unavailable docker/postgres host "db".
if [ "${RUN_LOCAL_KEEP_DB:-0}" != "1" ]; then
  sed -i 's/^DEBUG=.*/DEBUG=True/' .env
  sed -i 's|^DB_ENGINE=.*|DB_ENGINE=django.db.backends.sqlite3|' .env
  sed -i 's|^DB_HOST=.*|DB_HOST=127.0.0.1|' .env
fi

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
