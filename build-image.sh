#!/bin/bash
set -e

docker buildx build \
  --platform linux/arm/v7 \
  --builder pi-builder \
  -t backbone:latest \
  --load \
  .

docker save backbone:latest -o backbone.tar