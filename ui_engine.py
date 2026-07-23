"""Flask-based hacker-themed UI for IntelTrace."""

import os
import json
import glob

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from main import run_investigation
from database import IntelDB
from photo_intel import PhotoIntel

load_dotenv()

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,   # 16MB
    UPLOAD_FOLDER="uploads",
    JSON_SORT_KEYS=False
)

# Create uploads folder automatically
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    db = IntelDB()
    cases = db.list_cases()

    stats = {
        "total_cases": len(cases),
        "target_types": {},
        "recent_cases": cases[:10] if cases else []
    }

    for case in cases:
        t = case.get("target_type", "unknown")
        stats["target_types"][t] = stats["target_types"].get(t, 0) + 1

    return render_template("dashboard.html", stats=stats)


@app.route("/reports")
def reports():
    db = IntelDB()
    return render_template(
        "reports.html",
        cases=db.list_cases()
    )


@app.route("/reports/<case_id>")
def report_detail(case_id):
    db = IntelDB()

    case = db.get_case(case_id)

    if not case:
        return render_template(
            "404.html",
            message="Case not found"
        ), 404

    return render_template(
        "report_detail.html",
        case=case
    )


@app.route("/ddos")
def ddos_page():
    return render_template("ddos.html")


@app.route("/api/reports")
def api_reports():
    db = IntelDB()
    return jsonify(db.list_cases())


@app.route("/scan", methods=["POST"])
def scan():

    # Photo investigation
    if "photo" in request.files:
        return handle_photo_scan()

    data = request.get_json(silent=True) or {}

    target_type = data.get("type")
    target_value = data.get("value")
    investigator = data.get("investigator")

    if not target_type or not target_value:
        return jsonify({
            "status": "error",
            "message": "Target type and value are required."
        }), 400

    try:

        run_investigation(
            target_type,
            target_value,
            investigator
        )

        return jsonify({
            "status": "success",
            "target": target_value,
            "type": target_type
        })

    except Exception as e:

        app.logger.exception(e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def handle_photo_scan():

    if "photo" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No photo uploaded."
        }), 400

    file = request.files["photo"]

    if file.filename == "":
        return jsonify({
            "status": "error",
            "message": "No file selected."
        }), 400

    if not allowed_file(file.filename):
        return jsonify({
            "status": "error",
            "message": "Unsupported file type."
        }), 400

    filename = secure_filename(file.filename)

    photo_intel = PhotoIntel()

    filepath = photo_intel.save_upload(
        file.read(),
        filename
    )

    investigator = request.form.get("investigator")

    try:

        run_investigation(
            "photo",
            filepath,
            investigator
        )

        return jsonify({
            "status": "success",
            "target": filename,
            "path": filepath
        })

    except Exception as e:

        app.logger.exception(e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "404.html",
        message="Page not found."
    ), 404


@app.errorhandler(500)
def internal(error):
    return render_template(
        "500.html",
        message="Internal server error."
    ), 500


# Only used for development.
# Gunicorn imports app from this file.
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
