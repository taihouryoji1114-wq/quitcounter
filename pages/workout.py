from nicegui import ui
from datetime import date

from core.theme import Theme
from core.data import data
from core.utils import days_ago


@ui.page("/workout")
def workout():

    Theme.page("筋トレ")

    today = str(date.today())

    today_record = None

    for workout in data.get_workouts():
        if workout["date"] == today:
            today_record = workout
            break

    with ui.column().classes("w-full items-center q-pa-xl"):

        ui.label("💪").classes("text-6xl")
        ui.label("筋トレ").classes("text-4xl font-bold")

        ui.space().style("height:20px")

        chest = ui.checkbox(
            "胸",
            value=today_record is not None and "胸" in today_record["parts"],
        )

        shoulder = ui.checkbox(
            "肩",
            value=today_record is not None and "肩" in today_record["parts"],
        )

        arm = ui.checkbox(
            "腕",
            value=today_record is not None and "腕" in today_record["parts"],
        )

        back = ui.checkbox(
            "背中",
            value=today_record is not None and "背中" in today_record["parts"],
        )

        abs_ = ui.checkbox(
            "腹筋",
            value=today_record is not None and "腹筋" in today_record["parts"],
        )

        leg = ui.checkbox(
            "脚",
            value=today_record is not None and "脚" in today_record["parts"],
        )

        ui.space().style("height:20px")

        def save():

            parts = []

            if chest.value:
                parts.append("胸")

            if shoulder.value:
                parts.append("肩")

            if arm.value:
                parts.append("腕")

            if back.value:
                parts.append("背中")

            if abs_.value:
                parts.append("腹筋")

            if leg.value:
                parts.append("脚")

            workouts = data.get_workouts()

            if today_record:

                if len(parts) == 0:
                    workouts.remove(today_record)
                else:
                    today_record["parts"] = parts

            else:

                if len(parts) == 0:
                    ui.notify("部位を選択してください")
                    return

                workouts.append(
                    {
                        "date": today,
                        "parts": parts,
                    }
                )

            data.save()

            ui.notify("更新しました💪")

            ui.navigate.reload()

        ui.button(
            "💾 更新" if today_record else "💾 保存",
            on_click=save,
        ).classes("w-80")

        ui.space().style("height:30px")

        ui.label("📖 最近の記録").classes(
            "text-xl font-bold"
        )

        workouts = data.get_workouts()

        if not workouts:

            ui.label("まだ記録がありません")

        else:

            for workout in reversed(workouts):

                with ui.card().classes("w-80"):

                    ui.label(
                        days_ago(workout["date"])
                    ).classes(
                        "text-lg font-bold text-blue"
                    )

                    ui.label(workout["date"]).classes(
                        "text-grey"
                    )

                    ui.separator()

                    for part in workout["parts"]:
                        ui.label(f"✅ {part}")

        ui.space().style("height:20px")

        ui.button(
            "🏠 ホーム",
            on_click=lambda: ui.navigate.to("/"),
        ).classes("w-80")