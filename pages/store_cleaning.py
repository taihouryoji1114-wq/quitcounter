from nicegui import ui

from core.auth import require_app_access
from core.clock import operational_date_jst
from core.store_cleaning import store_cleaning
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/cleaning")
def store_cleaning_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("清掃｜店舗運営", app_name="store-ops")
    record_date = operational_date_jst().isoformat()
    items = store_cleaning.items(record_date)
    content = Theme.shell("清掃", "場所ごとに、終わったら1タップ",
                          back_to="/store-ops", action=store_header_actions,
                          brand="店舗運営")

    with content:
        done_count = sum(item["done"] for item in items)
        with ui.row().classes("cleaning-summary w-full items-center justify-between no-wrap"):
            with ui.column().classes("gap-0"):
                ui.label(record_date.replace("-", "/")).classes("cleaning-date")
                ui.label("今日の清掃").classes("cleaning-title")
            progress = ui.label(f"{done_count} / {len(items)}").classes("cleaning-progress")

        areas = []
        for item in items:
            if item["area"] not in areas:
                areas.append(item["area"])
        for area in areas:
            ui.label(area).classes("cleaning-area")
            for item in [value for value in items if value["area"] == area]:
                with ui.row().classes("cleaning-row w-full items-center justify-between no-wrap"):
                    ui.label(item["name"]).classes("cleaning-name")
                    button = ui.button().props("flat dense no-caps").classes(
                        "cleaning-toggle")

                    def paint(selected=item, control=button):
                        control.set_text("✓ 完了" if selected["done"] else "未完了")
                        control.classes(remove="is-done is-pending")
                        control.classes(add="is-done" if selected["done"] else "is-pending")

                    def toggle(selected=item, control=paint):
                        selected["done"] = store_cleaning.toggle(record_date, selected["id"])
                        control()
                        progress.set_text(
                            f"{sum(value['done'] for value in items)} / {len(items)}")

                    button.on("click", toggle)
                    paint()
        if not items:
            ui.label("清掃項目はまだありません").classes("cleaning-empty")
        ui.label("清掃項目は管理者の「登録・設定」から追加できます").classes(
            "cleaning-help")

    ui.add_css("""
    body{background:#f1f5f2!important}.cleaning-summary{padding:20px;border-radius:22px;background:linear-gradient(145deg,#174a3c,#0f352b);color:#fff;box-shadow:0 10px 24px rgba(20,55,43,.2)}.cleaning-date{font-size:10px;opacity:.72;font-weight:800}.cleaning-title{font-size:22px;font-weight:950}.cleaning-progress{padding:8px 13px;border-radius:999px;background:rgba(255,255,255,.15);font-size:14px;font-weight:950}.cleaning-area{margin:22px 4px 7px;color:#547064;font-size:12px;font-weight:950;letter-spacing:.08em}.cleaning-row{min-height:66px;padding:10px 12px 10px 17px;border:1px solid #e1e9e4;border-radius:17px;background:#fff;box-shadow:0 5px 13px rgba(38,63,51,.08);margin-bottom:8px}.cleaning-name{min-width:0;flex:1;font-size:14px;font-weight:900;line-height:1.35}.cleaning-toggle{min-width:76px!important;min-height:42px!important;border-radius:12px!important;font-size:11px!important;font-weight:950!important;touch-action:manipulation}.cleaning-toggle.is-pending{color:#b92f36!important;background:#fde6e7!important;border:1px solid #f4b9bd!important}.cleaning-toggle.is-done{color:#17623e!important;background:#e2f3e9!important}.cleaning-help,.cleaning-empty{width:100%;padding:18px 4px;color:#7a8780;font-size:10px;text-align:center}
    """)
