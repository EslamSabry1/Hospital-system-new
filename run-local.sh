#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi
SYSTEM_PYTHON="$(command -v python3)"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

ensure_venv_has_django() {
  if python -c "import django" >/dev/null 2>&1; then
    return 0
  fi

  if "$SYSTEM_PYTHON" -c "import django" >/dev/null 2>&1; then
    echo "Rebuilding .venv with system site-packages so local startup can use preinstalled Django..."
    deactivate >/dev/null 2>&1 || true
    rm -rf .venv
    "$SYSTEM_PYTHON" -m venv --system-site-packages .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    python -c "import django" >/dev/null 2>&1
    return 0
  fi

  return 1
}

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
    if ! ensure_venv_has_django; then
      echo "Django is not available (neither .venv nor system Python). Please ensure package index access and rerun."
      exit 1
    fi
    # Avoid retrying a known-unavailable package index on every run.
    # If requirements change, CURRENT_REQ_HASH will differ and trigger a fresh install attempt.
    printf '%s' "$CURRENT_REQ_HASH" > "$REQ_STAMP"
    echo "Existing environment appears usable; continuing with current packages."
  fi
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

set_env_value() {
  local key="$1"
  local value="$2"
  if grep -Eq "^[[:space:]]*${key}=" .env; then
    sed -i "s|^[[:space:]]*${key}=.*|${key}=${value}|" .env
  else
    printf '\n%s=%s\n' "$key" "$value" >> .env
  fi
}

# Enforce local-safe defaults unless explicitly opted out.
# This avoids local startup hanging on unavailable docker/postgres host "db".
if [ "${RUN_LOCAL_KEEP_DB:-0}" != "1" ]; then
  set_env_value "DEBUG" "True"
  set_env_value "DB_ENGINE" "django.db.backends.sqlite3"
  set_env_value "DB_HOST" "127.0.0.1"
fi

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
