from nicegui import ui

from core.auth import require_login
from core.calories import ACTIVITY_FACTORS, nutrition_settings
from core.data import data
from core.hydration import hydration
from core.theme import Theme


@ui.page("/habitory/settings")
def settings():
    if not require_login():
        return
    Theme.page("設定")
    page_user_id = data.active_user_id
    profile = data.get_profile(page_user_id)
    smoking = data.get_smoking(page_user_id)
    hydration_goal = hydration.get_goal(page_user_id)
    nutrition = nutrition_settings.get_settings(page_user_id)
    content = Theme.shell("設定", "あなたに合わせて整える", back_to="/habitory")
    with content:
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
            ui.label("プロフィール").classes("section-kicker q-mb-md")
            name = ui.input("名前", value=profile["name"]).props("outlined").classes("w-full")
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-lg"):
            ui.label("禁煙").classes("section-kicker q-mb-md")
            start_date = ui.input("開始日", value=smoking["start_date"]).props("type=date outlined").classes("w-full q-mb-sm")
            cigarettes = ui.number("1日の本数", value=smoking["cigarettes_per_day"], min=0).props("outlined").classes("w-full q-mb-sm")
            price = ui.number("1箱の価格", value=smoking["price_per_pack"], min=0).props("outlined prefix=¥").classes("w-full")
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-lg"):
            ui.label("水分").classes("section-kicker q-mb-md")
            hydration_goal_input = ui.number(
                "目標水分量",
                value=hydration_goal,
                min=100,
                step=100,
            ).props("outlined suffix=ml clearable").classes("w-full")
        with ui.card().classes("surface-card w-full q-pa-lg q-mb-lg"):
            ui.label("栄養").classes("section-kicker q-mb-md")
            protein_goal = ui.number(
                "目標タンパク質",
                value=nutrition["protein_goal"],
                min=1,
            ).props("outlined suffix=g clearable").classes("w-full q-mb-sm")
            calorie_goal = ui.number(
                "目標カロリー",
                value=nutrition["calorie_goal"],
                min=1,
            ).props("outlined suffix=kcal clearable").classes("w-full q-mb-sm")
            basal_metabolism = ui.number(
                "基礎代謝",
                value=nutrition["basal_metabolism"],
                min=1,
            ).props("outlined suffix=kcal clearable").classes("w-full q-mb-sm")
            activity_level = ui.select(
                list(ACTIVITY_FACTORS),
                label="活動量",
                value=nutrition["activity_level"],
                clearable=True,
            ).props("outlined").classes("w-full")

        def save_settings():
            try:
                hydration.validate_goal(hydration_goal_input.value)
                nutrition_settings.validate_settings(
                    protein_goal.value,
                    calorie_goal.value,
                    basal_metabolism.value,
                    activity_level.value,
                )
                data.update_profile(
                    name.value,
                    start_date.value,
                    cigarettes.value or 0,
                    price.value or 0,
                    page_user_id,
                )
                hydration.set_goal(hydration_goal_input.value, page_user_id)
                nutrition_settings.save_settings(
                    protein_goal.value,
                    calorie_goal.value,
                    basal_metabolism.value,
                    activity_level.value,
                    page_user_id,
                )
            except (RuntimeError, ValueError) as error:
                ui.notify(f"保存できませんでした: {error}", type="negative")
                return
            ui.notify("設定を保存しました", type="positive")
            ui.navigate.to("/habitory")

        ui.button("変更を保存", icon="check", on_click=save_settings).classes("w-full")
