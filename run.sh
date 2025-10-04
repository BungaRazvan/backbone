#!/bin/bash
set -e

docker rm backbone -f

docker load -i backbone.tar

docker run -d   --name backbone   -p 8000:8000   --env-file /home/pi/projects/backbone/.env.prod   --security-opt seccomp=unconfined   backbone:latest

sleep 5

docker run exec -it backbone ./manage.py collectstatic --noinput

docker run exec -it backbone ./manage.py migrate

docker run exec -it backbone  ./manage.py migrate --database=discord_db

docker run exec -it backbone  ./manage.py migrate --database=extension_db