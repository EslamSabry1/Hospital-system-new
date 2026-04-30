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

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  sed -i 's/DEBUG=False/DEBUG=True/' .env
fi

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
