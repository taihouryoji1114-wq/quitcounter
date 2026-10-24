"""Occasional finance settings, separate from daily work."""
from datetime import date
from math import isfinite
from nicegui import ui
from core.auth import require_app_access, require_permission, current_role, log_out
from core.clock import today_jst
from core.data import data
from core.theme import Theme


@ui.page('/mirai-kessan/settings')
def finance_settings_page():
    if not require_app_access('future_financials') or not require_permission('future_dashboard','/mirai-kessan/input'):
        return
    Theme.page('設定｜未来決算',app_name='mirai-kessan')
    with Theme.shell('設定','',brand='未来決算',back_to='/mirai-kessan/dashboard'):
        for title,caption,icon,path in [
            ('税金・利益','法人税30％・自動控除・経費の税区分','receipt_long','/mirai-kessan/taxes'),
            ('将来予測の条件','開始残高・成長率・返済予定','trending_up','/mirai-kessan/settings/wealth'),
            ('給与・時給','スタッフの時給・月給など','groups','/mirai-kessan/staffing')]:
            with ui.card().classes('surface-card w-full q-pa-md q-mb-sm cursor-pointer').on('click',lambda _,url=path:ui.navigate.to(url)):
                with ui.row().classes('w-full items-center no-wrap'):
                    ui.icon(icon).classes('finance-gold')
                    with ui.column().classes('grow gap-0'):
                        ui.label(title).classes('font-bold');ui.label(caption).classes('text-xs')
                    ui.icon('chevron_right')
        with ui.expansion('月末予測・損益分岐点',icon='tune').classes('w-full'):
            config=data.data.get('finance_outlook_settings',{})
            rate=ui.number('想定原価率（％・空欄は実績から）',value=config.get('cost_rate'),min=0,max=100).props('outlined').classes('w-full')
            fees=ui.checkbox('決済手数料を変動費に含める',value=config.get('fees_variable',True))
            ui.label('外す場合も決済手数料は固定費として計算します。').classes('text-xs')
            def save_outlook():
                if not require_permission('future_dashboard','/mirai-kessan/input'):return
                value=rate.value
                if value is not None and (not isfinite(float(value)) or not 0<=float(value)<=100):
                    ui.notify('原価率は0〜100％で入力してください',type='negative');return
                data.data.setdefault('finance_outlook_settings',{}).update(cost_rate=None if value is None else float(value),fees_variable=fees.value)
                data.save();ui.notify('予測条件を保存しました',type='positive')
            ui.button('予測条件を保存',on_click=save_outlook).classes('w-full')
        with ui.expansion('臨時休業日',icon='calendar_month').classes('w-full'):
            ui.label('通常は毎日営業。年末年始など休む日だけ登録します。').classes('text-sm')
            dates=ui.textarea('休業日（YYYY-MM-DDを1行ずつ）',value='\n'.join(data.data.get('landing_forecast_settings',{}).get('closed_dates',[]))).props('outlined').classes('w-full')
            def save_closed():
                if not require_permission('future_dashboard','/mirai-kessan/input'):return
                try:entries=sorted({date.fromisoformat(v.strip()).isoformat() for v in (dates.value or '').splitlines() if v.strip()})
                except ValueError:
                    ui.notify('日付はYYYY-MM-DDで入力してください',type='negative');return
                data.data.setdefault('landing_forecast_settings',{}).update(closed_weekdays=[],closed_dates=entries)
                data.save();ui.notify('休業日を保存しました',type='positive')
            ui.button('休業日を保存',on_click=save_closed).classes('w-full')
        with ui.expansion('アカウント',icon='person').classes('w-full'):
            if current_role()=='owner':ui.button('R-BASEへ戻る',on_click=lambda:ui.navigate.to('/')).props('flat')
            ui.button('ログアウト',on_click=lambda:log_out('/mirai-kessan/login')).props('flat')
