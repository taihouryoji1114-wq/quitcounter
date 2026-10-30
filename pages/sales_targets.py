from datetime import date, timedelta
from nicegui import ui
from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.sales_targets import build_target_plan, save_target_plan, plan_results, weekly_adjustment, with_historical_targets, recommend_target, automatic_target_plan, use_automatic_landing
from core.theme import Theme


def target_table(plan, start, printable=False):
    selected = date.fromisoformat(start)
    records = financials.sales_records()
    display_plan = with_historical_targets(plan, data.data.get('sales_target_plans', {}).values())
    result = weekly_adjustment(display_plan, records, selected, today_jst())
    actual_by_day = {r['date']:r['amount'] for r in records if r.get('amount') is not None and r['date'] < today_jst().isoformat()}
    rows = {r['date']:r for r in result['rows']}
    html = '<table class="target-table"><thead><tr><th>日付</th><th>ランチ<br>当初目標</th><th>ディナー<br>当初目標</th><th>当初目標</th><th>実績</th><th>差額</th><th>新目標</th></tr></thead><tbody>'
    total = actual_total = revised_total = 0
    count = revised_count = 0
    for offset in range(7):
        day = selected + timedelta(days=offset)
        key = day.isoformat()
        label = f'{day.month}/{day.day}（{"月火水木金土日"[day.weekday()]}）'
        row = rows.get(key)
        if row:
            total += row['target']
            known = row['actual'] is not None
            if known:
                actual_total += row['actual']; count += 1
            if row['revised_target'] is not None:
                revised_total += row['revised_target']; revised_count += 1
            actual = f"¥{row['actual']:,}" if known else '未入力' if day < today_jst() else '—'
            difference = f"{row['difference']:+,}円" if known else '—'
            revised = f"¥{row['revised_target']:,}" if row['revised_target'] is not None else '—'
            session_cells = ''.join(f"<td>¥{row[session]:,}" + (f"<small>目安 {row[session+'_customers']}人</small>" if row.get(session+'_customers') is not None else '') + '</td>' for session in ('lunch','dinner'))
            html += f"<tr><th>{label}</th>{session_cells}<td>¥{row['target']:,}</td><td>{actual}</td><td>{difference}</td><td><strong>{revised}</strong></td></tr>"
        else:
            state = '対象月外' if not key.startswith(plan['month']) else '休業日' if key in plan['closed_dates'] else '目標未設定'
            value = actual_by_day.get(key) if key.startswith(plan['month']) else None
            if value is not None:
                actual_total += value; count += 1
            actual = f'¥{value:,}' if value is not None else '未入力' if day < today_jst() and state == '目標未設定' else '—'
            html += f'<tr><th>{label}</th><td colspan="3">{state}</td><td>{actual}</td><td>—</td><td>—</td></tr>' 
    actual_label = f'¥{actual_total:,}<small>入力済み{count}日分</small>' if count else '—'
    revised_label = f'¥{revised_total:,}<small>残り{revised_count}日分</small>' if revised_count else '—'
    html += f'<tr><th colspan="3">この7日間の合計</th><td>¥{total:,}</td><td>{actual_label}</td><td>{result["difference"]:+,}円</td><td>{revised_label}</td></tr></tbody></table>'
    html += '<p class="target-note">実績は昨日までの入力済み分。差額＝実績−当初目標。新目標はこの7日間の差額を今日以降の当初目標の比率で配分（最低0円）。元の保存目標は変更しません。</p>'
    if any(r.get('historical_target') for r in result['rows']):
        html += '<p class="target-note">作成前の日は以前の保存目標を表示。新しい目標作成時に実績を織り込み済みのため、以前の差額を新目標に二重加算しません。</p>'
    html += '<p class="target-note">目標の記録がない日も実績は表示します。差額は目標と実績の両方がある日だけを合計します。</p>'
    if result['missing']:
        html += f'<p class="target-note">未入力{result["missing"]}日分は差額の計算対象外です。実績を入力すると新目標も再計算されます。</p>'
    if result['unallocated']:
        html += f'<p class="target-note">この期間には残りの日がないため、不足{result["unallocated"]:,}円は配分していません。翌週には自動で繰り越しません。</p>'
    return html



TARGET_CSS = '''
.target-table{width:100%;border-collapse:collapse;font-size:12px;color:#f5f5f5;table-layout:fixed}
.target-table th,.target-table td{padding:9px 4px;border:1px solid #666;text-align:center;overflow-wrap:anywhere}
.target-table th{background:#252525}.target-table small{display:block;font-size:10px;margin-top:4px;color:#eee}
@media(max-width:440px){.target-table{font-size:10px}.target-table small{font-size:9px}.target-table td,.target-table th{padding:7px 2px}}
@media print{@page{size:A4 landscape;margin:12mm}.target-print-controls,.app-bottom-nav{display:none!important}
body:has(.target-print-sheet){background:#fff!important;color:#111!important}
.target-print-sheet{width:100%!important;max-width:none!important;padding:0!important;margin:0!important;color:#111!important;break-inside:avoid}
.target-print-sheet{gap:8px!important}body:has(.target-print-sheet) .nicegui-content{padding:0!important;gap:0!important}.target-print-sheet h1{font-size:22pt;margin:0 0 6px;line-height:1.2}.target-print-sheet p{font-size:11pt}
.target-note{font-size:9pt!important;line-height:1.4}.target-table{font-size:12pt!important;color:#111!important}.target-table th,.target-table td{box-sizing:border-box;padding:5px 6px!important;height:12mm;border-color:#333!important;background:white!important;color:#111!important}
.target-table small{font-size:10pt!important;color:#333!important}}
'''


def render_sales_targets(month):
    ui.add_css(TARGET_CSS)
    ui.add_css('.target-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;width:100%}.target-amount{font-size:clamp(19px,5.2vw,30px);font-weight:800;overflow-wrap:anywhere}.target-action{min-height:54px!important;font-size:16px!important}.target-dialog{width:900px;max-width:96vw!important;background:#171717!important;color:#fff!important}.target-dialog .target-table{min-width:680px}.target-week-scroll{width:100%;overflow-x:auto}')
    @ui.refreshable
    def board():
        plans = sorted((p for p in data.data.get('sales_target_plans',{}).values() if p['month']==month), key=lambda p:p['created_at'],reverse=True)
        closed = data.data.get('landing_forecast_settings',{}).get('closed_dates',[])
        suggestion = recommend_target(financials.sales_records(),month,today_jst(),closed)
        forecast = suggestion['forecast']
        landing_mode = data.data.get('sales_target_modes', {}).get(month) == 'landing'
        automatic = landing_mode or not plans
        if automatic:
            generated = automatic_target_plan(financials.sales_records(),month,today_jst(),closed,use_landing=landing_mode)
            plans = ([generated] + plans) if generated else []
        def money(value):return '記録を増やそう' if value is None else f'¥{value:,}'
        with ui.element('div').classes('target-summary q-mb-sm'):
            for label,value,icon in [('このままなら',forecast['landing'],'trending_up'),('おすすめ目標',suggestion['target'],'flag')]:
                with ui.card().classes('surface-card w-full q-pa-sm gap-1'):
                    ui.icon(icon).classes('finance-gold text-xl')
                    ui.label(label).classes('text-sm')
                    ui.label(money(value)).classes('target-amount')
        if forecast['missing']:
            ui.button(f"売上未入力 {len(forecast['missing'])}日を確認",icon='edit_note',on_click=lambda:ui.navigate.to('/mirai-kessan/tasks?month='+month)).props('flat').classes('w-full')
        with ui.dialog() as reason, ui.card().classes('target-dialog q-pa-md'):
            ui.label('どう決めた？').classes('text-xl font-bold')
            ui.label(suggestion['reason'])
            ui.label('前年同月の同曜日、または直近12週の売上を参考にしています。昨日までの実績で計算し、天気・予約・祝日はまだ含めていません。')
            ui.label(f"直近12週の記録：{suggestion['sample_days']}日。金額は税込です。")
            if suggestion['target'] is None:ui.label('記録不足、残りの営業日なし、または過去の月のため、新しい目標は提案していません。')
            ui.button('閉じる',on_click=reason.close).classes('w-full')
        ui.button('どう決めた？',icon='help_outline',on_click=reason.open).props('flat dense').classes('w-full')

        def save(value,source):
            if not require_permission('future_dashboard','/mirai-kessan/input'):return
            try:
                if source == 'manual' and value == 0:
                    use_automatic_landing(data,month)
                    manual.close();ui.notify('着地予測を目標に使います',type='positive');board.refresh();return
                records = financials.sales_records()
                closure = data.data.get('landing_forecast_settings',{}).get('closed_dates',[])
                current = recommend_target(records,month,today_jst(),closure) if source == 'recommended' else None
                # Adopt exactly the amount shown; refresh if records changed in another tab.
                if current and current['target'] != value:
                    ui.notify('実績が更新されました。新しいおすすめを確認してください',type='warning');board.refresh();return
                plan = build_target_plan(records,month,value or 0,today_jst(),closure)
                plan['source'] = source
                if current:plan['recommendation'] = {k:current[k] for k in ('reason','uplift','sample_days','version')}
                save_target_plan(data,plan)
            except (ValueError,TypeError) as error:
                ui.notify(str(error),type='warning');return
            manual.close();ui.notify('目標を保存しました',type='positive');board.refresh()

        with ui.dialog() as manual, ui.card().classes('target-dialog q-pa-md'):
            ui.label('自分で目標を決める').classes('text-xl font-bold')
            goal = ui.number('月の売上目標',value=0 if landing_mode else plans[0]['monthly_target'] if plans else None,min=0,step=10000).props('outlined prefix=¥').classes('w-full')
            ui.label('0円で保存すると、着地予測を自動で使います').classes('text-sm')
            ui.button('この金額で保存',icon='save',on_click=lambda:save(goal.value,'manual')).classes('w-full target-action')
            ui.button('戻る',on_click=manual.close).props('flat').classes('w-full')
        use = ui.button('おすすめを使う',icon='auto_awesome',on_click=lambda:save(suggestion['target'],'recommended')).classes('w-full target-action q-mb-sm')
        if suggestion['target'] is None:use.disable()
        ui.button('自分で決める',icon='edit',on_click=manual.open).props('outline').classes('w-full target-action q-mb-sm')
        if plans:
            ui.label(f"{'着地予測の目標' if landing_mode else '自動目標' if automatic else '今の目標'}　¥{plans[0]['monthly_target']:,}").classes('font-bold q-mb-sm')
        else:ui.label('売上を入力すると、自動目標と週間表が出ます').classes('text-sm q-mb-sm')

        if automatic and plans:ui.label('自動目標は実績に合わせて更新されます。固定する場合は「おすすめを使う」で保存。').classes('text-xs q-mb-sm')
        with ui.dialog() as week, ui.card().classes('target-dialog q-pa-md'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('週間表・印刷').classes('text-xl font-bold')
                ui.button(icon='close',on_click=week.close).props('flat round aria-label=閉じる')
            if plans:
                with ui.expansion('以前の目標を選ぶ',icon='history').classes('w-full'):
                    choice = ui.select({p['id']:f"{p['created_at'][:16].replace('T',' ')}・¥{p['monthly_target']:,}" for p in plans},value=plans[0]['id'],label='表示する目標').props('outlined').classes('w-full')
                default = max(month+'-01', min((today_jst()-timedelta(days=today_jst().weekday())).isoformat(),plans[0]['rows'][-1]['date'])) if plans[0]['rows'] else month+'-01'
                start = ui.input('開始日',value=default).props('type=date outlined').classes('w-full')
                with ui.row().classes('w-full no-wrap'):
                    def move(days):
                        try:start.value=(date.fromisoformat(start.value)+timedelta(days=days)).isoformat()
                        except (ValueError,TypeError):ui.notify('開始日を選んでください',type='warning')
                    ui.button('前の週',icon='chevron_left',on_click=lambda:move(-7)).props('outline').classes('grow')
                    ui.button('次の週',icon='chevron_right',on_click=lambda:move(7)).props('outline').classes('grow')
                def print_view():
                    try:day=date.fromisoformat(start.value).isoformat()
                    except (ValueError,TypeError):ui.notify('開始日を選んでください',type='warning');return
                    ui.navigate.to(f"/mirai-kessan/targets/print/{choice.value}?start={day}&month={month}")
                ui.button('印刷する',icon='print',on_click=print_view).classes('w-full target-action')
                ui.label('横に動かすと、新目標まで見られます').classes('text-xs')
                with ui.element('div').classes('target-week-scroll'):
                    table = ui.html('',sanitize=False).classes('w-full')
                def show():
                    plan = next(p for p in plans if p['id']==choice.value)
                    try:table.set_content(target_table(plan,start.value))
                    except (ValueError,TypeError):ui.notify('開始日を選んでください',type='warning')
                choice.on_value_change(show);start.on_value_change(show);show()
        weekly_button=ui.button('週間表・印刷',icon='print',on_click=week.open).classes('w-full target-action q-mb-sm')
        if not plans:weekly_button.disable()
    board()


@ui.page('/mirai-kessan/targets/print/{plan_id}')
def print_targets(plan_id: str, start: str = '', month: str = ''):
    if not require_app_access('future_financials') or not require_permission('future_dashboard','/mirai-kessan/input'):return
    if plan_id == 'automatic':
        try:
            month = date.fromisoformat((month or today_jst().strftime('%Y-%m'))+'-01').strftime('%Y-%m')
            plan = automatic_target_plan(financials.sales_records(),month,today_jst(),data.data.get('landing_forecast_settings',{}).get('closed_dates',[]),use_landing=data.data.get('sales_target_modes',{}).get(month)=='landing')
        except (ValueError,TypeError):
            ui.label('対象月を選び直してください');return
    else:
        plan=data.data.get('sales_target_plans',{}).get(plan_id)
    if not plan:
        ui.label('目標がないか、自動目標を作るための実績が不足しています');return
    try:start=date.fromisoformat(start or plan['as_of']).isoformat()
    except ValueError:
        ui.label('開始日が正しくありません');return
    Theme.page('週間売上目標',app_name='mirai-kessan');ui.add_css(TARGET_CSS)
    with ui.row().classes('target-print-controls'):
        ui.button('予測へ戻る',on_click=lambda:ui.navigate.to('/mirai-kessan/forecast?month='+plan['month']))
        ui.button('印刷・PDF保存',icon='print',on_click=lambda:ui.run_javascript('window.print()'))
    with ui.column().classes('target-print-sheet w-full').style('max-width:1100px;margin:auto;padding:20px'):
        ui.html('<h1>みんなで目指す、今週の売上</h1>',sanitize=False)
        ui.label(f"{start} 〜 {(date.fromisoformat(start)+timedelta(days=6)).isoformat()} ／ {'自動計算日' if plan_id == 'automatic' else '保存日'} {plan['created_at'][:10]}")
        ui.html(target_table(plan,start,True),sanitize=False).classes('w-full')
        ui.label(f'金額は税込。実績集計：{(today_jst()-timedelta(days=1)).isoformat()}まで／再計算日：{today_jst().isoformat()}')
        ui.label('ひとこと・今週の取り組み：________________________________________________')
