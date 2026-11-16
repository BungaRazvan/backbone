#!/bin/bash
set -e

cd /home/pi/projects/backbone

echo "Stopping app containers..."
docker compose stop web worker beat bmw-listener || true

echo "Loading new image..."
docker load -i backbone.tar

echo "Running migrations and collecting static files..."
docker compose run --rm --no-deps web sh -c "
  python manage.py migrate &&
  python manage.py migrate --database=discord_db &&
  python manage.py migrate --database=extension_db &&
  python manage.py migrate --database=mytools_db &&
  python manage.py collectstatic --noinput
"

echo "Starting all services..."
docker compose up -d --no-deps --force-recreate web worker beat bmw-listener
docker compose up -d bmw-bridge

echo "Cleaning unused images..."
docker image prune -f

echo "Done."