from nicegui import ui

from core.auth import require_app_access
from core.store_manual import store_manual
from core.theme import Theme
from pages.store_common import store_header_actions


@ui.page("/store-ops/manual")
def store_manual_page():
    if not require_app_access("store_ops"):
        return
    Theme.page("マニュアル｜店舗運営", app_name="store-ops")
    content = Theme.shell("マニュアル", "困った時に、10秒で確認",
                          back_to="/store-ops", action=store_header_actions, brand="店舗運営")
    categories = store_manual.categories()
    manuals = store_manual.manuals()
    category_map = {value["id"]: value for value in categories}
    with content:
        if not manuals:
            with ui.card().classes("manual-empty w-full q-pa-xl text-center"):
                ui.icon("menu_book").classes("text-5xl text-primary")
                ui.label("マニュアルはまだありません").classes("text-base font-black q-mt-sm")
                ui.label("管理者が登録すると、ここへ表示されます").classes("text-xs text-grey-6")
        else:
            with ui.element("div").classes("manual-category-grid w-full"):
                for category in categories:
                    count = sum(value.get("category_id") == category["id"] for value in manuals)
                    if not count:
                        continue
                    with ui.card().classes("manual-category-card q-pa-md"):
                        ui.icon(category.get("icon", "menu_book")).classes("text-2xl")
                        ui.label(category["name"]).classes("text-sm font-black")
                        ui.label(f"{count}件").classes("text-[9px] text-grey-6")
            for manual in manuals:
                category = category_map.get(manual.get("category_id"), {})
                with ui.expansion(manual["title"], icon=category.get("icon", "article"),
                                  value=False).classes("manual-entry w-full q-mb-sm"):
                    if manual.get("summary"):
                        ui.label(manual["summary"]).classes("manual-summary")
                    if manual.get("image_url"):
                        ui.image(manual["image_url"]).classes("manual-image w-full")
                    for number, step in enumerate(manual.get("steps", []), 1):
                        with ui.row().classes("manual-step w-full items-start no-wrap"):
                            ui.label(str(number)).classes("manual-step-number")
                            ui.label(step).classes("manual-step-text")
                    if manual.get("caution"):
                        with ui.card().classes("manual-caution w-full q-pa-md"):
                            ui.label("注意").classes("text-[9px] font-black text-negative")
                            ui.label(manual["caution"]).classes("text-xs font-bold")
                    if manual.get("quiz_note"):
                        ui.label("ちゃんはや：" + manual["quiz_note"]).classes("manual-quiz-note")
        ui.add_css("""
        .manual-empty{border-radius:24px!important}.manual-category-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:16px}.manual-category-card{min-height:112px;border-radius:20px!important;border:1px solid #e2e9e5!important;box-shadow:0 6px 0 #d7dfda,0 11px 20px rgba(35,57,47,.1)!important;background:linear-gradient(145deg,#fff,#eff5f1)!important}.manual-entry{overflow:hidden;border:1px solid #dfe7e2!important;border-radius:18px!important;background:#fff!important}.manual-entry>.q-expansion-item__container>.q-item{min-height:62px;font-size:13px;font-weight:900}.manual-entry .q-expansion-item__content{padding:4px 15px 16px}.manual-summary{padding:10px 12px;margin-bottom:9px;border-radius:12px;background:#edf5f0;font-size:12px;font-weight:850;line-height:1.5}.manual-image{max-height:260px;object-fit:cover;border-radius:14px;margin-bottom:10px}.manual-step{padding:9px 2px;border-bottom:1px solid #edf0ee}.manual-step-number{display:grid;place-items:center;flex:0 0 27px;width:27px;height:27px;border-radius:50%;background:#28694e;color:#fff;font-size:11px;font-weight:950}.manual-step-text{font-size:12px;font-weight:750;line-height:1.5}.manual-caution{margin-top:11px;border:1px solid #f0c1bd!important;border-radius:14px!important;background:#fff3f1!important;box-shadow:none!important}.manual-quiz-note{margin-top:10px;padding:8px 10px;border-radius:11px;background:#fff4d6;color:#8a6419;font-size:10px;font-weight:850}
        """)
