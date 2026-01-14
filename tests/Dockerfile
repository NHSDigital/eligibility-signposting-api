# STAGE 1: Build dependencies
FROM python:3.13-alpine AS builder

WORKDIR /app
RUN apk add --no-cache build-base libffi-dev

# Create a virtual env to house all dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./
# Install dependencies into the virtual env
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# STAGE 2: Runtime
FROM openresty/openresty:alpine

# Install ONLY runtime dependencies for Python 3.13
RUN apk add --no-cache \
    gettext \
    --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main \
    --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community \
    python3

# Copy the entire virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy the source code
COPY src/eligibility_signposting_api /app/eligibility_signposting_api

# Copy the nginx template
COPY tests/nginx.conf /etc/nginx/conf.d/default.conf.template

# Create entrypoint
RUN cat <<EOF > /entrypoint.sh
#!/bin/sh
export PYTHONPATH=/app
envsubst < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Starting Gunicorn..."
gunicorn --workers 3 --bind 0.0.0.0:5000 "eligibility_signposting_api.app:create_app()" &

echo "Starting OpenResty..."
exec /usr/local/openresty/bin/openresty -g "daemon off;"
EOF

RUN chmod +x /entrypoint.sh

EXPOSE 9123 5000
ENTRYPOINT ["/entrypoint.sh"]
