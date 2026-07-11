from functools import wraps

from flask import jsonify, session

from app.models import User


def current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "auth_required"}), 401
        return fn(*args, **kwargs)

    return wrapper
