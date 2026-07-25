"""Small PIN gate for the private Habitory deployment."""

import hmac
import os

from nicegui import app, ui


def is_authenticated():
    return bool(app.storage.user.get("authenticated"))


def require_login():
    if is_authenticated():
        return True
    ui.navigate.to("/login")
    return False


def verify_pin(value):
    configured = os.environ.get("HABITORY_PIN", "")
    if not configured:
        return False
    return hmac.compare_digest(str(value or ""), configured)


def log_in():
    app.storage.user["authenticated"] = True


def log_out():
    app.storage.user.clear()
    ui.navigate.to("/login")
