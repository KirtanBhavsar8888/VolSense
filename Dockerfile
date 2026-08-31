FROM python:3.12-slim

WORKDIR /app

# Install build dependencies (cmake, gcc, g++) needed for scipy/numpy
RUN apt-get update && \
    apt-get install -y --no-install-recommends cmake gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY OPTIONS_DATA/ OPTIONS_DATA/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" || exit 1

# Use shell form so $PORT is expanded by the shell.
# Railway injects $PORT at runtime; fall back to 8000 for local runs.
CMD uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8000}
