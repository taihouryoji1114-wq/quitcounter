from datetime import date

from nicegui import ui

from core.data import data
from core.hydration import hydration
from core.theme import Theme


@ui.page("/hydration")
def hydration_page():
    Theme.page("水分")
    page_user_id = data.active_user_id
    today = date.today().isoformat()
    content = Theme.shell("水分", "今日も、こまめにひと息。", back_to="/")

    with content:
        @ui.refreshable
        def today_status():
            summary = hydration.summary(today, page_user_id)
            goal_text = f" / {summary['goal']}ml" if summary["goal"] else "ml"
            with ui.card().classes("hero-card w-full q-pa-xl q-mb-md"):
                ui.label("今日の水分量").classes("section-kicker")
                ui.label(f"{summary['amount']}{goal_text}").classes(
                    "text-4xl font-bold metric-value q-mt-sm"
                )
                if summary["percentage"] is None:
                    ui.label("設定画面で目標水分量を設定できます").classes(
                        "text-grey-7 q-mt-sm"
                    )
                else:
                    ui.label(f"達成率 {summary['percentage']}%").classes(
                        "text-xl font-bold q-mt-sm"
                    )

        def add_amount(amount):
            try:
                hydration.add(amount, today, page_user_id)
            except (RuntimeError, ValueError) as error:
                ui.notify(f"保存できませんでした: {error}", type="negative")
                return
            ui.notify(f"{int(amount)}mlを記録しました", type="positive")
            custom_amount.value = None
            today_status.refresh()

        today_status()
        with ui.card().classes("surface-card w-full q-pa-lg"):
            ui.label("水分を記録").classes("section-kicker q-mb-sm")
            with ui.row().classes("w-full gap-2 q-mb-md"):
                for amount in (100, 300, 500):
                    ui.button(
                        f"+{amount}ml",
                        on_click=lambda _, value=amount: add_amount(value),
                    ).props("outline").classes("flex-1")
            custom_amount = ui.number(
                "任意入力（ml）", min=100, step=100
            ).props("outlined suffix=ml").classes("w-full q-mb-sm")
            ui.button(
                "記録する",
                icon="add",
                on_click=lambda: add_amount(custom_amount.value),
            ).classes("w-full")
