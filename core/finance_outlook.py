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
    # Scheduled dates (including an explicit zero-shift day) are not extrapolated.
    plans=data.data.get('business_staff_shift_plans',{})
    unplanned=[date(y,m,d) for d in range(1,days+1) if date(y,m,d)>today and
               f'{month}-{d:02d}' not in plans and f'{month}-{d:02d}' not in closures]
    if unplanned:
        elapsed=0 if future else today.day
        hourly=staff['groups']['hourly']['company_cost']
        if elapsed and hourly>0:
            payroll+=round(hourly/elapsed*len(unplanned))
            messages.append(f'予定シフト未登録 {len(unplanned)}日分のアルバイト費用を今月の1日平均で補完。')
        else:
            payroll=None
            messages.append('予定シフトとアルバイト実績が不足しています。人件費見込・損益分岐点は保留。')
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
    # Approximate the input-tax share from the last three completed months.
    # This is a management reserve, not a tax return or cash balance.
    index=today.year*12+today.month-1
    tax_months=[f'{i//12:04d}-{i%12+1:02d}' for i in range(index-3,index)]
    purchase_total=sum(purchases.monthly_total(v) for v in tax_months)
    input_tax=sum(purchases.monthly_tax_summary(v)['input_tax'] for v in tax_months)
    input_fraction=input_tax/purchase_total if purchase_total else None
    fixed_input_tax=financials.get_monthly_advertising(month)['input_tax']
    cover=None
    if input_fraction is not None:
        cover=tax_and_repayment_threshold(landing,cost,fees,payroll,overhead,
                operations['loan_payment'],input_fraction,fixed_input_tax,config.get('fees_variable',True))
    messages.append('税・返済目安は売上10％、仕入控除は直近3か月の入力税額比率＋登録広告費で概算。家賃等の未登録控除・法人税・利息別入力は含みません。')
    return dict(values, tax_repayment_line=cover, month=month, forecast=forecast, report=report, sales=landing,
                projected_cost=round(cost) if cost is not None else None,
                projected_personnel=round(payroll) if payroll is not None else None,
                projected_fees=round(fees) if fees is not None else None,
                other_fixed=round(overhead), basis=basis, messages=messages,
                fees_variable=config.get('fees_variable',True))


def tax_and_repayment_threshold(sales, cost, fees, payroll, fixed, repayment,
                                input_tax_fraction=0, fixed_input_tax=0, fees_variable=True):
    if not sales or any(v is None for v in (cost, fees, payroll, fixed)):
        return None
    variable=(cost+(fees if fees_variable else 0))/sales
    total_fixed=payroll+fixed+(0 if fees_variable else fees)+repayment
    margin=1-variable
    if margin<=0:return None
    before=total_fixed/margin
    net_tax_rate=10/110-cost/sales*input_tax_fraction
    if before*net_tax_rate<=fixed_input_tax:return round(before)
    if margin-net_tax_rate<=0:return None
    return round(max(0,(total_fixed-fixed_input_tax)/(margin-net_tax_rate)))
