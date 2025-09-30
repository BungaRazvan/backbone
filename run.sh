#!/bin/bash
set -e

docker rm backbone -f

docker load -i backbone.tar

docker run -d   --name backbone   -p 8000:8000   --env-file /home/pi/projects/backbone/.env.prod   --security-opt seccomp=unconfined   backbone:latest

docker run exec -t ./manage.py migrate

docker run exec -t ./manage.py migrate --database=discord

docker run exec -t ./manage.py migrate --database=extension