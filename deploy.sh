#!/bin/bash
set -e

cd /home/pi/projects/backbone

echo "Stopping containers..."
docker compose down || true

echo "Loading image..."
docker load -i backbone.tar

echo "Starting services..."
docker compose up -d --force-recreate

echo "Cleaning unused images..."
docker image prune -a -f

echo "Done."