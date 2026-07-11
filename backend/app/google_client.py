"""Wraps Google OAuth + Drive API access.

Access tokens expire in ~1 hour. get_credentials() is the single choke point
every route goes through: it transparently refreshes an expired access token
using the stored refresh token and persists the new one, so callers never
have to think about token expiry. If the refresh token itself has been
revoked (user removed app access, or it's simply gone stale), Google raises
during refresh and we surface that as a 401 telling the frontend to
re-run the connect flow -- the "expired oAuth token" edge case called out
in the assignment.
"""
import os
from datetime import timezone

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.extensions import db
from app.models import GoogleOAuthToken


# drive.file (files created by or explicitly picked into this app) is the
# least-privilege choice in principle, but it only allows files.list() to
# see files the app has already touched -- it can't browse the user's
# existing Drive contents. Since this app implements its own file browser
# (rather than Google's official Picker, which handles per-file grants
# under drive.file internally), listing requires broader read access.
# drive.readonly grants read-only visibility into the whole Drive with no
# write/delete capability, which is the least-privilege option that still
# supports a custom "browse and import" UI.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# google-auth's Credentials.expiry is always a naive UTC datetime, while our
# DB column is timezone-aware UTC (SQLAlchemy/Postgres best practice). These
# convert at the boundary so neither side has to special-case the other.


def _to_aware_utc(naive_dt):
    return naive_dt.replace(tzinfo=timezone.utc)


def _to_naive_utc(aware_dt):
    return aware_dt.astimezone(timezone.utc).replace(tzinfo=None)


class DriveNotConnectedError(Exception):
    pass


class DriveReauthRequiredError(Exception):
    pass


# Google Docs/Sheets/Slides/Drawings are not stored as downloadable bytes --
# they only exist as Google's internal format and must be *exported* to a
# real file format via a separate API call. Folders aren't files at all and
# are excluded from listing entirely (recursive folder import is out of
# scope for this MVP).
_EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": (
        "application/pdf",
        ".pdf",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    "application/vnd.google-apps.drawing": (
        "image/png",
        ".png",
    ),
}


def _client_config() -> dict:
    return {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
        }
    }


def build_auth_flow() -> Flow:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    return flow


def save_token_from_flow(flow: Flow) -> None:
    creds = flow.credentials
    token_row = GoogleOAuthToken.query.first()
    if token_row is None:
        token_row = GoogleOAuthToken()
        db.session.add(token_row)

    token_row.access_token = creds.token
    token_row.refresh_token = creds.refresh_token
    token_row.scope = " ".join(creds.scopes or SCOPES)
    token_row.expires_at = _to_aware_utc(creds.expiry)
    db.session.commit()


def get_credentials() -> Credentials:
    token_row = GoogleOAuthToken.query.first()
    if token_row is None:
        raise DriveNotConnectedError()

    creds = Credentials(
        token=token_row.access_token,
        refresh_token=token_row.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=token_row.scope.split(" "),
    )
    creds.expiry = _to_naive_utc(token_row.expires_at)

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
        except Exception as exc:
            db.session.delete(token_row)
            db.session.commit()
            raise DriveReauthRequiredError() from exc

        token_row.access_token = creds.token
        token_row.expires_at = _to_aware_utc(creds.expiry)
        db.session.commit()

    return creds


def is_connected() -> bool:
    return GoogleOAuthToken.query.first() is not None


def disconnect() -> None:
    GoogleOAuthToken.query.delete()
    db.session.commit()


def list_drive_files(page_token: str | None = None) -> dict:
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)
    response = (
        service.files()
        .list(
            pageSize=50,
            pageToken=page_token,
            fields="nextPageToken, files(id, name, mimeType, size, iconLink)",
            q="trashed = false and mimeType != 'application/vnd.google-apps.folder'",
        )
        .execute()
    )
    return response


def download_drive_file(file_id: str, destination_path: str) -> dict:
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    metadata = service.files().get(fileId=file_id, fields="id, name, mimeType, size").execute()
    mime_type = metadata.get("mimeType", "application/octet-stream")

    export = _EXPORT_MIME_TYPES.get(mime_type)
    if export:
        export_mime_type, export_extension = export
        request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        metadata = {
            **metadata,
            "name": metadata.get("name", "Untitled") + export_extension,
            "mimeType": export_mime_type,
        }
    else:
        request = service.files().get_media(fileId=file_id)

    with open(destination_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return metadata
