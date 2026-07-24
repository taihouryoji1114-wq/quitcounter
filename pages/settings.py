from nicegui import ui

from core.data import data
from core.theme import Theme


@ui.page("/settings")
def settings():
    Theme.page("設定")
    profile, smoking = data.get_profile(), data.get_smoking()
    content = Theme.shell("設定", "あなたに合わせて整える", back_to="/")
    with content:
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("プロフィール").classes("section-kicker q-mb-md")
            name = ui.input("名前", value=profile["name"]).props("outlined").classes("w-full")
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-lg"):
            ui.label("禁煙").classes("section-kicker q-mb-md")
            start_date = ui.input("開始日", value=smoking["start_date"]).props("type=date outlined").classes("w-full q-mb-sm")
            cigarettes = ui.number("1日の本数", value=smoking["cigarettes_per_day"], min=0).props("outlined").classes("w-full q-mb-sm")
            price = ui.number("1箱の価格", value=smoking["price_per_pack"], min=0).props("outlined prefix=¥").classes("w-full")

        def save_settings():
            try:
                data.update_profile(name.value, start_date.value, cigarettes.value or 0, price.value or 0)
            except (RuntimeError, ValueError) as error:
                ui.notify(f"保存できませんでした: {error}", type="negative")
                return
            ui.notify("設定を保存しました", type="positive")
            ui.navigate.to("/")

        ui.button("変更を保存", icon="check", on_click=save_settings).classes("w-full")
