#!/bin/bash
set -e

docker buildx build \
  --platform linux/arm/v7 \
  -t backbone:latest \
  --load \
  .

docker save backbone:latest -o backbone.tar