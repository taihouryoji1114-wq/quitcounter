from calendar import monthrange
from nicegui import ui
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.landing_forecast import monthly_forecast
from core.purchases import purchases
from core.staffing import staffing


def compact_finance_home(month):
    settings=data.data.get('landing_forecast_settings',{})
    records=financials.sales_records()
    today=today_jst()
    r=monthly_forecast(records,month,today,settings.get('closed_weekdays',[]),settings.get('closed_dates',[]))
    money=lambda value:'算出待ち' if value is None else f'¥{value:,.0f}'
    y,m=map(int,month.split('-'))
    fiscal=y if m>=10 else y-1
    ui.label(f'今期 {fiscal}.10–{fiscal+1}.09').classes('finance-period')
    with ui.row().classes('w-full justify-between items-center q-mb-sm'):
        index=y*12+m-1
        ui.button(icon='chevron_left',on_click=lambda:ui.navigate.to(f'/mirai-kessan/month/{(index-1)//12:04d}-{(index-1)%12+1:02d}')).props('flat round aria-label=前月')
        ui.label(f'{y}年{m}月').classes('finance-month')
        ui.button(icon='chevron_right',on_click=lambda:ui.navigate.to(f'/mirai-kessan/month/{(index+1)//12:04d}-{(index+1)%12+1:02d}')).props('flat round aria-label=翌月')
    with ui.card().classes('surface-card w-full finance-hero'):
        ui.label('今月の着地予測').classes('finance-gold')
        ui.label(money(r['landing'])).classes('forecast-home-number self-center')
        ui.label('売上実績　'+money(r['actual'])).classes('self-center text-sm')
        length=monthrange(y,m)[1]
        actuals={int(v['date'][8:10]):float(v['amount']) for v in records if v['date'].startswith(month) and v['date']<today.isoformat() and v.get('amount') is not None}
        predictions={int(e['date'][8:10]):e['sales'] for e in r['estimates']}
        elapsed=length if month<today.strftime('%Y-%m') else max(0,today.day-1) if month==today.strftime('%Y-%m') else 0
        running=0; actual=[]; forecast=[]
        for day in range(1,length+1):
            if day<=elapsed:
                running+=actuals.get(day,0)
                actual.append(None if f'{month}-{day:02d}' in r['missing'] else round(running))
                forecast.append(round(running) if day==elapsed and r['landing'] is not None else None)
            else:
                actual.append(None)
                running+=predictions.get(day) or 0
                forecast.append(round(running) if r['landing'] is not None else None)
        ui.echart({'backgroundColor':'transparent','grid':{'left':58,'right':12,'top':18,'bottom':35},'tooltip':{'trigger':'axis'},
            'legend':{'bottom':0,'textStyle':{'color':'#e8edf5'}},
            'xAxis':{'type':'category','data':[f'{m}/{d}' for d in range(1,length+1)],'axisLabel':{'color':'#d2dceb','interval':6},'axisLine':{'lineStyle':{'color':'#56647a'}}},
            'yAxis':{'type':'value','axisLabel':{'color':'#d2dceb'},'splitLine':{'lineStyle':{'color':'#34445a'}}},
            'series':[{'name':'実績（円）','type':'line','data':actual,'connectNulls':False,'symbolSize':4,'itemStyle':{'color':'#e4bd6b'}},
                      {'name':'予測（円）','type':'line','data':forecast,'showSymbol':False,'itemStyle':{'color':'#e4bd6b'},'lineStyle':{'type':'dashed','color':'#e4bd6b'}}]}).classes('w-full').style('height:195px')
        if r['missing']:
            ui.label(f"未入力 {len(r['missing'])}日 · 着地は保留中").classes('finance-notice')
        elif r['landing'] is None:
            ui.label('予測に必要な実績がまだ足りません').classes('finance-notice')
        if not settings:ui.label('全曜日営業の仮定 · 予測画面で設定').classes('finance-notice')
    with ui.element('div').classes('finance-stat-grid w-full'):
        for label,value in [('記録済み1日平均',money(r['daily_average'])),('残りの予測売上',money(r['remaining']))]:
            with ui.card().classes('surface-card finance-mini'):
                ui.label(label).classes('text-xs');ui.label(value).classes('finance-mini-number')
    # Match the existing detailed dashboard's accounting basis, including
    # today's entries; the landing forecast above uses completed days only.
    sales = financials.monthly_sales_total(month)
    cost = purchases.monthly_total(month, kind='cost')
    personnel = (staffing.month_cost_summary(month, today)['company_cost']
                 or financials.get_monthly_operations(month)['personnel'])
    gross = sales - cost
    with ui.card().classes('surface-card w-full finance-ratios q-mb-sm'):
        ui.label('現在の経営指標').classes('finance-gold')
        with ui.element('div').classes('finance-ratio-grid w-full'):
            for label, value, formula in (
                ('原価率', cost / sales if sales > 0 else None, '原価 ÷ 売上'),
                ('人件費率', personnel / sales if sales > 0 else None, '人件費 ÷ 売上'),
                ('労働分配率', personnel / gross if gross > 0 else None, '人件費 ÷ 粗利'),
            ):
                with ui.column().classes('gap-1 items-center min-w-0'):
                    ui.label(label).classes('text-xs')
                    ui.label(f'{value:.1%}' if value is not None else '—').classes('finance-ratio-value')
                    ui.label(formula).classes('finance-ratio-formula')
        ui.label('選択月の入力済みデータによる暫定値（今日の入力を含む）').classes('finance-ratio-formula')
    with ui.card().classes('surface-card w-full finance-scenario'):
        ui.label('もし客単価が上がったら').classes('text-sm')
        slider=ui.slider(min=0,max=500,step=50,value=100).props('label-always color=amber-4').classes('w-full')
        impact=ui.label().classes('finance-impact')
        def update():
            impact.set_text(f"売上 ＋¥{round(r['customers']*slider.value):,}（＋{slider.value}円／人）" if r['customers'] is not None and r['landing'] is not None else '客数・売上の記録を確認してください')
        slider.on_value_change(update);update()
        ui.label('残りの予測客数を固定して試算。実績は変更しません。').classes('text-xs')
        ui.button('条件を変えて比較',icon='chevron_right',on_click=lambda:ui.navigate.to(f'/mirai-kessan/forecast?month={month}&price_change={slider.value}')).classes('w-full finance-compare')
    ui.button('月次記録・PDF保存',icon='description',on_click=lambda:ui.navigate.to('/mirai-kessan/reports')).props('outline').classes('w-full q-mt-sm')
