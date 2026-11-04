FROM python:3.12-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

# Create non-root user for security
RUN useradd -m -u 1001 relay && chown -R relay:relay /app

COPY --chown=relay:relay core /app/core
COPY --chown=relay:relay relay /app/relay

USER relay

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "uvicorn", "relay.server:app", "--host", "0.0.0.0", "--port", "8080"]

