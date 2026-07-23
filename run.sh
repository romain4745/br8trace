#!/bin/bash

echo "Starting BR8TRACE WSGI Server..."

# Check if gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "gunicorn not found. Installing..."
    sudo apt install python3-gunicorn -y
fi

# Run with 0.0.0.0 to allow external access
exec gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --reload \
    wsgi:application
