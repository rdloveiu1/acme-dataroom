"""Symmetric encryption for OAuth tokens at rest.

Tokens grant delegated access to a user's Google Drive, so they're stored
encrypted rather than as plaintext columns -- a stolen DB backup shouldn't
be enough to impersonate the OAuth grant.
"""
import os

from cryptography.fernet import Fernet

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ["TOKEN_ENCRYPTION_KEY"]
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()
