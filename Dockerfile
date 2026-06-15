FROM python:3.10-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Upgrade pip and core build tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

CMD ["gunicorn", "backbone.wsgi:application", "--bind", "0.0.0.0:8000"]