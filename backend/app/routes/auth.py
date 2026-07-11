import os
import re
import secrets

from flask import Blueprint, jsonify, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app import google_client
from app.auth_utils import current_user, login_required
from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.post("/register")
def register():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not _EMAIL_RE.match(email):
        return jsonify({"error": "invalid_email"}), 400
    if len(password) < 8:
        return jsonify({"error": "password_too_short"}), 400
    if User.query.filter_by(email=email).first() is not None:
        return jsonify({"error": "email_taken"}), 409

    user = User(email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify(user.to_dict()), 201


@auth_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "invalid_credentials"}), 401

    session["user_id"] = user.id
    return jsonify(user.to_dict())


@auth_bp.post("/logout")
def logout():
    session.pop("user_id", None)
    return "", 204


@auth_bp.get("/me")
def me():
    user = current_user()
    if user is None:
        return jsonify({"error": "auth_required"}), 401
    return jsonify(user.to_dict())


@auth_bp.get("/google/status")
@login_required
def google_status():
    return jsonify({"connected": google_client.is_connected(session["user_id"])})


@auth_bp.get("/google/login")
@login_required
def google_login():
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    flow = google_client.build_auth_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # force refresh_token issuance even on repeat auth
        state=state,
    )
    return redirect(authorization_url)


@auth_bp.get("/google/callback")
def google_callback():
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

    user_id = session.get("user_id")
    expected_state = session.pop("oauth_state", None)
    returned_state = request.args.get("state")
    if not user_id or not expected_state or expected_state != returned_state:
        return redirect(f"{frontend_origin}/?drive_error=state_mismatch")

    if request.args.get("error"):
        return redirect(f"{frontend_origin}/?drive_error=access_denied")

    flow = google_client.build_auth_flow()
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception:
        return redirect(f"{frontend_origin}/?drive_error=token_exchange_failed")

    google_client.save_token_from_flow(flow, user_id)
    return redirect(f"{frontend_origin}/?drive_connected=true")


@auth_bp.post("/google/disconnect")
@login_required
def google_disconnect():
    google_client.disconnect(session["user_id"])
    return jsonify({"connected": False})
