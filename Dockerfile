# Use Python 3.13 Alpine as the base
FROM python:3.13-alpine

# 1. Install System Dependencies (Build tools + OpenResty)
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    gettext \
    curl \
    pcre \
    libssl3 \
    perl \
    zlib \
    openresty

WORKDIR /app

# 2. Install Poetry
RUN pip install --no-cache-dir poetry

# 3. Install Project Dependencies
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# 4. Copy Application Source
# Ensure 'eligibility_signposting_api' folder is directly inside /app
COPY src/eligibility_signposting_api /app/eligibility_signposting_api
COPY tests/nginx.conf /etc/nginx/conf.d/default.conf.template

# 5. Fixed Entrypoint
RUN cat <<'EOF' > /entrypoint.sh
#!/bin/sh
# Set PYTHONPATH to the current directory so imports work
export PYTHONPATH=/app
export URL_PREFIX=${URL_PREFIX:-patient-check}

echo "--- 1. Rendering Nginx Config ---"
envsubst '$URL_PREFIX $LOGIN_ROOT_URL $APP_ROOT_URL $NBS_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "--- 2. Starting Gunicorn ---"
# We run gunicorn directly from the system path
gunicorn --workers 1 \
         --threads 4 \
         --bind 0.0.0.0:5000 \
         --preload \
         --access-logfile - \
         --error-logfile - \
         "eligibility_signposting_api.app:create_app()" &

GUNICORN_PID=$!

echo "--- 3. Waiting for Flask at http://127.0.0.1:5000/${URL_PREFIX}/_status ---"
MAX_RETRIES=30
COUNT=0
while true; do
    if ! kill -0 $GUNICORN_PID 2>/dev/null; then
        echo "FATAL: Gunicorn process died. Check the Traceback above."
        exit 1
    fi

    if curl -sf "http://127.0.0.1:5000/${URL_PREFIX}/_status"; then
        echo "SUCCESS: Flask is READY."
        break
    fi

    if [ $COUNT -eq $MAX_RETRIES ]; then
        echo "FATAL: Healthcheck timed out."
        exit 1
    fi
    sleep 1
    COUNT=$((COUNT + 1))
done

echo "--- 4. Starting OpenResty ---"
# Use which to find the exact binary location
NGINX_PATH=$(which openresty || which nginx)
exec $NGINX_PATH -g "daemon off;"
EOF

RUN chmod +x /entrypoint.sh

EXPOSE 9123 5000
ENTRYPOINT ["/entrypoint.sh"]
