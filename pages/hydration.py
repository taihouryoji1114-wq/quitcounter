from nicegui import ui

from core.auth import require_login, selected_user_id
from core.clock import today_jst_string
from core.data import data
from core.hydration import hydration
from core.theme import Theme


@ui.page("/habitory/hydration")
def hydration_page():
    if not require_login():
        return
    Theme.page("水分")
    page_user_id = selected_user_id()
    today = today_jst_string()
    content = Theme.shell("水分", "今日も、こまめにひと息。", back_to="/habitory")

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

        def undo_last():
            try:
                amount = hydration.undo_last(today, page_user_id)
            except (RuntimeError, ValueError) as error:
                ui.notify(str(error), type="warning")
                return
            ui.notify(f"直前の{amount}mlを取り消しました", type="positive")
            today_status.refresh()

        today_status()
        with ui.card().classes("surface-card w-full q-pa-lg"):
            ui.label("水分を記録").classes("section-kicker q-mb-sm")
            with ui.row().classes("w-full gap-2 q-mb-md"):
                for amount in (100, 250, 500):
                    ui.button(
                        f"+{amount}ml",
                        on_click=lambda _, value=amount: add_amount(value),
                    ).props("outline").classes("flex-1")
            custom_amount = ui.number(
                "任意入力（ml）", min=1, step=1
            ).props("outlined suffix=ml").classes("w-full q-mb-sm")
            ui.button(
                "記録する",
                icon="add",
                on_click=lambda: add_amount(custom_amount.value),
            ).classes("w-full")
            ui.button(
                "直前の記録を取り消す",
                icon="undo",
                on_click=undo_last,
            ).props("flat").classes("w-full q-mt-sm text-grey-7")
