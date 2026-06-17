FROM python:3.11-slim

LABEL maintainer="Chris Ruter (@roto31)"
LABEL description="Plex Metadata NFO Generator with Tunarr/TVDb/TMDb Integration"
LABEL version="1.0.0"

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir requests

# Create app directory
WORKDIR /app

# Copy application files
COPY plex_metadata_generator.py /app/
COPY plex-metadata-generator.conf /app/

# Create required directories
RUN mkdir -p /var/cache/plex-metadata \
    && mkdir -p /var/log/plex-metadata-generator

# Create non-root user
RUN useradd -m -u 1000 plex && \
    chown -R plex:plex /app /var/cache/plex-metadata /var/log/plex-metadata-generator

# Switch to non-root user
USER plex

# Volume mount points
VOLUME ["/mnt/media/TV", "/var/cache/plex-metadata", "/var/log/plex-metadata-generator"]

# Health check
HEALTHCHECK --interval=5m --timeout=1m --start-period=10s --retries=3 \
    CMD test -f /var/cache/plex-metadata/.health || exit 1

# Default command
CMD ["python3", "/app/plex_metadata_generator.py", "--config", "/app/plex-metadata-generator.conf"]
