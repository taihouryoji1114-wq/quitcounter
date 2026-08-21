from nicegui import ui

from core.auth import require_app_access
from core.system_status import get_system_status
from core.theme import Theme


def _size(value):
    if value < 1024:
        return f"{value} B"
    if value < 1024 ** 2:
        return f"{value / 1024:.1f} KB"
    return f"{value / 1024 ** 2:.1f} MB"


@ui.page("/system-status")
def system_status_page():
    if not require_app_access("system_status"):
        return
    Theme.page("システム状況")
    status = get_system_status()
    content = Theme.shell("システム状況", "容量・保存・バックアップ", back_to="/")
    with content:
        tone = "positive" if status["percent"] < 70 else "warning" if status["percent"] < 85 else "negative"
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            with ui.row().classes("w-full items-end justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label("保存容量").classes("section-kicker")
                    ui.label(_size(status["used"])).classes("text-4xl font-bold metric-value q-mt-xs")
                ui.label(f'{status["percent"]:.3f}% / 1 GB').classes("text-grey-7")
            ui.linear_progress(value=min(status["percent"] / 100, 1), color=tone).props("rounded size=12px").classes("q-mt-md")
            ui.label(f'残り 約{_size(status["capacity"] - status["used"])}').classes("text-grey-7 q-mt-sm")
            with ui.row().classes("w-full justify-between q-pt-md q-mt-md border-t border-grey-3"):
                ui.label("アプリ本体").classes("text-grey-7")
                ui.label(_size(status["application_size"])).classes("font-bold")
            ui.label("アプリ本体は保存用1GBとは別枠です").classes("text-grey-6 text-xs")

        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("保存の安全確認").classes("text-xl font-bold q-mb-md")
            with ui.row().classes("w-full items-center no-wrap q-mb-md"):
                ui.icon("check_circle" if status["writable"] else "error").classes("text-3xl " + ("text-positive" if status["writable"] else "text-negative"))
                with ui.column().classes("gap-0"):
                    ui.label("正常に保存できます" if status["writable"] else "保存に問題があります").classes("font-bold")
                    ui.label(status["write_message"]).classes("text-grey-7 text-sm")
            with ui.row().classes("w-full justify-between q-py-sm border-t border-grey-3"):
                ui.label("データ最終更新").classes("text-grey-7")
                ui.label(status["last_saved"].strftime("%Y/%m/%d %H:%M") if status["last_saved"] else "まだ保存なし").classes("font-bold")
            with ui.row().classes("w-full justify-between q-py-sm border-t border-grey-3"):
                ui.label("自動バックアップ").classes("text-grey-7")
                ui.label(f'{status["backup_count"]}件 / 最大{status["backup_limit"]}件').classes("font-bold")
            with ui.row().classes("w-full justify-between q-py-sm border-t border-grey-3"):
                ui.label("最終バックアップ").classes("text-grey-7")
                ui.label(status["latest_backup"].strftime("%Y/%m/%d %H:%M") if status["latest_backup"] else "次回保存時に作成").classes("font-bold")

        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("アプリ別データ概算").classes("text-xl font-bold")
            ui.label("同じ安全な保存ファイルの中身を分類").classes("text-grey-7 text-sm q-mb-md")
            for name in ("未来決算", "店舗管理", "Habitory", "スケジュール", "その他"):
                with ui.row().classes("w-full justify-between q-py-sm border-t border-grey-3"):
                    ui.label(name)
                    ui.label(_size(status["groups"][name])).classes("font-bold")

        if status["percent"] < 70 and status["writable"]:
            ui.label("主要アプリの保存容量には十分な余裕があります").classes("w-full text-center text-positive font-bold q-mt-sm")
