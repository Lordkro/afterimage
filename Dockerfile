FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV ALREADY_HOST=0.0.0.0
ENV ALREADY_PORT=8080
ENV ALREADY_SQLITE_PATH=/data/already.db
VOLUME ["/data"]
EXPOSE 8080

CMD ["already"]
