#!/bin/sh
set -e

# Railway injects PORT as an env var but passes it literally to CMD.
# This script reads the actual value and starts uvicorn.
PORT="${PORT:-8000}"

echo "Starting uvicorn on port $PORT"
exec uvicorn src.api.server:app --host 0.0.0.0 --port "$PORT"
