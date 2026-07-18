from nicegui import app, ui

app.add_static_files("/static", "static")

# ページ読み込み
import pages.home
import pages.smoking
import pages.settings
import pages.workout

ui.run(
    title="Habitory",
    host="0.0.0.0",
    port=8080,
    reload=True,
    favicon="static/habitory_icon.png",
)