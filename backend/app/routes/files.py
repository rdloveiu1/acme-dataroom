import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import File

files_bp = Blueprint("files", __name__)


@files_bp.get("")
def list_files():
    rows = (
        File.query.filter_by(deleted_at=None)
        .order_by(File.created_at.desc())
        .all()
    )
    return jsonify([row.to_dict() for row in rows])


@files_bp.post("/upload")
def upload_file():
    upload = request.files.get("file")
    if upload is None or upload.filename == "":
        return jsonify({"error": "file is required"}), 400

    original_name = secure_filename(upload.filename) or "untitled"
    storage_id = str(uuid.uuid4())
    destination_path = os.path.join(current_app.config["STORAGE_DIR"], storage_id)
    upload.save(destination_path)

    file_row = File(
        name=original_name,
        mime_type=upload.mimetype or "application/octet-stream",
        size_bytes=os.path.getsize(destination_path),
        source="upload",
        storage_path=storage_id,
    )
    db.session.add(file_row)
    db.session.commit()

    return jsonify(file_row.to_dict()), 201


@files_bp.get("/<file_id>")
def view_file(file_id):
    file_row = File.query.filter_by(id=file_id, deleted_at=None).first()
    if file_row is None:
        return jsonify({"error": "not_found"}), 404

    return send_from_directory(
        current_app.config["STORAGE_DIR"],
        file_row.storage_path,
        mimetype=file_row.mime_type,
        as_attachment=False,
        download_name=file_row.name,
    )


@files_bp.delete("/<file_id>")
def delete_file(file_id):
    file_row = File.query.filter_by(id=file_id, deleted_at=None).first()
    if file_row is None:
        return jsonify({"error": "not_found"}), 404

    disk_path = os.path.join(current_app.config["STORAGE_DIR"], file_row.storage_path)
    if os.path.exists(disk_path):
        os.remove(disk_path)

    file_row.deleted_at = datetime.now(timezone.utc)
    db.session.commit()

    return "", 204
