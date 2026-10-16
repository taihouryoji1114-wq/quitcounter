from nicegui import ui
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.landing_forecast import monthly_forecast, simulate, save_snapshot


def render_landing_forecast(month):
    settings=data.data.get('landing_forecast_settings',{})
    def money(value):
        return '算出待ち' if value is None else f'¥{value:,.0f}'
    with ui.card().classes('surface-card w-full q-pa-lg q-mb-md'):
        ui.label('実績から見る、今月の着地').classes('text-xl font-bold')
        ui.label('前日までの入力済み売上で計算。今日の途中入力は予測の基準に含めません。').classes('text-xs text-grey-7')
        @ui.refreshable
        def content():
            config=data.data.get('landing_forecast_settings',{})
            result=monthly_forecast(financials.sales_records(),month,today_jst(),config.get('closed_weekdays',[]),config.get('closed_dates',[]))
            with ui.element('div').classes('grid grid-cols-2 gap-3 w-full'):
                for title,value in [('前日までの売上',money(result['actual'])),('記録済み1日平均',money(result['daily_average'])),('今月の着地予測',money(result['landing'])),('残りの予測売上',money(result['remaining']))]:
                    with ui.column().classes('p-3 rounded-xl bg-green-1 gap-1'):
                        ui.label(title).classes('text-xs text-grey-8');ui.label(value).classes('text-xl font-bold')
            if not config:
                ui.label('営業日未設定：全曜日営業と仮定しています。下の設定を確認してください。').classes('text-orange-9 text-sm')
            if result['missing']:
                ui.label('売上未入力の営業日：'+', '.join(result['missing'])+'。着地の合計は保留しています。').classes('text-orange-9 text-sm')
            ui.label('日平均は売上記録がある日で計算します。登録済みの0円の日も含みます。').classes('text-xs text-grey-7')
            if result['landing'] is not None:
                ui.label('過去のばらつきによる参考幅：'+money(result['low'])+'〜'+money(result['high'])+'（確率を保証する区間ではありません）').classes('text-xs text-grey-7')
            with ui.expansion('根拠・日別予測を見る',icon='query_stats').classes('w-full'):
                ui.label('前年同月・同曜日が2日以上あれば優先。それ以外は直近12週の同曜日、さらに不足なら全曜日平均。祝日・予約・天候は未反映です。').classes('text-sm')
                for e in result['estimates']:
                    ui.label(f"{e['date']}　{money(e['sales'])}　{e['basis']}／{e['samples']}日参考").classes('text-xs')
            with ui.expansion('もしこう変えたら？',icon='tune').classes('w-full'):
                ui.label('変更するのは今日以降だけ。実際の売上・給与の記録は変わりません。')
                percent=ui.number('残りの予測売上から増減（%）',value=0,min=-100)
                ui.label('基準：'+money(result['remaining'])).classes('text-xs')
                price=ui.number('客単価の増減（円）',value=0)
                ui.label('残りの予測客数：'+(str(result['customers'])+'人' if result['customers'] is not None else '客数不足')).classes('text-xs')
                variable=ui.number('増減した売上に対する変動費率（%・仮定）',value=30,min=0,max=100)
                hourly=ui.number('対象従業員の時給増減（円）',value=0)
                hours=ui.number('その従業員の今月残りの勤務時間合計',value=0,min=0)
                salary=ui.number('社員給与の今月増減額合計（円）',value=0)
                officer=ui.number('役員報酬の今月増減額合計（円）',value=0)
                ui.label('客単価変更時の客数は一定。売上率変更と客単価変更は加算。会社負担保険料・税・返済の変動は含みません。利益総額ではなく変更による差額です。').classes('text-xs text-grey-7')
                output=ui.label().classes('font-bold')
                def run():
                    try:
                        values=[float(f.value or 0) for f in (percent,price,variable,hourly,hours,salary,officer)]
                        simulated=simulate(result,*values)
                        output.set_text(f"売上着地 {money(simulated['sales'])} ／ 利益への影響 {simulated['profit_delta']:+,}円")
                    except (ValueError,TypeError) as error:ui.notify(str(error),type='warning')
                ui.button('この条件で比較',on_click=run)
            def record():
                if result['landing'] is None:
                    ui.notify('入力を確認してから予測を保存してください',type='warning');return
                save_snapshot(data,result)
                ui.notify('本日の最初の予測を保存しました。後から上書きしません。',type='positive')
                history.refresh()
            ui.button('今日の予測を記録',icon='save',on_click=record).props('outline')
        content()
        with ui.expansion('営業日・休業日を設定',icon='calendar_month').classes('w-full'):
            closed=ui.select({i:d for i,d in enumerate('月火水木金土日')},multiple=True,value=settings.get('closed_weekdays',[]),label='毎週の定休日').classes('w-full')
            dates=ui.textarea('臨時休業日（YYYY-MM-DDを1行ずつ）',value='\n'.join(settings.get('closed_dates',[]))).classes('w-full')
            def update():
                from datetime import date
                try:
                    entries=[date.fromisoformat(v.strip()).isoformat() for v in (dates.value or '').splitlines() if v.strip()]
                except ValueError:
                    ui.notify('日付はYYYY-MM-DDで入力してください',type='warning');return
                data.data['landing_forecast_settings']={'closed_weekdays':closed.value,'closed_dates':entries}
                data.save();content.refresh()
            ui.button('設定を保存・再計算',on_click=update)
        @ui.refreshable
        def history():
            with ui.expansion('保存した予測と結果',icon='history').classes('w-full'):
                saved=data.data.get('landing_forecast_history',{})
                if not saved:ui.label('予測を記録すると、過去の予測と月末実績を比較できます。')
                for key,record in sorted(saved.items(),reverse=True)[:24]:
                    f=record['forecast'];text=f"{f['as_of']}時点 → {f['month']}予測 {money(f['landing'])}"
                    if f['month'] < today_jst().strftime('%Y-%m'):
                        current=monthly_forecast(financials.sales_records(),f['month'],today_jst(),data.data.get('landing_forecast_settings',{}).get('closed_weekdays',[]),data.data.get('landing_forecast_settings',{}).get('closed_dates',[]))
                        text+=' ／ 未入力あり・比較保留' if current['missing'] else f" ／ 実績 {money(current['actual'])} ／ 差 {current['actual']-f['landing']:+,}円"
                    ui.label(text).classes('text-xs')
        history()
