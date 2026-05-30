FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    DJANGO_DEBUG=False \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

# Run migrations and start gunicorn
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn HockeySub.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2"]
