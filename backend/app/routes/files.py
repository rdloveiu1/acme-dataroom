import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, send_from_directory, session
from werkzeug.utils import secure_filename

from app.auth_utils import login_required
from app.extensions import db
from app.models import File
from app.text_extract import extract_text

files_bp = Blueprint("files", __name__)


@files_bp.get("")
@login_required
def list_files():
    query = File.query.filter_by(deleted_at=None)

    search = (request.args.get("q") or "").strip()
    if search:
        # ILIKE '%term%' backed by a pg_trgm GIN index (see migration) so this
        # stays fast as the room grows, instead of a full sequential scan.
        pattern = f"%{search}%"
        query = query.filter(
            db.or_(File.name.ilike(pattern), File.content_text.ilike(pattern))
        )

    rows = query.order_by(File.created_at.desc()).all()
    return jsonify([row.to_dict() for row in rows])


@files_bp.post("/upload")
@login_required
def upload_file():
    upload = request.files.get("file")
    if upload is None or upload.filename == "":
        return jsonify({"error": "file is required"}), 400

    original_name = secure_filename(upload.filename) or "untitled"
    storage_id = str(uuid.uuid4())
    destination_path = os.path.join(current_app.config["STORAGE_DIR"], storage_id)
    upload.save(destination_path)

    mime_type = upload.mimetype or "application/octet-stream"
    file_row = File(
        name=original_name,
        mime_type=mime_type,
        size_bytes=os.path.getsize(destination_path),
        source="upload",
        storage_path=storage_id,
        uploaded_by_id=session["user_id"],
        content_text=extract_text(destination_path, mime_type),
    )
    db.session.add(file_row)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if os.path.exists(destination_path):
            os.remove(destination_path)
        current_app.logger.exception("Failed to save uploaded file %s", original_name)
        return jsonify({"error": "upload_failed"}), 500

    return jsonify(file_row.to_dict()), 201


@files_bp.get("/<file_id>")
@login_required
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
@login_required
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
