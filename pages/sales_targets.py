from datetime import date, timedelta
from nicegui import ui
from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.sales_targets import build_target_plan, save_target_plan, plan_results
from core.theme import Theme


def target_table(plan, start, printable=False):
    selected = date.fromisoformat(start)
    rows = {r['date']:r for r in plan['rows']}
    actual = {r['date']:r for r in plan_results(plan, financials.sales_records(), today_jst())}
    html = '<table class="target-table"><thead><tr><th>日付</th><th>ランチ</th><th>ディナー</th><th>合計目標</th><th>実績'+('' if printable else '／差額')+'</th></tr></thead><tbody>'
    total = 0
    for offset in range(7):
        day = selected + timedelta(days=offset)
        key = day.isoformat()
        label = f'{day.month}/{day.day}（{"月火水木金土日"[day.weekday()]}）'
        row = rows.get(key)
        if row:
            total += row['target']
            values = []
            for session in ('lunch','dinner'):
                customers = row[session+'_customers']
                note = f'<small>目安 {customers}人</small>' if customers is not None else '<small>客数目安なし</small>'
                values.append(f'<td>¥{row[session]:,}{note}</td>')
            a = actual.get(key,{})
            result = '' if printable else '—' if a.get('actual') is None else f"¥{a['actual']:,}<small>差 {a['difference']:+,}円</small>"
            html += f'<tr><th>{label}</th>'+''.join(values)+f"<td>¥{row['target']:,}</td><td>{result}</td></tr>"
        else:
            state = '対象月外' if not key.startswith(plan['month']) else '休業日' if key in plan['closed_dates'] else '目標未設定'
            html += f'<tr><th>{label}</th><td colspan="4">{state}</td></tr>'
    return html+f'<tr><th colspan="3">この期間の目標合計</th><td>¥{total:,}</td><td></td></tr></tbody></table>'


TARGET_CSS = '''
.target-table{width:100%;border-collapse:collapse;font-size:12px;color:#f5f5f5;table-layout:fixed}
.target-table th,.target-table td{padding:9px 4px;border:1px solid #666;text-align:center;overflow-wrap:anywhere}
.target-table th{background:#252525}.target-table small{display:block;font-size:10px;margin-top:4px;color:#eee}
@media(max-width:440px){.target-table{font-size:10px}.target-table small{font-size:9px}.target-table td,.target-table th{padding:7px 2px}}
@media print{@page{size:A4 landscape;margin:12mm}.target-print-controls,.app-bottom-nav{display:none!important}
body:has(.target-print-sheet){background:#fff!important;color:#111!important}
.target-print-sheet{width:100%!important;max-width:none!important;padding:0!important;margin:0!important;color:#111!important;break-inside:avoid}
.target-print-sheet{gap:8px!important}body:has(.target-print-sheet) .nicegui-content{padding:0!important;gap:0!important}.target-print-sheet h1{font-size:22pt;margin:0 0 6px;line-height:1.2}.target-print-sheet p{font-size:11pt}
.target-table{font-size:14pt!important;color:#111!important}.target-table th,.target-table td{box-sizing:border-box;padding:5px 6px!important;height:12mm;border-color:#333!important;background:white!important;color:#111!important}
.target-table small{font-size:10pt!important;color:#333!important}}
'''


def render_sales_targets(month):
    ui.add_css(TARGET_CSS)
    @ui.refreshable
    def board():
        plans = sorted((p for p in data.data.get('sales_target_plans',{}).values() if p['month']==month), key=lambda p:p['created_at'],reverse=True)
        with ui.card().classes('surface-card w-full q-pa-md q-mb-md'):
            ui.label('月の目標から、毎日の目標へ').classes('text-xl font-bold')
            ui.label('予測は見込み、目標は目指す売上。目標を保存してから週間表を印刷できます。').classes('finance-readable text-sm')
            goal = ui.number('月間売上目標（税込）', value=plans[0]['monthly_target'] if plans else None,min=1,step=10000).props('outlined prefix=¥').classes('w-full')
            def save():
                try:
                    plan = build_target_plan(financials.sales_records(),month,goal.value or 0,today_jst(),data.data.get('landing_forecast_settings',{}).get('closed_dates',[]))
                    save_target_plan(data,plan)
                except (ValueError,TypeError) as error:
                    ui.notify(str(error),type='warning');return
                ui.notify('目標を保存しました。以前の版も残しています。',type='positive');board.refresh()
            ui.button('目標を作成・保存' if not plans else '目標を見直して新しい版を保存',on_click=save,icon='save').classes('w-full')
            if not plans:
                ui.label('目標額は自動では決めません。達成したい月間売上を入力してください。').classes('finance-readable text-sm');return
            choice = ui.select({p['id']:f"{p['created_at'][:16].replace('T',' ')} 保存・¥{p['monthly_target']:,}" for p in plans},value=plans[0]['id'],label='保存した目標').classes('w-full').props('outlined')
            @ui.refreshable
            def details():
                p = next(p for p in plans if p['id']==choice.value)
                recent = {r['date']:r for r in financials.sales_records() if r.get('amount') is not None and r['date'] < today_jst().isoformat()}
                current_actual = sum(r['amount'] for key,r in recent.items() if key.startswith(month))
                ui.label(f"月間目標 ¥{p['monthly_target']:,} ／ 現在の入力済み実績 ¥{current_actual:,}").classes('font-bold')
                ui.label(f"実績との差額 あと ¥{max(0,p['monthly_target']-current_actual):,}").classes('font-bold')
                if p['missing']:
                    ui.label(f"作成時の未入力 {len(p['missing'])}日を ¥{p['imputed']:,} と推定し、残りの目標 ¥{p['remaining']:,} を配分しています。上の実績には推定を含みません。").classes('finance-warning text-sm')
                ui.label('保存済みの目標は自動変更しません。売上や休業日を変更した場合、必要に応じて新しい版を保存してください。').classes('finance-readable text-xs')
                if p['equal_allocation']:ui.label('日別の実績不足のため、営業日に均等配分しています。').classes('finance-warning text-sm')
                if any(r['split_basis']=='実績不足のため半分ずつ' for r in p['rows']):ui.label('時間帯の実績がない日はランチ・ディナー半分ずつ。客数は記録がある場合だけ表示します。').classes('finance-warning text-sm')
                results = plan_results(p,financials.sales_records(),today_jst())
                compared = [r for r in results if r['actual'] is not None]
                yesterday = (today_jst()-timedelta(days=1)).isoformat()
                previous = next((r for r in results if r['date']==yesterday),None)
                if previous:
                    ui.label('昨日の差額：'+(f"{previous['difference']:+,}円" if previous['difference'] is not None else '売上未入力')).classes('font-bold')
                ui.label(f"実績入力済み {len(compared)}日分の累計差額：{sum(r['difference'] for r in compared):+,}円").classes('text-sm')
                default = max(p['rows'][0]['date'], min((today_jst()+timedelta(days=1)).isoformat(),p['rows'][-1]['date'])) if p['rows'] else month+'-01'
                start = ui.input('週間表の開始日（7日間）',value=default).props('type=date outlined').classes('w-full')
                table=ui.html('',sanitize=False).classes('w-full')
                def show():
                    try:table.set_content(target_table(p,start.value))
                    except (ValueError,TypeError):ui.notify('開始日を入力してください',type='warning')
                start.on_value_change(show);show()
                def print_view():
                    try:day=date.fromisoformat(start.value).isoformat()
                    except (ValueError,TypeError):ui.notify('開始日を入力してください',type='warning');return
                    ui.navigate.to(f"/mirai-kessan/targets/print/{p['id']}?start={day}")
                ui.button('週間目標を印刷',icon='print',on_click=print_view).classes('w-full')
                with ui.expansion('配分の根拠',icon='info').classes('w-full'):
                    ui.label('日別は売上予測の比率で配分。時間帯は直近12週の同曜日（不足時は全曜日）の売上比。必要客数はその期間の客単価が続く場合の切り上げ目安です。')
                    for r in p['rows']:
                        ui.label(f"{r['date']}：{r['basis']}／{r['split_basis']}").classes('text-xs')
            choice.on_value_change(details.refresh);details()
    board()


@ui.page('/mirai-kessan/targets/print/{plan_id}')
def print_targets(plan_id: str, start: str = ''):
    if not require_app_access('future_financials') or not require_permission('future_dashboard','/mirai-kessan/input'):return
    plan=data.data.get('sales_target_plans',{}).get(plan_id)
    if not plan:
        ui.label('保存された目標が見つかりません');return
    try:start=date.fromisoformat(start or plan['as_of']).isoformat()
    except ValueError:
        ui.label('開始日が正しくありません');return
    Theme.page('週間売上目標',app_name='mirai-kessan');ui.add_css(TARGET_CSS)
    with ui.row().classes('target-print-controls'):
        ui.button('予測へ戻る',on_click=lambda:ui.navigate.to('/mirai-kessan/forecast?month='+plan['month']))
        ui.button('印刷・PDF保存',icon='print',on_click=lambda:ui.run_javascript('window.print()'))
    with ui.column().classes('target-print-sheet w-full').style('max-width:1100px;margin:auto;padding:20px'):
        ui.html('<h1>みんなで目指す、今週の売上</h1>',sanitize=False)
        ui.label(f"{start} 〜 {(date.fromisoformat(start)+timedelta(days=6)).isoformat()} ／ 保存日 {plan['created_at'][:10]}")
        ui.html(target_table(plan,start,True),sanitize=False).classes('w-full')
        ui.label('金額は税込。実績欄は手書き用。客数は最近の客単価から算出した目安です。')
        ui.label('ひとこと・今週の取り組み：________________________________________________')
