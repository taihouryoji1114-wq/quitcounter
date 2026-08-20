from nicegui import ui


class Theme:
    @staticmethod
    def page(title="Habitory", app_name="habitory"):
        ui.colors(primary="#4F7C68", secondary="#A7BCAE", positive="#4F7C68")
        ui.page_title(title)
        if app_name == "mirai-kessan":
            manifest = "/static/mirai-kessan-manifest.json"
            icon = "/static/mirai_kessan_icon.png"
            theme_color = "#164A38"
        elif app_name == "store-ops":
            manifest = "/static/store-ops-manifest.json"
            icon = "/static/store_ops_chanko_icon_v2.png"
            theme_color = "#164A38"
        elif app_name == "schedule":
            manifest = "/static/schedule-manifest.json"
            icon = "/static/schedule_icon.svg"
            theme_color = "#172F4B"
        elif app_name == "grid-empire":
            manifest = "/static/grid-empire-manifest.json"
            icon = "/static/grid_empire_icon.svg"
            theme_color = "#081525"
        else:
            manifest = "/static/manifest.json"
            icon = "/static/habitory_icon.png"
            theme_color = "#4F7C68"
        app_head = f"""
        <link rel="manifest" href="{manifest}">
        <link rel="apple-touch-icon" href="{icon}">
        <link rel="icon" href="{icon}">
        <meta name="theme-color" content="{theme_color}">
        """
        shared_styles = """
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
          .calendar-day.today-calendar-day { background: #FFF5F4; border: 2px solid #E3A09A; box-shadow: 0 0 0 2px rgba(255,255,255,.9) inset; }
          .today-date-number { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; color: #FFF; background: #D9544D; border-radius: 999px; font-size: 12px; font-weight: 800; box-shadow: 0 3px 9px rgba(217,84,77,.25); }
          .body-part .q-checkbox__label { font-weight: 600; }
          .q-btn { border-radius: 14px; min-height: 44px; font-weight: 650; letter-spacing: 0; }
          @media (min-width: 640px) { .app-shell { padding: 40px 32px 64px; } }
        </style>
        """
        ui.add_head_html(app_head + shared_styles)

    @staticmethod
    def shell(title, subtitle, back_to=None, action=None, brand="Habitory"):
        with ui.column().classes("app-shell gap-0"):
            with ui.row().classes("w-full items-center justify-between no-wrap q-mb-lg"):
                if back_to:
                    ui.button(icon="arrow_back", on_click=ui.navigate.back).props(
                        "flat round aria-label='1つ前へ戻る'"
                    ).classes("text-grey-8").tooltip("1つ前へ戻る")
                else:
                    ui.label(brand).classes("text-xl font-bold")
                if action:
                    action()
            ui.label(title).classes("text-4xl font-bold metric-value")
            ui.label(subtitle).classes("text-grey-7 q-mt-xs q-mb-xl")
            return ui.column().classes("w-full gap-0")
