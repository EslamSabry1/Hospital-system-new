#!/bin/bash
# Run this once to set up local development
echo "Setting up DeviceCare local environment..."

# Create .env from template with DEBUG=True
cp .env.example .env
sed -i 's/DEBUG=False/DEBUG=True/' .env
sed -i 's/SECRET_KEY=change-me.*/SECRET_KEY=django-insecure-dev-only-xyz123abc456/' .env

echo ".env created with DEBUG=True"
echo "Starting Docker..."
docker compose down
docker compose up --build
