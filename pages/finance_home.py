from calendar import monthrange
from nicegui import ui
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.landing_forecast import monthly_forecast
from core.purchases import purchases
from core.staffing import staffing
from core.financial_report_data import build_financial_report
from core.finance_outlook import month_outlook
from pages.finance_graphs import progress_chart


def compact_finance_home(month):
    settings=data.data.get('landing_forecast_settings',{})
    records=financials.sales_records()
    today=today_jst()
    r=monthly_forecast(records,month,today,[],settings.get('closed_dates',[]))
    outlook=month_outlook(month)
    from core.finance_tasks import build_finance_tasks
    tasks=build_finance_tasks(data,month,today,outlook)
    money=lambda value:'—' if value is None else f'¥{value:,.0f}'
    y,m=map(int,month.split('-'))
    fiscal=y if m>=10 else y-1
    ui.add_css('body:has(.finance-hero) .app-shell{padding-top:8px!important;padding-bottom:66px!important} body:has(.finance-hero) .app-shell>.metric-value{font-size:22px!important} body:has(.finance-hero) .app-shell>.q-mb-lg{display:none}')
    with ui.row().classes('w-full justify-between items-center q-mb-sm'):
        index=y*12+m-1
        ui.button(icon='chevron_left',on_click=lambda:ui.navigate.to(f'/mirai-kessan/month/{(index-1)//12:04d}-{(index-1)%12+1:02d}')).props('flat round aria-label=前月')
        ui.label(f'{y}年{m}月').classes('finance-month')
        ui.button(icon='settings',on_click=lambda:ui.navigate.to('/mirai-kessan/settings')).props('flat round dense aria-label=設定')
        ui.button(icon='chevron_right',on_click=lambda:ui.navigate.to(f'/mirai-kessan/month/{(index+1)//12:04d}-{(index+1)%12+1:02d}')).props('flat round aria-label=翌月')
    with ui.card().classes('surface-card w-full finance-hero'):
        ui.label('今月の着地予測').classes('finance-gold')
        ui.label(money(r['landing'])).classes('forecast-home-number self-center')
        ui.label('売上実績　'+money(r['actual'])).classes('self-center text-sm')
        ui.echart(progress_chart(month,outlook,compact=True)).classes('w-full finance-chart cursor-pointer').style('height:clamp(115px,22dvh,220px)').on('click',lambda:ui.navigate.to('/mirai-kessan/graphs?month='+month))
        with ui.row().classes('finance-chart-legend w-full justify-center'):
            ui.label('━ 実績').style('color:#ffffff')
            ui.label('┄ 予測').style('color:#f5cf80')
            ui.link('損益分岐点・詳細', '/mirai-kessan/graphs?month='+month).style('color:#ffb1aa')
        if r['missing'] and r['landing'] is not None:
            ui.label(f"未入力 {len(r['missing'])}日分は推定で補完").classes('finance-notice')
        elif r['landing'] is None:
            ui.label('予測に必要な実績がまだ足りません').classes('finance-notice')
    with ui.element('div').classes('finance-stat-grid w-full'):
        for label,value in [('1日平均',money(r['daily_average'])),('残りの予測売上',money(r['remaining']))]:
            with ui.card().classes('surface-card finance-mini'):
                ui.label(label).classes('text-xs');ui.label(value).classes('finance-mini-number')
    # Match the existing detailed dashboard's accounting basis, including
    # today's entries; the landing forecast above uses completed days only.
    period_end = today.isoformat() if month == today.strftime('%Y-%m') else f'{month}-{monthrange(y, m)[1]:02d}'
    report = build_financial_report(f'{month}-01', period_end)
    sales = report['sales_total']
    cost = report['cost_total']
    personnel = report['personnel']
    gross = report['gross_profit']
    with ui.card().classes('surface-card w-full finance-ratios q-mb-sm'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('現在の経営指標').classes('finance-gold')
            ui.link(f"やること {len(tasks)}項目" if tasks else 'やることを確認', '/mirai-kessan/tasks?month='+month).classes('text-xs').style('color:#ffda96')
        with ui.element('div').classes('finance-ratio-grid w-full'):
            for label, value, predicted in (
                ('原価率', cost / sales if sales > 0 else None, outlook['cost_rate']),
                ('人件費率', personnel / sales if sales > 0 else None, outlook['personnel_rate']),
                ('労働分配率', personnel / gross if gross > 0 else None, outlook['labor_rate']),
            ):
                with ui.column().classes('gap-1 items-center min-w-0'):
                    ui.label(label).classes('text-xs')
                    ui.label(f'{value:.1%}' if value is not None else '—').classes('finance-ratio-value')
                    ui.label(('着地(参考) ' if outlook.get('payroll_provisional') and label != '原価率' else '着地 ')+(f'{predicted:.1%}' if predicted is not None else '—')).classes('finance-outlook-label')

    settled = report['settlement']
    operating_profit = report['operating_profit']
    after_tax_and_loan = settled['post_repayment_profit']
    with ui.element('div').classes('finance-stat-grid finance-profit-grid w-full'):
        for label, value in [('原価', cost), ('粗利益', gross), ('営業利益', operating_profit), (settled['surplus_label'], after_tax_and_loan)]:
            with ui.card().classes('surface-card finance-mini'):
                if label == settled['surplus_label']:
                    ui.link(label + (' ※' if settled['provisional'] else ''), '/mirai-kessan/taxes?month='+month).classes('text-xs').style('color:#ffda92').tooltip('税設定を確認')
                else:
                    ui.label(label).classes('text-xs')
                ui.label(money(value)).classes('finance-mini-number')
