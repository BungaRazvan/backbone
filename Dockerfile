# ==========================================
# STAGE 1: The Builder (Using Full Python Image)
# ==========================================
FROM python:3.10-bullseye AS builder

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies into a localized directory
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ==========================================
# STAGE 2: The Final Runtime (Back to Slim!)
# ==========================================
FROM  python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Pillow still needs the basic runtime image library to decode JPEGs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Pluck only the working, compiled packages from the full image stage
COPY --from=builder /install /usr/local

COPY . .

CMD ["gunicorn", "backbone.wsgi:application", "--bind", "0.0.0.0:8000"]