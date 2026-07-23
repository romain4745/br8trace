#!/bin/bash

echo "Starting BR8TRACE WSGI Server..."

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "gunicorn not found. Installing..."
    sudo apt install python3-gunicorn -y
fi

# Run with 127.0.0.1 for local access only (default)
exec gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --reload \
    wsgi:application
