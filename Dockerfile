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

EXPOSE 8000

CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
