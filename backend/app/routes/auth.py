import os
import secrets

from flask import Blueprint, jsonify, redirect, request, session

from app import google_client

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/google/status")
def google_status():
    return jsonify({"connected": google_client.is_connected()})


@auth_bp.get("/google/login")
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

    expected_state = session.pop("oauth_state", None)
    returned_state = request.args.get("state")
    if not expected_state or expected_state != returned_state:
        return redirect(f"{frontend_origin}/?drive_error=state_mismatch")

    if request.args.get("error"):
        return redirect(f"{frontend_origin}/?drive_error=access_denied")

    flow = google_client.build_auth_flow()
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception:
        return redirect(f"{frontend_origin}/?drive_error=token_exchange_failed")

    google_client.save_token_from_flow(flow)
    return redirect(f"{frontend_origin}/?drive_connected=true")


@auth_bp.post("/google/disconnect")
def google_disconnect():
    google_client.disconnect()
    return jsonify({"connected": False})
