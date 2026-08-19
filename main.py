from pathlib import Path
import os

from nicegui import app, ui


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.add_static_files("/static", str(STATIC_DIR))

# ページ読み込み
import pages.home
import pages.calendar_page
import pages.hydration
import pages.login
import pages.portal
import pages.reading
import pages.purchases
import pages.sales
import pages.future_financials
import pages.financial_analysis
import pages.consulting
import pages.staffing
import pages.store_operations
import pages.schedule
import pages.attendance
import pages.smoking
import pages.settings
import pages.workout

ui.run(
    title="R-BASE",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8080")),
    reload=os.environ.get("RENDER") is None,
    favicon=str(STATIC_DIR / "habitory_icon.png"),
    storage_secret=os.environ.get(
        "STORAGE_SECRET", "habitory-local-development"
    ),
)
