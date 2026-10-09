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
    content = Theme.shell('シフトボード', '半月分の勤務予定をひと目で',
                          back_to='/store-ops', action=store_header_actions, brand='SHIFT BOARD')
    today = today_jst()
    selected = {'year': today.year, 'month': today.month, 'half': 'first' if today.day <= 15 else 'second'}
    identity = current_staff_id()

    ui.add_css(""".shift-scroll{overflow:auto;border:1px solid #d6ded8;border-radius:12px}.shift-cell{padding:3px 2px;min-height:30px;min-width:0;font-size:clamp(8px,1.8vw,12px);line-height:1.25;overflow-wrap:anywhere;border-right:1px solid #cbd5ce;border-bottom:1px solid #cbd5ce;white-space:pre-wrap}.shift-date{position:sticky;left:0;z-index:2;background:#f4f6f4}.shift-head{position:sticky;top:0;z-index:3;background:#edf2ee;font-weight:bold}.shift-own{box-shadow:inset 0 0 0 2px #47765b}.shift-warning{color:#8a291a;font-size:11px;font-weight:bold}""")

    def grid(entries, year, month, cells=None, warnings=False):
        staff_ids = [s for s in shift_board.STAFF if entries.get(s) or s == identity]
        if not staff_ids:
            ui.label('勤務予定の入力はありません')
            return
        ui.label('橙：ランチ　青：ディナー　緑：通し　—：未入力').classes('text-xs text-grey-7')
        with ui.element('div').classes('w-full shift-scroll'):
            with ui.element('div').style(f'display:grid;grid-template-columns:40px repeat({len(staff_ids)},minmax(0,1fr));width:100%'):
                ui.label('日付').classes('shift-cell shift-head shift-date')
                for staff in staff_ids:
                    ui.label(staff_display_name(staff) + ('★' if staff == identity else '')).classes('shift-cell shift-head ' + ('shift-own' if staff == identity else ''))
                for d in shift_board.days(year, month, selected['half']):
                    weekday = '月火水木金土日'[date(year, month, d).weekday()]
                    ui.label(f'{d} {weekday}').classes('shift-cell shift-date')
                    for staff in staff_ids:
                        text = entries.get(staff, {}).get(str(d), '')
                        cell = (cells or {}).get(staff, {}).get(str(d))
                        if cell is None:
                            # Legacy published shifts retain their original text, without importing later wishes.
                            kind = next((k for k in ('通し','ランチ','ディナー') if k in text), 'off')
                            cell = {'text': text or '—', 'kind': kind, 'warning': ''}
                        color = {'ランチ':'#ffe0b2','ディナー':'#d6eaff','通し':'#d5edcf'}.get(cell['kind'], '#f8f9f8')
                        with ui.column().classes('shift-cell gap-0 ' + ('shift-own' if staff == identity else '')).style('background:'+color):
                            ui.label(cell['text'].replace('未指定', '').replace('ディナー', '夜').replace('ランチ', '昼').replace('希望 ', '').replace('〜', '〜\n'))
                            if warnings and cell.get('warning'):
                                with ui.element('button').classes('shift-warning').props('aria-label="希望との相違を確認"'):
                                    ui.label('⚠')
                                    with ui.menu():
                                        ui.label(cell['warning']).classes('p-3').style('max-width:280px')

    @ui.refreshable
    def body():
        year, month = selected['year'], selected['month']
        board = shift_board.month(year, month)
        published = board['published']
        if published and published.get('periods') and selected['half'] not in published['periods']:
            published = None
        half_label = '前半（1〜15日）' if selected['half'] == 'first' else '後半（16日〜月末）'
        with ui.card().classes('w-full p-2'):
            ui.label(f'{year}年{month}月 {half_label}').classes('text-base font-bold')
            if published is None:
                ui.label('未公開').classes('text-orange-8 font-bold')
            else:
                ui.label('最終反映：' + published.get('periods', {}).get(selected['half'], published['updated_at'])).classes('text-xs text-grey-7')
                grid(published['entries'], year, month, published.get('cells'), warnings=True)
        if not has_permission('store_manage'):
            return
        with ui.expansion('管理者：シフトを入力・公開', icon='edit_calendar', value=False).classes('w-full'):
            ui.label('Excelで決定した内容を転記してください。下書きはスタッフには表示されません。')
            ui.label('ランチ＝オレンジ／ディナー＝青／通し＝緑。提出済みの希望時間を自動表示します。時間の直接入力もできます。').classes('text-xs text-grey-7')
            person = ui.select({s: staff_display_name(s) for s in shift_board.STAFF}, value=identity or 'スタッフA', label='入力する人').classes('w-full')

            @ui.refreshable
            def editor():
                staff = person.value
                saved = shift_board.month(year, month)['draft'].get(staff, {})
                fields = {}
                for d in shift_board.days(year, month, selected['half']):
                    weekday = '月火水木金土日'[date(year, month, d).weekday()]
                    fields[str(d)] = ui.input(f'{month}/{d}（{weekday}）', value=saved.get(str(d), ''), placeholder='勤務時間・休み').props('outlined dense maxlength=100').classes('w-full')

                @ui.refreshable
                def input_preview():
                    entries = {staff: {d: f.value for d, f in fields.items()}}
                    grid(entries, year, month, shift_board.resolved(year, month, entries), warnings=True)
                for field in fields.values():
                    field.on_value_change(lambda: input_preview.refresh())
                input_preview()

                def save():
                    try:
                        check_editor()
                        previous = shift_board.month(year, month)['draft'].get(staff, {})
                        updated = {d: t for d, t in previous.items() if d not in fields}
                        updated.update({d: f.value for d, f in fields.items()})
                        shift_board.save_staff(year, month, staff, updated)
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
                all_draft = shift_board.month(year, month)['draft']
                days = {str(d) for d in shift_board.days(year, month, selected['half'])}
                draft = {s: {d: t for d, t in v.items() if d in days} for s, v in all_draft.items() if s in shift_board.STAFF}
                resolved = shift_board.resolved(year, month, draft)
                issues = sum(bool(c['warning']) for v in resolved.values() for c in v.values())
                with ui.dialog() as dialog, ui.card().classes('w-full').style('max-width:950px'):
                    ui.label(f'{year}年{month}月 {half_label} 公開前の確認').classes('text-lg font-bold')
                    ui.label('選択した半月の保存済み下書きを公開します。入力欄で未保存の変更は含まれません。')
                    missing = [staff_display_name(s) for s in shift_board.STAFF if not draft.get(s)]
                    if missing:
                        ui.label('未入力の人：' + '、'.join(missing))
                    grid(draft, year, month, resolved, warnings=True)
                    acknowledgement = ui.checkbox(f'警告{issues}件を確認し、本人と勤務を確認しました') if issues else None
                    def publish():
                        try:
                            check_editor()
                            # Publish exactly the saved draft reviewed in this dialog.
                            if shift_board.month(year, month)['draft'] != all_draft:
                                raise ValueError('下書きが更新されました。確認画面を開き直してください')
                            if acknowledgement and not acknowledgement.value:
                                raise ValueError('警告を確認してチェックを入れてください')
                            shift_board.publish(year, month, selected['half'], expected=resolved)
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
        ui.toggle({'first': '前半 1〜15日', 'second': '後半 16日〜月末'}, value=selected['half'], on_change=lambda e: (selected.update(half=e.value), body.refresh())).classes('w-full')
        body()
