"""Transparent monthly estimates; no missing day is treated as zero sales."""
from calendar import monthrange
from datetime import date, timedelta
from statistics import mean
from core.clock import now_jst


def monthly_forecast(records, month, as_of, closed_weekdays=(), closed_dates=()):
    year, number = map(int, month.split('-'))
    days = [date(year, number, d) for d in range(1, monthrange(year, number)[1]+1)]
    # Today can still be in progress. Only prior days enter the forecast's actuals.
    history = {}
    for r in records:
        day = date.fromisoformat(r['date'])
        if day >= as_of or r.get('amount') is None:
            continue
        history[day] = r
    actual = {d: history[d] for d in days if d in history}
    open_days = [d for d in days if d.weekday() not in closed_weekdays and d.isoformat() not in closed_dates]
    missing = [d.isoformat() for d in open_days if d < as_of and d not in actual]
    future = [d for d in open_days if d >= as_of]
    recent = [(d,r) for d,r in history.items() if 0 < (as_of-d).days <= 84]
    estimates = []
    for target in future:
        seasonal = [(d,r) for d,r in history.items() if d.year == year-1 and d.month == number and d.weekday() == target.weekday()]
        weekday = [(d,r) for d,r in recent if d.weekday() == target.weekday()]
        pool = seasonal if len(seasonal) >= 2 else weekday if len(weekday) >= 2 else recent
        method = '前年同月・同曜日' if pool is seasonal else '直近12週・同曜日' if pool is weekday else '直近12週平均（暫定）'
        if not pool:
            estimates.append({'date':target.isoformat(),'sales':None,'customers':None,'basis':'実績不足','samples':0})
            continue
        amounts = [float(r['amount']) for _,r in pool]
        customers = [float(r['lunch_customers'])+float(r['dinner_customers']) for _,r in pool
                     if r.get('lunch_customers') is not None and r.get('dinner_customers') is not None]
        value=mean(amounts)
        spread=mean(abs(v-value) for v in amounts) if len(amounts)>1 else value*.3
        estimates.append({'date':target.isoformat(),'sales':round(value),'customers':round(mean(customers),1) if customers else None,
                          'basis':method,'samples':len(pool),'low':round(max(0,value-spread)), 'high':round(value+spread)})
    total=sum(float(r['amount']) for r in actual.values())
    known=all(e['sales'] is not None for e in estimates)
    remaining=sum(e['sales'] for e in estimates) if known else None
    return {'month':month,'as_of':as_of.isoformat(),'actual':round(total),'actual_days':len(actual),
            'daily_average':round(total/len(actual)) if actual else None,'missing':missing,
            'remaining_days':len(future),'remaining':remaining,
            'landing':round(total+remaining) if known and not missing else None,
            'low':round(total+sum(e.get('low',0) for e in estimates)) if known and not missing else None,
            'high':round(total+sum(e.get('high',0) for e in estimates)) if known and not missing else None,
            'customers':round(sum(e['customers'] for e in estimates)) if all(e['customers'] is not None for e in estimates) else None,
            'estimates':estimates}


def simulate(forecast, sales_percent=0, price_change=0, variable_cost_percent=0, hourly_change=0, remaining_hours=0, salary_change=0, officer_change=0):
    if forecast['landing'] is None:
        raise ValueError('売上実績や営業日の設定を確認してから試算してください')
    if price_change and forecast['customers'] is None:
        raise ValueError('客数の記録が足りないため、客単価の試算はできません')
    if not 0 <= variable_cost_percent <= 100 or remaining_hours < 0 or sales_percent < -100:
        raise ValueError('割合と勤務時間を確認してください')
    delta=forecast['remaining']*sales_percent/100+(forecast['customers'] or 0)*price_change
    payroll=hourly_change*remaining_hours+salary_change+officer_change
    return {'sales':round(forecast['landing']+delta),'sales_delta':round(delta),
            'payroll_delta':round(payroll),'profit_delta':round(delta*(1-variable_cost_percent/100)-payroll)}


def save_snapshot(manager, forecast):
    """Preserve the original prediction; never rewrite it with later actuals."""
    from copy import deepcopy
    key=forecast['month']+'/'+forecast['as_of']
    records=manager.data.setdefault('landing_forecast_history',{})
    if key not in records:
        records[key]={'created_at':now_jst().isoformat(),'forecast':deepcopy(forecast)}
        manager.save()
    return records[key]
