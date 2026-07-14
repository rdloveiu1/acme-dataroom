import os
import uuid

from flask import Blueprint, current_app, jsonify, request, session

from app import google_client
from app.auth_utils import login_required
from app.extensions import db
from app.models import File
from app.text_extract import extract_text

drive_bp = Blueprint("drive", __name__)


@drive_bp.get("/files")
@login_required
def list_files():
    page_token = request.args.get("pageToken")
    try:
        result = google_client.list_drive_files(session["user_id"], page_token=page_token)
    except google_client.DriveNotConnectedError:
        return jsonify({"error": "drive_not_connected"}), 401
    except google_client.DriveReauthRequiredError:
        return jsonify({"error": "drive_reauth_required"}), 401

    return jsonify(
        {
            "files": result.get("files", []),
            "nextPageToken": result.get("nextPageToken"),
        }
    )


@drive_bp.post("/import")
@login_required
def import_file():
    body = request.get_json(silent=True) or {}
    google_file_id = body.get("fileId")
    if not google_file_id:
        return jsonify({"error": "fileId is required"}), 400

    # Idempotency: importing the same Drive file twice updates nothing new,
    # it just returns the existing record.
    existing = File.query.filter_by(
        google_file_id=google_file_id, deleted_at=None
    ).first()
    if existing:
        return jsonify(existing.to_dict()), 200

    storage_id = str(uuid.uuid4())
    destination_path = os.path.join(current_app.config["STORAGE_DIR"], storage_id)

    try:
        metadata = google_client.download_drive_file(
            session["user_id"], google_file_id, destination_path
        )
    except google_client.DriveNotConnectedError:
        return jsonify({"error": "drive_not_connected"}), 401
    except google_client.DriveReauthRequiredError:
        return jsonify({"error": "drive_reauth_required"}), 401
    except Exception:
        if os.path.exists(destination_path):
            os.remove(destination_path)
        return jsonify({"error": "download_failed"}), 502

    mime_type = metadata.get("mimeType", "application/octet-stream")
    size_bytes = os.path.getsize(destination_path)
    file_row = File(
        name=metadata.get("name", "Untitled"),
        mime_type=mime_type,
        size_bytes=size_bytes,
        source="google_drive",
        google_file_id=google_file_id,
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
        current_app.logger.exception("Failed to save imported Drive file %s", google_file_id)
        return jsonify({"error": "import_failed"}), 500

    return jsonify(file_row.to_dict()), 201
