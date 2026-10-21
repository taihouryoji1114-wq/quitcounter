"""Review tax assumptions without re-entering expenses."""
from calendar import monthrange
from copy import deepcopy
from datetime import datetime
from nicegui import ui
from core.auth import require_app_access, require_permission
from core.clock import today_jst
from core.financials import financials
from core.purchases import purchases
from core.consumption_tax import EXPENSE_KEYS, period_tax, validate_tax_settings
from core.theme import Theme

LABELS = dict(rent='家賃',utilities='水道光熱費',other_admin='その他管理費',tabelog='食べログ',hotpepper='ホットペッパー',other='その他広告費',payment_fees='決済手数料')

@ui.page('/mirai-kessan/taxes')
def finance_taxes_page(month: str = ''):
    if not require_app_access('future_financials') or not require_permission('future_dashboard','/mirai-kessan/input'):
        return
    try:
        month = datetime.strptime(month,'%Y-%m').strftime('%Y-%m')
    except ValueError:
        month = today_jst().strftime('%Y-%m')
    raw = financials._data_manager.data
    saved = deepcopy(raw.get('business_tax_settings',{}).get(month,{}))
    Theme.page('税金・利益の確認',app_name='mirai-kessan')
    with Theme.shell('税金・利益の確認','',brand='未来決算'):
        ui.link('ホームへ戻る','/mirai-kessan/month/'+month).style('color:#ffda92')
        ui.label(month+' の設定').classes('font-bold')
        ui.label('売上・仕入・経費は税込のまま。ここでは登録済み経費の税区分を指定します。金額を経費へもう一度入力する必要はありません。').classes('text-sm')
        ui.label('未確認の控除は差し引かず、消費税を多めに見積もります。法人税が未設定なら「法人税前」と表示します。').classes('text-sm')
        y,m=map(int,month.split('-'))
        summary=period_tax(financials,purchases,month+'-01',f'{month}-{monthrange(y,m)[1]:02d}')
        with ui.card().classes('surface-card w-full'):
            ui.label(f"消費税見込 ¥{summary['net_tax']:,} ／ 未確認控除 ¥{summary['unconfirmed_credit']:,}")
            ui.label('月全体の概算。ホームは今日までの同じ期間で計算。マイナスは還付見込で、残額には入れません。').classes('text-xs')
        with ui.card().classes('surface-card w-full'):
            ui.label('法人税等').classes('font-bold')
            rate=ui.number('概算税率（全月・将来予測共通）',value=raw.get('finance_tax_policy',{}).get('corporate_rate'),min=0,max=100,suffix='%').classes('w-full').props('outlined clearable')
            actual=ui.number('この月の法人税等（空欄は概算税率）',value=saved.get('corporate_tax_amount'),min=0).classes('w-full').props('outlined clearable')
            ui.label('法人税・住民税・事業税の当月負担分。納付した日ではなく対象月へ登録します。0円が確定していれば0を入力。年額をそのまま各月へ入力しないでください。').classes('text-xs')
        specs={}
        ops=financials.get_monthly_operations(month); ads=financials.get_monthly_advertising(month)
        with ui.expansion('経費に含まれる消費税',icon='receipt_long').classes('w-full'):
            ui.label('課税・非課税が混在する費目は対象税率と控除対象の税額を指定。決済手数料も契約に合わせて確認します。').classes('text-sm')
            for key in EXPENSE_KEYS:
                spec=saved.get('expenses',{}).get(key,{})
                amount=financials.monthly_payment_summary(month)['total_fees'] if key=='payment_fees' else ads[key] if key in ads else ops[key]
                with ui.card().classes('surface-card w-full'):
                    ui.label(f'{LABELS[key]}　登録済み ¥{amount:,}').classes('font-bold')
                    r=ui.select({'unknown':'未確認','exempt':'非課税・不課税','8':'8％','10':'10％'},value=spec.get('rate','unknown'),label='税区分').classes('w-full').props('outlined')
                    status=ui.select({'unknown':'未確認','registered':'全額控除の条件を確認済み','transition':'経過措置の適用条件を確認済み','none':'控除対象外と確認済み'},value=spec.get('status','unknown'),label='控除区分').classes('w-full').props('outlined')
                    tax=ui.number('対象税額（空欄は税込額から計算）',value=spec.get('tax_amount'),min=0,max=amount).classes('w-full').props('outlined clearable')
                    specs[key]=(r,status,tax,amount)
            ui.label('経過措置は日付に応じ80％→70％→50％→30％を適用。適用条件・上限等は請求書と申告内容で確認し、対象外分は対象税額に含めません。').classes('text-xs')
        with ui.expansion('仕入・営業用品・一般経費の控除確認',icon='fact_check').classes('w-full'):
            ui.label('登録番号だけでなく、請求書・帳簿など控除条件を確認してください。税額の修正は仕入入力から行えます。').classes('text-sm')
            for record in purchases.records(month=month):
                with ui.row().classes('w-full items-center'):
                    ui.label(f"{record['date'][5:]} {record['supplier']} ¥{record['total']:,}").classes('text-sm')
                    current='registered' if record.get('invoice_status')=='registered' else 'transition' if record.get('transition_eligible') else 'none' if record.get('credit_reviewed') else 'unknown'
                    choice=ui.select({'unknown':'未確認','registered':'全額控除を確認','transition':'経過措置を確認','none':'対象外を確認'},value=current).props('outlined').classes('w-full')
                    def review(e, rid=record['id']):
                        if not require_permission('future_dashboard','/mirai-kessan/input'): return
                        purchases.review_credit(rid,e.value)
                        ui.notify('控除区分を保存しました')
                    choice.on_value_change(review)
        extra={}
        with ui.expansion('重複を避ける調整',icon='tune').classes('w-full'):
            ui.label('既に経費に入っている利息・減価償却は追加しません。元金返済は月次費用の借入返済へ。').classes('text-sm')
            for key,label in [('interest','経費に未計上の利息'),('depreciation','経費に未計上の減価償却'),('tax_payments_in_expenses','経費に含めた消費税・法人税の納付額（重複分の戻し）')]:
                extra[key]=ui.number(label,value=saved.get(key,0),min=0).classes('w-full').props('outlined')
            ui.label('税金の納付を一般経費・その他管理費にも入力した場合、その支出を重ねて引かないための戻しです。対象税金以外の経費は含めません。').classes('text-xs')
        def save():
            if not require_permission('future_dashboard','/mirai-kessan/input'): return
            try:
                proposed=dict(saved,corporate_tax_amount=actual.value,expenses={k:dict(rate=r.value,status=s.value,tax_amount=t.value) for k,(r,s,t,a) in specs.items()},**{k:v.value for k,v in extra.items()})
                cleaned, tax_rate=validate_tax_settings(proposed,rate.value)
                for key,(r,s,t,amount) in specs.items():
                    if t.value is not None and t.value>amount: raise ValueError(LABELS[key]+'の税額が経費額を超えています')
                raw.setdefault('business_tax_settings',{})[month]=cleaned
                raw.setdefault('finance_tax_policy',{})['corporate_rate']=tax_rate
                financials._data_manager.save()
            except (ValueError,TypeError) as error:
                ui.notify(str(error),type='negative');return
            ui.navigate.to('/mirai-kessan/taxes?month='+month)
        ui.button('設定を保存',on_click=save).classes('w-full')
        ui.label('管理用の概算です。申告書の端数処理、繰越控除、均等割などは確定税額で調整してください。').classes('text-xs')
