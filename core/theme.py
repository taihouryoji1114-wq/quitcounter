from nicegui import ui


class Theme:
    @staticmethod
    def page(title="Habitory"):
        ui.colors(primary="#4F7C68", secondary="#A7BCAE", positive="#4F7C68")
        ui.page_title(title)
        ui.add_head_html("""
        <style>
          body { background: #F7F7F5; color: #1D2822; font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; }
          .app-shell { width: min(100%, 680px); margin: 0 auto; padding: 28px 20px 48px; box-sizing: border-box; }
          .hero-card, .surface-card { background: rgba(255,255,255,.92); border: 1px solid #E6E8E4; border-radius: 28px; box-shadow: 0 8px 28px rgba(39,55,45,.06); }
          .habit-card { background: #FFF; border: 1px solid #E6E8E4; border-radius: 28px; box-shadow: 0 8px 24px rgba(39,55,45,.055); transition: transform .18s ease, box-shadow .18s ease; }
          .habit-card:hover { transform: translateY(-2px); box-shadow: 0 14px 32px rgba(39,55,45,.10); }
          .section-kicker { color: #718078; font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
          .metric-value { letter-spacing: -.045em; }
          .calendar-day { min-height: 72px; border-radius: 16px; background: #FBFCFA; border: 1px solid #EEF0EC; }
          .calendar-day:hover { background: #F0F5F1; }
          .body-part .q-checkbox__label { font-weight: 600; }
          .q-btn { border-radius: 14px; min-height: 44px; font-weight: 650; letter-spacing: 0; }
          @media (min-width: 640px) { .app-shell { padding: 40px 32px 64px; } }
        </style>
        """)

    @staticmethod
    def shell(title, subtitle, back_to=None, action=None):
        with ui.column().classes("app-shell gap-0"):
            with ui.row().classes("w-full items-center justify-between no-wrap q-mb-lg"):
                if back_to:
                    ui.button("ホーム", icon="arrow_back", on_click=lambda: ui.navigate.to(back_to)).props("flat").classes("text-grey-8")
                else:
                    ui.label("Habitory").classes("text-xl font-bold")
                if action:
                    action()
            ui.label(title).classes("text-4xl font-bold metric-value")
            ui.label(subtitle).classes("text-grey-7 q-mt-xs q-mb-xl")
            return ui.column().classes("w-full gap-0")
