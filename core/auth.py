"""Small PIN gate for the private Habitory deployment."""

import hmac
import os
import unicodedata

from nicegui import app, ui


def is_authenticated():
    return bool(app.storage.user.get("authenticated"))


def require_login():
    if is_authenticated():
        return True
    ui.navigate.to("/login")
    return False


def verify_pin(value):
    configured = _normalize_pin(os.environ.get("HABITORY_PIN", ""))
    if not configured:
        return False
    return hmac.compare_digest(_normalize_pin(value), configured)


def _normalize_pin(value):
    """Treat full-width and half-width digits as the same PIN."""
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def log_in():
    app.storage.user["authenticated"] = True


def log_out():
    app.storage.user.clear()
    ui.navigate.to("/login")


def selected_user_id():
    """Return the profile selected in this browser only."""
    from core.data import data

    users = data.users.get_users()
    stored = app.storage.user.get("selected_user_id")
    if stored in users:
        return stored
    default = "user1" if "user1" in users else next(iter(users))
    app.storage.user["selected_user_id"] = default
    return default


def select_user_for_browser(user_id):
    from core.data import data

    data.users.get_user(user_id)
    app.storage.user["selected_user_id"] = user_id
    return user_id
