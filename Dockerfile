FROM python:3.11-slim

RUN mkdir app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONNUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x manage.py

RUN ./manage.py migrate

CMD ["gunicorn", "backbone.wsgi:application", "--bind", "0.0.0.0:8000", '--workers', '3']
