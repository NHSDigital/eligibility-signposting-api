# First Stage: Build Proxy service
FROM python:3.13-alpine AS deps

# Install poetry
RUN pip install poetry

# Install python dependencies in /.venv
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true && poetry install --no-root

FROM deps AS runtime

# Copy virtual env from python-deps stage
COPY --from=deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Create and switch to a new user
RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup && \
    mkdir /home/appuser/app
WORKDIR /home/appuser/app
USER appuser

# Install application into container
COPY app.py __init__.py /home/appuser/app/
# Copy supervisord configuration
COPY supervisord.conf /etc/supervisord.conf

COPY ./specification /home/appuser/app/specification
# Install Prism
USER root
RUN apk add --no-cache nodejs npm && \
    npm install --ignore-scripts -g @stoplight/prism-cli && \
    apk add --no-cache supervisor

# Expose ports
EXPOSE 9000
ENV UPSTREAM_HOST=http://localhost:5000
# Run supervisord
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
