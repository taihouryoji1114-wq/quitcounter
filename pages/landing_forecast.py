from nicegui import ui
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.landing_forecast import monthly_forecast, save_snapshot


def render_landing_forecast(month, price_change=0):
    from pages.sales_targets import render_sales_targets
    ui.button('利益剰余金・返済後の将来予測', icon='trending_up', on_click=lambda: ui.navigate.to('/mirai-kessan/forecast/wealth')).classes('w-full q-mb-md')
    render_sales_targets(month)
    settings=data.data.get('landing_forecast_settings',{})
    def money(value):
        return '算出待ち' if value is None else f'¥{value:,.0f}'
    with ui.card().classes('surface-card w-full q-pa-lg q-mb-md'):
        ui.label('実績から見る、今月の着地').classes('text-xl font-bold')
        ui.label('前日までの入力済み売上で計算。今日の途中入力は予測の基準に含めません。').classes('text-xs finance-readable')
        @ui.refreshable
        def content():
            config=data.data.get('landing_forecast_settings',{})
            result=monthly_forecast(financials.sales_records(),month,today_jst(),[],config.get('closed_dates',[]))
            with ui.element('div').classes('grid grid-cols-2 gap-3 w-full'):
                for title,value in [('前日までの売上',money(result['actual'])),('記録済み1日平均',money(result['daily_average'])),('今月の着地予測',money(result['landing'])),('残りの予測売上',money(result['remaining']))]:
                    with ui.column().classes('p-3 rounded-xl forecast-metric gap-1'):
                        ui.label(title).classes('text-xs finance-readable');ui.label(value).classes('text-xl font-bold')
            if result['missing'] and result['landing'] is not None:
                ui.label('売上未入力の営業日：'+', '.join(result['missing'])+'。記録がある日の傾向から補完した暫定予測です。').classes('finance-warning text-sm')
            ui.label('日平均は売上記録がある日で計算します。登録済みの0円の日も含みます。').classes('text-xs finance-readable')
            if result['landing'] is not None:
                ui.label('過去のばらつきによる参考幅：'+money(result['low'])+'〜'+money(result['high'])+'（確率を保証する区間ではありません）').classes('text-xs finance-readable')
            with ui.expansion('根拠・日別予測を見る',icon='query_stats').classes('w-full'):
                ui.label('前年同月・同曜日が2日以上あれば優先。それ以外は直近12週の同曜日、さらに不足なら全曜日平均。祝日・予約・天候は未反映です。').classes('text-sm')
                for e in result['estimates']:
                    ui.label(f"{e['date']}　{money(e['sales'])}　{e['basis']}／{e['samples']}日参考").classes('text-xs')
            def record():
                if result['landing'] is None:
                    ui.notify('入力を確認してから予測を保存してください',type='warning');return
                save_snapshot(data,result)
                ui.notify('本日の最初の予測を保存しました。後から上書きしません。',type='positive')
                history.refresh()
            ui.button('今日の予測を記録',icon='save',on_click=record).props('outline')
        content()
        with ui.expansion('休業日を登録（通常は毎日営業）',icon='calendar_month').classes('w-full'):
            dates=ui.textarea('臨時休業日（YYYY-MM-DDを1行ずつ）',value='\n'.join(settings.get('closed_dates',[]))).classes('w-full')
            def update():
                from datetime import date
                try:
                    entries=[date.fromisoformat(v.strip()).isoformat() for v in (dates.value or '').splitlines() if v.strip()]
                except ValueError:
                    ui.notify('日付はYYYY-MM-DDで入力してください',type='warning');return
                data.data['landing_forecast_settings']={'closed_weekdays':[],'closed_dates':entries}
                data.save();ui.navigate.to("/mirai-kessan/forecast?month="+month)
            ui.button('設定を保存・再計算',on_click=update)
        @ui.refreshable
        def history():
            with ui.expansion('保存した予測と結果',icon='history').classes('w-full'):
                saved=data.data.get('landing_forecast_history',{})
                if not saved:ui.label('予測を記録すると、過去の予測と月末実績を比較できます。')
                for key,record in sorted(saved.items(),reverse=True)[:24]:
                    f=record['forecast'];text=f"{f['as_of']}時点 → {f['month']}予測 {money(f['landing'])}"
                    if f['month'] < today_jst().strftime('%Y-%m'):
                        current=monthly_forecast(financials.sales_records(),f['month'],today_jst(),[],data.data.get('landing_forecast_settings',{}).get('closed_dates',[]))
                        text+=' ／ 未入力あり・比較保留' if current['missing'] else f" ／ 実績 {money(current['actual'])} ／ 差 {current['actual']-f['landing']:+,}円"
                    ui.label(text).classes('text-xs')
        history()
