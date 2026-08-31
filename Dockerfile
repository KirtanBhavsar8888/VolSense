FROM python:3.12-slim

WORKDIR /app

# Install build tools needed for scipy/numpy compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends cmake gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copy source code and data
COPY src/ src/
COPY OPTIONS_DATA/ OPTIONS_DATA/

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
