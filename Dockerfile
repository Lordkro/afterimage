FROM python:3.12-slim-bookworm

WORKDIR /app

# Install dependencies first so source-only deploys reuse this layer.
COPY pyproject.toml README.md ./
RUN mkdir -p src/afterimage \
    && printf '%s\n' '__version__ = "0.1.0"' > src/afterimage/__init__.py \
    && pip install --no-cache-dir -e .

COPY src ./src

ENV AFTERIMAGE_HOST=0.0.0.0
ENV AFTERIMAGE_PORT=8080
ENV AFTERIMAGE_SQLITE_PATH=/data/afterimage.db
RUN mkdir -p /data
EXPOSE 8080

CMD ["afterimage"]
