FROM python:3.9-slim-buster

USER root
RUN mkdir -p /app && chmod -R 755 /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN python -m pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "backbone.wsgi:application", "--bind", "0.0.0.0:8000"]
