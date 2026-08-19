"""Small PIN gate for the private Habitory deployment."""

import hmac
import os
import unicodedata

from nicegui import app, ui


ROLE_PERMISSIONS = {
    "owner": {"portal", "habitory", "store_ops", "future_financials", "schedule"},
    "partner": {"habitory"},
    "executive": {"store_ops", "future_financials"},
    "manager": {"store_ops", "future_financials"},
    "employee": {"store_ops", "future_financials"},
    "staff": {"store_ops"},
}

ROLE_ACTIONS = {
    "owner": {"store_input", "store_manage", "future_input", "future_dashboard"},
    "executive": {"store_input", "store_manage", "future_input", "future_dashboard"},
    "manager": {"store_input", "store_manage", "future_input"},
    "employee": {"store_input", "future_input"},
    "staff": {"store_input"},
    "partner": set(),
}

APP_LOGIN_PATHS = {
    "portal": "/login", "habitory": "/habitory/login",
    "store_ops": "/store-ops/login", "future_financials": "/mirai-kessan/login",
    "schedule": "/schedule/login",
}


def is_authenticated():
    return bool(app.storage.user.get("authenticated"))


def require_login():
    if is_authenticated():
        return True
    ui.navigate.to("/login")
    return False


def current_role():
    return str(app.storage.user.get("role", "owner" if is_authenticated() else ""))


def can_access(app_id):
    return app_id in ROLE_PERMISSIONS.get(current_role(), set())


def has_permission(action):
    return action in ROLE_ACTIONS.get(current_role(), set())


def require_permission(action, fallback):
    if has_permission(action):
        return True
    ui.notify("この画面を開く権限がありません", type="negative")
    ui.navigate.to(fallback)
    return False


def require_app_access(app_id):
    if not is_authenticated():
        ui.navigate.to(APP_LOGIN_PATHS.get(app_id, "/login"))
        return False
    if can_access(app_id):
        return True
    ui.notify("このアプリを開く権限がありません", type="negative")
    ui.navigate.to(APP_LOGIN_PATHS.get(app_id, "/login"))
    return False


def verify_pin(value):
    return authenticate_pin(value) is not None


def authenticate_pin(value, app_id=None):
    """Return the matching account without exposing which configured PIN matched."""
    entered = _normalize_pin(value)
    accounts = (
        ("owner", "user1", os.environ.get("RBASE_OWNER_PIN") or os.environ.get("HABITORY_PIN", "")),
        ("partner", "user2", os.environ.get("RBASE_PARTNER_PIN", "")),
        ("executive", "", os.environ.get("RBASE_EXECUTIVE_PIN", "")),
        ("manager", "", os.environ.get("RBASE_MANAGER_PIN", "")),
        ("employee", "", os.environ.get("RBASE_EMPLOYEE_PIN", "")),
        ("staff", "", os.environ.get("RBASE_STAFF_PIN", "")),
    )
    for role, user_id, configured_value in accounts:
        configured = _normalize_pin(configured_value)
        if configured and hmac.compare_digest(entered, configured):
            account = {"role": role, "user_id": user_id}
            if app_id and app_id not in ROLE_PERMISSIONS.get(role, set()):
                continue
            return account
    return None


def _normalize_pin(value):
    """Treat full-width and half-width digits as the same PIN."""
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def log_in(account=None):
    app.storage.user["authenticated"] = True
    account = account or {"role": "owner", "user_id": "user1"}
    app.storage.user["role"] = account.get("role", "owner")
    if account.get("user_id"):
        app.storage.user["account_user_id"] = account["user_id"]
        app.storage.user["selected_user_id"] = account["user_id"]


def log_out(target="/login"):
    app.storage.user.clear()
    ui.navigate.to(target)


def selected_user_id():
    """Return the profile selected in this browser only."""
    from core.data import data

    users = data.users.get_users()
    account_user_id = app.storage.user.get("account_user_id")
    if account_user_id in users:
        return account_user_id
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
