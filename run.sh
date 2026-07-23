#!/bin/bash

echo "Starting IntelTrace WSGI Server..."

exec gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    wsgi:application
