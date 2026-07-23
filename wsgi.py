
"""
WSGI entry point for IntelTrace.

Production:
    gunicorn -w 4 -b 0.0.0.0:5000 wsgi:application

Development:
    python ui_engine.py
"""

from ui_engine import app

application = app

if __name__ == "__main__":
    application.run(host="127.0.0.1", port=5000, debug=False)
