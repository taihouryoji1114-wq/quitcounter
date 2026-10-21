"""Scenario estimates: retained earnings and repayment-adjusted surplus are separate."""
from calendar import monthrange
from datetime import date
from math import isfinite
from statistics import mean
from core.consumption_tax import CORPORATE_TAX_RATE


def fiscal_year(day):
    return day.year + (day.month >= 10)


def validate_settings(settings):
    result = dict(settings, corporate_tax_rate=CORPORATE_TAX_RATE)
    for key in ('corporate_tax_rate', 'sales_growth', 'cost_growth', 'interest',
                'depreciation', 'investment', 'dividend', 'extra_input_tax',
                'opening_retained', 'opening_surplus', 'payroll', 'fixed', 'principal'):
        value = result.get(key)
        if value is None or value == '':
            result[key] = None
            continue
        value = float(value)
        if not isfinite(value):
            raise ValueError('有限の数値を入力してください')
        if key == 'corporate_tax_rate' and not 0 <= value <= 100:
            raise ValueError('税率は0〜100％で入力してください')
        if key in ('sales_growth', 'cost_growth') and not -99 <= value <= 100:
            raise ValueError('年間変化率は−99〜100％で入力してください')
        if key not in ('opening_retained', 'opening_surplus', 'sales_growth', 'cost_growth') and value < 0:
            raise ValueError('金額は0円以上で入力してください')
        result[key] = value
    end = result.get('repayment_end', '') or ''
    if end:
        date.fromisoformat(end + '-01')
    result['repayment_end'] = end
    return result


def accumulate(rows, tax_rate, opening_retained=None, opening_surplus=None):
    """Tax on positive fiscal-year profit; no invented loss carryforward/flat tax.

    Operating figures are tax-inclusive. Subtract the estimated consumption-tax
    reserve once, then interest/depreciation to get estimated pre-tax earnings.
    Depreciation is added back ONLY to the surplus, principal ONLY subtracted there.
    """
    if tax_rate is None:
        return []
    years = {}
    for row in rows:
        year = fiscal_year(date.fromisoformat(row['month'] + '-01'))
        group = years.setdefault(year, dict(year=year, pretax=0, principal=0,
                                            depreciation=0, investment=0, dividend=0, months=0, consumption_tax=0))
        group['consumption_tax'] += row['consumption_tax']
        group['pretax'] += row['operating'] - row['consumption_tax'] - row['interest'] - row['depreciation']
        for key in ('principal', 'depreciation', 'investment', 'dividend'):
            group[key] += row[key]
        group['months'] += 1
    retained = surplus = 0
    output = []
    for year, group in sorted(years.items()):
        corporate_tax = max(0, group['pretax']) * tax_rate / 100
        net = group['pretax'] - corporate_tax
        earnings = net - group['dividend']
        remaining = earnings + group['depreciation'] - group['principal'] - group['investment'] - max(0, -group['consumption_tax'])
        retained += earnings
        surplus += remaining
        output.append(dict(group, tax=round(corporate_tax), net=round(net),
                           retained_delta=round(earnings), surplus_delta=round(remaining),
                           retained_growth=round(retained), surplus_growth=round(surplus),
                           retained_balance=None if opening_retained is None else round(opening_retained + retained),
                           surplus_balance=None if opening_surplus is None else round(opening_surplus + surplus)))
    return output


def project(base, records, settings, as_of, end_year, input_fraction):
    config = validate_settings(settings)
    first_year = fiscal_year(as_of)
    if not first_year <= end_year <= first_year + 100:
        raise ValueError('予測年は今期から100年後以内で指定してください')
    payroll = config.get('payroll') if config.get('payroll') is not None else base['projected_personnel']
    fixed = config.get('fixed') if config.get('fixed') is not None else base['other_fixed']
    required = (base['sales'], base['projected_cost'], base['projected_fees'], payroll, fixed, input_fraction, config.get('corporate_tax_rate'))
    if any(v is None for v in required) or base['sales'] <= 0:
        return {'years': [], 'rows': [], 'seasonal_missing': [], 'message': '売上・原価・人件費の実績を確認してください。人件費は設定で補えます。法人税等は30％固定です。'}
    cost_ratio = base['projected_cost'] / base['sales']
    fee_ratio = base['projected_fees'] / base['sales']
    start = as_of.year * 12 + as_of.month - 1
    end = end_year * 12 + 8
    # Same-calendar-month averages use the latest completed recorded year.
    history = {}
    for record in records:
        day = date.fromisoformat(record['date'])
        if day < as_of.replace(day=1) and record.get('amount') is not None:
            history.setdefault((day.year, day.month), {})[day] = record['amount']
    seasonal = {}
    for (year, month), values in sorted(history.items()):
        if len(values) >= 14:
            seasonal[month] = mean(values.values())
    baseline_daily = base['sales'] / monthrange(as_of.year, as_of.month)[1]
    rows = []
    missing = set()
    principal = config.get('principal') if config.get('principal') is not None else base.get('principal', 0)
    for index in range(start, end + 1):
        year, month = index // 12, index % 12 + 1
        key = f'{year:04d}-{month:02d}'
        elapsed = (index-start) / 12
        sales_factor = (1 + (config.get('sales_growth') or 0) / 100) ** elapsed
        cost_factor = (1 + (config.get('cost_growth') or 0) / 100) ** elapsed
        if index == start:
            sales = base['sales']
        else:
            if month not in seasonal:
                missing.add(month)
            sales = seasonal.get(month, baseline_daily) * monthrange(year, month)[1] * sales_factor
        cost = sales * cost_ratio
        fees = sales * fee_ratio
        operating = sales-cost-fees-(payroll+fixed)*cost_factor
        credit = cost*input_fraction + fees*base.get('fee_input_fraction',0) + base.get('fixed_input_tax', 0)*cost_factor + (config.get('extra_input_tax') or 0)
        if index == start and base.get('current_input_tax') is not None:
            credit = base['current_input_tax'] + (config.get('extra_input_tax') or 0)
        consumption_tax = sales*10/110-credit
        repayment = 0 if config['repayment_end'] and key > config['repayment_end'] else principal
        rows.append(dict(month=key, sales=round(sales), operating=operating,
                         consumption_tax=consumption_tax, principal=repayment,
                         interest=0 if config['repayment_end'] and key > config['repayment_end'] else (config.get('interest') or 0),
                         depreciation=config.get('depreciation') or 0,
                         investment=config.get('investment') or 0,
                         dividend=config.get('dividend') or 0))
    years = accumulate(rows, config['corporate_tax_rate'], config.get('opening_retained'), config.get('opening_surplus'))
    return {'years': years, 'rows': rows, 'seasonal_missing': sorted(missing), 'message': ''}


def load_projection(settings, as_of, end_year):
    from core.finance_outlook import month_outlook
    from core.financials import financials
    from core.purchases import purchases
    month = as_of.strftime('%Y-%m')
    base = month_outlook(month, as_of)
    base['principal'] = financials.get_monthly_operations(month)['loan_payment']
    from core.consumption_tax import forecast_credits
    credits=forecast_credits(financials,purchases,month,as_of,base['projected_cost'],base['projected_fees'])
    base['fixed_input_tax']=credits['fixed_credit']
    base['fee_input_fraction']=credits['fee_fraction']
    base['current_input_tax']=credits['current_credit']
    effective_settings = dict(settings)
    extra_unreviewed=bool(effective_settings.get("extra_input_tax")) and not settings.get("extra_credit_reviewed")
    if extra_unreviewed:
        effective_settings["extra_input_tax"]=0
    raw=financials._data_manager.data
    effective_settings['corporate_tax_rate']=CORPORATE_TAX_RATE
    month_settings=raw.get('business_tax_settings',{}).get(month,{})
    for key in ('interest','depreciation'):
        if effective_settings.get(key) is None:
            effective_settings[key]=month_settings.get(key,0)
    stale_opening = settings.get('opening_month') != month and any(settings.get(k) is not None for k in ('opening_retained', 'opening_surplus'))
    if stale_opening:
        effective_settings.update(opening_retained=None, opening_surplus=None)
    result = project(base, financials.sales_records(), effective_settings, as_of, end_year,
                     credits['cost_fraction'])
    result['opening_stale'] = stale_opening
    result['basis_messages'] = list(base['messages'])
    if extra_unreviewed:
        result['basis_messages'].append('以前の追加控除は税設定との重複確認が必要です。予測の前提で確認するまで加算しません。')
    if credits['issues']:
        result['basis_messages'].append('月次経費の税区分に未設定項目があります。仕入の消費税は自動控除済みです。')
    result['basis_messages'].append('法人税等は各期の利益のプラス分×30％固定です。')
    return result
