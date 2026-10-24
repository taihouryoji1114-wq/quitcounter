"""Share login identity only; preview is owner-only."""
from core.auth import *
from core.auth import require_app_access as _require_app_access
from nicegui import ui

def require_app_access(app_id):
    if not _require_app_access(app_id):return False
    if current_role() != "owner":
        ui.navigate.to("/store-ops")
        return False
    return True
