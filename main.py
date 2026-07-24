from pathlib import Path

from nicegui import app, ui


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.add_static_files("/static", str(STATIC_DIR))

# ページ読み込み
import pages.home
import pages.hydration
import pages.smoking
import pages.settings
import pages.workout

ui.run(
    title="Habitory",
    host="0.0.0.0",
    port=8080,
    reload=True,
    favicon=str(STATIC_DIR / "habitory_icon.png"),
)
