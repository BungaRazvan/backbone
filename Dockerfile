FROM python:3.10-slim

USER root
RUN mkdir -p /app && chmod -R 755 /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONNUNBUFFERED=1

RUN python -m pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt


RUN chmod +x manage.py

CMD ["gunicorn", "backbone.wsgi:application", "--bind", "0.0.0.0:8000"]
