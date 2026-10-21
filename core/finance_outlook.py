"""Management estimates using explicit cost assumptions, not final accounts."""
from calendar import monthrange
from datetime import date, timedelta
from core.clock import today_jst
from core.data import data
from core.financials import financials
from core.purchases import purchases
from core.staffing import staffing
from core.financial_report_data import build_financial_report
from core.landing_forecast import monthly_forecast


def calculate_outlook(sales, cost, fees, payroll, other_fixed, fees_variable=True):
    valid = all(v is not None for v in (sales, cost, fees, payroll, other_fixed)) and sales > 0
    if not valid:
        return dict(cost_rate=cost/sales if sales and cost is not None else None, personnel_rate=payroll/sales if sales and payroll is not None else None, labor_rate=payroll/(sales-cost) if sales and cost is not None and payroll is not None and sales>cost else None, break_even=None, profit=None, margin=None)
    gross = sales-cost
    variable_rate = (cost + (fees if fees_variable else 0))/sales
    fixed = payroll + other_fixed + (0 if fees_variable else fees)
    break_even = fixed/(1-variable_rate) if variable_rate < 1 else None
    return {'cost_rate':cost/sales, 'personnel_rate':payroll/sales,
            'labor_rate':payroll/gross if gross > 0 else None,
            'break_even':round(break_even) if break_even is not None else None,
            'profit':round(sales-cost-fees-payroll-other_fixed),
            'margin':round(sales-break_even) if break_even is not None else None}


def month_outlook(month, as_of=None):
    today = as_of or today_jst()
    y,m=map(int,month.split('-'))
    days=monthrange(y,m)[1]
    end=f'{month}-{days:02d}'
    past=month<today.strftime('%Y-%m')
    future=month>today.strftime('%Y-%m')
    config=data.data.get('finance_outlook_settings',{})
    closures=data.data.get('landing_forecast_settings',{}).get('closed_dates',[])
    forecast=monthly_forecast(financials.sales_records(),month,today,closed_dates=closures)
    report=build_financial_report(month+'-01',end if past or future else today.isoformat())
    messages=[]
    if forecast['missing']:messages.append('売上未入力日は推定を含みます。')
    history_start=(today-timedelta(days=84)).isoformat()
    history_end=(today-timedelta(days=1)).isoformat()
    history=build_financial_report(history_start,history_end)
    manual=config.get('cost_rate')
    rate=manual/100 if manual is not None else history['cost_total']/history['sales_total'] if history['sales_total']>0 and history['cost_total']>0 else None
    basis=f'設定した原価率 {manual:g}％' if manual is not None else '直近12週の仕入額÷売上（棚卸なし）'
    landing=forecast['landing']
    remaining=max(0,landing-report['sales_total']) if landing is not None else None
    cost=report['cost_total'] if past else report['cost_total']+remaining*rate if remaining is not None and rate is not None else None
    fee_rate=history['payment_fees']/history['sales_total'] if history['sales_total']>0 else None
    fees=report['payment_fees'] if past else report['payment_fees']+remaining*fee_rate if remaining is not None and fee_rate is not None else None
    staff=staffing.month_cost_summary(month,today)
    payroll=staff['company_cost'] if past else staff['forecast_company_cost']
    coverage = staff['plan_coverage']
    if coverage['board_cells']:
        messages.append(f"公開済みシフトボード {coverage['board_cells']}件を人件費予測に反映。")
    if coverage['learned_cells']:
        messages.append(f"時刻のない勤務 {coverage['learned_cells']}件は過去の勤務時間で推定。休憩時間も過去実績を使用。")
    elif coverage['board_cells']:
        messages.append('シフトボードの時刻を使用。休憩時間は過去実績から推定。')
    missing = coverage['missing_by_staff']
    missing_count = sum(len(v) for v in missing.values())
    payroll_provisional = bool(coverage['unknown_wages'] or missing_count or coverage['learned_cells'])
    if missing_count:
        messages.append(f'未公開・未入力・時間不明の勤務枠が {missing_count}人日あります。将来分は公開済みの読み取れる勤務のみを集計した参考値です。')
    if coverage['unknown_wages']:
        messages.append(f"時給未登録の勤務 {coverage['unknown_wages']}件は金額未反映です。時給を登録すると再計算します。")
    messages.append('人件費＝今日までの入力済みバイト実績＋社員等の登録月給全額＋明日以降の公開済みシフト。交通費・会社負担保険を含みます。')
    operations=financials.get_monthly_operations(month)
    advertising=financials.get_monthly_advertising(month)['total']
    overhead=operations['rent']+operations['utilities']+operations['other_admin']+advertising
    if past:
        overhead=report['operating_expenses']-report['personnel']-report['payment_fees']
    else:
        # Supplies/general expenses have no explicit forward commitments; use
        # the observed daily spend, labelled as a projection.
        elapsed=0 if future else today.day
        observed=report['supply_total']+report['expense_total']
        overhead+=observed*days/elapsed if elapsed else (history['supply_total']+history['expense_total'])/84*days
        messages.append('営業用品・一般経費は日平均を月末まで延長。家賃等は登録月額を使用。')
    if not any(operations.values()) and not advertising:
        messages.append('月次費用が未登録または0円です。費用を入力するまで参考値として確認してください。')
    if rate is None and not past:messages.append('原価の実績不足です。仕入れを入力するか想定原価率を設定してください。')
    values=calculate_outlook(landing,cost,fees,payroll,overhead,config.get('fees_variable',True))
    from core.consumption_tax import forecast_credits
    credits=forecast_credits(financials,purchases,month,today,cost,fees)
    cover=tax_and_repayment_threshold(landing,cost,fees,payroll,overhead,
            operations['loan_payment'],credits['cost_fraction'],credits['fixed_credit'],config.get('fees_variable',True),credits['fee_fraction'])
    messages.append('税・返済線は法人税前の目安。原価・決済手数料・その他経費の控除を別々に計算し、仕入の消費税は自動控除し、月次経費は税設定を使用します。')
    if credits['issues']: messages.append('控除未確認の経費があります。税設定で確認すると予測に反映します。')
    return dict(values, payroll_issues=coverage['issues'], payroll_estimated=coverage['estimated'],
                payroll_breakdown={'入力済みバイト給与':staff['groups']['hourly']['gross_wages'],
                                   '社員等の月給':sum(staffing.monthly_salaries().values()),
                                   '明日以降のバイト給与':staff['planned_hourly_gross'],
                                   '交通費・会社負担保険':staff['forecast_transportation']+staff['forecast_employer_insurance']},
                payroll_provisional=payroll_provisional, tax_repayment_line=cover, month=month, forecast=forecast, report=report, sales=landing,
                projected_cost=round(cost) if cost is not None else None,
                projected_personnel=round(payroll) if payroll is not None else None,
                projected_fees=round(fees) if fees is not None else None,
                other_fixed=round(overhead), basis=basis, messages=messages,
                fees_variable=config.get('fees_variable',True))


def tax_and_repayment_threshold(sales, cost, fees, payroll, fixed, repayment,
                                input_tax_fraction=0, fixed_input_tax=0, fees_variable=True, fee_input_fraction=0):
    if not sales or any(v is None for v in (cost, fees, payroll, fixed)):
        return None
    variable=(cost+(fees if fees_variable else 0))/sales
    total_fixed=payroll+fixed+(0 if fees_variable else fees)+repayment
    margin=1-variable
    if margin<=0:return None
    before=total_fixed/margin
    net_tax_rate=10/110-cost/sales*input_tax_fraction-fees/sales*fee_input_fraction
    if before*net_tax_rate<=fixed_input_tax:return round(before)
    if margin-net_tax_rate<=0:return None
    return round(max(0,(total_fixed-fixed_input_tax)/(margin-net_tax_rate)))
