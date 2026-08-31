FROM python:3.12-slim

WORKDIR /app

# Install build tools needed for scipy/numpy compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends cmake gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data
COPY src/ src/
COPY OPTIONS_DATA/ OPTIONS_DATA/

EXPOSE 8000

# exec form + /bin/sh -c expands $PORT at runtime
CMD ["/bin/sh", "-c", "uvicorn src.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
