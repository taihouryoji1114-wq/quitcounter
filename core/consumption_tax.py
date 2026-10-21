"""Shared tax-inclusive management calculations, separate from filing amounts."""
from calendar import monthrange
from datetime import date, timedelta
from math import isfinite

EXPENSE_KEYS = ('rent', 'utilities', 'other_admin', 'tabelog', 'hotpepper', 'other', 'payment_fees')


def transition_rate(day):
    day = date.fromisoformat(day)
    if day < date(2023,10,1): return 1
    if day < date(2026,10,1): return .8
    if day < date(2028,10,1): return .7
    if day < date(2030,10,1): return .5
    if day < date(2031,10,1): return .3
    return 0


def purchase_credit(record):
    """Unconfirmed invoice/legacy tax breakdown never silently counts as confirmed."""
    breakdown = record.get('tax_breakdown')
    if breakdown:
        tax = sum(int(breakdown.get(k,0)) for k in ('tax_1','tax_8','tax_10'))
    else:
        rate = 8 if record.get('kind','cost') == 'cost' else 10
        tax = int(record.get('total',0))*rate//(100+rate)
    status = record.get('invoice_status','unknown')
    if status == 'registered':
        return dict(credit=tax, potential=0, estimated=not bool(breakdown))
    if status == 'unregistered' and record.get('transition_eligible'):
        return dict(credit=int(tax*transition_rate(record['date'])), potential=0, estimated=not bool(breakdown))
    if status == 'unregistered' and record.get('credit_reviewed'):
        return dict(credit=0,potential=0,estimated=False)
    return dict(credit=0,potential=tax,estimated=not bool(breakdown))


def expense_credit(amount, spec, day):
    if not amount: return dict(credit=0,potential=0)
    if spec.get('rate') == 'exempt': return dict(credit=0,potential=0)
    rate = spec.get('rate')
    if rate not in ('8','10'): return dict(credit=0,potential=amount*10//110)
    tax = spec.get('tax_amount')
    tax = min(int(amount), int(tax)) if tax is not None else int(amount)*int(rate)//(100+int(rate))
    if spec.get('status') == 'registered': return dict(credit=tax,potential=0)
    if spec.get('status') == 'transition': return dict(credit=int(tax*transition_rate(day)),potential=0)
    if spec.get('status') == 'none': return dict(credit=0,potential=0)
    return dict(credit=0,potential=tax)


def period_tax(financials, purchases, start, end):
    start_day,end_day = date.fromisoformat(start),date.fromisoformat(end)
    output = sum(int(r.get('amount',0)) for r in financials.sales_records() if start<=r['date']<=end)*10//110
    credit = potential = 0
    issues = []
    for r in purchases.records():
        if not start<=r['date']<=end: continue
        info = purchase_credit(r)
        credit += info['credit']; potential += info['potential']
        if info['potential'] or info['estimated']:
            issues.append(dict(date=r['date'],label=r.get('supplier','仕入'),reason='税額・控除条件の確認',amount=info['potential']))
    cursor = start_day.replace(day=1)
    raw = financials._data_manager.data
    expenses_credit = 0
    while cursor<=end_day:
        month=cursor.strftime('%Y-%m');last=monthrange(cursor.year,cursor.month)[1]
        days=(min(end_day,cursor.replace(day=last))-max(start_day,cursor)).days+1
        ratio=days/last
        operations=financials.get_monthly_operations(month)
        ads=financials.get_monthly_advertising(month)
        fees=financials.monthly_payment_summary(month)['total_fees']
        settings=raw.get('business_tax_settings',{}).get(month,{})
        for key in EXPENSE_KEYS:
            amount=fees if key=='payment_fees' else ads[key] if key in ('tabelog','hotpepper','other') else operations[key]
            allocation = ratio
            if key == 'payment_fees':
                selected = [r for r in financials.sales_records(month=month) if start <= r['date'] <= end]
                rates = financials.get_payment_fee_rates()
                selected_fees = sum(round(sum(int(r.get(field,0)) for r in selected)*rates.get(method,0)/100) for field,method in (('credit_sales','credit'),('paypay_sales','paypay'),('electronic_money_sales','electronic_money'),('travel_agency_sales','travel_agency')))
                allocation = selected_fees / fees if fees else 0
            info=expense_credit(amount,settings.get('expenses',{}).get(key,{}),cursor.isoformat())
            part=round(info['credit']*allocation)
            credit+=part;expenses_credit+=part;potential+=round(info['potential']*allocation)
            if info['potential']:
                issues.append(dict(date=month,label=key,reason='経費の税区分・控除条件が未確認',amount=round(info['potential']*allocation)))
        cursor=(cursor.replace(day=28)+timedelta(days=4)).replace(day=1)
    return dict(output_tax=output,input_tax=credit,net_tax=output-credit,
                payable=max(0,output-credit),credit_balance=max(0,credit-output),
                unconfirmed_credit=potential,issues=issues,expense_input_tax=expenses_credit)


def settlement(financials, purchases, report):
    tax=period_tax(financials,purchases,report['start'],report['end'])
    raw=financials._data_manager.data
    start=date.fromisoformat(report['start']);end=date.fromisoformat(report['end'])
    cursor=start.replace(day=1)
    principal=interest=depreciation=adjustment=corporate_actual=0
    all_corporate=True
    confirmed_pretax=0
    while cursor<=end:
        month=cursor.strftime('%Y-%m');last=monthrange(cursor.year,cursor.month)[1]
        ratio=((min(end,cursor.replace(day=last))-max(start,cursor)).days+1)/last
        settings=raw.get('business_tax_settings',{}).get(month,{})
        principal+=financials.get_monthly_operations(month)['loan_payment']*ratio
        interest+=settings.get('interest',0)*ratio
        depreciation+=settings.get('depreciation',0)*ratio
        adjustment+=settings.get('tax_payments_in_expenses',0)*ratio
        amount=settings.get('corporate_tax_amount')
        if amount is None: all_corporate=False
        else:
            corporate_actual+=amount*ratio
            part=next((r for r in report.get('month_reports',[]) if r['start'][:7]==month),report)
            part_tax=period_tax(financials,purchases,part['start'],part['end'])['net_tax']
            confirmed_pretax+=part['operating_profit']-part_tax+(settings.get('tax_payments_in_expenses',0)-settings.get('interest',0)-settings.get('depreciation',0))*ratio
        cursor=(cursor.replace(day=28)+timedelta(days=4)).replace(day=1)
    pretax=round(report['operating_profit']+adjustment-tax['net_tax']-interest-depreciation)
    rate=raw.get('finance_tax_policy',{}).get('corporate_rate')
    corporate=round(corporate_actual) if all_corporate else round(corporate_actual+max(0,pretax-confirmed_pretax)*rate/100) if rate is not None else None
    net=pretax-(corporate or 0)
    # A tax credit balance is not money in the bank: don't count it as spendable.
    surplus=round(net+depreciation-principal-tax['credit_balance'])
    return dict(tax=tax,pretax_profit=pretax,corporate_tax=corporate,
                corporate_estimated=not all_corporate,net_profit=net,
                corporate_basis='期間内の登録税額' if all_corporate else '登録税額＋未登録月の利益×概算税率' if rate is not None else '未設定',
                net_label='税引後利益（概算）' if corporate is not None else '法人税前利益',
                surplus_label='税・返済後（概算）' if corporate is not None else '返済後（法人税前）',
                post_repayment_profit=surplus,loan_payment=round(principal),
                interest=round(interest),depreciation=round(depreciation),tax_expense_adjustment=round(adjustment),
                provisional=corporate is None or bool(tax['issues']))


def validate_tax_settings(settings, rate):
    from copy import deepcopy
    result=deepcopy(settings)
    def number(value, optional=False):
        if optional and value in ('',None):return None
        v=float(value or 0)
        if not isfinite(v) or v<0:raise ValueError('金額は0以上で入力してください')
        return round(v)
    for key in ('interest','depreciation','tax_payments_in_expenses'):
        result[key]=number(result.get(key))
    result['corporate_tax_amount']=number(result.get('corporate_tax_amount'),True)
    for spec in result.get('expenses',{}).values():
        if spec.get('rate') not in ('unknown','exempt','8','10') or spec.get('status') not in ('unknown','registered','transition','none'):
            raise ValueError('税区分を確認してください')
        spec['tax_amount']=number(spec.get('tax_amount'),True)
    rate=None if rate in ('',None) else float(rate)
    if rate is not None and (not isfinite(rate) or not 0<=rate<=100):raise ValueError('税率は0〜100％です')
    return result,rate


def forecast_credits(financials, purchases, month, as_of, projected_cost, projected_fees):
    """Keep food, other purchases and monthly expenses on their own bases."""
    y,m=map(int,month.split('-'));days=monthrange(y,m)[1]
    end=f'{month}-{days:02d}'
    current=as_of.strftime('%Y-%m')==month
    cutoff=as_of.isoformat() if current else end
    index=y*12+m-1
    first=f'{(index-3)//12:04d}-{(index-3)%12+1:02d}-01'
    costs=[r for r in purchases.records() if first<=r['date']<=cutoff and r.get('kind','cost')=='cost']
    amount=sum(r['total'] for r in costs)
    fraction=sum(purchase_credit(r)['credit'] for r in costs)/amount if amount else 0
    actual_cost_rows=[r for r in purchases.records(month=month) if r['date']<=cutoff and r.get('kind','cost')=='cost']
    actual_amount=sum(r['total'] for r in actual_cost_rows)
    actual_credit=sum(purchase_credit(r)['credit'] for r in actual_cost_rows)
    other=[r for r in purchases.records(month=month) if r['date']<=cutoff and r.get('kind','cost')!='cost']
    other_credit=sum(purchase_credit(r)['credit'] for r in other)*(days/max(1,as_of.day) if current else 1)
    full=period_tax(financials,purchases,month+'-01',end)
    settings=financials._data_manager.data.get('business_tax_settings',{}).get(month,{})
    fees=financials.monthly_payment_summary(month)['total_fees']
    fee_credit=expense_credit(fees,settings.get('expenses',{}).get('payment_fees',{}),month+'-01')['credit']
    fee_fraction=fee_credit/fees if fees else 0
    fixed=full['expense_input_tax']-fee_credit+other_credit
    projected=actual_credit+max(0,(projected_cost or 0)-actual_amount)*fraction+fixed+(projected_fees or 0)*fee_fraction
    return dict(cost_fraction=fraction,fixed_credit=fixed,fee_fraction=fee_fraction,current_credit=projected,
                issues=full['issues'])
