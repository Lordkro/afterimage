FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV AFTERIMAGE_HOST=0.0.0.0
ENV AFTERIMAGE_PORT=8080
ENV AFTERIMAGE_SQLITE_PATH=/data/afterimage.db
RUN mkdir -p /data
EXPOSE 8080

CMD ["afterimage"]
