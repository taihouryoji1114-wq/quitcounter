"""The signed-in staff member's home; identity always comes from the session."""
from nicegui import ui
from core.auth import current_staff_id, require_app_access
from core.clock import today_jst
from core.staff_identity import staff_display_name
from core.shift_board import shift_board
from core.shift_submissions import shift_submissions
from core.theme import Theme
from pages.store_common import store_header_actions


def submission_period_for(today):
    if today.day <= 5:
        return today.year, today.month, 'second'
    month = today.month % 12 + 1
    year = today.year + (today.month == 12)
    return year, month, 'first' if today.day <= 20 else 'second'


@ui.page('/store-ops/me')
def personal_home():
    if not require_app_access('store_ops'):
        return
    identity = current_staff_id()
    if not identity:
        ui.navigate.to('/store-ops')
        return
    name = staff_display_name(identity)
    Theme.page(f'{name}のマイページ', app_name='store-ops')
    content = Theme.shell(f'{name}さん、お疲れさま！', '自分の予定と店舗の情報を、ここから',
                          back_to='/store-ops', action=store_header_actions, brand='MY PAGE')
    today = today_jst()
    year, month, half = submission_period_for(today)
    submitted = shift_submissions.submission(identity, year, month, half)
    published = shift_board.month(today.year, today.month)['published']
    with content:
        with ui.card().classes('surface-card w-full q-pa-lg'):
            ui.label('自分のシフト提出').classes('text-lg font-bold')
            ui.label(submitted['period']['label'])
            status = '変更申請の確認待ち' if submitted['pending_change'] else '提出済み' if submitted['submitted_at'] else '未提出'
            ui.label(status).classes('text-primary font-bold')
            ui.label('期限 '+submitted['period']['deadline']).classes('text-xs text-grey-7')
            ui.button('自分のシフトを提出・確認', icon='edit_calendar', on_click=lambda:
                      ui.navigate.to('/store-ops/shift-submission')).classes('w-full')
        with ui.card().classes('surface-card w-full q-pa-lg'):
            ui.label('シフトボード').classes('text-lg font-bold')
            ui.label(f'{today.month}月：' + ('公開済み' if published else '未公開')).classes('font-bold')
            ui.label('管理者が入力・公開した確定シフトを確認できます。').classes('text-xs text-grey-7')
            ui.button('シフトボードを見る', icon='calendar_month', on_click=lambda:
                      ui.navigate.to('/store-ops/shift-board')).classes('w-full')
        ui.button('店舗のライブボード・引き継ぎ', icon='dashboard', on_click=lambda:
                  ui.navigate.to('/store-ops')).classes('w-full q-mt-md')
        ui.button('仕入れリスト', icon='shopping_basket', on_click=lambda:
                  ui.navigate.to('/store-ops/purchase-list')).props('outline').classes('w-full')
