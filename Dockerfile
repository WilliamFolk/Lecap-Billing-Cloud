FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /app/logs
COPY . /app
EXPOSE 8000
CMD ["sh", "-c", "\
    touch /app/logs/kaiten_api.log && \
    python manage.py migrate --noinput && \
    gunicorn LecapProject.wsgi:application --bind 0.0.0.0:8000\
"]
