"""Compact, configurable long-range management scenarios."""
from nicegui import ui
from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.data import data
from core.theme import Theme
from core.wealth_forecast import fiscal_year, load_projection, validate_settings


def money(value):
    if value is None:
        return '—'
    return f'{value/100000000:,.2f}億円' if abs(value) >= 100000000 else f'{value/10000:,.1f}万円'


@ui.page('/mirai-kessan/forecast/wealth')
def wealth_forecast_page():
    if not require_app_access('future_financials') or not require_permission('future_dashboard', '/mirai-kessan/input'):
        return
    today = today_jst()
    fiscal = fiscal_year(today)
    Theme.page('将来の積み上げ', app_name='mirai-kessan')
    with Theme.shell('将来の積み上げ', '', brand='未来決算'):
        ui.link('予測へ戻る', '/mirai-kessan/forecast').classes('text-sm').style('color:#f6d390')
        with ui.row().classes('w-full items-center gap-2'):
            horizon = ui.number('何年後？', value=5, min=1, max=100, step=1).props('outlined suffix=年後').classes('w-40')
            ui.label('3年後でも、20年後でも').classes('text-sm finance-readable')
        ui.label(f'{today.year}年{today.month}月から積み上げる概算。決算は9月です。').classes('text-xs finance-readable')
        @ui.refreshable
        def result():
            value = horizon.value
            if value is None or not float(value).is_integer() or not 1 <= float(value) <= 100:
                ui.label('年数は1〜100の整数で入力してください。').classes('finance-warning')
                return
            target_year = today.year + int(value)
            end_year = max(fiscal + 1, target_year)
            config = data.data.get('wealth_forecast_settings', {})
            forecast = load_projection(config, today, end_year)
            if not forecast['years']:
                with ui.card().classes('surface-card w-full'):
                    ui.label('予測の前提を設定しましょう').classes('font-bold')
                    ui.label(forecast['message']).classes('text-sm finance-readable')
                    ui.label('下の「予測の前提・開始残高」を開いて設定できます。').classes('text-sm')
                return
            if forecast.get('opening_stale'):
                config = dict(config, opening_retained=None, opening_surplus=None)
                ui.label('開始残高は以前の月の設定です。今月初の残高を更新するまでは、今月からの増加分を表示します。').classes('text-xs finance-warning')
            years = forecast['years']
            mode = '残高' if config.get('opening_retained') is not None else '増加額'
            cashmode = '残高目安' if config.get('opening_surplus') is not None else '積み上げ額'
            for label, row in [('今期末', years[0]), ('来期末', years[1]), (f'{int(value)}年後', next(r for r in years if r['year'] == target_year))]:
                with ui.card().classes('surface-card w-full p-3 gap-2'):
                    ui.label(f"{label} · {row['year']}年9月末").classes('finance-gold font-bold text-sm')
                    with ui.element('div').classes('grid grid-cols-2 gap-3 w-full'):
                        for title, amount, color in [
                            (f'利益剰余金 · {mode}', row['retained_balance'] if config.get('opening_retained') is not None else row['retained_growth'], '#f6d390'),
                            (f'税・返済後 · {cashmode}', row['surplus_balance'] if config.get('opening_surplus') is not None else row['surplus_growth'], '#8bc9ff')]:
                            with ui.column().classes('gap-1 min-w-0'):
                                ui.label(title).classes('text-xs finance-readable')
                                ui.label(money(amount)).classes('text-lg font-bold').style(f'color:{color}')
            if int(value) >= 10:
                ui.label('長期の条件付き試算です。税制・返済額・成長率が続くと仮定しています。').classes('text-xs finance-warning')
            ui.label('予測は銀行残高や確定決算ではありません。開始残高が空欄の項目は、今月からの増加分を表示します。').classes('text-xs finance-readable')
            with ui.expansion('グラフ・年ごとの内訳', icon='show_chart').classes('w-full'):
                from pages.finance_graphs import chart_options
                series = []
                for title, key, opening in [('利益剰余金', 'retained', 'opening_retained'), ('税・返済後', 'surplus', 'opening_surplus')]:
                    field = key + ('_balance' if config.get(opening) is not None else '_growth')
                    series.append({'name': title + '（万円）', 'type': 'line', 'showSymbol': False,
                                   'data': [round(row[field]/10000, 1) for row in years]})
                ui.echart(chart_options([str(r['year'])+'年9月' for r in years], series)).classes('w-full').style('height:270px')
                for row in years:
                    with ui.expansion(f"{row['year']}年9月期 · 利益 {money(row['net'])} / 返済後 {money(row['surplus_delta'])}").classes('w-full text-sm'):
                        ui.label(f"対象 {row['months']}か月 / 法人税等 {money(row['tax'])} / 元金返済 {money(row['principal'])}")
                        ui.label(f"減価償却 {money(row['depreciation'])} / 設備投資 {money(row['investment'])} / 配当 {money(row['dividend'])}")
            with ui.expansion('この予測の根拠・不足している記録', icon='info').classes('w-full'):
                ui.label('今月は売上着地予測。翌月以降は各月の直近の記録年（14日以上）の1日平均を使い、季節差を反映します。')
                if forecast['seasonal_missing']:
                    ui.label('同月実績が不足する月：'+ '・'.join(map(str,forecast['seasonal_missing']))+'月。今月の1日平均で仮置きしているため、季節差は未反映です。').classes('finance-warning')
                ui.label('原価・決済手数料は売上連動。人件費・その他営業経費は今月見込を継続し、設定した年間変化率を反映。将来の個別月の費用やシフトは未反映です。')
                ui.label('税込収支から消費税納税見込を一度控除し、追加利息・減価償却・法人税等を引いて利益を試算。利益剰余金は配当を引いて累積します。')
                ui.label('返済後は利益に減価償却を戻し、元金返済・設備投資・配当を反映。売掛・買掛・在庫の増減、新規借入は含みません。')
                ui.label('法人税等は各期の対象期間の黒字×設定税率。今月より前の今期損益、繰越欠損金・均等割・税制変更は未反映です。')
                ui.label('仕入控除は直近3か月＋今月の入力税額比率を原価に適用し、登録広告費の税額を加算。その他の控除は設定で補います。還付は見込みません。')
                for note in forecast.get('basis_messages', []):
                    ui.label(note).classes('text-xs finance-readable')
        horizon.on_value_change(result.refresh)
        result()
        with ui.expansion('予測の前提・開始残高', icon='settings').classes('w-full') as settings_panel:
            saved = data.data.get('wealth_forecast_settings', {})
            fields = {}
            ui.label('人件費・その他経費の空欄は今月見込を使用し、元金返済の空欄は登録した返済月額を使用します。').classes('text-xs')
            ui.label('未入力の開始残高は0円と決めつけず、増加分だけ表示します。開始日は今月1日です。').classes('text-xs')
            definitions = [
                ('opening_retained', '今月初の利益剰余金（円・任意）', None),
                ('opening_surplus', '今月初の資金残高（円・任意）', None),
                ('corporate_tax_rate', '法人税等の概算実効税率（％・必須）', None),
                ('sales_growth', '売上の年間変化率（％）', 0),
                ('cost_growth', '人件費・固定費の年間変化率（％）', 0),
                ('payroll', '人件費／月（円・空欄は自動）', None),
                ('fixed', 'その他経費／月（円・空欄は自動）', None),
                ('principal', '元金返済／月（円・空欄は自動）', None),
                ('interest', '追加の借入利息月額（円）', 0),
                ('depreciation', '追加の減価償却月額（円）', 0),
                ('investment', '毎月の設備投資予定（円）', 0),
                ('dividend', '毎月の配当予定（円）', 0),
                ('extra_input_tax', '追加の仕入税額控除月額（円）', 0),
            ]
            for key, label, default in definitions:
                fields[key] = ui.number(label, value=saved.get(key, default)).props('outlined').classes('w-full')
            repayment = ui.input('返済終了月（空欄は同額で継続）', value=saved.get('repayment_end', '')).props('type=month outlined').classes('w-full')
            ui.label('登録返済額が利息込みなら、上の元金と追加利息に分けて入力してください。追加利息・減価償却・税額控除には、既存経費に含まれる分を重ねて入れないでください。').classes('text-xs finance-warning')
            ui.label('返済終了月の翌月から元金返済と追加利息を0円にします。法人税等の税率は税理士等に確認した想定値を入力してください。').classes('text-xs')
            def save():
                try:
                    settings = validate_settings(dict({key: field.value for key, field in fields.items()}, repayment_end=repayment.value))
                except (ValueError, TypeError):
                    ui.notify('金額・税率・年月の入力を確認してください。税率0〜100％、変化率−99〜100％です。', type='warning')
                    return
                settings['opening_month'] = today.strftime('%Y-%m')
                data.data['wealth_forecast_settings'] = settings
                data.save()
                result.refresh()
                settings_panel.set_value(False)
                ui.notify('予測の前提を保存しました', type='positive')
            ui.button('前提を保存・再計算', on_click=save).classes('w-full')
