from nicegui import ui
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.landing_forecast import monthly_forecast


def compact_finance_home(month):
    settings=data.data.get('landing_forecast_settings',{})
    r=monthly_forecast(financials.sales_records(),month,today_jst(),settings.get('closed_weekdays',[]),settings.get('closed_dates',[]))
    money=lambda value:'算出待ち' if value is None else f'¥{value:,.0f}'
    y,m=map(int,month.split('-'))
    with ui.row().classes('w-full justify-between items-center q-mb-sm'):
        for delta,label in [(-1,'前月'),(1,'翌月')]:
            index=y*12+m-1+delta
            target=f'/mirai-kessan/month/{index//12:04d}-{index%12+1:02d}'
            ui.button(label,on_click=lambda _,url=target:ui.navigate.to(url)).props('flat')
    with ui.card().classes('surface-card w-full q-pa-lg'):
        ui.label(month.replace('-','年')+'月 · 着地予測').classes('text-sm')
        ui.label(money(r['landing'])).classes('forecast-home-number')
        ui.label('前日までの実績 ＋ 残り営業日の予測').classes('text-xs text-grey-6')
        with ui.row().classes('w-full justify-between q-mt-md'):
            for title,value in [('売上実績',r['actual']),('記録済み1日平均',r['daily_average'])]:
                with ui.column().classes('gap-1'):
                    ui.label(title).classes('text-xs text-grey-6');ui.label(money(value)).classes('text-lg font-bold')
        if r['missing']:
            ui.label(f"未入力の営業日 {len(r['missing'])}日 · 予測の合計は保留中").classes('text-orange-5 text-xs')
        if not settings:
            ui.label('営業日未設定 · 予測画面で定休日を設定してください').classes('text-orange-5 text-xs')
        ui.button('条件を変えて比較',icon='query_stats',on_click=lambda:ui.navigate.to('/mirai-kessan/forecast')).classes('w-full q-mt-md')
    with ui.row().classes('w-full gap-2 q-mt-md'):
        ui.button('経営の詳しい数字',icon='analytics',on_click=lambda:ui.navigate.to('/mirai-kessan/details')).props('outline').classes('grow')
        ui.button('入力を確認',icon='fact_check',on_click=lambda:ui.navigate.to('/mirai-kessan/audit')).props('outline').classes('grow')
    ui.label('9月決算 · 今期は10月〜翌年9月').classes('text-xs text-grey-6 q-mt-md')
