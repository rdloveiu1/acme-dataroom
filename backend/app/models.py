import uuid
from datetime import datetime, timezone

from app.crypto import decrypt, encrypt
from app.extensions import db


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email}


class GoogleOAuthToken(db.Model):
    """One Drive connection per logged-in user. The data room itself is a
    shared space (multiple users see the same files -- that's the point of a
    due-diligence data room), but each user connects their *own* Google
    Drive to import from, so a unique constraint on user_id keeps this a
    proper one-to-one rather than the single global row this table started
    as before the auth layer existed.
    """

    __tablename__ = "google_oauth_tokens"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False, unique=True
    )
    _access_token = db.Column("access_token", db.Text, nullable=False)
    _refresh_token = db.Column("refresh_token", db.Text, nullable=False)
    scope = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    @property
    def access_token(self) -> str:
        return decrypt(self._access_token)

    @access_token.setter
    def access_token(self, value: str) -> None:
        self._access_token = encrypt(value)

    @property
    def refresh_token(self) -> str:
        return decrypt(self._refresh_token)

    @refresh_token.setter
    def refresh_token(self, value: str) -> None:
        self._refresh_token = encrypt(value)

    def is_expired(self) -> bool:
        return _now() >= self.expires_at


class File(db.Model):
    __tablename__ = "files"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(512), nullable=False)
    mime_type = db.Column(db.String(255), nullable=False)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    source = db.Column(db.String(20), nullable=False)  # 'upload' | 'google_drive'
    google_file_id = db.Column(db.String(255), nullable=True, index=True)
    storage_path = db.Column(db.String(1024), nullable=False)
    uploaded_by_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    # Best-effort extracted text (pdf/docx/txt) used for content search. Null
    # when extraction wasn't attempted (unsupported type) or failed -- never
    # blocks the upload/import itself.
    content_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    uploaded_by = db.relationship("User")

    __table_args__ = (
        db.CheckConstraint("source in ('upload', 'google_drive')", name="ck_files_source"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mimeType": self.mime_type,
            "sizeBytes": self.size_bytes,
            "source": self.source,
            "createdAt": self.created_at.isoformat(),
            "uploadedByEmail": self.uploaded_by.email if self.uploaded_by else None,
        }
