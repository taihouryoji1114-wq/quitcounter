import json
from nicegui import ui
from core.auth import has_permission, require_app_access
from core.announcements import announcements
from core.clock import now_jst


def announcement_player():
    ui.add_head_html('<script src="/static/store_announcements.js"></script>')
    with ui.row().classes("gap-0"):
        ui.button("音声開始", icon="volume_up").props("flat dense").on(
            "click", js_handler="(e) => window.chankoAnnouncements?.enable(e.currentTarget)")
        ui.button(icon="volume_off").props("flat round dense aria-label='音声を停止'").on(
            "click", js_handler="() => { window.chankoAnnouncements?.stop(); }")
    async def tick():
        await ui.run_javascript("window.chankoAnnouncements?.tick(" + json.dumps(announcements.items(), ensure_ascii=True) + "," + json.dumps(now_jst().strftime("%Y-%m-%d %H:%M")) + ");")
    ui.timer(10, tick)


def announcement_settings():
    with ui.expansion("定時アナウンス", icon="campaign").classes("w-full q-mb-sm"):
        ui.label("毎日、指定時刻にこのページを開いている端末で鳴ります。音声開始を押して音量を確認してください。画面ロック中・別アプリ使用中は鳴りません。").classes("text-sm")
        @ui.refreshable
        def rows():
            for row in announcements.items() + [{"id": None, "time": "15:00", "message": "", "enabled": True}]:
                with ui.card().classes("w-full q-pa-sm"):
                    ui.label("新しいアナウンス" if not row["id"] else "登録済み").classes("font-bold")
                    time = ui.input("毎日の時刻", value=row["time"]).props("outlined dense type=time")
                    message = ui.input("セリフ（最初にチャイムが鳴ります）", value=row["message"]).props("outlined dense maxlength=120").classes("w-full")
                    enabled = ui.checkbox("有効", value=row["enabled"])
                    def save(_, selected=row, t=time, m=message, en=enabled):
                        if not has_permission("store_manage"):
                            return
                        try:
                            announcements.save(t.value, m.value, en.value, selected["id"])
                        except (ValueError, TypeError) as error:
                            ui.notify(str(error), type="negative")
                            return
                        rows.refresh()
                    ui.button("保存", on_click=save)
                    if row["id"]:
                        def delete(_, item_id=row["id"]):
                            if not has_permission("store_manage"):
                                return
                            announcements.delete(item_id)
                            rows.refresh()
                        ui.button("削除", on_click=delete).props("flat color=negative")
        rows()


@ui.page("/store-ops/announcements")
def announcement_page():
    if not require_app_access("store_ops"):
        return
    from pages.store_common import store_header_actions
    from core.theme import Theme
    Theme.page("アナウンス｜店舗運営", app_name="store-ops")
    content = Theme.shell("アナウンス", "開いている端末で、チャイムと声のお知らせ",
                          back_to="/store-ops", action=store_header_actions, brand="店舗運営")
    with content:
        ui.label("上の「音声開始」を押し、端末の音量を確認してください。ページを移動・再読み込みした時はもう一度押してください。ロック中・別アプリ使用中は鳴りません。").classes("text-sm")
        ui.label("毎日のアナウンス").classes("text-lg font-bold q-mt-lg")
        items = announcements.items()
        if not items:
            ui.label("まだ登録されていません。管理者が登録・設定から追加できます。")
        for item in items:
            with ui.card().classes("w-full"):
                ui.label(f"{item['time']}　{'有効' if item['enabled'] else '停止中'}").classes("font-bold")
                ui.label(item["message"])
        if has_permission("store_manage"):
            ui.button("管理者設定へ", icon="settings", on_click=lambda: ui.navigate.to("/store-ops/settings"))
        ui.label("お試しアナウンス").classes("text-lg font-bold q-mt-lg")
        ui.label("この端末だけで鳴ります。連打防止のため10秒間隔です。").classes("text-xs")
        for text in ("在庫チェックの時間です。", "そろそろご飯の時間です。", "みなさん、今日もお疲れさまです！"):
            ui.button(text, icon="play_arrow").classes("w-full").on("click", js_handler=
                "() => window.chankoAnnouncements?.test(" + json.dumps(text, ensure_ascii=True) + ")")
