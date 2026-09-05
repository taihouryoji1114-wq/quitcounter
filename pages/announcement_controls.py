import json
from nicegui import ui
from core.auth import has_permission, require_app_access
from core.announcements import announcements
from core.clock import now_jst

receivers = {}


def announcement_player():
    ui.add_head_html('<script src="/static/store_announcements.js?v=2"></script>')
    with ui.row().classes("gap-0"):
        ui.button("音声開始", icon="volume_up").props("flat dense").on(
            "click", js_handler="(e) => window.chankoAnnouncements?.enable(e.currentTarget)")
        ui.button(icon="volume_off").props("flat round dense aria-label='音声を停止'").on(
            "click", js_handler="() => { window.chankoAnnouncements?.stop(); }")
    async def tick():
        status = await ui.run_javascript("return window.chankoAnnouncements?.sync(" + json.dumps(announcements.items(), ensure_ascii=True) + "," + json.dumps(now_jst().isoformat()) + ");")
        current = now_jst().timestamp()
        for key in list(receivers):
            if current - receivers[key]["seen"] > 60:
                del receivers[key]
        if isinstance(status, dict):
            receivers[ui.context.client.id] = {"seen": current, "ready": bool(status.get("ready"))}
    ui.timer(5, tick)


def announcement_settings():
    with ui.expansion("① スマホで時刻・セリフを設定", icon="campaign", value=False).classes("w-full q-mb-sm"):
        ui.label("ここで保存した設定は店のiPadにも共有されます。保存しただけでは音は鳴りません。iPadで「アナウンス」を開き「店内スピーカーを開始」を押してください。").classes("text-sm")
        ui.button("② 鳴らす端末の準備画面へ", icon="tablet_mac", on_click=lambda: ui.navigate.to("/store-ops/announcements")).classes("w-full")
        @ui.refreshable
        def receiver_status():
            count = sum(1 for record in receivers.values() if record["ready"] and now_jst().timestamp() - record["seen"] < 20)
            ui.label(f"接続中の再生待機画面：{count}件" if count else "再生待機中の端末がありません。店のiPadで開始してください。").classes("text-sm font-bold q-my-sm")
        receiver_status()
        ui.timer(5, receiver_status.refresh)
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
                        ui.notify("保存しました。接続中のiPadへ約5秒で共有されます。", type="positive")
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
        with ui.card().classes("w-full q-pa-lg").style("background:#173D30;color:white;border-radius:24px"):
            ui.label("② 店のiPadをスピーカーにする").classes("text-xl font-bold")
            ui.label("このiPadで下のボタンを押してください。スマホ側で押してもiPadの音声は開始しません。").classes("text-sm")
            ui.button("店内スピーカーを開始", icon="volume_up").props("unelevated color=amber-8 text-color=black").classes("w-full q-py-md text-lg").on(
                "click", js_handler="(e) => window.chankoAnnouncements?.enable(e.currentTarget)")
            ui.label("停止中：開始ボタンを押してください").props("data-announcement-status").classes("text-base font-bold q-mt-sm")
            ui.label().props("data-announcement-lock").classes("text-xs")
            ui.button("停止する", icon="volume_off").props("outline color=white").on("click", js_handler="() => window.chankoAnnouncements?.stop()")
        ui.label("開始の声が聞こえたら、この画面を表示したままにしてください。画面ロック・別アプリへの移動では止まります。充電につなぎ、熱がこもらない場所で使用してください。").classes("text-sm q-mt-md")
        ui.label("ページ移動・再読み込み後は、もう一度開始ボタンを押してください。").classes("text-sm font-bold")
        ui.label("最終再生").classes("font-bold q-mt-md")
        ui.label("まだ再生していません").props("data-announcement-last").classes("text-sm")
        ui.label("毎日のアナウンス").classes("text-lg font-bold q-mt-lg")
        @ui.refreshable
        def schedule():
            items = announcements.items()
            if not items:
                ui.label("まだ登録されていません。管理者が登録・設定から追加できます。")
            for item in sorted(items, key=lambda item: item["time"]):
                with ui.card().classes("w-full"):
                    ui.label(f"{item['time']}　{'有効' if item['enabled'] else '停止中'}").classes("font-bold")
                    ui.label(item["message"])
        schedule()
        ui.timer(5, schedule.refresh)
        if has_permission("store_manage"):
            ui.button("管理者設定へ", icon="settings", on_click=lambda: ui.navigate.to("/store-ops/settings"))
        ui.label("お試しアナウンス").classes("text-lg font-bold q-mt-lg")
        ui.label("この端末だけで鳴ります。連打防止のため10秒間隔です。").classes("text-xs")
        for text in ("在庫チェックの時間です。", "そろそろご飯の時間です。", "みなさん、今日もお疲れさまです！"):
            ui.button(text, icon="play_arrow").classes("w-full").on("click", js_handler=
                "() => window.chankoAnnouncements?.test(" + json.dumps(text, ensure_ascii=True) + ")")
