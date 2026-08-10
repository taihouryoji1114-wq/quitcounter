from datetime import datetime

from nicegui import ui

from core.auth import require_login, selected_user_id
from core.clock import today_jst_string
from core.data import data
from core.reading import reading
from core.theme import Theme


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}時間{minutes}分{seconds}秒"
    return f"{minutes}分{seconds}秒"


@ui.page("/habitory/reading")
def reading_page():
    if not require_login():
        return
    Theme.page("読書")
    page_user_id = selected_user_id()
    today = today_jst_string()
    current_month = today[:7]
    content = Theme.shell("読書", "本と過ごした時間を、少しずつ。", back_to="/habitory")

    with content:
        @ui.refreshable
        def timer_card():
            active = reading.active_started_at(page_user_id)
            goal = reading.get_goal_minutes(page_user_id)
            with ui.card().classes("hero-card w-full q-pa-xl q-mb-md"):
                ui.label("今日の読書").classes("section-kicker")
                elapsed = ui.label().classes("text-4xl font-bold metric-value q-mt-sm")
                goal_label = ui.label().classes("text-grey-7 q-mt-sm")

                def update_elapsed():
                    seconds = reading.total_seconds(today, page_user_id)
                    elapsed.text = format_duration(seconds)
                    goal_label.text = (
                        f"目標 {goal}分・達成率 {round(seconds / (goal * 60) * 100)}%"
                        if goal else "下の設定から目標時間を登録できます"
                    )
                    elapsed.update()
                    goal_label.update()

                update_elapsed()
                if active:
                    ui.label("📖 読書中").classes("text-positive font-bold q-mt-md")
                    ui.button("読み終わる", icon="stop", on_click=stop_reading).props(
                        "color=negative"
                    ).classes("w-full q-mt-md")
                    ui.timer(1, update_elapsed)
                else:
                    ui.button("読み始める", icon="play_arrow", on_click=start_reading).classes(
                        "w-full q-mt-md"
                    )

        @ui.refreshable
        def monthly_card():
            summary = reading.monthly_summary(current_month, page_user_id)
            with ui.card().classes("surface-card w-full q-pa-lg q-mb-md"):
                ui.label("今月の読書").classes("section-kicker")
                ui.label(format_duration(summary["seconds"])).classes(
                    "text-3xl font-bold metric-value q-mt-sm"
                )
                ui.label(
                    f"{current_month.replace('-', '年')}月・読書した日 {summary['days']}日"
                ).classes("text-grey-7 q-mt-xs")

        def start_reading():
            try:
                reading.start(page_user_id)
            except (RuntimeError, ValueError) as error:
                ui.notify(str(error), type="negative")
                return
            timer_card.refresh()
            ui.notify("読書タイマーを開始しました", type="positive")

        def stop_reading():
            try:
                reading.stop(page_user_id)
            except (RuntimeError, ValueError) as error:
                ui.notify(str(error), type="negative")
                return
            timer_card.refresh()
            session_list.refresh()
            monthly_card.refresh()
            ui.notify("読書時間を記録しました", type="positive")

        timer_card()
        monthly_card()

        with ui.expansion("目標時間を設定", icon="flag").classes(
            "surface-card w-full q-mb-md"
        ):
            goal_input = ui.number(
                "1日の目標", value=reading.get_goal_minutes(page_user_id), min=1, step=1
            ).props("outlined suffix=分").classes("w-full q-mb-sm")

            def save_goal():
                try:
                    reading.set_goal_minutes(goal_input.value, page_user_id)
                except (RuntimeError, ValueError) as error:
                    ui.notify(str(error), type="negative")
                    return
                timer_card.refresh()
                ui.notify("読書目標を保存しました", type="positive")

            ui.button("目標を保存", icon="check", on_click=save_goal).props("outline").classes("w-full")

        ui.label("今日の読書履歴").classes("text-xl font-bold q-mb-sm")

        @ui.refreshable
        def session_list():
            sessions = reading.sessions(today, page_user_id)
            if not sessions:
                ui.label("まだ読書記録はありません。").classes("text-grey-7")
                return
            for session in reversed(sessions):
                started = datetime.fromisoformat(session["started_at"])
                ended = datetime.fromisoformat(session["ended_at"])
                with ui.card().classes("surface-card w-full q-pa-md q-mb-sm"):
                    ui.label(
                        f"{started.strftime('%H:%M')} 〜 {ended.strftime('%H:%M')}"
                    ).classes("font-bold")
                    ui.label(format_duration(session["seconds"])).classes("text-grey-7")

        session_list()
