gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 0.0.0.0:5000 \   # Changed from 127.0.0.1
    --timeout 120 \
    wsgi:application
