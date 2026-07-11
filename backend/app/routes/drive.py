import os
import uuid

from flask import Blueprint, current_app, jsonify, request

from app import google_client
from app.extensions import db
from app.models import File

drive_bp = Blueprint("drive", __name__)


@drive_bp.get("/files")
def list_files():
    page_token = request.args.get("pageToken")
    try:
        result = google_client.list_drive_files(page_token=page_token)
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
        metadata = google_client.download_drive_file(google_file_id, destination_path)
    except google_client.DriveNotConnectedError:
        return jsonify({"error": "drive_not_connected"}), 401
    except google_client.DriveReauthRequiredError:
        return jsonify({"error": "drive_reauth_required"}), 401
    except Exception:
        if os.path.exists(destination_path):
            os.remove(destination_path)
        return jsonify({"error": "download_failed"}), 502

    size_bytes = os.path.getsize(destination_path)
    file_row = File(
        name=metadata.get("name", "Untitled"),
        mime_type=metadata.get("mimeType", "application/octet-stream"),
        size_bytes=size_bytes,
        source="google_drive",
        google_file_id=google_file_id,
        storage_path=storage_id,
    )
    db.session.add(file_row)
    db.session.commit()

    return jsonify(file_row.to_dict()), 201
