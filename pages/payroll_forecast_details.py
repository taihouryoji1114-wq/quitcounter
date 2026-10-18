"""Shared read-only explanation of included and excluded payroll."""
from collections import defaultdict
from nicegui import ui
from core.staff_identity import staff_display_name


def render_payroll_details(outlook):
    issues = outlook.get('payroll_issues', [])
    title = f'人件費予測・未反映の内訳（{len(issues)}件）' if issues else '人件費予測の内訳'
    with ui.expansion(title, icon='fact_check').classes('w-full'):
        ui.label(outlook['month']+' の人件費予測').classes('font-bold')
        for label, amount in outlook.get('payroll_breakdown', {}).items():
            with ui.row().classes('w-full justify-between'):
                ui.label(label).classes('text-xs')
                ui.label(f'¥{amount:,}').classes('font-bold text-sm')
        if issues:
            ui.label('次の勤務枠は金額に含まれていません。休みの場合はシフトボードに「休み」と入力して公開してください。').classes('finance-warning text-sm')
        else:
            ui.label('未反映の勤務枠はありません。').classes('text-sm')
        grouped = defaultdict(list)
        for item in issues:
            grouped[(item['staff'],item['reason'])].append(item['date'])
        for (staff, reason), dates in grouped.items():
            with ui.column().classes('w-full gap-1 q-mt-sm'):
                ui.label(f'{staff_display_name(staff)} · {reason}').classes('font-bold text-sm')
                ui.label('、'.join(f'{int(d[5:7])}/{int(d[8:])}' for d in sorted(dates))).classes('text-xs').style('overflow-wrap:anywhere')
        estimates = outlook.get('payroll_estimated', [])
        if estimates:
            with ui.expansion(f'推定時間で反映済み（{len(estimates)}件）').classes('w-full'):
                for item in estimates:
                    ui.label(f"{item['date']} · {staff_display_name(item['staff'])} · {item['reason']}").classes('text-xs')
        ui.label('勤務時間があるシフトも、休憩時間は過去実績から推定しています。').classes('text-xs finance-readable')
        with ui.row().classes('w-full gap-2'):
            ui.link('シフトボードで確認', '/store-ops/shift-board').style('color:#f6d390')
            ui.link('時給・実績を確認', '/mirai-kessan/staffing').style('color:#f6d390')
