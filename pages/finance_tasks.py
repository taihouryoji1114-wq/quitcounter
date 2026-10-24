from datetime import datetime
from nicegui import ui
from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.data import data
from core.finance_outlook import month_outlook
from core.finance_tasks import build_finance_tasks
from core.theme import Theme


@ui.page('/mirai-kessan/tasks')
def finance_tasks_page(month: str=''):
    if not require_app_access('future_financials') or not require_permission('future_dashboard','/mirai-kessan/input'):return
    try:month=datetime.strptime(month,'%Y-%m').strftime('%Y-%m')
    except ValueError:month=today_jst().strftime('%Y-%m')
    Theme.page('やること｜未来決算',app_name='mirai-kessan')
    tasks=build_finance_tasks(data,month,today_jst(),month_outlook(month))
    with Theme.shell('やること','',brand='未来決算',back_to='/mirai-kessan/dashboard'):
        field=ui.input('対象月',value=month).props('outlined type=month').classes('w-full q-mb-sm')
        field.on('change',lambda:ui.navigate.to('/mirai-kessan/tasks?month='+str(field.value)))
        ui.label(f'{len(tasks)}項目を確認' if tasks else '確認が必要な項目は見つかりませんでした').classes('font-bold q-mb-sm')
        ui.label('売上・勤務実績は昨日までを確認。入力・修正すると一覧も更新されます。').classes('text-xs q-mb-sm')
        for task in tasks:
            with ui.card().classes('surface-card w-full q-pa-md q-mb-sm'):
                ui.label(task['area']+' · '+task['level']).classes('finance-gold text-xs')
                ui.label(task['title']).classes('font-bold')
                items=task['items'];first=items[0]
                ui.label(first['detail']).classes('text-sm')
                if first['date']:ui.label(first['date']+(' ほか'+str(len(items)-1)+'件' if len(items)>1 else '')).classes('text-sm')
                ui.button('入力・確認へ',icon='arrow_forward',on_click=lambda _,url=first['path']:ui.navigate.to(url)).classes('w-full')
                if len(items)>1:
                    with ui.expansion(f'対象の全{len(items)}件を見る').classes('w-full'):
                        for item in items:
                            ui.link(item['date']+' '+item['detail'],item['path']).classes('text-sm').style('color:#ffe1a6')
        ui.link('入力画面へ','/mirai-kessan/input').classes('q-mt-sm').style('color:#ffe1a6')
        ui.label('入力漏れをすべて検知するものではありません。仕入れのない日を未入力扱いにはしません。').classes('text-xs q-mt-sm')
