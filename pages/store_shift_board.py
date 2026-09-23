"""A shared, manually published shift board."""
from calendar import monthrange
from datetime import date
from nicegui import ui
from core.auth import current_staff_id, has_permission, require_app_access
from core.clock import today_jst
from core.shift_board import shift_board
from core.staff_identity import staff_display_name
from core.theme import Theme
from pages.store_common import store_header_actions


def check_editor():
    if not has_permission('store_manage'):
        raise ValueError('シフトを編集・公開できるのは管理者だけです')


@ui.page('/store-ops/shift-board')
def shift_board_page():
    if not require_app_access('store_ops'):
        return
    Theme.page('シフトボード', app_name='store-ops')
    content = Theme.shell('シフトボード', 'Excelで決めた勤務予定を共有',
                          back_to='/store-ops', action=store_header_actions, brand='SHIFT BOARD')
    today = today_jst()
    selected = {'year': today.year, 'month': today.month}
    identity = current_staff_id()

    def grid(entries, year, month):
        staff_ids = [s for s in shift_board.STAFF if entries.get(s) or s == identity]
        if not staff_ids:
            ui.label('勤務予定の入力はありません')
            return
        ui.label('横にスクロールできます。— は未入力です（休みとは別です）。').classes('text-xs text-grey-7')
        with ui.element('div').classes('w-full overflow-x-auto'):
            with ui.element('div').style(f'display:grid;grid-template-columns:85px repeat({len(staff_ids)},150px);width:max-content'):
                ui.label('日付').classes('p-2 font-bold bg-grey-2')
                for staff in staff_ids:
                    ui.label(staff_display_name(staff) + ('（あなた）' if staff == identity else '')).classes('p-2 font-bold ' + ('bg-green-2' if staff == identity else 'bg-grey-2'))
                for d in range(1, monthrange(year, month)[1]+1):
                    weekday = '月火水木金土日'[date(year, month, d).weekday()]
                    ui.label(f'{month}/{d}（{weekday}）').classes('p-2 border-b bg-grey-1')
                    for staff in staff_ids:
                        ui.label(entries.get(staff, {}).get(str(d), '—')).classes('p-2 border-b whitespace-pre-wrap ' + ('bg-green-1' if staff == identity else ''))

    @ui.refreshable
    def body():
        year, month = selected['year'], selected['month']
        board = shift_board.month(year, month)
        published = board['published']
        with ui.card().classes('w-full p-4'):
            ui.label(f'{year}年{month}月の確定シフト').classes('text-xl font-bold')
            if published is None:
                ui.label('未公開').classes('text-orange-8 font-bold')
            else:
                ui.label('最終公開：' + published['updated_at']).classes('text-xs text-grey-7')
                grid(published['entries'], year, month)
        if not has_permission('store_manage'):
            return
        with ui.expansion('管理者：シフトを入力・公開', icon='edit_calendar', value=True).classes('w-full'):
            ui.label('Excelで決定した内容を転記してください。下書きはスタッフには表示されません。')
            ui.label('例：11:00〜15:00 / 17:00〜22:00、ランチ、休み。空欄は未入力として表示します。').classes('text-xs text-grey-7')
            person = ui.select({s: staff_display_name(s) for s in shift_board.STAFF}, value=identity or 'スタッフA', label='入力する人').classes('w-full')

            @ui.refreshable
            def editor():
                staff = person.value
                saved = shift_board.month(year, month)['draft'].get(staff, {})
                fields = {}
                for d in range(1, monthrange(year, month)[1]+1):
                    weekday = '月火水木金土日'[date(year, month, d).weekday()]
                    fields[str(d)] = ui.input(f'{month}/{d}（{weekday}）', value=saved.get(str(d), ''), placeholder='勤務時間・休み').props('outlined dense maxlength=100').classes('w-full')

                def save():
                    try:
                        check_editor()
                        shift_board.save_staff(year, month, staff, {d: f.value for d, f in fields.items()})
                    except ValueError as error:
                        ui.notify(str(error), type='negative')
                        return
                    ui.notify('下書きを保存しました。スタッフへの表示には公開が必要です。', type='positive')
                ui.button('この人の下書きを保存', on_click=save, icon='save').classes('w-full')
            person.on_value_change(lambda: editor.refresh())
            ui.label('人や月を切り替える前に、下書きを保存してください。').classes('text-xs text-orange-9')
            editor()

            def review():
                try:
                    check_editor()
                except ValueError as error:
                    ui.notify(str(error), type='negative')
                    return
                draft = shift_board.month(year, month)['draft']
                with ui.dialog() as dialog, ui.card().classes('w-full').style('max-width:950px'):
                    ui.label(f'{year}年{month}月 公開前の確認').classes('text-lg font-bold')
                    ui.label('保存済みの下書き全員分を公開します。入力欄で未保存の変更は含まれません。')
                    missing = [staff_display_name(s) for s in shift_board.STAFF if not draft.get(s)]
                    if missing:
                        ui.label('未入力の人：' + '、'.join(missing))
                    grid(draft, year, month)
                    def publish():
                        try:
                            check_editor()
                            # Publish exactly the saved draft reviewed in this dialog.
                            if shift_board.month(year, month)['draft'] != draft:
                                raise ValueError('下書きが更新されました。確認画面を開き直してください')
                            shift_board.publish(year, month)
                        except ValueError as error:
                            ui.notify(str(error), type='negative')
                            return
                        dialog.close()
                        body.refresh()
                        ui.notify('シフトボードに公開しました', type='positive')
                    ui.button('この内容をシフトボードに公開', on_click=publish)
                    ui.button('戻る', on_click=dialog.close).props('flat')
                dialog.open()
            ui.button('保存済みの下書きを確認・公開', on_click=review, icon='publish').classes('w-full q-mt-md')

    def move(delta):
        index = selected['year'] * 12 + selected['month'] - 1 + delta
        selected['year'], zero_month = divmod(index, 12)
        selected['month'] = zero_month + 1
        month_label.set_text(f"{selected['year']}年{selected['month']}月")
        body.refresh()

    with content:
        with ui.row().classes('w-full items-center justify-between'):
            ui.button('前月', on_click=lambda: move(-1)).props('flat')
            month_label = ui.label(f'{today.year}年{today.month}月').classes('font-bold')
            ui.button('翌月', on_click=lambda: move(1)).props('flat')
        body()
