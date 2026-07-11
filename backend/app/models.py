import uuid
from datetime import datetime, timezone

from app.crypto import decrypt, encrypt
from app.extensions import db


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GoogleOAuthToken(db.Model):
    """Single-tenant token store: this MVP has no login/user system (per the
    take-home's optional-extra-credit auth layer), so there is exactly one
    row representing "the" Drive connection. A multi-user version would add
    a user_id FK and a unique index on (user_id, provider) here.
    """

    __tablename__ = "google_oauth_tokens"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
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
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

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
        }
