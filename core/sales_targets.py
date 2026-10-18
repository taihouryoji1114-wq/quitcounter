"""Saved sales targets are plans, never actual sales or revised forecasts."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
from math import ceil, isfinite
from uuid import uuid4
from core.clock import now_jst
from core.landing_forecast import monthly_forecast


def allocate(total, weights):
    """Largest remainder allocation keeps the yen total exact."""
    if not weights:
        return []
    weights = [max(0, w) for w in weights]
    if not sum(weights):
        weights = [1] * len(weights)
    raw = [total * w / sum(weights) for w in weights]
    amounts = [int(v) for v in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - amounts[i], reverse=True)[:total-sum(amounts)]:
        amounts[i] += 1
    return amounts


def build_target_plan(records, month, target, as_of, closed_dates=()):
    target = float(target)
    if not isfinite(target) or target <= 0 or target != int(target):
        raise ValueError('月間売上目標は1円以上の整数で入力してください')
    year, number = map(int, month.split('-'))
    monthrange(year, number)  # Validate the month before any allocations.
    if month < as_of.strftime('%Y-%m'):
        raise ValueError('目標を作成できるのは今月以降です')
    forecast = monthly_forecast(records, month, as_of, closed_dates=closed_dates)
    if forecast['missing'] and forecast['imputed'] is None:
        raise ValueError('過去の未入力日を補完する実績がありません。売上を入力してから作成してください')
    baseline = forecast['actual'] + (forecast['imputed'] or 0)
    remaining = max(0, int(target) - baseline)
    estimates = forecast['estimates']
    if remaining and not estimates:
        raise ValueError('残りの営業日がありません。休業日または対象月を確認してください')
    weights = [e['sales'] or 0 for e in estimates]
    amounts = allocate(remaining, weights)
    history = [r for r in records if r.get('amount') is not None and
               0 < (as_of-date.fromisoformat(r['date'])).days <= 84 and
               r.get('lunch_sales') is not None and r.get('dinner_sales') is not None]
    rows = []
    for e, amount in zip(estimates, amounts):
        day = date.fromisoformat(e['date'])
        weekday = [r for r in history if date.fromisoformat(r['date']).weekday() == day.weekday()]
        pool = weekday if len(weekday) >= 2 else history
        lunch = sum(float(r['lunch_sales']) for r in pool)
        dinner = sum(float(r['dinner_sales']) for r in pool)
        split = allocate(amount, [lunch, dinner])
        customers = []
        for session, value in zip(('lunch', 'dinner'), split):
            valid = [r for r in pool if (r.get(session+'_customers') or 0) > 0]
            revenue = sum(float(r[session+'_sales']) for r in valid)
            count = sum(float(r[session+'_customers']) for r in valid)
            customers.append(ceil(value / (revenue/count)) if revenue > 0 and count > 0 else None)
        rows.append({'date':e['date'], 'target':amount, 'lunch':split[0], 'dinner':split[1],
                     'lunch_customers':customers[0], 'dinner_customers':customers[1],
                     'forecast':e['sales'], 'basis':e['basis'],
                     'split_basis':'同曜日の売上比' if pool is weekday and lunch+dinner else '直近12週の売上比' if lunch+dinner else '実績不足のため半分ずつ'})
    return {'month':month,'as_of':as_of.isoformat(),'monthly_target':int(target),
            'actual':forecast['actual'],'imputed':forecast['imputed'] or 0,
            'missing':forecast['missing'],'remaining':remaining,'rows':rows,
            'closed_dates':list(closed_dates),'equal_allocation':not any(weights)}


def save_target_plan(manager, plan):
    saved = deepcopy(plan)
    saved['id'] = uuid4().hex
    saved['created_at'] = now_jst().isoformat()
    manager.data.setdefault('sales_target_plans', {})[saved['id']] = saved
    manager.save()
    return saved


def plan_results(plan, records, as_of):
    actual = {r['date']:r['amount'] for r in records if r.get('amount') is not None and r['date'] < as_of.isoformat()}
    rows = []
    for row in plan['rows']:
        value = actual.get(row['date'])
        rows.append(dict(row, actual=value, difference=None if value is None else value-row['target']))
    return rows
