from calendar import monthrange
from datetime import date
from math import isfinite
from nicegui import ui
from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.financial_report_data import build_financial_report
from core.finance_outlook import month_outlook
from core.theme import Theme


def chart_options(labels, series, percent=False, compact=False):
    return {'backgroundColor':'transparent','color':['#f6d390','#8bc9ff','#a3e5b5','#ffb1aa'],
            'tooltip':{'trigger':'axis'},'legend':{'show':not compact,'bottom':0,'textStyle':{'color':'#fff'}},
            'grid':{'left':60,'right':12,'top':10,'bottom':25 if compact else 60},
            'xAxis':{'type':'category','data':labels,'axisLabel':{'color':'#eee','hideOverlap':True}},
            'yAxis':{'type':'value','splitNumber':2 if compact else 4,'axisLabel':{'color':'#eee','formatter':'{value}%' if percent else '{value}'},'splitLine':{'lineStyle':{'color':'#444'}}},
            'series':series}


def progress_chart(month, outlook, compact=False, tax_line=False):
    y,m=map(int,month.split('-'));days=monthrange(y,m)[1];today=today_jst().isoformat()
    actual={r['date']:r['amount'] for r in financials.sales_records(month=month) if r.get('amount') is not None and r['date']<today}
    f=outlook['forecast'];estimated={r['date']:r['sales'] for r in f['estimates']+f['missing_estimates']}
    running=0;predicted=0;real=[];future=[]
    for day in range(1,days+1):
        key=f'{month}-{day:02d}'
        running+=actual.get(key,0)
        predicted+=actual.get(key,estimated.get(key) or 0)
        real.append(running if key<today else None)
        future.append(predicted if f['landing'] is not None else None)
    series=[{'name':'実績（円）','type':'line','data':real,'showSymbol':False,'itemStyle':{'color':'#fff'}},
            {'name':'予測（円）','type':'line','data':future,'showSymbol':False,'lineStyle':{'type':'dashed'},'itemStyle':{'color':'#f6d390'}}]
    threshold=outlook.get('tax_repayment_line') if tax_line else outlook['break_even']
    if threshold is not None:
        series.append({'name':'税・返済確保目安' if tax_line else '損益分岐点（見込）','type':'line','data':[threshold]*days,'showSymbol':False,'lineStyle':{'type':'dotted'},'itemStyle':{'color':'#ffb1aa'}})
    if not compact:
        plans=sorted((p for p in data.data.get('sales_target_plans',{}).values() if p['month']==month),key=lambda p:p['created_at'])
        if plans:series.append({'name':'月間売上目標','type':'line','data':[plans[-1]['monthly_target']]*days,'showSymbol':False,'itemStyle':{'color':'#8bc9ff'}})
    return chart_options([f'{m}/{d}' for d in range(1,days+1)],series,compact=compact)


def months_before(month,count=12):
    y,m=map(int,month.split('-'));index=y*12+m-1
    return [f'{v//12:04d}-{v%12+1:02d}' for v in range(index-count+1,index+1)]


@ui.page('/mirai-kessan/graphs')
def finance_graphs(month: str = ''):
    if not require_app_access('future_financials') or not require_permission('future_dashboard','/mirai-kessan/input'):return
    try:
        selected=date.fromisoformat(month+'-01').strftime('%Y-%m')
    except ValueError:selected=today_jst().strftime('%Y-%m')
    Theme.page('経営グラフ',app_name='mirai-kessan')
    with Theme.shell('経営グラフ','',brand='未来決算'):
        field=ui.input('対象月',value=selected).props('type=month outlined').classes('w-full')
        field.on('change',lambda:ui.navigate.to('/mirai-kessan/graphs?month='+str(field.value)))
        kind=ui.toggle(['売上','利益','比率','曜日'],value='売上').classes('w-full')
        tax=ui.checkbox('消費税・元金返済を含む目安に切替',value=False).classes('w-full')
        @ui.refreshable
        def content():
            outlook=month_outlook(selected)
            if kind.value=='売上':
                ui.label('累計売上と、月間目標・損益分岐点').classes('font-bold q-mt-sm')
                options=progress_chart(selected,outlook,tax_line=tax.value)
            elif kind.value in ('利益','比率'):
                months=months_before(selected)
                reports=[]
                for month in months:
                    y,m=map(int,month.split('-'))
                    end=today_jst().isoformat() if month==today_jst().strftime('%Y-%m') else f'{month}-{monthrange(y,m)[1]:02d}'
                    reports.append(build_financial_report(month+'-01',end))
                known=[bool(r['sales'] or r['purchases']) for r in reports]
                ui.label('直近12か月（今月は今日まで・記録のない月は空欄）').classes('finance-readable text-sm')
                if kind.value=='利益':
                    options=chart_options(months,[{'name':'売上','type':'bar','data':[r['sales_total'] if k else None for r,k in zip(reports,known)]},
                                                 {'name':'営業利益','type':'line','data':[r['operating_profit'] if k else None for r,k in zip(reports,known)]}])
                else:
                    series=[]
                    for title,key in [('原価率','cost_rate'),('人件費率','personnel_rate'),('労働分配率','labor_distribution')]:
                        series.append({'name':title,'type':'line','data':[round(r['ratios'][key]*100,1) if k and r['ratios'][key] is not None else None for r,k in zip(reports,known)]})
                    options=chart_options(months,series,percent=True)
            else:
                records=[r for r in financials.sales_records(month=selected) if r['date']<today_jst().isoformat() and r.get('lunch_sales') is not None and r.get('dinner_sales') is not None]
                groups=[[r for r in records if date.fromisoformat(r['date']).weekday()==d] for d in range(7)]
                labels=[f'{label}({len(g)}日)' for label,g in zip('月火水木金土日',groups)]
                options=chart_options(labels,[{'name':label,'type':'bar','data':[round(sum(r[key] for r in g)/len(g)) if g else None for g in groups]} for label,key in [('ランチ平均','lunch_sales'),('ディナー平均','dinner_sales')]])
                ui.label('選択月の記録済み日平均。休業日・未入力日は0円扱いしません。').classes('text-sm finance-readable')
            ui.echart(options).classes('w-full').style('height:clamp(240px,43dvh,420px)')
            if kind.value=='売上':
                yen=lambda v:'算出保留' if v is None else f'¥{v:,}'
                ui.label(('税・返済確保目安：' if tax.value else '損益分岐点：')+yen(outlook['tax_repayment_line'] if tax.value else outlook['break_even'])).classes('font-bold')
                threshold=outlook['tax_repayment_line'] if tax.value else outlook['break_even']
                if threshold is not None and outlook['sales'] is not None:
                    ui.label(f"着地予測との差：{outlook['sales']-threshold:+,}円").classes('font-bold')
                for note in outlook['messages']:ui.label(note).classes('finance-warning text-xs')
                with ui.expansion('計算の前提・設定',icon='settings').classes('w-full'):
                    ui.label('損益分岐点は営業利益ゼロの見込。税・返済は含めません。今月の予定人件費を固定の費用見込として扱います。')
                    ui.label('原価見込：入力済み仕入れ＋残り予測売上×想定原価率。'+outlook['basis'])
                    ui.label('人件費見込：月額給与＋実績＋公開済みシフトボード（優先）＋人件費管理の予定。未登録分は本人の日平均で補完。')
                    config=data.data.get('finance_outlook_settings',{})
                    rate=ui.number('想定原価率（％・空欄は直近12週）',value=config.get('cost_rate'),min=0,max=100).props('outlined').classes('w-full')
                    fees=ui.checkbox('決済手数料も変動費に含める',value=config.get('fees_variable',True))
                    ui.label('外した場合も決済手数料は経費から除外せず、固定の費用見込に含めます。').classes('text-xs')
                    def save():
                        value=rate.value
                        if value is not None and (not isfinite(float(value)) or not 0<=float(value)<=100):
                            ui.notify('原価率は0〜100％で入力してください',type='warning');return
                        data.data['finance_outlook_settings']={'cost_rate':None if value is None else float(value),'fees_variable':fees.value}
                        data.save();content.refresh()
                    ui.button('設定を保存',on_click=save)
        kind.on_value_change(lambda: (tax.set_visibility(kind.value=='売上'),content.refresh()));tax.on_value_change(content.refresh);content()
