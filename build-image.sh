#!/bin/bash
set -e  

docker buildx build --platform linux/arm/v7 -t backbone:latest .

docker save -o backbone.tar backbone:latest