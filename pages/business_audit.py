from datetime import timedelta

from nicegui import ui

from core.auth import require_app_access, require_permission
from core.business_audit import BusinessAuditManager
from core.clock import today_jst
from core.data import data
from core.theme import Theme


audit = BusinessAuditManager(data)


@ui.page("/mirai-kessan/audit")
def business_audit_page():
    if not require_app_access("future_financials"):
        return
    if not require_permission("future_dashboard", "/mirai-kessan/input"):
        return
    Theme.page("入力の自動チェック｜未来決算", app_name="mirai-kessan")
    today = today_jst()
    content = Theme.shell("入力の自動チェック", "売上・仕入れ・人件費の入力ミスをまとめて確認",
                          back_to="/mirai-kessan/dashboard")
    with content:
        month_input = ui.input("対象月", value=today.strftime("%Y-%m")).props("type=month outlined").classes("w-full")

        @ui.refreshable
        def audit_view():
            try:
                result = audit.inspect(str(month_input.value), today - timedelta(days=1))
            except ValueError:
                ui.label("対象月を正しく選んでください").classes("text-negative")
                return
            with ui.card().classes("audit-summary w-full q-pa-lg q-mt-sm"):
                ui.label("入力の信頼度チェック").classes("text-sm font-black")
                ui.label("売上の未入力は前日分まで確認します").classes("text-[9px] text-grey-6")
                if result["ok"]:
                    ui.icon("verified").classes("text-positive text-4xl q-mt-sm")
                    ui.label("大きな入力ミスは見つかりませんでした").classes("text-lg font-black")
                else:
                    with ui.element("div").classes("audit-counts w-full q-mt-sm"):
                        for label, value, tone in (
                            ("要修正", result["danger"], "danger"),
                            ("要確認", result["warning"], "warning"),
                            ("未入力", result["missing"], "missing"),
                        ):
                            with ui.element("div").classes(f"audit-count {tone}"):
                                ui.label(label).classes("text-[9px] font-bold")
                                ui.label(f"{value}件").classes("text-xl font-black")
                ui.label(f"売上・仕入れ・勤務の {result['checked_records']} 件を確認").classes("text-[9px] text-grey-6 q-mt-sm")
            if result["issues"]:
                ui.label("確認する項目").classes("text-base font-black q-mt-md")
                for issue in result["issues"]:
                    with ui.card().classes(f"audit-issue {issue['level']} w-full q-pa-md cursor-pointer").on(
                        "click", lambda _, path=issue["path"]: ui.navigate.to(path)):
                        with ui.row().classes("w-full items-start justify-between no-wrap"):
                            with ui.column().classes("gap-1 min-w-0"):
                                ui.label(f"{issue['area']}　{issue['date'].replace('-', '/')}" if issue["date"] else issue["area"]).classes("text-[9px] font-bold text-grey-6")
                                ui.label(issue["title"]).classes("text-sm font-black")
                                ui.label(issue["detail"]).classes("text-[10px] text-grey-7")
                            ui.icon("chevron_right").classes("text-grey-5")

        month_input.on("change", audit_view.refresh)
        ui.button("もう一度チェック", icon="refresh", on_click=audit_view.refresh).props(
            "unelevated no-caps").classes("w-full q-mt-sm")
        audit_view()
        ui.add_css("""
        .audit-summary{border-radius:22px!important;background:linear-gradient(145deg,#F5F8F6,#EAF2ED)!important}.audit-counts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.audit-count{padding:10px;border-radius:13px;text-align:center;background:#fff}.audit-count.danger{color:#A9342E;background:#FCE9E7}.audit-count.warning{color:#8B5D11;background:#FFF2D8}.audit-count.missing{color:#405E72;background:#EAF2F7}.audit-issue{border-radius:16px!important;box-shadow:none!important;border-left:5px solid #9AA7A0!important}.audit-issue.danger{border-left-color:#C34D45!important}.audit-issue.warning{border-left-color:#D39A32!important}.audit-issue.missing{border-left-color:#66889D!important}
        """)
